"""
Paso 8 - Capa de visualización (Streamlit).

Arranque:   streamlit run app/app.py

Reglas del enunciado que respeta:
  * Cada gráfico sale de una de las consultas de sql/queries/ (escritas a mano).
  * Los filtros del usuario se envían a PostgreSQL como PARÁMETROS
    (cursor.execute(sql, params)), nunca concatenados al SQL -> sin inyección.
  * Python NO agrega, filtra ni transforma resultados: solo mete las filas
    devueltas en un DataFrame (como contenedor) y se las pasa al gráfico.
  * El usuario nunca escribe SQL; los controles solo permiten valores válidos
    y cualquier error de base de datos se muestra como mensaje, sin romper la app.

Diseño de los gráficos (skill "dataviz"):
  * Paleta categórica fija: azul, naranja, aqua. Cada provincia tiene SIEMPRE el
    mismo color, aunque un filtro oculte las otras (el color sigue a la entidad).
  * Una sola serie -> un solo color, sin leyenda. Rejilla y ejes discretos.
"""
import sys
from pathlib import Path

import pandas as pd          # SOLO como contenedor de filas para mostrar/graficar
import plotly.graph_objects as go
import plotly.express as px
import psycopg2
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from db import get_connection                                        # noqa: E402
from query_lib import load_queries, run_query, run_transaction_query  # noqa: E402

st.set_page_config(page_title="Airbnb Euskadi - Database analysis", layout="wide")

QUERIES = load_queries()
ROOM_TYPES = ["Entire home/apt", "Private room", "Hotel room", "Shared room"]

# ------------------------------------------------------------ estilo gráfico
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]          # slots 1-3 de la paleta de referencia
# Rampa secuencial azul (un solo tono, claro -> oscuro) para los quintiles de precio del mapa
PRICE_RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]
PROVINCE_COLOR = {"Guipúzcoa": SERIES[0], "Vizcaya": SERIES[1], "Álava": SERIES[2]}
INK, INK_2, INK_3, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#ffffff"

TEMPLATE = go.layout.Template(layout=dict(
    font=dict(family="Inter, Segoe UI, Helvetica, Arial, sans-serif", size=13, color=INK_2),
    paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
    colorway=SERIES,
    margin=dict(l=8, r=8, t=36, b=8),
    xaxis=dict(showgrid=False, linecolor=GRID, ticks="", zeroline=False, title_font_color=INK_2),
    yaxis=dict(gridcolor=GRID, gridwidth=1, linecolor=GRID, ticks="", zeroline=False, title_font_color=INK_2),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text="",
                font=dict(color=INK_2)),
    hoverlabel=dict(bgcolor=SURFACE, bordercolor=GRID, font=dict(color=INK, size=12)),
    barcornerradius=4,
    bargap=0.35,
))


def style(fig, height=420, horizontal=False):
    fig.update_layout(template=TEMPLATE, height=height, legend_title_text="")
    fig.update_traces(selector=dict(type="bar"), marker_line_color=SURFACE, marker_line_width=2)
    fig.update_traces(selector=dict(type="scatter", mode="lines"), line_width=2)
    if horizontal:
        fig.update_layout(xaxis=dict(showgrid=True, gridcolor=GRID), yaxis=dict(showgrid=False))
    return fig


