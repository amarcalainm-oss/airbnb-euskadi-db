import json
import sys
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from db import RAW_DIR, get_connection                               # noqa: E402
from query_lib import load_queries, run_query, run_transaction_query  # noqa: E402

# Plotly treats Decimal as a category, so NUMERIC is returned as float
psycopg2.extensions.register_type(psycopg2.extensions.new_type(
    psycopg2.extensions.DECIMAL.values, "NUMERIC_FLOAT", lambda v, cur: None if v is None else float(v)))

st.set_page_config(page_title="Airbnb Euskadi - Database analysis", layout="wide")

QUERIES = load_queries()
ROOM_TYPES = ["Entire home/apt", "Private room", "Hotel room", "Shared room"]

SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
PRICE_RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]
INK, INK_2, INK_3, GRID, PANEL = "#142430", "#52606a", "#87939a", "#e1e6e4", "#ffffff"
# Álava is white, so it always gets a dark outline to stay visible
PROVINCE_COLOR = {"Vizcaya": "#d52b1e", "Guipúzcoa": "#009b48", "Álava": "#ffffff"}
WHITE_PROVINCE = "Álava"
SANS = "'Schibsted Grotesk', 'Segoe UI', Helvetica, Arial, sans-serif"

TEMPLATE = go.layout.Template(layout=dict(
    font=dict(family=SANS, size=13, color=INK_2),
    paper_bgcolor=PANEL, plot_bgcolor=PANEL,
    colorway=SERIES,
    margin=dict(l=4, r=8, t=40, b=4),
    xaxis=dict(showgrid=False, linecolor=GRID, ticks="", zeroline=False, title_font_color=INK_2,
               tickfont=dict(color=INK_3)),
    yaxis=dict(gridcolor=GRID, gridwidth=1, linecolor="rgba(0,0,0,0)", ticks="", zeroline=False,
               title_font_color=INK_2, tickfont=dict(color=INK_3)),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text="",
                font=dict(color=INK_2, size=12)),
    hoverlabel=dict(bgcolor=PANEL, bordercolor=GRID, font=dict(family=SANS, color=INK, size=12)),
    barcornerradius=4,
    bargap=0.35,
))


def style(fig, height=420):
    fig.update_layout(template=TEMPLATE, height=height, legend_title_text="")
    fig.update_traces(selector=dict(type="bar"), marker_line_color=PANEL, marker_line_width=2)
    fig.update_traces(selector=dict(type="scatter", mode="lines"), line_width=2)
    fig.update_traces(selector=dict(type="bar", name=WHITE_PROVINCE), marker_line_color=INK, marker_line_width=1.2)
    fig.update_traces(selector=dict(type="scatter", name=WHITE_PROVINCE), line_color=INK,
                      marker=dict(color=PROVINCE_COLOR[WHITE_PROVINCE], line=dict(color=INK, width=1.5)))
    return fig


CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&family=Schibsted+Grotesk:wght@400;500;600;700&display=swap');

  :root {
    --mist: #eef1ef; --panel: #ffffff; --ink: #142430; --ink-2: #52606a; --ink-3: #87939a;
    --rule: #d6dddb; --rule-soft: #e6ebe9; --sea: #1d5a85; --sea-wash: #e4eef5;
    --slate: #142430; --slate-ink: #e4eaec; --slate-ink-2: #9fb0ba; --slate-rule: #2e4554;
    --sans: 'Schibsted Grotesk', 'Segoe UI', Helvetica, Arial, sans-serif;
    --serif: 'Newsreader', Georgia, 'Times New Roman', serif;
    --ease: cubic-bezier(.2, .7, .2, 1);
  }

  html, body, .stApp, .stMarkdown, button, input, label, textarea, [data-baseweb] {
    font-family: var(--sans); }
  .stApp { color: var(--ink); }
  .block-container { padding: 2.4rem 2.6rem 3rem; max-width: 1240px; }
  h1, h2, h3, h4 { font-family: var(--sans) !important; color: var(--ink) !important; }
  [data-testid="stHeader"] { background: transparent; }
  :focus-visible { outline: 2px solid var(--sea) !important; outline-offset: 2px; }
  ::selection { background: var(--sea-wash); }

  [data-testid="stSidebar"] { border-right: 1px solid var(--slate-rule); }
  [data-testid="stSidebar"] .block-container, [data-testid="stSidebarContent"] { padding-top: 0.6rem; }
  .brand { margin: 0.2rem 0 2rem; }
  .brand-marks { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.85rem; }
  .brand-mark { width: 52px; height: 52px; flex: none; }
  .brand-flag { width: 66px; height: 37px; flex: none; border-radius: 3px;
                box-shadow: 0 0 0 1px var(--slate-rule); }
  .brand-name { font-family: var(--serif); font-size: 1.7rem; font-weight: 500; line-height: 1.1;
                color: #fff; letter-spacing: -0.005em; }
  .brand-sub { font-size: 0.9rem; color: var(--slate-ink-2); margin-top: 0.25rem; }
  .side-h { font-size: 0.86rem; font-weight: 600; color: var(--slate-ink); margin: 0 0 0.5rem; }
  .side-note { font-size: 0.8rem; line-height: 1.45; color: var(--slate-ink-2); margin: 0.3rem 0 1.6rem; }
  .side-rule { height: 1px; background: var(--slate-rule); margin: 1.4rem 0 1.3rem; }
  .key { list-style: none; padding: 0; margin: 0; }
  .key li { display: flex; align-items: center; gap: 0.6rem; font-size: 0.88rem; color: var(--slate-ink);
            padding: 0.28rem 0; transition: opacity .2s var(--ease); }
  .key li.dim { opacity: 0.38; }
  .key i { width: 10px; height: 10px; border-radius: 3px; display: inline-block;
           box-shadow: 0 0 0 1px rgba(255,255,255,0.35); }
  [data-testid="stSidebar"] label p { font-size: 0.82rem !important; color: var(--slate-ink-2) !important; }

  .masthead { padding: 0.4rem 0 0.2rem; }
  .kicker { display: flex; flex-wrap: wrap; gap: 0.5rem 1.2rem; align-items: center;
            font-size: 0.85rem; color: var(--ink-2); margin-bottom: 1.1rem; }
  .kicker .live { display: inline-flex; align-items: center; gap: 0.45rem; color: var(--sea); font-weight: 600; }
  .kicker .live::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--sea);
                          box-shadow: 0 0 0 3px var(--sea-wash); }
  h1.title { font-size: 1.02rem !important; font-weight: 600 !important; letter-spacing: 0;
             margin: 0 0 0.5rem !important; padding: 0 !important; color: var(--ink-2) !important; }
  .lede { font-family: var(--serif); font-weight: 400; font-size: clamp(1.65rem, 1.1rem + 1.9vw, 2.65rem);
          line-height: 1.18; letter-spacing: -0.012em; color: var(--ink); max-width: 30ch;
          margin: 0 0 1.1rem; font-variant-numeric: lining-nums tabular-nums;
          animation: rise .7s var(--ease) both; }
  .lede b { font-weight: 600; color: var(--sea);
            background: linear-gradient(var(--sea-wash), var(--sea-wash)) no-repeat 0 88% / 100% 0.32em;
            padding: 0 0.04em; }
  .scope { color: var(--ink-2); font-size: 0.95rem; line-height: 1.55; max-width: 68ch; margin-bottom: 2rem;
           animation: rise .7s .12s var(--ease) both; }
  @keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }

  .stTabs [data-baseweb="tab-list"] { gap: 0.25rem; border-bottom: 1px solid var(--rule);
                                      overflow-x: auto; scrollbar-width: none; }
  .stTabs [data-baseweb="tab"] { font-size: 0.93rem; font-weight: 500; color: var(--ink-2);
                                 padding: 0.7rem 0.95rem 0.8rem; height: auto; background: transparent;
                                 border-radius: 8px 8px 0 0; transition: color .15s var(--ease), background .15s var(--ease); }
  .stTabs [data-baseweb="tab"]:hover { color: var(--ink); background: rgba(20, 36, 48, 0.04); }
  .stTabs [aria-selected="true"] { color: var(--sea) !important; font-weight: 600; }
  .stTabs [data-baseweb="tab-highlight"] { background: var(--sea); height: 2px; }
  .stTabs [data-baseweb="tab-border"] { display: none; }
  .stTabs [data-baseweb="tab-panel"] { padding-top: 1.6rem; animation: fade .28s var(--ease) both; }
  @keyframes fade { from { opacity: 0; } to { opacity: 1; } }

  [class*="st-key-panel_"] { background: var(--panel); border: 1px solid var(--rule-soft) !important;
                             border-radius: 14px; padding: 1.5rem 1.6rem 0.9rem !important;
                             box-shadow: 0 1px 0 rgba(20, 36, 48, 0.03), 0 12px 32px -24px rgba(20, 36, 48, 0.28);
                             margin-bottom: 1.4rem; }
  .q-head { display: flex; gap: 1rem; align-items: flex-start; justify-content: space-between; margin-bottom: 0.4rem; }
  h3.q-title { font-family: var(--serif) !important; font-size: 1.5rem !important; font-weight: 500 !important;
               line-height: 1.2 !important; letter-spacing: -0.008em; color: var(--ink) !important;
               margin: 0 !important; padding: 0 !important; max-width: 46ch; }
  .q-id { flex: none; font-size: 0.76rem; font-weight: 600; color: var(--sea); background: var(--sea-wash);
          border-radius: 999px; padding: 0.22rem 0.62rem; margin-top: 0.3rem; font-variant-numeric: tabular-nums; }
  .q-question { color: var(--ink-2); font-size: 0.97rem; line-height: 1.5; max-width: 72ch; margin: 0 0 0.25rem; }
  .q-byline { color: var(--ink-3); font-size: 0.8rem; margin-bottom: 1.1rem; }
  .q-note { color: var(--ink-2); font-size: 0.93rem; line-height: 1.55; max-width: 72ch;
            border-left: 2px solid var(--sea); padding: 0.1rem 0 0.1rem 0.9rem; margin: 0 0 1.2rem; }
  .q-note code { font-size: 0.86em; background: var(--sea-wash); color: var(--sea); padding: 0.05em 0.35em; border-radius: 4px; }

  [class*="st-key-panel_"] label p { font-size: 0.84rem !important; color: var(--ink-2) !important; font-weight: 500; }
  [data-testid="stSlider"] [role="slider"] { box-shadow: 0 0 0 4px rgba(29, 90, 133, 0.12); }

  [class*="st-key-panel_"] .js-plotly-plot .main-svg { background: transparent !important; }
  [class*="st-key-panel_"] .js-plotly-plot rect.bg { fill: transparent !important; }

  [data-testid="stExpander"] details { border: none !important; border-top: 1px solid var(--rule-soft) !important;
                                       border-radius: 0 !important; background: transparent; }
  [data-testid="stExpander"] summary { padding: 0.85rem 0 0.4rem !important; color: var(--ink-2); font-size: 0.86rem; }
  [data-testid="stExpander"] summary:hover { color: var(--sea); }
  [data-testid="stExpander"] summary p { font-size: 0.86rem !important; }
  [data-testid="stExpanderDetails"] { padding: 0.4rem 0 0.8rem !important; }
  [data-testid="stCode"] pre, .stCode pre { border-radius: 10px !important; font-size: 0.82rem !important; }

  [data-testid="stDataFrame"] { border: 1px solid var(--rule-soft); border-radius: 10px; overflow: hidden; margin-top: 0.4rem; }
  [data-testid="stAlert"] { border-radius: 10px; }
  .stButton button[kind="primary"] { border-radius: 8px; padding: 0.55rem 1.3rem; font-weight: 600;
                                     transition: transform .12s var(--ease), box-shadow .2s var(--ease); }
  .stButton button[kind="primary"]:hover { box-shadow: 0 6px 18px -8px rgba(29, 90, 133, 0.7); }
  .stButton button[kind="primary"]:active { transform: translateY(1px); }

  .footer { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 0.6rem 2rem;
            color: var(--ink-3); font-size: 0.8rem; margin-top: 2.6rem; border-top: 1px solid var(--rule);
            padding-top: 1rem; }

  @media (max-width: 760px) {
    .block-container { padding: 1.6rem 1rem 2rem; }
    [class*="st-key-panel_"] { padding: 1.1rem 1rem 0.6rem !important; border-radius: 12px; }
    h3.q-title { font-size: 1.25rem !important; }
    .q-head { flex-direction: column-reverse; gap: 0.4rem; }
    .q-id { margin-top: 0; }
  }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; }
  }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_resource
