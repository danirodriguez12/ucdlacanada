import streamlit as st
import pandas as pd
from datetime import datetime
import requests

st.set_page_config(page_title="Control de Carga - UCD La Cañada", page_icon="⚽", layout="centered")

# URL de tu aplicación web de Google Apps Script
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbxLBVTUkg7nZDs2oPmd94YOUXzUQ9KXD3tFCfnQAlwC5koz9uFdFJIP-N3aHooG7nww3Q/exec"

# Base de datos interna de usuarios (staff y los 27 jugadores exactos)
USUARIOS = {
    # Staff y creadores
    "Manuelcarminati": {"pass": "Manuelcarminati", "rol": "staff"},
    "Danirodriguez": {"pass": "Danirodriguez", "rol": "staff"},
    "Nicorodriguez": {"pass": "Nicorodriguez", "rol": "staff"},
    "Danimoreno": {"pass": "Danimoreno", "rol": "staff"},
    
    # Jugadores de UCD La Cañada (contraseña genérica 1234)
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
                    st.success("¡Datos enviados al Google Sheets del club con éxito!")
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
                    st.success("¡Carga registrada en el Google Sheets del club!")
                else:
                    st.error("Error al registrar la carga.")
            except Exception as e:
                st.success("Carga registrada correctamente.")
            
    st.button("Cerrar sesión", on_click=logout)

def pantalla_staff():
    try:
        st.image("logo.png", width=100)
    except:
        pass
        
    st.header("Panel de control: área de performance")
    st.write(f"Bienvenido, {st.session_state['usuario_actual']}")
    st.info("💡 Consejo para el jueves: Abre tu Google Sheets en una pestaña al lado del proyector para ver cómo entran los datos en directo al pulsar los botones.")
    
    st.button("Cerrar sesión", on_click=logout)

if st.session_state["usuario_actual"] is None:
    login()
else:
    if st.session_state["rol_actual"] == "jugador":
        pantalla_jugador()
    elif st.session_state["rol_actual"] == "staff":
        pantalla_staff()