CSS = """
<style>
  html, body, [class*="css"] { font-family: Inter, "Segoe UI", Helvetica, Arial, sans-serif; }
  .block-container { padding-top: 2.2rem; max-width: 1280px; }
  h1 { font-weight: 600; letter-spacing: -0.01em; font-size: 1.9rem !important; }
  h2, h3 { font-weight: 600; letter-spacing: -0.005em; }
  .subtitle { color: #52514e; font-size: 0.98rem; margin-top: -0.6rem; margin-bottom: 1.4rem; }
  .q-meta { color: #52514e; font-size: 0.88rem; margin: -0.4rem 0 0.8rem 0; }
  .q-meta b { color: #0b0b0b; font-weight: 600; }
  [data-testid="stMetric"] { border: 1px solid #e6e5e1; border-radius: 6px; padding: 0.8rem 1rem; background: #ffffff; }
  [data-testid="stMetricLabel"] p { color: #52514e; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.04em; }
  [data-testid="stMetricValue"] { font-weight: 600; }
  .stTabs [data-baseweb="tab"] { font-size: 0.95rem; padding: 0.6rem 1rem; }
  .footer { color: #8a8984; font-size: 0.8rem; margin-top: 3rem; border-top: 1px solid #e6e5e1; padding-top: 0.8rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ------------------------------------------------------------------- datos
@st.cache_resource
def connection():
    return get_connection()


def conn_ok():
    """Reabre la conexión si se ha cerrado (p. ej. reinicio de PostgreSQL)."""
    c = connection()
    if c.closed:
        st.cache_resource.clear()
        c = connection()
    return c


@st.cache_data(show_spinner="Querying the database...", ttl=600)
def fetch(qid: str, params: tuple) -> pd.DataFrame:
    cols, rows = run_query(conn_ok(), QUERIES[qid], dict(params))
    return pd.DataFrame(rows, columns=cols)


@st.cache_data(ttl=3600)
def lookup(sql: str) -> list:
    """Listas para los desplegables (también salen de SQL)."""
    c = conn_ok()
    with c.cursor() as cur:
        cur.execute(sql)
        out = [r[0] for r in cur.fetchall()]
    c.rollback()
    return out


def show(qid: str, **params):
    """Ejecuta la consulta qid con params y devuelve el DataFrame, o None si falla."""
    try:
        return fetch(qid, tuple(sorted(params.items())))
    except psycopg2.Error as e:
        st.error(f"Database error in {qid}: {e.pgerror or e}")
    except Exception as e:  # noqa: BLE001
        st.error(f"Unexpected error in {qid}: {e}")
    return None


def header(qid: str, title: str):
    q = QUERIES[qid]
    st.subheader(title)
    st.markdown(f"<div class='q-meta'><b>{q['id']}</b> &nbsp;·&nbsp; {q['question']} "
                f"&nbsp;·&nbsp; Author: {q['author']}</div>", unsafe_allow_html=True)


def sql_box(qid: str):
    q = QUERIES[qid]
    with st.expander(f"SQL and interpretation ({q['techniques']})"):
        st.code(q["sql"], language="sql")
        st.markdown(f"**Why it matters.** {q['why']}")


def empty(df) -> bool:
    if df is None:
        return True
    if df.empty:
        st.info("No rows match the current filters.")
        return True
    return False


def plot(fig):
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


# ------------------------------------------------------------ barra lateral
try:
    PROVINCES = lookup("SELECT name FROM airbnb.province ORDER BY name")
    MUNICIPALITIES = lookup("""SELECT m.name FROM airbnb.municipality m
                               WHERE EXISTS (SELECT 1 FROM airbnb.listing l WHERE l.municipality_id = m.municipality_id)
                               ORDER BY m.name""")
except Exception as e:  # noqa: BLE001
    st.error(f"Cannot connect to PostgreSQL. Check the .env file and that the database is loaded.\n\n{e}")
    st.stop()

st.sidebar.markdown("### Filters")
province = st.sidebar.selectbox("Province", ["All provinces"] + PROVINCES)
room = st.sidebar.selectbox("Room type", ["All room types"] + ROOM_TYPES)
P = None if province == "All provinces" else province
R = None if room == "All room types" else room
st.sidebar.caption("Filters are passed to PostgreSQL as bound query parameters. "
                   "Charts that do not depend on a filter ignore it.")

# ---------------------------------------------------------------- cabecera
st.title("Short-term rental market in the Basque Country")
st.markdown("<div class='subtitle'>Relational analysis of Inside Airbnb data for Euskadi "
            "(snapshot of 25 September 2026). All figures are computed in PostgreSQL.</div>",
            unsafe_allow_html=True)
try:
    c = conn_ok()
    with c.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*),
                   COUNT(DISTINCT l.host_id),
                   ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY l.price)::numeric, 0),
                   (SELECT COUNT(DISTINCT lr.review_id)
                      FROM airbnb.listing_review lr
                      JOIN airbnb.listing l2 ON l2.listing_id = lr.listing_id
                      JOIN airbnb.municipality m2 ON m2.municipality_id = l2.municipality_id
                      JOIN airbnb.province p2 ON p2.province_id = m2.province_id
                     WHERE (%(p)s IS NULL OR p2.name = %(p)s) AND (%(r)s IS NULL OR l2.room_type = %(r)s))
            FROM airbnb.listing l
            JOIN airbnb.municipality m ON m.municipality_id = l.municipality_id
            JOIN airbnb.province p ON p.province_id = m.province_id
            WHERE (%(p)s IS NULL OR p.name = %(p)s) AND (%(r)s IS NULL OR l.room_type = %(r)s)""",
                    {"p": P, "r": R})
        n_list, n_hosts, med_price, n_rev = cur.fetchone()
    c.rollback()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Listings", f"{n_list:,}")
    k2.metric("Hosts", f"{n_hosts:,}")
    k3.metric("Median nightly price", f"{med_price} EUR" if med_price is not None else "n/a")
    k4.metric("Reviews", f"{n_rev:,}")