def connection():
    return get_connection()


def conn_ok():
    """Reopens the connection if it was closed."""
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
    c = conn_ok()
    with c.cursor() as cur:
        cur.execute(sql)
        out = [r[0] for r in cur.fetchall()]
    c.rollback()
    return out


def reset_conn():
    """Rolls back an aborted transaction so the connection stays usable."""
    try:
        c = connection()
        if not c.closed:
            c.rollback()
    except Exception:  # noqa: BLE001
        pass


def show(qid: str, **params):
    try:
        return fetch(qid, tuple(sorted(params.items())))
    except psycopg2.Error as e:
        reset_conn()
        st.error(f"Database error in {qid}: {e.pgerror or e}")
    except Exception as e:  # noqa: BLE001
        reset_conn()
        st.error(f"Unexpected error in {qid}: {e}")
    return None


def header(qid: str, title: str):
    q = QUERIES[qid]
    st.markdown(f"<div class='q-head'><h3 class='q-title'>{title}</h3><span class='q-id'>{q['id']}</span></div>"
                f"<p class='q-question'>{q['question']}</p>"
                f"<div class='q-byline'>Written by {q['author']}</div>", unsafe_allow_html=True)


def sql_box(qid: str):
    q = QUERIES[qid]
    with st.expander(f"Show the SQL and interpretation ({q['techniques']})"):
        st.code(q["sql"], language="sql")
        st.markdown(f"**Why it matters.** {q['why']}")


