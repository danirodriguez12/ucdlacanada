from __future__ import annotations

import os
import io
import html
import math
import unicodedata
from collections import defaultdict
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# -------------------------------------------------------------------
# LA CAÑADA | CONTROL DE CARGA
# Configuración segura: define WEBHOOK_URL, USERS y STAFF_USERS en
# .streamlit/secrets.toml (plantilla incluida en secrets.toml.example).
# -------------------------------------------------------------------
st.set_page_config(
    page_title="UCD La Cañada | Control de carga",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

CLUB = "UCD La Cañada Atlético"
CSV_TQR_URL = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vTNC-xJmcfT39bVMWEjqGAbfTUv1kRRudtLWwTQvsoCDy_gb5ggcCyZaHkqAT9CkoQhQ2v8eB0jTPjc/pub?gid=0&single=true&output=csv"
)
CSV_RPE_URL = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vTNC-xJmcfT39bVMWEjqGAbfTUv1kRRudtLWwTQvsoCDy_gb5ggcCyZaHkqAT9CkoQhQ2v8eB0jTPjc/pub?gid=1&single=true&output=csv"
)

ROSTER = [
    "Samu", "Enrique", "Nico", "Cotul", "Alex Rubio", "Iván", "Héctor",
    "Antonio Jesús", "Jorge", "Diego Peña", "Aliaga", "Caye", "Luis",
    "Jesús", "Alex Moya", "Iker", "Juanfe", "Pato", "Rouzki",
    "Pablo Céspedes", "Akram", "Ettibary", "Pita", "Miguel Prado",
    "Iker Soriano", "Ortega", "Alberto",
]
# Fichas opcionales: completar jugadores.csv en el repositorio, sin cambiar
# usuarios, contraseñas ni datos históricos de Google Sheets.
PLAYER_PROFILE_FILE = Path(__file__).with_name("jugadores.csv")

@st.cache_data(ttl=90, show_spinner=False)
def load_profiles() -> pd.DataFrame:
    columns = ["Usuario", "Nombre", "Apellidos", "Fecha_nacimiento", "Posicion", "Dorsal"]
    if not PLAYER_PROFILE_FILE.exists():
        return pd.DataFrame(columns=columns)
    df = pd.read_csv(PLAYER_PROFILE_FILE, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df.columns = [str(c).strip() for c in df.columns]
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    df["Usuario"] = df["Usuario"].astype(str).str.strip()
    return df[columns]


def player_profile(username: str, profiles: pd.DataFrame) -> dict[str, str]:
    matches = profiles[profiles["Usuario"].str.casefold() == username.casefold()]
    if matches.empty:
        return {"Usuario": username, "Nombre": username, "Apellidos": "", "Fecha_nacimiento": "", "Posicion": "", "Dorsal": ""}
    return matches.iloc[0].to_dict()


def age_from_birthdate(value: str) -> str:
    birth = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if pd.isna(birth):
        return "Sin completar"
    today = date.today()
    return str(today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day)))


DEFAULT_STAFF = ["Manuelcarminati", "Danirodriguez", "Nicorodriguez", "Danimoreno"]