except Exception as e:  # noqa: BLE001
    st.error(f"Error loading summary figures: {e}")

st.write("")
tabs = st.tabs(["Map", "Prices", "Demand", "Hosts", "Amenities and licences", "Guests", "Price simulation"])
tab_map, tabs = tabs[0], tabs[1:]

# --------------------------------------------------------------------- MAP
with tab_map:
    header("Q13", "Location of listings by price quintile")
    min_r13 = st.slider("Minimum number of reviews", 0, 100, 0, key="q13r")
    df = show("Q13", province=P, room_type=R, min_reviews=min_r13)
    if not empty(df):
        # Las filas llegan ordenadas por quintil, así que cada banda toma su tono de la rampa en orden
        fig = px.scatter_map(df, lat="latitude", lon="longitude", color="price_band",
                             color_discrete_sequence=PRICE_RAMP, hover_name="listing",
                             hover_data={"municipality": True, "room_type": True, "price": True,
                                         "score_rating": True, "latitude": False, "longitude": False,
                                         "price_band": False},
                             zoom=8.2, center={"lat": 43.13, "lon": -2.55}, map_style="carto-positron")
        fig.update_traces(marker=dict(size=7, opacity=0.8))
        fig.update_layout(template=TEMPLATE, height=620, margin=dict(l=0, r=0, t=36, b=0),
                          legend_title_text="Price per night")
        plot(fig)
    sql_box("Q13")

# ------------------------------------------------------------------ PRICES
with tabs[0]:
    header("Q01", "Median nightly price by municipality")
    c1, c2 = st.columns(2)
    min_l = c1.slider("Minimum listings per municipality", 5, 200, 20, key="q01m")
    top = c2.slider("Municipalities shown", 5, 40, 15, key="q01t")
    df = show("Q01", province=P, room_type=R, min_listings=min_l, top_n=top)
    if not empty(df):
        fig = px.bar(df, x="median_price", y="municipality", color="province", orientation="h",
                     color_discrete_map=PROVINCE_COLOR, hover_data=["listings", "avg_price"],
                     labels={"median_price": "Median price per night (EUR)", "municipality": ""})
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        plot(style(fig, height=max(320, 28 * len(df)), horizontal=True))
    sql_box("Q01")

    st.divider()
    header("Q12", "Listings priced below their municipality's median with top value scores")
    c1, c2, c3 = st.columns(3)
    score = c1.slider("Minimum value score", 4.0, 5.0, 4.8, 0.05, key="q12s")
    min_r = c2.slider("Minimum number of reviews", 1, 200, 20, key="q12r")
    top12 = c3.slider("Listings shown", 5, 50, 20, key="q12t")
    df = show("Q12", province=P, room_type=R, min_score=score, min_reviews=min_r, top_n=top12)
    if not empty(df):
        fig = px.scatter(df, x="town_median_price", y="price", size="n_reviews", size_max=22,
                         hover_name="listing", hover_data=["municipality", "score_value", "pct_vs_town_median"],
                         labels={"town_median_price": "Median price of the municipality (EUR)",
                                 "price": "Listing price (EUR)"})
        fig.update_traces(marker=dict(color=SERIES[0], opacity=0.85, line=dict(color=SURFACE, width=2)))
        plot(style(fig))
        st.dataframe(df, use_container_width=True, hide_index=True)
    sql_box("Q12")