@contextmanager
def panel(qid: str, title: str):
    with st.container(border=True, key=f"panel_{qid}"):  # key -> clase CSS st-key-panel_<qid>
        header(qid, title)
        yield
        sql_box(qid)


def empty(df) -> bool:
    if df is None:
        return True
    if df.empty:
        st.info("No rows match these filters. Lower the thresholds above or widen the province "
                "and room type in the sidebar.")
        return True
    return False


def fix_text(s):
    """Repairs UTF-8 text read as Latin-1 (same as rule R01)."""
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError, AttributeError):
        return s


@st.cache_data
def province_shapes() -> dict:
    """Municipality boundaries grouped by province; {} if the file is missing."""
    path = RAW_DIR / "neighbourhoods.geojson"
    if not path.exists():
        return {}
    shapes = {}
    for feature in json.loads(path.read_text(encoding="utf-8"))["features"]:
        name = fix_text(feature["properties"].get("neighbourhood_group"))
        shapes.setdefault(name, {"type": "FeatureCollection", "features": []})["features"].append(feature)
    return shapes


PROVINCE_LABEL_AT = {"Vizcaya": (43.27, -2.93), "Guipúzcoa": (43.17, -2.17), "Álava": (42.80, -2.72)}


def province_layers(selected):
    layers = []
    for name, shape in province_shapes().items():
        color = PROVINCE_COLOR.get(name, INK_3)
        border = INK if name == WHITE_PROVINCE else color
        strong = selected is None or selected == name
        layers.append(dict(sourcetype="geojson", source=shape, type="fill", below="traces",
                           color=color, opacity=0.13 if strong else 0.04))
        layers.append(dict(sourcetype="geojson", source=shape, type="line", below="traces",
                           color=border, opacity=0.45 if strong else 0.15, line=dict(width=0.7)))
    return layers


def plot(fig):
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


def plot_ranking(fig, n_rows: int):
    style(fig, height=max(320, 28 * n_rows))
    fig.update_layout(xaxis=dict(showgrid=True, gridcolor=GRID),
                      yaxis=dict(showgrid=False, categoryorder="total ascending", tickfont=dict(color=INK_2)))
    plot(fig)


