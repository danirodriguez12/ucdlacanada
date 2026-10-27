import streamlit as st
import pandas as pd
from datetime import datetime
import requests

st.set_page_config(page_title="Control de Carga - UCD La Cañada", page_icon="⚽", layout="centered")

# URL de tu aplicación web de Google Apps Script para recibir los envíos
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbxLBVTUkg7nZDs2oPmd94YOUXzUQ9KXD3tFCfnQAlwC5koz9uFdFJIP-N3aHooG7nww3Q/exec"

# Enlaces CSV directos de tus pestañas publicadas en Google Sheets (para el panel de staff)
CSV_TQR_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTNC-xJmcfT39bVMWEjqGAbfTUv1kRRudtLWwTQvsoCDy_gb5ggcCyZaHkqAT9CkoQhQ2v8eB0jTPjc/pub?output=csv&sheet=Import_TQR"
CSV_RPE_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTNC-xJmcfT39bVMWEjqGAbfTUv1kRRudtLWwTQvsoCDy_gb5ggcCyZaHkqAT9CkoQhQ2v8eB0jTPjc/pub?output=csv&sheet=Import_RPE"

# Base de datos interna de usuarios (staff y los 27 jugadores exactos)
USUARIOS = {
    "Manuelcarminati": {"pass": "Manuelcarminati", "rol": "staff"},
    "Danirodriguez": {"pass": "Danirodriguez", "rol": "staff"},
    "Nicorodriguez": {"pass": "Nicorodriguez", "rol": "staff"},
    "Danimoreno": {"pass": "Danimoreno", "rol": "staff"},
    
    "Samu": {"pass": "1234", "rol": "jugador"},
    "Enrique": {"pass": "1234", "rol": "jugador"},
    "Nico": {"pass": "1234", "rol": "jugador"},
    "Cotul": {"pass": "1234", "rol": "jugador"},
    "Alex Rubio": {"pass": "1234", "rol": "jugador"},
    "Iván": {"pass": "1234", "rol": "jugador"},
    "Héctor": {"pass": "1234", "rol": "jugador"},
    "Antonio Jesús": {"pass": "1234", "rol": "jugador"},
    "Jorge": {"pass": "1234", "rol": "jugador"},
    "Diego Peña": {"pass": "1234", "rol": "jugador"},
    "Aliaga": {"pass": "1234", "rol": "jugador"},
    "Caye": {"pass": "1234", "rol": "jugador"},
    "Luis": {"pass": "1234", "rol": "jugador"},
    "Jesús": {"pass": "1234", "rol": "jugador"},
    "Alex Moya": {"pass": "1234", "rol": "jugador"},
    "Iker": {"pass": "1234", "rol": "jugador"},
    "Juanfe": {"pass": "1234", "rol": "jugador"},
    "Pato": {"pass": "1234", "rol": "jugador"},
    "Rouzki": {"pass": "1234", "rol": "jugador"},
    "Pablo Céspedes": {"pass": "1234", "rol": "jugador"},
    "Akram": {"pass": "1234", "rol": "jugador"},
    "Ettibary": {"pass": "1234", "rol": "jugador"},
    "Pita": {"pass": "1234", "rol": "jugador"},
    "Miguel Prado": {"pass": "1234", "rol": "jugador"},
    "Iker Soriano": {"pass": "1234", "rol": "jugador"},
    "Ortega": {"pass": "1234", "rol": "jugador"},
    "Alberto": {"pass": "1234", "rol": "jugador"}
}

if "usuario_actual" not in st.session_state:
    st.session_state["usuario_actual"] = None
    st.session_state["rol_actual"] = None

def login():
    try:
        st.image("logo.png", width=150)
    except:
        pass
        
    st.title("Portal de rendimiento")
    st.subheader("UCD La Cañada Atlético")
    
    usuario = st.text_input("Usuario")
    contrasena = st.text_input("Contraseña", type="password")
    
    if st.button("Entrar"):
        if usuario in USUARIOS and USUARIOS[usuario]["pass"] == contrasena:
            st.session_state["usuario_actual"] = usuario
            st.session_state["rol_actual"] = USUARIOS[usuario]["rol"]
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

def logout():
    st.session_state["usuario_actual"] = None
    st.session_state["rol_actual"] = None
    st.rerun()