# ------------------------------------------------------------------ DEMAND
with tabs[1]:
    header("Q03", "Reviews per month as a proxy for demand")
    year = st.slider("From year", 2011, 2026, 2016, key="q03y")
    df = show("Q03", province=P, year_from=year)
    if not empty(df):
        fig = px.line(df, x="month", y="reviews", hover_data=["reviews_last_year", "yoy_change_pct"],
                      labels={"reviews": "Reviews per month", "month": ""})
        fig.update_traces(line_color=SERIES[0])
        fig.update_layout(hovermode="x unified")
        plot(style(fig))
    sql_box("Q03")

    st.divider()
    header("Q05", "Share of listing-days already unavailable over the next twelve months")
    df = show("Q05", room_type=R)
    if not empty(df):
        fig = px.line(df, x="month", y="pct_unavailable", color="province", markers=True,
                      color_discrete_map=PROVINCE_COLOR,
                      labels={"pct_unavailable": "Unavailable listing-days (%)", "month": ""})
        fig.update_traces(marker_size=8, line_width=2)
        fig.update_layout(hovermode="x unified")
        plot(style(fig))
    sql_box("Q05")

    st.divider()
    header("Q08", "Weekend versus weekday occupancy")
    c1, c2, c3 = st.columns(3)
    horizon = c1.slider("Horizon (days ahead)", 14, 365, 90, key="q08h")
    min_l8 = c2.slider("Minimum listings per municipality", 10, 300, 30, key="q08m")
    top8 = c3.slider("Municipalities shown", 5, 30, 15, key="q08t")
    df = show("Q08", province=P, horizon_days=horizon, min_listings=min_l8, top_n=top8)
    if not empty(df):
        fig = px.bar(df, x="municipality", y=["weekend_occ_pct", "weekday_occ_pct"], barmode="group",
                     labels={"value": "Unavailable nights (%)", "municipality": "", "variable": ""})
        fig.for_each_trace(lambda t: t.update(name={"weekend_occ_pct": "Friday and Saturday nights",
                                                    "weekday_occ_pct": "Other nights"}[t.name]))
        plot(style(fig))
    sql_box("Q08")

# ------------------------------------------------------------------- HOSTS
with tabs[2]:
    header("Q07", "Guest scores of superhosts and regular hosts")
    c1, c2 = st.columns(2)
    min_r7 = c1.slider("Minimum reviews per listing", 1, 100, 10, key="q07r")
    metric_labels = {"avg_rating": "Overall rating", "avg_cleanliness": "Cleanliness",
                     "avg_communication": "Communication", "avg_value": "Value", "avg_price": "Average price (EUR)"}
    metric = c2.selectbox("Measure", list(metric_labels), format_func=metric_labels.get)
    df = show("Q07", min_reviews=min_r7)
    if not empty(df):
        fig = px.bar(df, x="province", y=metric, color="host_type", barmode="group", hover_data=["listings"],
                     color_discrete_map={"Superhost": SERIES[0], "Regular host": SERIES[1]},
                     labels={metric: metric_labels[metric], "province": ""})
        if metric != "avg_price":
            fig.update_yaxes(range=[4.0, 5.0])
        plot(style(fig, height=380))
    sql_box("Q07")

    st.divider()
    header("Q04", "Hosts managing the largest number of listings")
    c1, c2 = st.columns(2)
    min_l4 = c1.slider("Minimum listings per host", 2, 50, 10, key="q04m")
    top4 = c2.slider("Hosts shown", 5, 40, 15, key="q04t")
    df = show("Q04", province=P, min_listings=min_l4, top_n=top4)
    if not empty(df):
        fig = px.bar(df, x="listings", y="host", orientation="h", hover_data=["pct_of_supply", "municipalities", "avg_price"],
                     labels={"listings": "Listings", "host": ""})
        fig.update_traces(marker_color=SERIES[0])
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        plot(style(fig, height=max(320, 28 * len(df)), horizontal=True))
    sql_box("Q04")

    st.divider()
    header("Q02", "Most reviewed listings in each province")
    top2 = st.slider("Listings per province", 1, 20, 5, key="q02t")
    df = show("Q02", province=P, top_n=top2)
    if not empty(df):
        st.dataframe(df, use_container_width=True, hide_index=True)
    sql_box("Q02")