def rename_series(fig, names: dict):
    fig.for_each_trace(lambda t: t.update(name=names[t.name]))


BRAND_BLUE = "#8cbbe0"
BRAND = f"""
<div class='brand'>
  <div class='brand-marks'>
    <svg class='brand-mark' viewBox='0 0 52 52' role='img' aria-label='Airbnb'>
      <rect width='52' height='52' rx='12' fill='#1f3444'/>
      <g transform='translate(10 9) scale(1.0)' fill='none' stroke='{BRAND_BLUE}' stroke-width='2.6'
         stroke-linejoin='round' stroke-linecap='round'>
        <path d='M16 25 C12.4 29.3 10.1 30.3 7.8 30.3 C5.1 30.3 3.2 28.2 3.2 25.6 C3.2 24.5 3.5 23.6 4.1 22.4
                 L12.5 5.4 C13.4 3.6 14.5 2.6 16 2.6 C17.5 2.6 18.6 3.6 19.5 5.4 L27.9 22.4
                 C28.5 23.6 28.8 24.5 28.8 25.6 C28.8 28.2 26.9 30.3 24.2 30.3 C21.9 30.3 19.6 29.3 16 25 Z'/>
        <path d='M16 25 C13.1 21.5 11.8 19 11.8 16.9 C11.8 14.4 13.6 12.8 16 12.8 C18.4 12.8 20.2 14.4 20.2 16.9
                 C20.2 19 18.9 21.5 16 25 Z'/>
      </g>
    </svg>
    <svg class='brand-flag' viewBox='0 0 50 28' role='img' aria-label='Ikurriña, flag of Euskadi'>
      <rect width='50' height='28' fill='#d52b1e'/>
      <path d='M0 0 L50 28 M50 0 L0 28' stroke='#009b48' stroke-width='4.3'/>
      <rect x='22.85' width='4.3' height='28' fill='#ffffff'/>
      <rect y='11.85' width='50' height='4.3' fill='#ffffff'/>
    </svg>
  </div>
  <div class='brand-name'>Airbnb Euskadi</div>
  <div class='brand-sub'>Database analysis</div>
</div>"""
st.sidebar.markdown(BRAND, unsafe_allow_html=True)

try:
    PROVINCES = lookup("SELECT name FROM airbnb.province ORDER BY name")
    MUNICIPALITIES = lookup("""SELECT m.name FROM airbnb.municipality m
                               WHERE EXISTS (SELECT 1 FROM airbnb.listing l WHERE l.municipality_id = m.municipality_id)
                               ORDER BY m.name""")
except Exception as e:  # noqa: BLE001
    st.error(f"Cannot connect to PostgreSQL. Check the .env file and that the database is loaded.\n\n{e}")
    st.stop()

st.sidebar.markdown("<div class='side-h'>Filters</div>", unsafe_allow_html=True)
province = st.sidebar.selectbox("Province", ["All provinces"] + PROVINCES)
room = st.sidebar.selectbox("Room type", ["All room types"] + ROOM_TYPES)
# None = no filter
P = None if province == "All provinces" else province
R = None if room == "All room types" else room
st.sidebar.markdown("<div class='side-note'>Filters are passed to PostgreSQL as bound query parameters. "
                    "Charts that do not depend on a filter ignore it.</div>", unsafe_allow_html=True)

key_items = "".join(
    f"<li class='{'dim' if P and P != name else ''}'><i style='background:{PROVINCE_COLOR.get(name, INK_3)}'></i>{name}</li>"
    for name in PROVINCES)
st.sidebar.markdown(f"<div class='side-rule'></div><div class='side-h'>Province colours</div>"
                    f"<ul class='key'>{key_items}</ul>"
                    f"<div class='side-note'>Each province keeps its colour in every chart.</div>",
                    unsafe_allow_html=True)