# Identidad visual: interfaz compacta de rendimiento, sin alterar autenticación.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');
:root{--navy:#142742;--red:#e44855;--muted:#66768b;--line:#e3e9f1;--surface:#ffffff}
.stApp{background:#f3f6fb;color:#172a44;font-family:'DM Sans',sans-serif}
.block-container{max-width:1540px;padding-top:1.4rem;padding-bottom:3rem}
h1,h2,h3{color:#142742;font-family:'Space Grotesk',sans-serif;letter-spacing:-.025em}
[data-testid="stSidebar"]{background:#12233c}
[data-testid="stSidebar"] *{color:#e8edf6!important}
[data-testid="stSidebar"] [data-baseweb="select"] *{color:#142742!important}
.hero{background:linear-gradient(115deg,#142742 0%,#244467 72%,#a53b4d 150%);padding:1.7rem 2rem;border-radius:18px;color:#fff;margin-bottom:1.3rem;box-shadow:0 12px 32px #14274218}
.hero h1{color:#fff;margin:0;font-size:2rem}
.hero p{color:#dbe5f3;margin:.45rem 0 0}
.kpi{border:1px solid var(--line);border-radius:15px;padding:1rem 1.15rem;background:#fff;min-height:108px}
.kpi-label{font-size:.8rem;color:var(--muted)}
.kpi-value{font-size:1.8rem;font-weight:800;color:var(--navy)}
.kpi-note{font-size:.78rem;color:var(--muted)}
div[data-testid="stMetric"]{background:#fff;border:1px solid var(--line);padding:14px 16px;border-radius:14px;box-shadow:0 3px 14px #14274208}
[data-testid="stMetricLabel"]{font-weight:650}
[data-testid="stTabs"] button{font-weight:650}
[data-testid="stDataFrame"]{border-radius:12px;overflow:hidden}
.section-kicker{font-size:.78rem;letter-spacing:.11em;font-weight:800;color:#a33a49;text-transform:uppercase;margin-bottom:.25rem}
</style>
""", unsafe_allow_html=True)

NAVY, RED, TEAL, LIGHT = "#142742", "#e44855", "#168c92", "#e7edf4"

def chart_style(fig, height=360):
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=14,r=18,t=32,b=18),
                      font=dict(family="DM Sans, Arial",color=NAVY,size=12),
                      paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                      hoverlabel=dict(bgcolor=NAVY,font_color="white"),
                      legend=dict(orientation="h",y=1.13,x=0),
                      xaxis=dict(showgrid=False,zeroline=False),
                      yaxis=dict(gridcolor=LIGHT,zeroline=False))
    return fig


def plot_daily(data, title="Carga diaria", show_mean=True):
    fig=go.Figure()
    if not data.empty:
        fig.add_bar(x=data["Día"],y=data["Carga"],name="Carga (UA)",marker_color=TEAL,
                    hovertemplate="%{x|%d/%m/%Y}<br>%{y:,.0f} UA<extra></extra>")
        if show_mean:
            avg=data["Carga"].mean()
            fig.add_hline(y=avg,line_color=RED,line_dash="dot",
                          annotation_text=f"Media {avg:,.0f} UA",annotation_position="top left")
    fig.update_layout(title=dict(text=title,font_size=17),bargap=.32,yaxis_title="UA")
    return chart_style(fig)


def plot_wellness(df):
    fig=go.Figure()
    for col,color in [("TQR",TEAL),("Sueño","#5677c5"),("DOMS",RED),("Estrés","#d69a31")]:
        if col in df:
            fig.add_trace(go.Scatter(x=df["Fecha"],y=df[col],mode="lines+markers",name=col,
                                     line=dict(color=color,width=2),marker=dict(size=6)))
    fig.update_layout(title="Evolución del bienestar",yaxis_title="Escala de respuesta")
    return chart_style(fig)


def secret(name: str, default: Any = None) -> Any:
    """Lee primero Streamlit Secrets y después variables de entorno."""
    try:
        value = st.secrets.get(name, default)
        if value is not None:
            return value
    except Exception:
        pass
    return os.getenv(name, default)


def get_users() -> dict[str, str]:
    """Credenciales en secrets.toml: [users], una clave por usuario."""
    try:
        raw = st.secrets.get("users", {})
        return {str(k): str(v) for k, v in raw.items()}
    except Exception:
        return {}


def get_staff() -> set[str]:
    try:
        values = st.secrets.get("staff_users", DEFAULT_STAFF)
        return {str(x) for x in values}
    except Exception:
        return set(DEFAULT_STAFF)


def init_state() -> None:
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("role", None)


def logout() -> None:
    st.session_state["user"] = None
    st.session_state["role"] = None
    st.rerun()


def fetch_csv(url: str) -> pd.DataFrame:
    """Lee CSV publicado con timeout; el resultado se cachea brevemente."""
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    if response.text.lstrip().lower().startswith(("<!doctype html", "<html")):
        raise ValueError("La URL publicada devuelve HTML en lugar de CSV. Revisa el gid y la publicación de Google Sheets.")
    response.encoding = response.apparent_encoding or "utf-8"
    from io import StringIO
    return pd.read_csv(StringIO(response.text), engine="python", on_bad_lines="warn")


@st.cache_data(ttl=90, show_spinner=False)
def load_data(url: str) -> pd.DataFrame:
    df = fetch_csv(url)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def find_col(df: pd.DataFrame, starts: str) -> str | None:
    starts = starts.casefold()
    return next((c for c in df.columns if c.casefold().startswith(starts)), None)


def extract_scale(value: Any) -> float | None:
    """Convierte valores como '9 - Bien recuperado...' en 9."""
    if pd.isna(value):
        return None
    import re
    match = re.search(r"-?\d+(?:[.,]\d+)?", str(value))
    if not match:
        return None
    try:
        return float(match.group().replace(",", "."))
    except ValueError:
        return None


def normalize_tqr(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Fecha","Jugador","TQR","Sueño","DOMS","Estrés","Zona"])
    out = df.copy()
    time_col = find_col(out, "marca temporal")
    name_col = find_col(out, "nombre")
    if not time_col or not name_col:
        return pd.DataFrame(columns=["Fecha","Jugador","TQR","Sueño","DOMS","Estrés","Zona"])
    raw_dates = out[time_col].astype(str).str.strip()
    iso = pd.to_datetime(raw_dates, format="%Y-%m-%d %H:%M:%S", errors="coerce")
    local = pd.to_datetime(raw_dates, format="mixed", errors="coerce", dayfirst=True)
    out["Fecha"] = iso.fillna(local)
    out["Jugador"] = out[name_col].astype(str).str.strip()
    mapping = {
        "TQR": "¿Cómo te sientes de recuperado",
        "Sueño": "Calidad de sueño",
        "DOMS": "Dolor Muscular DOMS",
        "Estrés": "Nivel de Estrés",
    }
    for target, prefix in mapping.items():
        col = find_col(out, prefix.casefold())
        out[target] = out[col].map(extract_scale) if col else pd.NA
    zone = find_col(out, "zona corporal")
    out["Zona"] = out[zone].fillna("").astype(str).str.strip() if zone else ""
    return out.dropna(subset=["Fecha", "Jugador"]).sort_values("Fecha")


def normalize_rpe(df: pd.DataFrame) -> pd.DataFrame:
    """Interpreta tanto las cabeceras del formulario como las del envío web.

    No crea ni altera filas en Google Sheets. Solo transforma datos para lectura.
    """
    expected = ["Fecha", "Jugador", "RPE", "Minutos", "Carga", "Tipo", "Observaciones"]
    if df.empty:
        return pd.DataFrame(columns=expected)
    out = df.copy()
    time_col = find_col(out, "marca temporal") or find_col(out, "fecha")
    name_col = find_col(out, "nombre") or find_col(out, "jugador") or find_col(out, "usuario")
    rpe_col = find_col(out, "percepción del esfuerzo") or find_col(out, "rpe") or find_col(out, "esfuerzo")
    mins_col = find_col(out, "duración") or find_col(out, "minutos")
    type_col = find_col(out, "tipo de sesión") or find_col(out, "tipo")
    obs_col = find_col(out, "observaciones")
    # Cuando la pestaña usa títulos genéricos, se respeta el orden exacto del
    # payload actual: fecha, jugador, RPE, tipo, minutos, observaciones.
    if len(out.columns) >= 6 and (not time_col or not name_col or not rpe_col or not mins_col):
        cols = list(out.columns)
        time_col = time_col or cols[0]
        name_col = name_col or cols[1]
        rpe_col = rpe_col or cols[2]
        type_col = type_col or cols[3]
        mins_col = mins_col or cols[4]
        obs_col = obs_col or cols[5]
    if not all([time_col, name_col, rpe_col, mins_col]):
        return pd.DataFrame(columns=expected)
    # Los nuevos envíos usan formato ISO; los antiguos pueden ser dd/mm/aaaa.
    raw_dates = out[time_col].astype(str).str.strip()
    dates_iso = pd.to_datetime(raw_dates, format="%Y-%m-%d %H:%M:%S", errors="coerce")
    dates_local = pd.to_datetime(raw_dates, dayfirst=True, errors="coerce", format="mixed")
    out["Fecha"] = dates_iso.fillna(dates_local)
    out["Jugador"] = out[name_col].fillna("").astype(str).str.strip()
    out["RPE"] = pd.to_numeric(out[rpe_col].map(extract_scale), errors="coerce")
    out["Minutos"] = pd.to_numeric(out[mins_col], errors="coerce")
    out["Carga"] = out["RPE"] * out["Minutos"]
    out["Tipo"] = out[type_col].fillna("Sin especificar").astype(str) if type_col else "Sin especificar"
    out["Observaciones"] = out[obs_col].fillna("").astype(str) if obs_col else ""
    out = out.dropna(subset=["Fecha", "RPE", "Minutos"])
    out = out[out["Jugador"].ne("")]
    return out.sort_values("Fecha")


def submit_to_sheet(sheet_name: str, row: list[Any]) -> tuple[bool, str]:
    webhook = secret("WEBHOOK_URL", "")
    if not webhook:
        return False, "Falta configurar WEBHOOK_URL en los Secrets de Streamlit."
    try:
        response = requests.post(
            str(webhook),
            json={"sheet": sheet_name, "row": row},
            timeout=20,
        )
        response.raise_for_status()
        # Apps Script puede devolver texto o JSON según su implementación.
        try:
            body = response.json()
            if isinstance(body, dict):
                if body.get("status") == "error" or body.get("success") is False:
                    return False, str(body.get("message", "El servidor rechazó el registro."))
                if body.get("status") != "success" and body.get("success") is not True:
                    return False, "Respuesta inesperada del servidor. Comprueba la hoja antes de repetir."
        except ValueError:
            return False, "El servidor no devolvió una confirmación JSON. Comprueba la hoja antes de repetir."
        return True, "Registro confirmado por el servidor."
    except requests.RequestException as exc:
        return False, f"No se pudo confirmar el envío: {exc}. No vuelvas a enviarlo sin comprobar la hoja."


def show_brand(compact: bool = False) -> None:
    # Logo opcional; la app no falla si no se despliega el archivo.
    try:
        st.image("logo.png", width=90 if compact else 125)
    except Exception:
        st.markdown("⚽")
    if not compact:
        st.markdown(
            f'<div class="hero"><h1>Control de carga</h1>'
            f'<p>{CLUB} · Bienestar, esfuerzo y planificación</p></div>',
            unsafe_allow_html=True,
        )


def login() -> None:
    _, center, _ = st.columns([1, 1.2, 1])
    with center:
        show_brand()
        st.subheader("Acceso al portal")
        users = get_users()
        if not users:
            st.warning(
                "La aplicación está preparada, pero falta configurar las credenciales "
                "en `.streamlit/secrets.toml`. Consulta `secrets.toml.example`."
            )
        with st.form("login_form"):
            username = st.text_input("Usuario", placeholder="Tu usuario")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Entrar", type="primary", use_container_width=True)
        if submitted:
            if username in users and users[username] == password:
                st.session_state["user"] = username
                st.session_state["role"] = "staff" if username in get_staff() else "jugador"
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")


def player_portal() -> None:
    player = st.session_state["user"]
    show_brand(compact=True)
    st.title(f"Hola, {player}")
    st.caption(f"Fecha de hoy: {date.today().strftime('%d/%m/%Y')}")
    st.info("Responde con sinceridad. Si tienes dolor importante o una molestia que empeora, comunícalo directamente al cuerpo técnico o al servicio sanitario.")
    tqr_tab, rpe_tab, history_tab = st.tabs(
        ["🌤️ Control de mañana", "🏃 Post-entrenamiento", "📈 Mi seguimiento"]
    )

    with tqr_tab:
        st.subheader("Cuestionario de bienestar")
        with st.form("tqr_form", clear_on_submit=False):
            recovery = st.select_slider(
                "¿Cómo te sientes de recuperado?",
                options=[1, 3, 5, 7, 9], value=7,
                format_func=lambda x: {
                    1: "1 · Nada recuperado", 3: "3 · Poco recuperado",
                    5: "5 · Adecuadamente", 7: "7 · Bastante recuperado",
                    9: "9 · Muy recuperado",
                }[x],
            )
            sleep = st.select_slider(
                "Calidad del sueño (1 = muy mala, 5 = excelente)",
                options=[1, 2, 3, 4, 5], value=3,
            )
            doms = st.select_slider(
                "Dolor muscular / agujetas (1 = ninguno, 5 = muy alto)",
                options=[1, 2, 3, 4, 5], value=1,
            )
            stress = st.select_slider(
                "Estrés general (1 = muy bajo, 5 = muy alto)",
                options=[1, 2, 3, 4, 5], value=2,
            )
            zone = st.text_input("Zona corporal con molestias (opcional)", placeholder="Ej. aductor derecho")
            tqr_ok = st.form_submit_button("Enviar bienestar", type="primary", use_container_width=True)
        if tqr_ok:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            payload = [now, player, f"{recovery} - Escala de recuperación", f"{sleep} - Sueño",
                       f"{doms} - DOMS", f"{stress} - Estrés", zone.strip()]
            with st.spinner("Enviando respuesta…"):
                ok, message = submit_to_sheet("Import_TQR", payload)
            (st.success if ok else st.error)(message)
            if ok:
                load_data.clear()

    with rpe_tab:
        st.subheader("Carga de la sesión")
        with st.form("rpe_form", clear_on_submit=False):
            effort = st.select_slider(
                "¿Cómo de exigente ha sido la sesión?",
                options=list(range(1, 11)), value=3,
                format_func=lambda x: {
                    1: "1 · Muy ligero", 2: "2 · Ligero", 3: "3 · Moderado",
                    4: "4 · Moderado +", 5: "5 · Duro", 6: "6 · Duro +",
                    7: "7 · Muy duro", 8: "8 · Muy duro +",
                    9: "9 · Muy muy duro", 10: "10 · Máximo",
                }[x],
            )
            session_type = st.selectbox("Tipo de sesión", [
                "Campo", "Gimnasio", "Sesión de gimnasio + sesión de campo",
                "Entrenamiento porteros + sesión de campo", "Partido", "Otro"
            ])
            minutes = st.number_input("Duración total (minutos)", min_value=0, max_value=240, value=90, step=5)
            observations = st.text_area("Observaciones o molestias (opcional)", placeholder="Cuéntanos cómo te has encontrado…")
            rpe_ok = st.form_submit_button("Registrar carga", type="primary", use_container_width=True)
        if rpe_ok:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            payload = [now, player, f"{effort} - Escala RPE", session_type, int(minutes), observations.strip()]
            with st.spinner("Registrando sesión…"):
                ok, message = submit_to_sheet("Import_RPE", payload)
            (st.success if ok else st.error)(message)
            if ok:
                load_data.clear()
                st.caption(f"Carga interna estimada: {effort * int(minutes)} unidades (RPE × minutos).")

    with history_tab:
        st.subheader("Tu seguimiento")
        try:
            tqr = normalize_tqr(load_data(CSV_TQR_URL))
            rpe = normalize_rpe(load_data(CSV_RPE_URL))
            tqr = tqr[tqr["Jugador"].str.casefold() == player.casefold()]
            rpe = rpe[rpe["Jugador"].str.casefold() == player.casefold()]
            c1, c2 = st.columns(2)
            c1.metric("Respuestas de bienestar", len(tqr))
            c2.metric("Sesiones registradas", len(rpe))
            if not tqr.empty:
                st.markdown("**Bienestar reciente**")
                st.line_chart(tqr.set_index("Fecha")[["TQR", "Sueño", "DOMS", "Estrés"]].tail(21))
            if not rpe.empty:
                st.markdown("**Carga interna por sesión**")
                st.bar_chart(rpe.set_index("Fecha")[["Carga"]].tail(21))
            if tqr.empty and rpe.empty:
                st.info("Todavía no hay datos tuyos disponibles.")
        except Exception:
            st.warning("No se ha podido cargar el histórico ahora mismo.")
    st.divider()
    st.button("Cerrar sesión", on_click=logout)


def semaforo(row: pd.Series) -> str:
    tqr, doms = row.get("TQR"), row.get("DOMS")
    zone = str(row.get("Zona", "") or "").strip()
    if pd.isna(tqr):
        return "⚪ Sin respuesta"
    # Criterios iniciales tomados del documento compartido; no son diagnóstico médico.
    if tqr <= 3 or (pd.notna(doms) and doms >= 3) or zone:
        return "🔴 Revisar antes de entrenar"
    if tqr == 4 or (pd.notna(doms) and doms == 2):
        return "🟡 Atención"
    return "🟢 Seguimiento habitual"



# Las sesiones son planificación, no registros de carga. Se exportan para
# persistir en GitHub; nunca se escriben automáticamente en Import_RPE.
SESSION_FILE = Path(__file__).with_name("sesiones.csv")
SESSION_COLS = ["Fecha", "Tipo", "Etiqueta", "Rival", "Notas"]
SESSION_TYPES = ["Campo", "Gimnasio", "Sesión de gimnasio + sesión de campo",
                 "Entrenamiento porteros + sesión de campo", "Partido", "Otro"]

@st.cache_data(ttl=90,show_spinner=False)
def load_sessions():
    if not SESSION_FILE.exists():
        return pd.DataFrame(columns=SESSION_COLS)
    df=pd.read_csv(SESSION_FILE,dtype=str,keep_default_na=False,encoding="utf-8-sig")
    for c in SESSION_COLS:
        if c not in df: df[c]=""
    return df[SESSION_COLS]


def current_sessions():
    if "sessions_edit" not in st.session_state:
        st.session_state["sessions_edit"]=load_sessions().copy()
    return st.session_state["sessions_edit"]


def player_key(value):
    text=str(value).strip().casefold()
    return "".join(ch for ch in unicodedata.normalize("NFKD",text) if not unicodedata.combining(ch))


def valid_rpe(df):
    if df.empty or "Fecha" not in df: return pd.DataFrame(columns=["Fecha","Jugador","Carga","RPE","Minutos"])
    out=df.copy()
    out["Carga"]=pd.to_numeric(out["Carga"],errors="coerce")
    out=out.dropna(subset=["Fecha","Carga"])
    return out[out["Carga"]>=0].copy()


def daily_loads(df, player, end_date, days=7):
    dates=pd.date_range(end=pd.Timestamp(end_date).normalize(),periods=days,freq="D")
    d=df[df["Jugador"].map(player_key)==player_key(player)].copy() if not df.empty else df.copy()
    if d.empty: return pd.Series(0.0,index=dates)
    d["Día"]=d["Fecha"].dt.normalize()
    return d.groupby("Día")["Carga"].sum().reindex(dates,fill_value=0.0).astype(float)


def weekly_metrics(df, player, end_date):
    daily=daily_loads(df,player,end_date,7)
    total=float(daily.sum()); mean=float(daily.mean()); sd=float(daily.std(ddof=0))
    monotony=mean/sd if sd>0 else None
    strain=total*monotony if monotony is not None else None
    return daily,total,monotony,strain


def microcycle_table(sessions, match_day):
    if sessions.empty: return pd.DataFrame(columns=["Fecha","Día relativo","Tipo","Etiqueta","Rival","Notas"])
    out=sessions.copy()
    out["Fecha_dt"]=pd.to_datetime(out["Fecha"],errors="coerce",format="%Y-%m-%d")
    out=out.dropna(subset=["Fecha_dt"])
    delta=(out["Fecha_dt"].dt.normalize()-pd.Timestamp(match_day).normalize()).dt.days
    out["Día relativo"]=delta.map(lambda n: "MD" if n==0 else f"MD{n:+d}")
    out=out[delta.between(-7,0)].sort_values("Fecha_dt")
    return out[["Fecha","Día relativo","Tipo","Etiqueta","Rival","Notas"]]


def pdf_weekly(player, profile, rpe, tqr, end_date):
    # PDF exclusivamente en memoria; no persiste ni envía información.
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib.colors import HexColor,white
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    buff=io.BytesIO()
    doc=SimpleDocTemplate(buff,pagesize=A4,rightMargin=1.8*cm,leftMargin=1.8*cm,
                          topMargin=1.8*cm,bottomMargin=1.8*cm)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ClubTitle",parent=styles["Title"],fontName="Helvetica-Bold",fontSize=20,
                              leading=25,textColor=HexColor(NAVY),spaceAfter=8,alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="ClubBody",parent=styles["BodyText"],fontSize=9.5,leading=14,spaceAfter=9))
    name=" ".join(str(profile.get(k,"")).strip() for k in ("Nombre","Apellidos")).strip() or player
    daily,total,monotony,strain=weekly_metrics(rpe,player,end_date)
    start=(pd.Timestamp(end_date)-pd.Timedelta(days=6)).date()
    filtered=rpe[(rpe["Jugador"].map(player_key)==player_key(player)) &
                 (rpe["Fecha"].dt.date>=start)&(rpe["Fecha"].dt.date<=end_date)].copy() if not rpe.empty else rpe.copy()
    own_tqr=tqr[(tqr["Jugador"].map(player_key)==player_key(player)) &
                (tqr["Fecha"].dt.date>=start)&(tqr["Fecha"].dt.date<=end_date)].copy() if not tqr.empty else tqr.copy()
    p=lambda t: Paragraph(html.escape(str(t)),styles["ClubBody"])
    story=[Paragraph("UCD LA CAÑADA ATLÉTICO",styles["ClubTitle"]),
           p("INFORME INDIVIDUAL · CONTROL DE CARGA"),
           p(f"Futbolista: {name} | Periodo: {start:%d/%m/%Y} – {end_date:%d/%m/%Y}"),
           Spacer(1,10)]
    rows=[["Carga 7 días","Sesiones","RPE medio","Monotonía","Strain"],
          [f"{total:,.0f} UA",str(len(filtered)),
           f"{filtered['RPE'].mean():.1f}" if not filtered.empty else "—",
           f"{monotony:.2f}" if monotony is not None else "N/D",
           f"{strain:,.0f}" if strain is not None else "N/D"]]
    table=Table(rows,colWidths=[3.2*cm]*5,rowHeights=[.8*cm,.9*cm]);table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),HexColor(NAVY)),("TEXTCOLOR",(0,0),(-1,0),white),
        ("BACKGROUND",(0,1),(-1,1),HexColor("#edf3f8")),
        ("TEXTCOLOR",(0,1),(-1,1),HexColor(NAVY)),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),9),
        ("BOTTOMPADDING",(0,0),(-1,-1),9)]))
    story += [table,Spacer(1,18),p("CARGA DIARIA (UA)")]
    day_rows=[["Día","Carga (UA)"]]+[[d.strftime("%d/%m/%Y"),f"{v:,.0f}"] for d,v in daily.items()]
    day_table=Table(day_rows,colWidths=[8*cm,8*cm]);day_table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),HexColor("#e6edf5")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[white,HexColor("#f6f8fb")]),
        ("FONTSIZE",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("TOPPADDING",(0,0),(-1,-1),6)]))
    story += [day_table,Spacer(1,14),p(f"Bienestar: {len(own_tqr)} respuestas registradas durante el periodo."),
              p("Monotonía = media de la carga diaria / desviación estándar poblacional de 7 días. "
                "Strain = carga semanal × monotonía. Si la desviación es cero, se informa N/D. "
                "Los días sin registro se contabilizan como 0 UA registradas; no confirman descanso. "
                "Indicadores descriptivos, no diagnósticos de lesión."),
              p("Fuente: registros disponibles de Google Sheets (RPE y TQR). "
                "La ausencia de registro no implica ausencia de entrenamiento.")]
    doc.build(story)
    return buff.getvalue()


def participation_panel(rpe, players, sessions):
    st.markdown('<div class="section-kicker">Seguimiento operativo</div>',unsafe_allow_html=True)
    st.subheader("Control de participación · registros RPE")
    st.caption("Se comprueba quién ha enviado RPE, no quién asistió físicamente. Una sesión sin respuesta no equivale a ausencia.")
    if sessions.empty:
        st.info("Primero planifica al menos una sesión en 'Microciclos'. No se presupone que todos entrenen cada día.")
        return
    sessions=sessions.copy()
    sessions["Fecha_dt"]=pd.to_datetime(sessions["Fecha"],format="%Y-%m-%d",errors="coerce")
    sessions=sessions.dropna(subset=["Fecha_dt"])
    if sessions.empty:
        st.info("No hay sesiones con fecha válida.")
        return
    options=sorted(sessions["Fecha_dt"].dt.date.unique(),reverse=True)
    day=st.selectbox("Fecha de sesión planificada",options,format_func=lambda x:x.strftime("%d/%m/%Y"))
    day_sessions=sessions[sessions["Fecha_dt"].dt.date==day]
    st.dataframe(day_sessions[["Tipo","Etiqueta","Rival","Notas"]],hide_index=True,use_container_width=True)
    st.caption("Si hay varias sesiones el mismo día, el formulario actual no permite atribuir cada RPE a una sesión concreta.")
    eligible=st.multiselect("Jugadores convocados / esperados para registrar",players,default=players,
                            help="Ajusta los esperados según convocatoria y disponibilidad; no se guarda fuera de esta sesión.")
    recorded=rpe[rpe["Fecha"].dt.date==day] if not rpe.empty else rpe
    keys={player_key(v) for v in recorded.get("Jugador",pd.Series(dtype=str))}
    done=[p for p in eligible if player_key(p) in keys]
    pending=[p for p in eligible if player_key(p) not in keys]
    a,b,c=st.columns(3)
    a.metric("Esperados",len(eligible));b.metric("RPE recibidos",len(done));c.metric("Pendientes",len(pending))
    if eligible: st.progress(len(done)/len(eligible),text=f"Cumplimiento de registro: {len(done)}/{len(eligible)}")
    left,right=st.columns(2)
    with left:
        st.markdown("**Registrados**")
        st.dataframe(pd.DataFrame({"Jugador":done}),hide_index=True,use_container_width=True)
    with right:
        st.markdown("**Pendientes de registrar**")
        st.dataframe(pd.DataFrame({"Jugador":pending}),hide_index=True,use_container_width=True)
        st.download_button("Descargar pendientes CSV",pd.DataFrame({"Jugador":pending}).to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"rpe_pendientes_{day}.csv",mime="text/csv")


def microcycles_panel(sessions):
    st.markdown('<div class="section-kicker">Planificación deportiva</div>',unsafe_allow_html=True)
    st.subheader("Calendario de microciclos")
    st.caption("Planifica entrenamientos y partidos. Los cambios se guardan en la sesión del navegador hasta descargar sesiones.csv y subirlo al repositorio.")
    with st.form("new_session",clear_on_submit=True):
        c1,c2,c3=st.columns([1,2,1])
        with c1: session_date=st.date_input("Fecha",value=date.today(),key="new_session_date")
        with c2: kind=st.selectbox("Tipo",SESSION_TYPES)
        with c3: label=st.text_input("Etiqueta",placeholder="MD-2, técnica…")
        rival=st.text_input("Rival (si corresponde)")
        notes=st.text_input("Notas")
        add=st.form_submit_button("Añadir sesión planificada",type="primary")
    if add:
        new=pd.DataFrame([{"Fecha":session_date.isoformat(),"Tipo":kind,"Etiqueta":label.strip(),
                           "Rival":rival.strip(),"Notas":notes.strip()}])
        st.session_state["sessions_edit"]=pd.concat([sessions,new],ignore_index=True)
        st.success("Sesión añadida a la planificación local. Descarga el CSV para conservarla.")
        sessions=st.session_state["sessions_edit"]
    if not sessions.empty:
        st.markdown("**Editar planificación**")
        edited=st.data_editor(sessions,num_rows="dynamic",hide_index=True,use_container_width=True,key="sessions_editor")
        if st.button("Aplicar cambios de calendario"):
            st.session_state["sessions_edit"]=edited[SESSION_COLS].fillna("").astype(str)
            sessions=st.session_state["sessions_edit"]
            st.success("Cambios aplicados en esta sesión.")
        st.dataframe(sessions,use_container_width=True,hide_index=True)
    st.download_button("Descargar sesiones.csv",sessions.to_csv(index=False).encode("utf-8-sig"),
                       file_name="sesiones.csv",mime="text/csv",use_container_width=True)
    st.divider()
    match_day=st.date_input("Fecha de partido (MD)",value=date.today(),key="md_day")
    micro=microcycle_table(sessions,match_day)
    if micro.empty:
        st.info("Sin sesiones planificadas entre MD-7 y MD para la fecha seleccionada.")
    else:
        st.dataframe(micro,hide_index=True,use_container_width=True)
        counts=micro.groupby("Día relativo").size().reset_index(name="Sesiones")
        fig=px.bar(counts,x="Día relativo",y="Sesiones",color_discrete_sequence=[TEAL],text="Sesiones")
        fig.update_layout(title="Distribución del microciclo")
        st.plotly_chart(chart_style(fig,310),use_container_width=True)


def analytics_panel(rpe, tqr, players):
    st.markdown('<div class="section-kicker">Ciencia del deporte</div>',unsafe_allow_html=True)
    st.subheader("Análisis de carga semanal")
    st.caption("Los cálculos utilizan las cargas registradas. Un día sin registro se representa como 0 UA, pero puede ser un dato pendiente.")
    end_date=st.date_input("Fecha final de la semana",value=date.today(),key="analysis_date")
    if not players:
        st.info("No hay futbolistas en plantilla.")
        return
    player=st.selectbox("Futbolista",players,key="analysis_player")
    daily,total,monotony,strain=weekly_metrics(rpe,player,end_date)
    cols=st.columns(4)
    cols[0].metric("Carga 7 días",f"{total:,.0f} UA")
    cols[1].metric("Media diaria",f"{daily.mean():,.0f} UA")
    cols[2].metric("Monotonía",f"{monotony:.2f}" if monotony is not None else "N/D")
    cols[3].metric("Strain",f"{strain:,.0f}" if strain is not None else "N/D")
    fig=plot_daily(pd.DataFrame({"Día":daily.index,"Carga":daily.values}),"Distribución diaria · últimos 7 días")
    st.plotly_chart(fig,use_container_width=True)
    st.caption("Monotonía = media diaria / desviación estándar poblacional. Strain = carga de 7 días × monotonía. "
               "No se calcula monotonía si la desviación es cero; no se utilizan umbrales de riesgo clínico.")
    with st.expander("Comparativa de plantilla · misma semana"):
        rows=[]
        for name in players:
            d,t,m,stn=weekly_metrics(rpe,name,end_date)
            rows.append({"Jugador":name,"Carga 7d":round(t),"Media diaria":round(d.mean()),
                         "Monotonía":round(m,2) if m is not None else None,
                         "Strain":round(stn) if stn is not None else None})
        comp=pd.DataFrame(rows).sort_values("Carga 7d",ascending=False)
        st.dataframe(comp,use_container_width=True,hide_index=True)
        fig=px.bar(comp.head(15).sort_values("Carga 7d"),x="Carga 7d",y="Jugador",orientation="h",
                   color_discrete_sequence=[TEAL],text="Carga 7d")
        fig.update_layout(title="Carga semanal · 15 primeras cargas registradas")
        st.plotly_chart(chart_style(fig,480),use_container_width=True)


def reports_panel(rpe,tqr,profiles,players):
    st.markdown('<div class="section-kicker">Documentación</div>',unsafe_allow_html=True)
    st.subheader("Informe individual semanal · PDF")
    if not players:
        st.info("Sin futbolistas disponibles.")
        return
    player=st.selectbox("Futbolista",players,key="pdf_player")
    end_date=st.date_input("Fecha de cierre",value=date.today(),key="pdf_end")
    st.caption("Informe de 7 días con carga, sesiones, distribución diaria, monotonía y strain. No se almacena ni envía a terceros.")
    if st.button("Preparar informe PDF",type="primary"):
        try:
            pdf=pdf_weekly(player,player_profile(player,profiles),rpe,tqr,end_date)
            st.session_state["weekly_pdf"]=(player,end_date,pdf)
        except ImportError:
            st.error("Falta la dependencia reportlab. Añade reportlab>=4.0 a requirements.txt.")
        except Exception as exc:
            st.error(f"No se ha podido generar el informe: {exc}")
    if "weekly_pdf" in st.session_state:
        pdf_player,pdf_date,pdf_bytes=st.session_state["weekly_pdf"]
        st.download_button(f"Descargar PDF · {pdf_player}",pdf_bytes,
                           file_name=f"informe_{player_key(pdf_player).replace(' ','_')}_{pdf_date}.pdf",
                           mime="application/pdf",use_container_width=True)


def staff_portal() -> None:
    show_brand(compact=True)
    st.title("Panel de control · Rendimiento")
    st.caption(f"Bienvenido, {st.session_state['user']} · {date.today().strftime('%d/%m/%Y')}")
    refresh_col, logout_col = st.columns([5, 1])
    with refresh_col:
        st.caption("Datos de Google Sheets · actualización automática de caché cada 90 segundos")
    with logout_col:
        st.button("Cerrar sesión", on_click=logout)

    try:
        raw_tqr = load_data(CSV_TQR_URL)
        raw_rpe = load_data(CSV_RPE_URL)
        tqr = normalize_tqr(raw_tqr)
        rpe = normalize_rpe(raw_rpe)
    except Exception as exc:
        st.error("No se han podido leer las hojas publicadas de Google Sheets.")
        st.caption(f"Detalle técnico: {exc}")
        if st.button("Reintentar carga"):
            load_data.clear()
            st.rerun()
        return

    with st.sidebar:
        st.markdown("### Primer equipo")
        section = st.radio("Área", ["Panel de rendimiento", "Jugadores", "Participación RPE", "Análisis semanal", "Microciclos", "Informes PDF"], key="staff_section")

    profiles = load_profiles()
    players = sorted((set(ROSTER) | set(profiles["Usuario"].dropna()) |
                      set(tqr.get("Jugador", pd.Series(dtype=str)).dropna()) |
                      set(rpe.get("Jugador", pd.Series(dtype=str)).dropna())) - {""})
    rpe = valid_rpe(rpe)
    sessions = current_sessions()
    if section == "Participación RPE":
        participation_panel(rpe,players,sessions)
        return
    if section == "Análisis semanal":
        analytics_panel(rpe,tqr,players)
        return
    if section == "Microciclos":
        microcycles_panel(sessions)
        return
    if section == "Informes PDF":
        reports_panel(rpe,tqr,profiles,players)
        return

    if section == "Jugadores":
        profiles = load_profiles()
        players = sorted((set(ROSTER) | set(profiles["Usuario"].dropna()) |
                          set(tqr.get("Jugador", pd.Series(dtype=str)).dropna()) |
                          set(rpe.get("Jugador", pd.Series(dtype=str)).dropna())) - {""})
        st.subheader("Primer equipo · Gestión de plantilla")
        st.caption("Fichas, carga individual y edición de datos. Los cambios de fichas se exportan a CSV para conservarlos en el repositorio.")
        search = st.text_input("Buscar jugador", placeholder="Usuario, nombre o apellidos")
        filtered = [u for u in players if search.casefold() in
                    (u + " " + player_profile(u, profiles).get("Nombre", "") + " " +
                     player_profile(u, profiles).get("Apellidos", "")).casefold()]
        if not filtered:
            st.info("No hay jugadores que coincidan con la búsqueda.")
            return
        selected = st.selectbox("Seleccionar futbolista", filtered)
        if "profiles_edit" not in st.session_state:
            st.session_state["profiles_edit"] = profiles.copy()
        working = st.session_state["profiles_edit"]
        info = player_profile(selected, working)
        name = " ".join(x for x in [info.get("Nombre", ""), info.get("Apellidos", "")] if x).strip() or selected
        st.markdown(f"### {name}")
        profile_tab, performance_tab, edit_tab = st.tabs(["Ficha", "Rendimiento", "Editar ficha"])
        own_rpe = rpe[rpe["Jugador"].astype(str).str.casefold() == selected.casefold()].copy() if not rpe.empty else rpe.copy()
        own_tqr = tqr[tqr["Jugador"].astype(str).str.casefold() == selected.casefold()].copy() if not tqr.empty else tqr.copy()
        with profile_tab:
            a, b, c = st.columns(3)
            a.metric("Edad", age_from_birthdate(info.get("Fecha_nacimiento", "")))
            b.metric("Posición", info.get("Posicion") or "Sin completar")
            c.metric("Dorsal", info.get("Dorsal") or "Sin completar")
            st.write(f"**Nombre:** {info.get('Nombre') or 'Sin completar'}")
            st.write(f"**Apellidos:** {info.get('Apellidos') or 'Sin completar'}")
            st.write(f"**Fecha de nacimiento:** {info.get('Fecha_nacimiento') or 'Sin completar'}")
            st.caption(f"Identificador de acceso: {selected}")
        with performance_tab:
            st.markdown("#### Carga interna · RPE × minutos")
            end_date = st.date_input("Fecha de referencia", value=date.today(), key="player_end_date")
            end_ts = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
            metrics = st.columns(3)
            for col, window in zip(metrics, (7, 14, 28)):
                cutoff = pd.Timestamp(end_date) - pd.Timedelta(days=window-1)
                window_rpe = own_rpe[(own_rpe["Fecha"] >= cutoff) & (own_rpe["Fecha"] <= end_ts)] if not own_rpe.empty else own_rpe
                col.metric(f"Últimos {window} días", f"{window_rpe['Carga'].sum():.0f} UA", f"{len(window_rpe)} sesiones", delta_color="off")
            a, b, c = st.columns(3)
            a.metric("Sesiones registradas", len(own_rpe))
            b.metric("Carga total histórica", f"{own_rpe['Carga'].sum():.0f} UA" if not own_rpe.empty else "0 UA")
            c.metric("Respuestas de bienestar", len(own_tqr))
            if not own_rpe.empty:
                chart_rpe = own_rpe.copy()
                chart_rpe["Día"] = chart_rpe["Fecha"].dt.date
                daily = chart_rpe.groupby("Día", as_index=False)["Carga"].sum()
                st.plotly_chart(px.bar(daily, x="Día", y="Carga", title="Evolución diaria de la carga interna"), use_container_width=True)
                st.dataframe(own_rpe[["Fecha", "RPE", "Minutos", "Carga", "Tipo"]].sort_values("Fecha", ascending=False), use_container_width=True, hide_index=True)
            else:
                st.info("No hay sesiones RPE reconocidas para este futbolista. Comprueba la coincidencia del nombre de usuario con Google Sheets.")
            if not own_tqr.empty:
                st.markdown("#### Evolución del bienestar")
                wellness_cols = [c for c in ["TQR", "Sueño", "DOMS", "Estrés"] if c in own_tqr]
                if wellness_cols:
                    st.plotly_chart(plot_wellness(own_tqr.tail(60)),use_container_width=True)
        with edit_tab:
            st.info("La edición se mantiene durante esta sesión. Descarga el CSV y sustituye jugadores.csv en GitHub para guardar los cambios de forma permanente. No modifica Google Sheets ni los registros de carga.")
            with st.form("edit_player_profile"):
                first = st.text_input("Nombre", value=info.get("Nombre", ""))
                last = st.text_input("Apellidos", value=info.get("Apellidos", ""))
                birth = st.text_input("Fecha de nacimiento (DD/MM/AAAA)", value=info.get("Fecha_nacimiento", ""))
                position = st.text_input("Posición", value=info.get("Posicion", ""))
                number = st.text_input("Dorsal", value=info.get("Dorsal", ""))
                save = st.form_submit_button("Aplicar cambios a la plantilla", type="primary")
            if save:
                if birth.strip() and pd.isna(pd.to_datetime(birth, dayfirst=True, errors="coerce")):
                    st.error("La fecha de nacimiento no es válida. Usa DD/MM/AAAA.")
                else:
                    row = {"Usuario": selected, "Nombre": first.strip(), "Apellidos": last.strip(),
                           "Fecha_nacimiento": birth.strip(), "Posicion": position.strip(), "Dorsal": number.strip()}
                    working = working[working["Usuario"].str.casefold() != selected.casefold()].copy()
                    working = pd.concat([working, pd.DataFrame([row])], ignore_index=True)
                    st.session_state["profiles_edit"] = working
                    st.success("Cambios aplicados en esta sesión. Descarga el CSV para conservarlos.")
            st.download_button("Descargar jugadores.csv actualizado",
                               data=st.session_state["profiles_edit"].to_csv(index=False).encode("utf-8-sig"),
                               file_name="jugadores.csv", mime="text/csv", use_container_width=True)
        return

    if tqr.empty and rpe.empty:
        st.info("Las hojas están accesibles, pero aún no hay registros que se puedan interpretar.")
        return

    tqr["Semáforo"] = tqr.apply(semaforo, axis=1) if not tqr.empty else []
    all_players = sorted(set(tqr.get("Jugador", pd.Series(dtype=str)).dropna().tolist()) |
                         set(rpe.get("Jugador", pd.Series(dtype=str)).dropna().tolist()))
    today = date.today()
    with st.sidebar:
        st.header("Filtros")
        selected_date = st.date_input("Fecha de referencia", value=today)
        player_filter = st.selectbox("Jugador", ["Toda la plantilla"] + all_players)
        days = st.selectbox("Ventana de carga", [7, 14, 28], index=1, format_func=lambda x: f"Últimos {x} días")
        if st.button("Actualizar datos", use_container_width=True):
            load_data.clear()
            st.rerun()

    ref = pd.Timestamp(selected_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    start = ref - pd.Timedelta(days=days-1)
    recent_tqr = tqr[(tqr["Fecha"] >= start) & (tqr["Fecha"] <= ref)] if not tqr.empty else tqr
    recent_rpe = rpe[(rpe["Fecha"] >= start) & (rpe["Fecha"] <= ref)] if not rpe.empty else rpe
    if player_filter != "Toda la plantilla":
        recent_tqr = recent_tqr[recent_tqr["Jugador"] == player_filter]
        recent_rpe = recent_rpe[recent_rpe["Jugador"] == player_filter]

    latest = (recent_tqr.sort_values("Fecha").groupby("Jugador", as_index=False).tail(1)
              if not recent_tqr.empty else pd.DataFrame())
    red_count = int(latest["Semáforo"].str.startswith("🔴").sum()) if not latest.empty else 0
    yellow_count = int(latest["Semáforo"].str.startswith("🟡").sum()) if not latest.empty else 0
    responses_today = int((recent_tqr["Fecha"].dt.date == selected_date).sum()) if not recent_tqr.empty else 0
    total_load = float(recent_rpe["Carga"].sum()) if not recent_rpe.empty else 0.0
    avg_tqr = float(latest["TQR"].mean()) if not latest.empty else float("nan")

    st.subheader("Vista rápida")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Respuestas de bienestar", len(recent_tqr), f"{responses_today} en la fecha elegida")
    k2.metric("Jugadores en rojo", red_count, "Revisar individualmente")
    k3.metric("TQR medio más reciente", "—" if pd.isna(avg_tqr) else f"{avg_tqr:.1f}/9")
    k4.metric(f"Carga acumulada · {days} días", f"{total_load:,.0f} UA".replace(",", "."))

    if not recent_rpe.empty:
        st.markdown("### Pulso de la plantilla")
        a,b=st.columns([1.5,1])
        with a:
            by_day=recent_rpe.assign(Día=recent_rpe["Fecha"].dt.normalize()).groupby("Día",as_index=False)["Carga"].sum()
            st.plotly_chart(plot_daily(by_day,"Carga diaria · plantilla"),use_container_width=True)
        with b:
            types=recent_rpe.groupby("Tipo",as_index=False)["Carga"].sum().sort_values("Carga",ascending=False)
            fig=px.pie(types,values="Carga",names="Tipo",hole=.68,
                       color_discrete_sequence=[NAVY,TEAL,RED,"#7897b2","#d3a34a","#8794a9"])
            fig.update_layout(title="Distribución de carga por tipo",showlegend=True)
            fig.update_traces(textinfo="percent",hovertemplate="%{label}: %{value:,.0f} UA<extra></extra>")
            st.plotly_chart(chart_style(fig),use_container_width=True)

    tab1, tab2, tab3, tab4 = st.tabs(
        ["🚦 Bienestar diario", "🏃 Carga interna", "📈 Evolución individual", "📋 Datos y exportación"]
    )
    with tab1:
        st.subheader("Última respuesta disponible por jugador")
        if latest.empty:
            st.info("No hay respuestas de bienestar en el periodo seleccionado.")
        else:
            view = latest[["Jugador", "Fecha", "TQR", "Sueño", "DOMS", "Estrés", "Zona", "Semáforo"]].copy()
            view["Fecha"] = view["Fecha"].dt.strftime("%d/%m/%Y %H:%M")
            view = view.sort_values(["Semáforo", "TQR"], ascending=[True, True])
            st.dataframe(view, use_container_width=True, hide_index=True)
            st.caption("El semáforo es una señal de seguimiento, no un diagnóstico ni una autorización médica para entrenar.")
            if red_count:
                st.warning(f"Hay {red_count} jugador(es) que requieren revisión individual antes de decidir la carga.")
            if not recent_tqr.empty:
                daily = recent_tqr.groupby(recent_tqr["Fecha"].dt.date).agg(
                    TQR_medio=("TQR", "mean"), Respuestas=("Jugador", "nunique")
                ).reset_index(names="Fecha")
                fig=px.line(daily,x="Fecha",y="TQR_medio",markers=True,
                            color_discrete_sequence=[TEAL],title="Evolución del TQR medio")
                fig.update_traces(line_width=3,marker_size=8)
                st.plotly_chart(chart_style(fig),use_container_width=True)
    with tab2:
        st.subheader("Carga interna (RPE × duración)")
        if recent_rpe.empty:
            st.info("No hay cargas en el periodo seleccionado.")
        else:
            daily_load = recent_rpe.groupby(recent_rpe["Fecha"].dt.date, as_index=False).agg(
                Carga=("Carga", "sum"), Sesiones=("Jugador", "count"), RPE_medio=("RPE", "mean")
            ).rename(columns={"Fecha": "Día"})
            st.plotly_chart(plot_daily(daily_load,"Carga interna registrada por día"),use_container_width=True)
            per_player = recent_rpe.groupby("Jugador", as_index=False).agg(
                Carga_total=("Carga", "sum"), Minutos=("Minutos", "sum"), Sesiones=("Carga", "count"),
                RPE_medio=("RPE", "mean")
            ).sort_values("Carga_total", ascending=False)
            st.dataframe(per_player, use_container_width=True, hide_index=True)
            st.caption("UA = RPE de la sesión × minutos. Comparar tendencias del mismo jugador es más útil que interpretar un valor aislado.")
    with tab3:
        st.subheader("Histórico de un jugador")
        if not all_players:
            st.info("No hay jugadores en los registros.")
        else:
            chosen = st.selectbox("Selecciona jugador para el histórico", all_players, key="history_player")
            ptqr = tqr[tqr["Jugador"] == chosen].sort_values("Fecha") if not tqr.empty else pd.DataFrame()
            prpe = rpe[rpe["Jugador"] == chosen].sort_values("Fecha") if not rpe.empty else pd.DataFrame()
            left, right = st.columns(2)
            with left:
                st.markdown("**Bienestar**")
                if not ptqr.empty:
                    st.plotly_chart(plot_wellness(ptqr.tail(60)),use_container_width=True)
                else:
                    st.info("Sin datos de bienestar.")
            with right:
                st.markdown("**Carga interna**")
                if not prpe.empty:
                    prpe_daily=prpe.assign(Día=prpe["Fecha"].dt.normalize()).groupby("Día",as_index=False)["Carga"].sum()
                    st.plotly_chart(plot_daily(prpe_daily,"Carga interna individual"),use_container_width=True)
                else:
                    st.info("Sin datos de carga.")
            if not ptqr.empty and not prpe.empty:
                st.markdown("**Contexto reciente**")
                st.write(f"Último TQR: {ptqr.iloc[-1]['TQR'] if pd.notna(ptqr.iloc[-1]['TQR']) else 'sin dato'} · "
                         f"Última respuesta: {ptqr.iloc[-1]['Fecha']:%d/%m/%Y %H:%M}")
                st.write(f"Última carga registrada: {prpe.iloc[-1]['Carga']:.0f} UA · "
                         f"{prpe.iloc[-1]['Fecha']:%d/%m/%Y %H:%M}")
    with tab4:
        st.subheader("Registros del periodo")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Bienestar (TQR)**")
            st.dataframe(recent_tqr.sort_values("Fecha", ascending=False), use_container_width=True, hide_index=True)
            st.download_button("Descargar TQR CSV", recent_tqr.to_csv(index=False).encode("utf-8-sig"),
                               file_name="control_tqr.csv", mime="text/csv", use_container_width=True)
        with c2:
            st.markdown("**Carga (RPE)**")
            st.dataframe(recent_rpe.sort_values("Fecha", ascending=False), use_container_width=True, hide_index=True)
            st.download_button("Descargar RPE CSV", recent_rpe.to_csv(index=False).encode("utf-8-sig"),
                               file_name="control_rpe.csv", mime="text/csv", use_container_width=True)


init_state()
if st.session_state["user"] is None:
    login()
elif st.session_state["role"] == "jugador":
    player_portal()
else:
    staff_portal()
