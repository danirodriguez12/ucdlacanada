from __future__ import annotations

import os
from datetime import datetime, date, timedelta
from typing import Any

import pandas as pd
import plotly.express as px
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
DEFAULT_STAFF = ["Manuelcarminati", "Danirodriguez", "Nicorodriguez", "Danimoreno"]

# Estética adaptada a la referencia visual del club.
st.markdown("""
<style>
:root { --navy:#172b4d; --red:#f0444d; --muted:#6b7890; }
.block-container {max-width: 1440px; padding-top: 1.8rem; padding-bottom: 3rem;}
h1,h2,h3 {color:var(--navy);}
.hero {background:linear-gradient(120deg,#172b4d,#243e65);padding:1.35rem 1.5rem;border-radius:18px;color:white;margin-bottom:1.2rem;}
.hero h1 {color:white;margin:0;font-size:2rem;}
.hero p {color:#e8eef8;margin:.35rem 0 0 0;}
.kpi {border:1px solid #e6eaf0;border-radius:14px;padding:1rem 1.1rem;background:#fff;min-height:105px;}
.kpi-label {font-size:.84rem;color:#6b7890;}
.kpi-value {font-size:1.75rem;font-weight:750;color:#172b4d;line-height:1.3;}
.kpi-note {font-size:.8rem;color:#6b7890;}
.small-muted {color:#6b7890;font-size:.9rem;}
div[data-testid="stMetric"] {background:#fff;border:1px solid #e6eaf0;padding:14px 16px;border-radius:14px;}
</style>
""", unsafe_allow_html=True)


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
        return df.copy()
    out = df.copy()
    time_col = find_col(out, "marca temporal")
    name_col = find_col(out, "nombre")
    if not time_col or not name_col:
        return pd.DataFrame()
    out["Fecha"] = pd.to_datetime(out[time_col], errors="coerce", dayfirst=True)
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
    if df.empty:
        return df.copy()
    out = df.copy()
    time_col = find_col(out, "marca temporal")
    name_col = find_col(out, "nombre")
    rpe_col = find_col(out, "percepción del esfuerzo")
    mins_col = find_col(out, "duración")
    type_col = find_col(out, "tipo de sesión")
    obs_col = find_col(out, "observaciones")
    if not time_col or not name_col:
        return pd.DataFrame()
    out["Fecha"] = pd.to_datetime(out[time_col], errors="coerce", dayfirst=True)
    out["Jugador"] = out[name_col].astype(str).str.strip()
    out["RPE"] = out[rpe_col].map(extract_scale) if rpe_col else pd.NA
    out["Minutos"] = pd.to_numeric(out[mins_col], errors="coerce") if mins_col else 0
    out["Carga"] = out["RPE"] * out["Minutos"]
    out["Tipo"] = out[type_col].fillna("Sin especificar").astype(str) if type_col else "Sin especificar"
    out["Observaciones"] = out[obs_col].fillna("").astype(str) if obs_col else ""
    return out.dropna(subset=["Fecha", "Jugador"]).sort_values("Fecha")


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
            if isinstance(body, dict) and body.get("success") is False:
                return False, str(body.get("message", "El servidor rechazó el registro."))
        except ValueError:
            pass
        return True, "Registro enviado. Comprueba la hoja si no aparece de inmediato."
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

    with rpe_tab:
        st.subheader("Carga de la sesión")
        with st.form("rpe_form", clear_on_submit=False):
            effort = st.select_slider(
                "¿Cómo de exigente ha sido la sesión?",
                options=[1, 2, 3, 5, 7, 10], value=3,
                format_func=lambda x: {
                    1: "1 · Muy ligero", 2: "2 · Ligero", 3: "3 · Moderado",
                    5: "5 · Duro", 7: "7 · Muy duro", 10: "10 · Máximo",
                }[x],
            )
            session_type = st.selectbox("Tipo de sesión", ["Campo", "Gimnasio", "Recuperación", "Partido", "Otro"])
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
                st.plotly_chart(px.line(daily, x="Fecha", y="TQR_medio", markers=True,
                                       title="Evolución del TQR medio"), use_container_width=True)
    with tab2:
        st.subheader("Carga interna (RPE × duración)")
        if recent_rpe.empty:
            st.info("No hay cargas en el periodo seleccionado.")
        else:
            daily_load = recent_rpe.groupby(recent_rpe["Fecha"].dt.date, as_index=False).agg(
                Carga=("Carga", "sum"), Sesiones=("Jugador", "count"), RPE_medio=("RPE", "mean")
            ).rename(columns={"Fecha": "Día"})
            st.plotly_chart(px.bar(daily_load, x="Día", y="Carga", title="Carga interna registrada por día"),
                            use_container_width=True)
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
                    st.line_chart(ptqr.set_index("Fecha")[["TQR", "Sueño", "DOMS", "Estrés"]].tail(60))
                else:
                    st.info("Sin datos de bienestar.")
            with right:
                st.markdown("**Carga interna**")
                if not prpe.empty:
                    st.bar_chart(prpe.set_index("Fecha")[["Carga"]].tail(60))
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