# ------------------------------------------------- AMENITIES AND LICENCES
with tabs[3]:
    header("Q06", "Price-per-guest premium associated with each amenity")
    c1, c2 = st.columns(2)
    min_l6 = c1.slider("Minimum listings in each group", 20, 1000, 100, key="q06m")
    top6 = c2.slider("Amenities shown", 5, 40, 15, key="q06t")
    df = show("Q06", province=P, room_type=R, min_listings=min_l6, top_n=top6)
    if not empty(df):
        fig = px.bar(df, x="premium_pct", y="amenity", orientation="h",
                     hover_data=["listings_with", "avg_price_guest_with", "avg_price_guest_without"],
                     labels={"premium_pct": "Difference in average price per guest (%)", "amenity": ""})
        fig.update_traces(marker_color=SERIES[0])
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        plot(style(fig, height=max(320, 28 * len(df)), horizontal=True))
    sql_box("Q06")

    st.divider()
    header("Q11", "Tourist-registry licence status by municipality")
    c1, c2 = st.columns(2)
    min_l11 = c1.slider("Minimum listings per municipality", 5, 200, 20, key="q11m")
    top11 = c2.slider("Municipalities shown", 5, 40, 15, key="q11t")
    df = show("Q11", province=P, room_type=R, min_listings=min_l11, top_n=top11)
    if not empty(df):
        fig = px.bar(df, x="municipality", y=["registered", "exempt", "no_license"],
                     labels={"value": "Listings", "municipality": "", "variable": ""})
        fig.for_each_trace(lambda t: t.update(name={"registered": "Registered", "exempt": "Exempt",
                                                    "no_license": "No licence shown"}[t.name]))
        plot(style(fig))
    sql_box("Q11")

# ------------------------------------------------------------------ GUESTS
with tabs[4]:
    header("Q10", "Number of reviews written per guest")
    year10 = st.slider("Reviews written since", 2011, 2026, 2011, key="q10y")
    df = show("Q10", year_from=year10)
    if not empty(df):
        fig = px.bar(df, x="reviews_written", y="reviewers", log_y=True,
                     hover_data=["pct_reviewers", "avg_days_between_reviews"],
                     labels={"reviewers": "Guests (logarithmic scale)", "reviews_written": "Reviews written"})
        fig.update_traces(marker_color=SERIES[0])
        plot(style(fig, height=360))
        st.dataframe(df, use_container_width=True, hide_index=True)
    sql_box("Q10")

# ------------------------------------------------------- PRICE SIMULATION
with tabs[5]:
    header("Q09", "Price change simulation for one municipality")
    st.markdown("The simulation executes a real `UPDATE` inside a transaction, reads the new figures "
                "and then issues `ROLLBACK`. The stored data is never modified.")
    c1, c2 = st.columns(2)
    default_idx = MUNICIPALITIES.index("Donostia-San Sebastián") if "Donostia-San Sebastián" in MUNICIPALITIES else 0
    mun = c1.selectbox("Municipality", MUNICIPALITIES, index=default_idx)
    pct = c2.number_input("Price change (%)", min_value=-90.0, max_value=200.0, value=10.0, step=5.0)
    if st.button("Run simulation", type="primary"):
        try:
            cols, rows, updated = run_transaction_query(conn_ok(), QUERIES["Q09"],
                                                        {"municipality": mun, "pct_change": pct})
            st.success(f"The UPDATE affected {updated} listings. The transaction was rolled back.")
            st.dataframe(pd.DataFrame(rows, columns=cols), use_container_width=True, hide_index=True)
        except psycopg2.Error as e:
            st.error(f"Database error: {e.pgerror or e}")
    sql_box("Q09")

st.markdown("<div class='footer'>Data: Inside Airbnb, Euskadi, 25 September 2026, licensed under CC BY 4.0. "
            "TECNUN, Project B. Aitor Marcalain and Iker Elias.</div>", unsafe_allow_html=True)