st.markdown("<div class='masthead'><div class='kicker'><span class='live'>Inside Airbnb snapshot</span>"
            "<span>25 September 2026</span><span>Álava, Guipúzcoa and Vizcaya</span></div>"
            "<h1 class='title'>Short-term rentals in the Basque Country</h1></div>", unsafe_allow_html=True)
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
    where = f" in {province}" if P else " in Euskadi"
    kind = f" ({room.lower()})" if R else ""
    price = f"<b>{med_price:.0f} EUR</b> per night" if med_price is not None else "no published price"
    st.markdown(f"<div class='lede'><b>{n_list:,}</b> listings{kind}{where}, run by <b>{n_hosts:,}</b> hosts, "
                f"with a median of {price} and <b>{n_rev:,}</b> guest reviews.</div>", unsafe_allow_html=True)
except Exception as e:  # noqa: BLE001
    reset_conn()
    st.error(f"Could not load the summary figures: {e}")

st.markdown("<div class='scope'>Every number and chart below is the result of a hand-written SQL query "
            "run against PostgreSQL. Use the filters in the sidebar to narrow the province and room type; "
            "each panel adds its own controls.</div>", unsafe_allow_html=True)
tab_map, tab_prices, tab_demand, tab_hosts, tab_amenities, tab_guests, tab_simulation = st.tabs(
    ["Map", "Prices", "Demand", "Hosts", "Amenities and licences", "Guests", "Price simulation"])

with tab_map:
    with panel("Q13", "Location of listings by price quintile"):
        min_reviews = st.slider("Minimum number of reviews", 0, 100, 0, key="q13r")
        df = show("Q13", province=P, room_type=R, min_reviews=min_reviews)
        if not empty(df):
            # Rows are ordered by quintile, so each band takes its shade in order
            fig = px.scatter_map(df, lat="latitude", lon="longitude", color="price_band",
                                 color_discrete_sequence=PRICE_RAMP, hover_name="listing",
                                 hover_data={"municipality": True, "room_type": True, "price": True,
                                             "score_rating": True, "latitude": False, "longitude": False,
                                             "price_band": False},
                                 zoom=8.2, center={"lat": 43.13, "lon": -2.55}, map_style="carto-positron")
            fig.update_traces(marker=dict(size=6, opacity=0.85))
            for name, (lat, lon) in PROVINCE_LABEL_AT.items():
                fig.add_trace(go.Scattermap(lat=[lat], lon=[lon], mode="text", text=[name],
                                            hoverinfo="skip", showlegend=False,
                                            textfont=dict(size=15, family="Open Sans Bold",
                                                          color=INK if name == WHITE_PROVINCE else PROVINCE_COLOR[name])))
            fig.update_layout(template=TEMPLATE, height=640, margin=dict(l=0, r=0, t=40, b=0),
                              legend_title_text="Price per night",
                              map=dict(layers=province_layers(P), style="carto-positron"))
            plot(fig)
            if not province_shapes():
                st.caption("Province areas are not shown: run scripts/download_data.py to fetch the boundaries.")

with tab_prices:
    with panel("Q01", "Median nightly price by municipality"):
        c1, c2 = st.columns(2)
        min_listings = c1.slider("Minimum listings per municipality", 5, 200, 20, key="q01m")
        top_n = c2.slider("Municipalities shown", 5, 40, 15, key="q01t")
        df = show("Q01", province=P, room_type=R, min_listings=min_listings, top_n=top_n)
        if not empty(df):
            fig = px.bar(df, x="median_price", y="municipality", color="province", orientation="h",
                         color_discrete_map=PROVINCE_COLOR, hover_data=["listings", "avg_price"],
                         labels={"median_price": "Median price per night (EUR)", "municipality": ""})
            plot_ranking(fig, len(df))

    with panel("Q12", "Listings priced below their municipality's median with top value scores"):
        c1, c2, c3 = st.columns(3)
        min_score = c1.slider("Minimum value score", 4.0, 5.0, 4.8, 0.05, key="q12s")
        min_reviews = c2.slider("Minimum number of reviews", 1, 200, 20, key="q12r")
        top_n = c3.slider("Listings shown", 5, 50, 20, key="q12t")
        df = show("Q12", province=P, room_type=R, min_score=min_score, min_reviews=min_reviews, top_n=top_n)
        if not empty(df):
            fig = px.scatter(df, x="town_median_price", y="price", size="n_reviews", size_max=22,
                             hover_name="listing", hover_data=["municipality", "score_value", "pct_vs_town_median"],
                             labels={"town_median_price": "Median price of the municipality (EUR)",
                                     "price": "Listing price (EUR)"})
            fig.update_traces(marker=dict(color=SERIES[0], opacity=0.85, line=dict(color=PANEL, width=2)))
            plot(style(fig))
            st.dataframe(df, use_container_width=True, hide_index=True)