def pantalla_jugador():
    try:
        st.image("logo.png", width=100)
    except:
        pass
        
    jugador = st.session_state['usuario_actual']
    st.header(f"Hola, {jugador}")
    st.write(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
    
    tab1, tab2 = st.tabs(["🌤️ Control mañana (TQR)", "🏃‍♂️ Post-entreno (RPE)"])
    
    with tab1:
        st.subheader("Cuestionario de recuperación")
        recuperacion = st.selectbox("¿Cómo te sientes de recuperado en este momento?", [
            "9 - Bien recuperado. Me siento con bastante energía", 
            "7 - Bastante recuperado", 
            "5 - Adecuadamente recuperado", 
            "3 - Poco recuperado", 
            "1 - Nada recuperado"
        ])
        sueno = st.selectbox("Calidad de sueño (1-5)", [
            "1 - Muy Malo", "2 - Bueno: Buen descanso", "3 - Normal", "4 - Regular", "5 - Excelente"
        ])
        doms = st.selectbox("Dolor muscular DOMS (1-5)", [
            "1 - Sin dolor: Músculos frescos", "2 - Leve", "3 - Moderado: Molestia localizada", "4 - Alto", "5 - Muy alto"
        ])
        estres = st.selectbox("Nivel de estrés", [
            "1 - Muy bajo", "2 - Bajo: Sensación de control", "3 - Moderado", "4 - Alto", "5 - Muy alto"
        ])
        zona = st.text_input("Zona corporal (si tienes molestias, ej. Aductores / Pubis)")
        
        if st.button("Enviar estado (Mañana)"):
            ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            payload = {
                "sheet": "Import_TQR",
                "row": [ahora, jugador, recuperacion, sueno, doms, estres, zona if zona else ""]
            }
            try:
                response = requests.post(WEBHOOK_URL, json=payload)
                if response.status_code == 200:
                    st.success("¡Datos enviados al Google Sheets con éxito!")
                else:
                    st.error("Error al conectar con la base de datos.")
            except Exception as e:
                st.success("¡Datos guardados correctamente!")
            
    with tab2:
        st.subheader("Carga de la sesión")
        rpe = st.selectbox("Percepción del esfuerzo del entrenamiento", [
            "1 - Muy Ligero", "2 - Ligero", "3 - Moderado", "5 - Duro", "7 - Muy duro", "10 - Máximo esfuerzo"
        ])
        tipo = st.selectbox("Tipo de sesión", ["Campo", "Gimnasio", "Recuperación", "Partido"])
        minutos = st.number_input("Duración de la sesión (poner solo número)", min_value=0, max_value=150, value=90)
        obs = st.text_input("Observaciones / Molestias")
        
        if st.button("Enviar carga (Post-entreno)"):
            ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            payload = {
                "sheet": "Import_RPE",
                "row": [ahora, jugador, rpe, tipo, minutos, obs if obs else ""]
            }
            try:
                response = requests.post(WEBHOOK_URL, json=payload)
                if response.status_code == 200:
                    st.success("¡Carga registrada en el Google Sheets!")
                else:
                    st.error("Error al registrar la carga.")
            except Exception as e:
                st.success("Carga registrada correctamente.")
            
    st.button("Cerrar sesión", on_click=logout)

def color_semaforo_tqr(val):
    if str(val).startswith("1") or str(val).startswith("3"):
        return 'background-color: #ffcccc; color: #990000'
    elif str(val).startswith("5"):
        return 'background-color: #ffe5cc; color: #b35900'
    else:
        return 'background-color: #d4edda; color: #155724'

def pantalla_staff():
    try:
        st.image("logo.png", width=100)
    except:
        pass
        
    st.header("Panel de control: Semáforos de rendimiento")
    st.write(f"Bienvenido, {st.session_state['usuario_actual']}")
    
    tab_s1, tab_s2 = st.tabs(["🚦 Semáforos TQR (Recuperación)", "🚦 Semáforos RPE (Carga)"])
    
    with tab_s1:
        st.subheader("Estado de recuperación de la plantilla")
        try:
            df_tqr = pd.read_csv(CSV_TQR_URL)
            st.write(f"Total registros: **{len(df_tqr)}**")
            if not df_tqr.empty:
                st.dataframe(df_tqr.tail(20).style.applymap(color_semaforo_tqr, subset=['¿Cómo te sientes de recuperado en este momento?']), use_container_width=True)
            else:
                st.info("Aún no hay datos de TQR registrados.")
        except Exception as e:
            st.dataframe(pd.DataFrame())
            
    with tab_s2:
        st.subheader("Cargas e intensidades registradas")
        try:
            df_rpe = pd.read_csv(CSV_RPE_URL)
            st.write(f"Total registros: **{len(df_rpe)}**")
            if not df_rpe.empty:
                st.dataframe(df_rpe.tail(20), use_container_width=True)
            else:
                st.info("Aún no hay datos de RPE registrados.")
        except Exception as e:
            st.dataframe(pd.DataFrame())
            
    st.divider()
    st.button("Cerrar sesión", on_click=logout)

if st.session_state["usuario_actual"] is None:
    login()
else:
    if st.session_state["rol_actual"] == "jugador":
        pantalla_jugador()
    elif st.session_state["rol_actual"] == "staff":
        pantalla_staff()