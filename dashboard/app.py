"""Industrial machine health dashboard powered by the fog/cloud pipeline."""

from datetime import datetime
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st


st.set_page_config(
    page_title="ForgeWatch | Machine Intelligence",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

COLORS = {
    "bg": "#07111f",
    "panel": "#0d1b2a",
    "panel_2": "#102238",
    "text": "#f2f7fb",
    "muted": "#8fa6bb",
    "cyan": "#35d7ff",
    "blue": "#4f7cff",
    "green": "#35e59a",
    "amber": "#ffbd4a",
    "red": "#ff5d73",
    "grid": "rgba(143,166,187,.13)",
}
STATUS_COLORS = {
    "Normal": COLORS["green"],
    "Warning": COLORS["amber"],
    "Critical": COLORS["red"],
    "Unknown": COLORS["muted"],
}
THRESHOLDS = {"vibration": 0.75, "temperature": 110.0, "pressure": 9.5}


def inject_styles():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

        :root { --cyan:#35d7ff; --green:#35e59a; --amber:#ffbd4a; --red:#ff5d73; }
        .stApp {
            background:
                radial-gradient(circle at 82% 0%, rgba(53,215,255,.09), transparent 28rem),
                radial-gradient(circle at 8% 30%, rgba(79,124,255,.07), transparent 24rem),
                #07111f;
            color: #f2f7fb;
        }
        html, body, [class*="css"], [data-testid="stAppViewContainer"] {
            font-family: "DM Sans", sans-serif;
        }
        h1, h2, h3 { font-family: "Space Grotesk", sans-serif !important; letter-spacing:-.025em; }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stMainBlockContainer"] { padding-top: 2rem; max-width: 1500px; }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b1928 0%, #081421 100%);
            border-right: 1px solid rgba(143,166,187,.13);
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#b7c8d7; }
        .brand { display:flex; align-items:center; gap:.8rem; margin:.35rem 0 1.8rem; }
        .brand-mark {
            width:42px; height:42px; border-radius:13px; display:grid; place-items:center;
            background:linear-gradient(135deg,#35d7ff,#4f7cff); color:#06111d;
            font:700 20px "Space Grotesk"; box-shadow:0 0 24px rgba(53,215,255,.24);
        }
        .brand-name { color:#f2f7fb; font:700 1.15rem "Space Grotesk"; line-height:1.05; }
        .brand-sub { color:#718ba1; font-size:.72rem; letter-spacing:.13em; text-transform:uppercase; margin-top:.25rem; }
        .eyebrow { color:#35d7ff; font-size:.75rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase; }
        .hero { display:flex; justify-content:space-between; align-items:flex-end; gap:2rem; margin:.2rem 0 1.5rem; }
        .hero h1 { margin:.25rem 0 .35rem; font-size:clamp(2rem,4vw,3.25rem); line-height:1.04; }
        .hero p { color:#8fa6bb; max-width:680px; margin:0; font-size:1rem; }
        .live-pill {
            white-space:nowrap; padding:.55rem .85rem; border:1px solid rgba(53,229,154,.28);
            background:rgba(53,229,154,.08); border-radius:999px; color:#9af4cd;
            font-size:.78rem; font-weight:700; letter-spacing:.06em;
        }
        .live-dot { display:inline-block; width:7px; height:7px; margin-right:.45rem; border-radius:50%;
            background:#35e59a; box-shadow:0 0 0 5px rgba(53,229,154,.10),0 0 12px #35e59a; }
        .section-head { margin:1.8rem 0 .7rem; }
        .section-head h2 { margin:.15rem 0; font-size:1.25rem; }
        .section-head p { margin:0; color:#7891a7; font-size:.86rem; }
        .metric-card {
            min-height:126px; padding:1.2rem 1.25rem; border:1px solid rgba(143,166,187,.13);
            border-radius:18px; background:linear-gradient(145deg,rgba(16,34,56,.96),rgba(10,25,41,.96));
            box-shadow:0 10px 30px rgba(0,0,0,.12); position:relative; overflow:hidden;
        }
        .metric-card:after { content:""; position:absolute; width:90px; height:90px; right:-42px; top:-42px;
            border-radius:50%; background:var(--accent); filter:blur(28px); opacity:.16; }
        .metric-label { color:#8fa6bb; font-size:.78rem; font-weight:600; letter-spacing:.04em; }
        .metric-value { color:#f2f7fb; font:700 1.68rem "Space Grotesk"; margin:.5rem 0 .25rem; }
        .metric-note { color:#718ba1; font-size:.73rem; }
        .metric-icon { float:right; color:var(--accent); font-size:1.05rem; }
        .status-banner {
            padding:1rem 1.15rem; margin:.75rem 0 .25rem; border-radius:14px;
            border:1px solid color-mix(in srgb,var(--status) 28%,transparent);
            border-left:4px solid var(--status); background:color-mix(in srgb,var(--status) 7%,#0d1b2a);
            color:#dce8f1;
        }
        .status-banner strong { color:var(--status); margin-right:.5rem; }
        .side-card { padding:1rem; border:1px solid rgba(143,166,187,.13); border-radius:14px;
            background:rgba(16,34,56,.6); margin:.7rem 0; }
        .side-card small { color:#718ba1; display:block; margin-bottom:.25rem; }
        .side-card b { color:#e8f2fa; font-weight:600; }
        div[data-testid="stPlotlyChart"] { border:1px solid rgba(143,166,187,.12); border-radius:18px;
            overflow:hidden; background:rgba(13,27,42,.82); padding:.25rem; }
        div[data-testid="stDataFrame"] { border:1px solid rgba(143,166,187,.13); border-radius:14px; overflow:hidden; }
        .stTabs [data-baseweb="tab-list"] { gap:.4rem; border-bottom:1px solid rgba(143,166,187,.13); }
        .stTabs [data-baseweb="tab"] { border-radius:9px 9px 0 0; padding:.65rem 1rem; color:#8fa6bb; }
        .stTabs [aria-selected="true"] { color:#35d7ff !important; background:rgba(53,215,255,.07); }
        .stButton button { border-radius:10px; border:1px solid rgba(143,166,187,.2); font-weight:700; }
        .footer { color:#607b91; text-align:center; padding:2rem 0 1rem; font-size:.76rem; }
        @media (max-width: 700px) { .hero { align-items:flex-start; flex-direction:column; gap:1rem; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def fetch_json(base_url, endpoint):
    try:
        response = requests.get(f"{base_url.rstrip('/')}{endpoint}", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def clear_data(base_url):
    try:
        response = requests.delete(f"{base_url.rstrip('/')}/clear", timeout=5)
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


def number(value, default=0.0):
    try:
        return default if value is None else float(value)
    except (TypeError, ValueError):
        return default


def rerun():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()


def metric_card(label, value, note, icon, accent):
    st.markdown(
        f"""<div class="metric-card" style="--accent:{accent}">
        <span class="metric-icon">{icon}</span><div class="metric-label">{escape(label)}</div>
        <div class="metric-value">{escape(str(value))}</div><div class="metric-note">{escape(note)}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def section(title, subtitle):
    st.markdown(
        f'<div class="section-head"><h2>{escape(title)}</h2><p>{escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def chart_style(fig, height=330):
    fig.update_layout(
        height=height,
        margin=dict(l=18, r=18, t=58, b=18),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color=COLORS["muted"], size=12),
        title=dict(font=dict(family="Space Grotesk", color=COLORS["text"], size=16), x=0.04),
        legend=dict(orientation="h", y=1.08, x=1, xanchor="right"),
        hoverlabel=dict(bgcolor=COLORS["panel_2"], font_color=COLORS["text"]),
    )
    fig.update_xaxes(gridcolor=COLORS["grid"], zeroline=False)
    fig.update_yaxes(gridcolor=COLORS["grid"], zeroline=False)
    return fig


def trend_chart(data, y, title, unit, color, threshold=None):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["reading_no"], y=data[y], mode="lines",
            line=dict(color=color, width=2.5, shape="spline"),
            fill="tozeroy", fillcolor=color.replace("#", "rgba(") if False else "rgba(53,215,255,.035)",
            name=title, hovertemplate=f"Reading %{{x}}<br>%{{y:.2f}} {unit}<extra></extra>",
        )
    )
    if threshold is not None:
        fig.add_hline(
            y=threshold, line_dash="dot", line_color=COLORS["red"], line_width=1.3,
            annotation_text=f"Limit {threshold:g}", annotation_font_color=COLORS["red"],
        )
    fig.update_layout(title=title, showlegend=False)
    fig.update_yaxes(title=unit)
    fig.update_xaxes(title="Reading")
    return chart_style(fig)


inject_styles()

with st.sidebar:
    st.markdown(
        """<div class="brand"><div class="brand-mark">F</div><div>
        <div class="brand-name">ForgeWatch</div><div class="brand-sub">Fog intelligence</div>
        </div></div>""",
        unsafe_allow_html=True,
    )
    st.markdown("##### CONNECTION")
    backend_url = st.text_input(
        "Backend endpoint", value="https://swx9zp4ye8.execute-api.us-east-1.amazonaws.com",
        help="URL of the FastAPI cloud backend", label_visibility="collapsed",
    )
    auto_refresh = st.toggle("Auto refresh", value=False, help="Refresh the view every 10 seconds")
    st.markdown(
        """<div class="side-card"><small>DATA PIPELINE</small>
        <b>Sensor → Fog node → Cloud → Dashboard</b></div>
        <div class="side-card"><small>FOG ANALYTICS</small>
        <b>Rolling RMS · Temperature mean · Rule-based detection</b></div>""",
        unsafe_allow_html=True,
    )
    st.markdown("##### SAFETY LIMITS")
    st.caption("Vibration  ·  0.75 mm/s")
    st.caption("Temperature  ·  110 °C")
    st.caption("Pressure  ·  9.5 bar")
    st.divider()
    st.caption("Industrial Fault Detection · MSc Project")

st.markdown(
    """<div class="hero"><div><div class="eyebrow">Operations centre</div>
    <h1>Machine intelligence,<br>at a glance.</h1>
    <p>Live condition monitoring from edge sensors, enriched by low-latency fog analytics.</p>
    </div><div class="live-pill"><span class="live-dot"></span>LIVE MONITORING</div></div>""",
    unsafe_allow_html=True,
)

action_left, action_mid, action_right = st.columns([1, 1.25, 6])
with action_left:
    if st.button("↻  Refresh", use_container_width=True):
        rerun()
with action_mid:
    if st.button("Clear data", use_container_width=True):
        if clear_data(backend_url):
            st.toast("Backend readings cleared", icon="✅")
            rerun()
        else:
            st.error("Could not clear the backend data.")
with action_right:
    st.caption(f"Updated {datetime.now().strftime('%H:%M:%S')} · {backend_url}")

summary_data = fetch_json(backend_url, "/summary")
latest_data = fetch_json(backend_url, "/latest")
readings_data = fetch_json(backend_url, "/readings?limit=500")

if summary_data is None:
    st.error("The cloud backend is offline. Start it, then refresh this page.")
    st.code("uvicorn cloud_backend.backend:app --host 0.0.0.0 --port 9000", language="powershell")
    st.stop()

if int(number(summary_data.get("total"))) == 0:
    section("Waiting for telemetry", "The dashboard is connected, but no sensor readings have arrived yet.")
    st.info("Start the fog node and sensor simulator to begin streaming machine data.")
    st.code(
        "python fog_layer/fog_node.py\n"
        "python sensor_layer/sensor_simulator.py --count 100 --generate-interval 1 "
        "--dispatch-interval 2 --fog-url http://localhost:7000/ingest",
        language="powershell",
    )
    st.stop()

latest = latest_data.get("latest", {}) if latest_data else {}
status = latest.get("machine_status", "Unknown")
status_color = STATUS_COLORS.get(status, COLORS["muted"])
total = int(number(summary_data.get("total")))
normal = int(number(summary_data.get("normal_count")))
warning = int(number(summary_data.get("warning_count")))
critical = int(number(summary_data.get("critical_count")))
health_rate = (normal / total * 100) if total else 0

section("Live overview", "Most recent condition signals and fleet health")
kpi_cols = st.columns(5)
with kpi_cols[0]:
    metric_card("Machine status", status.upper(), "Latest classification", "●", status_color)
with kpi_cols[1]:
    metric_card("Vibration", f"{number(latest.get('vibration')):.3f}", "mm/s · limit 0.75", "〰", COLORS["cyan"])
with kpi_cols[2]:
    metric_card("Temperature", f"{number(latest.get('temperature')):.1f}°", "Celsius · limit 110", "♨", COLORS["amber"])
with kpi_cols[3]:
    metric_card("Pressure", f"{number(latest.get('pressure')):.2f}", "bar · limit 9.5", "◎", COLORS["blue"])
with kpi_cols[4]:
    metric_card("Healthy samples", f"{health_rate:.1f}%", f"{normal:,} of {total:,} readings", "✓", COLORS["green"])

alert = latest.get("alert_message") or "No diagnostic message available."
st.markdown(
    f'<div class="status-banner" style="--status:{status_color}"><strong>{escape(status.upper())}</strong>'
    f'{escape(alert)}</div>',
    unsafe_allow_html=True,
)

if not readings_data or not readings_data.get("readings"):
    st.warning("The summary is available, but detailed readings could not be loaded.")
    st.stop()

df = pd.DataFrame(readings_data["readings"])
required = [
    "timestamp", "machine_id", "vibration", "temperature", "pressure",
    "rolling_rms_vibration", "rolling_mean_temperature", "machine_status", "alert_message",
]
for column in required:
    if column not in df:
        df[column] = None
for column in ["vibration", "temperature", "pressure", "rolling_rms_vibration", "rolling_mean_temperature"]:
    df[column] = pd.to_numeric(df[column], errors="coerce")
df["reading_no"] = range(1, len(df) + 1)
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

section("Telemetry workspace", "Explore sensor behavior, fog analytics, and incident history")
overview_tab, fog_tab, alerts_tab, data_tab = st.tabs(
    ["Sensor trends", "Fog analytics", f"Alerts ({warning + critical})", "Data explorer"]
)

with overview_tab:
    filter_a, filter_b = st.columns([2, 1])
    with filter_a:
        window = st.select_slider(
            "Visible history", options=[25, 50, 100, 250, 500],
            value=min(100, max([x for x in [25, 50, 100, 250, 500] if x <= max(len(df), 25)])),
            format_func=lambda x: f"Last {x} readings",
        )
    with filter_b:
        show_limits = st.toggle("Show safety limits", value=True)
    visible = df.tail(window)
    plot_a, plot_b = st.columns(2)
    with plot_a:
        st.plotly_chart(
            trend_chart(visible, "vibration", "Vibration signature", "mm/s", COLORS["cyan"],
                        THRESHOLDS["vibration"] if show_limits else None),
            use_container_width=True,
        )
    with plot_b:
        st.plotly_chart(
            trend_chart(visible, "temperature", "Thermal profile", "°C", COLORS["amber"],
                        THRESHOLDS["temperature"] if show_limits else None),
            use_container_width=True,
        )
    plot_c, plot_d = st.columns([1.55, 1])
    with plot_c:
        st.plotly_chart(
            trend_chart(visible, "pressure", "Pressure stability", "bar", COLORS["blue"],
                        THRESHOLDS["pressure"] if show_limits else None),
            use_container_width=True,
        )
    with plot_d:
        counts = df["machine_status"].fillna("Unknown").value_counts().rename_axis("Status").reset_index(name="Count")
        donut = px.pie(
            counts, names="Status", values="Count", hole=.72,
            color="Status", color_discrete_map=STATUS_COLORS, title="Condition mix",
        )
        donut.update_traces(textinfo="percent", textfont_color=COLORS["text"], marker_line_width=0)
        donut.add_annotation(
            text=f"<b>{total:,}</b><br><span style='font-size:11px'>SAMPLES</span>",
            x=.5, y=.5, showarrow=False, font=dict(color=COLORS["text"], size=18),
        )
        st.plotly_chart(chart_style(donut), use_container_width=True)

with fog_tab:
    st.caption("Rolling features are computed near the machine at the fog node before cloud transmission.")
    fog_a, fog_b = st.columns(2)
    with fog_a:
        st.plotly_chart(
            trend_chart(df.tail(150), "rolling_rms_vibration", "Rolling RMS vibration", "mm/s", "#b980ff"),
            use_container_width=True,
        )
    with fog_b:
        st.plotly_chart(
            trend_chart(df.tail(150), "rolling_mean_temperature", "Rolling mean temperature", "°C", "#ff71ad"),
            use_container_width=True,
        )
    st.info("A 10-reading rolling window smooths noise while keeping fault detection responsive.")

with alerts_tab:
    incidents = df[df["machine_status"].isin(["Warning", "Critical"])].copy().sort_values("reading_no", ascending=False)
    if incidents.empty:
        st.success("No warning or critical events detected in the current dataset.")
    else:
        severity = st.radio(
            "Severity", ["All", "Critical", "Warning"], index=0, horizontal=True,
            help="Filter the incident log by severity",
        )
        if severity and severity != "All":
            incidents = incidents[incidents["machine_status"] == severity]
        incident_view = incidents[
            ["timestamp", "machine_id", "machine_status", "alert_message", "vibration", "temperature", "pressure"]
        ].head(50).rename(columns={
            "timestamp": "Time", "machine_id": "Machine", "machine_status": "Severity",
            "alert_message": "Diagnostic", "vibration": "Vibration (mm/s)",
            "temperature": "Temperature (°C)", "pressure": "Pressure (bar)",
        })
        st.dataframe(
            incident_view, use_container_width=True, hide_index=True,
            column_config={
                "Time": st.column_config.DatetimeColumn(format="DD MMM, HH:mm:ss"),
                "Vibration (mm/s)": st.column_config.NumberColumn(format="%.3f"),
                "Temperature (°C)": st.column_config.NumberColumn(format="%.1f"),
                "Pressure (bar)": st.column_config.NumberColumn(format="%.2f"),
            },
        )

with data_tab:
    data_a, data_b, data_c, data_d = st.columns(4)
    data_a.metric("Total samples", f"{total:,}")
    data_b.metric("Normal", f"{normal:,}")
    data_c.metric("Warning", f"{warning:,}")
    data_d.metric("Critical", f"{critical:,}")
    st.dataframe(
        df.sort_values("reading_no", ascending=False), use_container_width=True, hide_index=True,
        column_config={"timestamp": st.column_config.DatetimeColumn("Timestamp", format="DD MMM YYYY, HH:mm:ss")},
    )
    st.download_button(
        "Download CSV", df.to_csv(index=False).encode("utf-8"),
        file_name=f"forgewatch-readings-{datetime.now():%Y%m%d-%H%M}.csv", mime="text/csv",
    )

st.markdown(
    f'<div class="footer">FORGEWATCH · FOG-TO-CLOUD CONDITION MONITORING · '
    f'{datetime.now():%d %b %Y, %H:%M:%S}</div>',
    unsafe_allow_html=True,
)

if auto_refresh:
    import time

    time.sleep(10)
    rerun()