with tab_demand:
    with panel("Q03", "Reviews per month as a proxy for demand"):
        year_from = st.slider("From year", 2011, 2026, 2016, key="q03y")
        df = show("Q03", province=P, year_from=year_from)
        if not empty(df):
            fig = px.line(df, x="month", y="reviews", hover_data=["reviews_last_year", "yoy_change_pct"],
                          labels={"reviews": "Reviews per month", "month": ""})
            fig.update_traces(line_color=SERIES[0])
            fig.update_layout(hovermode="x unified")
            plot(style(fig))

    with panel("Q05", "Share of listing-days already unavailable over the next twelve months"):
        df = show("Q05", room_type=R)
        if not empty(df):
            fig = px.line(df, x="month", y="pct_unavailable", color="province", markers=True,
                          color_discrete_map=PROVINCE_COLOR,
                          labels={"pct_unavailable": "Unavailable listing-days (%)", "month": ""})
            fig.update_traces(marker_size=8, line_width=2)
            fig.update_layout(hovermode="x unified")
            plot(style(fig))

    with panel("Q08", "Weekend versus weekday unavailability"):
        c1, c2, c3 = st.columns(3)
        horizon_days = c1.slider("Horizon (days ahead)", 14, 365, 90, key="q08h")
        min_listings = c2.slider("Minimum listings per municipality", 10, 300, 30, key="q08m")
        top_n = c3.slider("Municipalities shown", 5, 30, 15, key="q08t")
        df = show("Q08", province=P, horizon_days=horizon_days, min_listings=min_listings, top_n=top_n)
        if not empty(df):
            fig = px.bar(df, x="municipality", y=["weekend_occ_pct", "weekday_occ_pct"], barmode="group",
                         labels={"value": "Unavailable nights (%)", "municipality": "", "variable": ""})
            rename_series(fig, {"weekend_occ_pct": "Friday and Saturday nights", "weekday_occ_pct": "Other nights"})
            plot(style(fig))

with tab_hosts:
    with panel("Q07", "Guest scores of superhosts and regular hosts"):
        c1, c2 = st.columns(2)
        min_reviews = c1.slider("Minimum reviews per listing", 1, 100, 10, key="q07r")
        metric_labels = {"avg_rating": "Overall rating", "avg_cleanliness": "Cleanliness",
                         "avg_communication": "Communication", "avg_value": "Value", "avg_price": "Average price (EUR)"}
        metric = c2.selectbox("Measure", list(metric_labels), format_func=metric_labels.get)
        df = show("Q07", min_reviews=min_reviews)
        if not empty(df):
            fig = px.bar(df, x="province", y=metric, color="host_type", barmode="group", hover_data=["listings"],
                         color_discrete_map={"Superhost": SERIES[0], "Regular host": SERIES[1]},
                         labels={metric: metric_labels[metric], "province": ""})
            if metric != "avg_price":
                fig.update_yaxes(range=[4.0, 5.0])
            plot(style(fig, height=380))

    with panel("Q04", "Hosts managing the largest number of listings"):
        c1, c2 = st.columns(2)
        min_listings = c1.slider("Minimum listings per host", 2, 50, 10, key="q04m")
        top_n = c2.slider("Hosts shown", 5, 40, 15, key="q04t")
        df = show("Q04", province=P, min_listings=min_listings, top_n=top_n)
        if not empty(df):
            fig = px.bar(df, x="listings", y="host", orientation="h",
                         hover_data=["pct_of_supply", "municipalities", "avg_price"],
                         labels={"listings": "Listings", "host": ""})
            fig.update_traces(marker_color=SERIES[0])
            plot_ranking(fig, len(df))

    with panel("Q02", "Most reviewed listings in each province"):
        top_n = st.slider("Listings per province", 1, 20, 5, key="q02t")
        df = show("Q02", province=P, top_n=top_n)
        if not empty(df):
            st.dataframe(df, use_container_width=True, hide_index=True)

with tab_amenities:
    with panel("Q06", "Price-per-guest premium associated with each amenity"):
        c1, c2 = st.columns(2)
        min_listings = c1.slider("Minimum listings in each group", 20, 1000, 100, key="q06m")
        top_n = c2.slider("Amenities shown", 5, 40, 15, key="q06t")
        df = show("Q06", province=P, room_type=R, min_listings=min_listings, top_n=top_n)
        if not empty(df):
            fig = px.bar(df, x="premium_pct", y="amenity", orientation="h",
                         hover_data=["listings_with", "avg_price_guest_with", "avg_price_guest_without"],
                         labels={"premium_pct": "Difference in average price per guest (%)", "amenity": ""})
            fig.update_traces(marker_color=SERIES[0])
            plot_ranking(fig, len(df))

    with panel("Q11", "Tourist-registry licence status by municipality"):
        c1, c2 = st.columns(2)
        min_listings = c1.slider("Minimum listings per municipality", 5, 200, 20, key="q11m")
        top_n = c2.slider("Municipalities shown", 5, 40, 15, key="q11t")
        df = show("Q11", province=P, room_type=R, min_listings=min_listings, top_n=top_n)
        if not empty(df):
            fig = px.bar(df, x="municipality", y=["registered", "exempt", "no_license"],
                         labels={"value": "Listings", "municipality": "", "variable": ""})
            rename_series(fig, {"registered": "Registered", "exempt": "Exempt", "no_license": "No licence shown"})
            plot(style(fig))

with tab_guests:
    with panel("Q10", "Number of reviews written per guest"):
        year_from = st.slider("Reviews written since", 2011, 2026, 2011, key="q10y")
        df = show("Q10", year_from=year_from)
        if not empty(df):
            fig = px.bar(df, x="reviews_written", y="reviewers", log_y=True,
                         hover_data=["pct_reviewers", "avg_days_between_reviews"],
                         labels={"reviewers": "Guests (logarithmic scale)", "reviews_written": "Reviews written"})
            fig.update_traces(marker_color=SERIES[0])
            plot(style(fig, height=360))
            st.dataframe(df, use_container_width=True, hide_index=True)

with tab_simulation:
    with panel("Q09", "Price change simulation for one municipality"):
        st.markdown("<div class='q-note'>The simulation runs a real <code>UPDATE</code> inside a transaction, "
                    "reads the new figures and then issues <code>ROLLBACK</code>. The stored data is never "
                    "modified.</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        default_idx = MUNICIPALITIES.index("Donostia-San Sebastián") if "Donostia-San Sebastián" in MUNICIPALITIES else 0
        municipality = c1.selectbox("Municipality", MUNICIPALITIES, index=default_idx)
        pct_change = c2.number_input("Price change (%)", min_value=-90.0, max_value=200.0, value=10.0, step=5.0)
        if st.button("Run simulation", type="primary"):
            try:
                cols, rows, updated = run_transaction_query(conn_ok(), QUERIES["Q09"],
                                                            {"municipality": municipality, "pct_change": pct_change})
                st.success(f"The UPDATE affected {updated} listings. The transaction was rolled back.")
                st.dataframe(pd.DataFrame(rows, columns=cols), use_container_width=True, hide_index=True)
            except psycopg2.Error as e:
                reset_conn()
                st.error(f"Database error: {e.pgerror or e}")

st.markdown("<div class='footer'><span>Data: Inside Airbnb, Euskadi, 25 September 2026, licensed under CC BY 4.0.</span>"
            "<span>TECNUN, Project B. Aitor Marcalain and Iker Elias.</span></div>", unsafe_allow_html=True)
