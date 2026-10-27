import streamlit as st
import pandas as pd
from datetime import date

# configuración de la página (pestaña del navegador y diseño)
st.set_page_config(page_title="Datos Físicos - La Cañada FC", page_icon="⚽", layout="centered")

# base de datos simulada de usuarios y contraseñas
USUARIOS = {
    "Danimoreno": {"pass": "Danimoreno", "rol": "staff"},
    "Nico": {"pass": "Nico", "rol": "staff"},
    "Pato": {"pass": "Pato", "rol": "jugador"},
    "Jesus": {"pass": "Jesus", "rol": "jugador"}
}

# inicializar el estado de la sesión para el login
if "usuario_actual" not in st.session_state:
    st.session_state["usuario_actual"] = None
    st.session_state["rol_actual"] = None

def login():
    # mostrar logo (asegúrate de tener la imagen descargada en la misma carpeta)
    try:
        st.image("logo.png", width=150)
    except:
        st.warning("Logo no encontrado. Sube logo.png a la carpeta.")
        
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
    st.image("logo.png", width=100)
    st.header(f"Hola, {st.session_state['usuario_actual']}")
    st.write(f"Fecha: {date.today().strftime('%d/%m/%Y')}")
    
    tab1, tab2 = st.tabs(["🌤️ Control mañana (Wellness)", "🏃‍♂️ Post-entreno (RPE)"])
    
    with tab1:
        st.subheader("Cuestionario de estado")
        sueno = st.select_slider("Calidad del sueño", options=[1, 2, 3, 4, 5], value=3, help="1=Muy malo, 5=Excelente")
        fatiga = st.select_slider("Nivel de fatiga general", options=[1, 2, 3, 4, 5], value=3, help="1=Agotado, 5=Muy fresco")
        dolor = st.select_slider("Dolor muscular (DOMS)", options=[1, 2, 3, 4, 5], value=3, help="1=Mucho dolor, 5=Sin dolor")
        estres = st.select_slider("Nivel de estrés (personal/académico)", options=[1, 2, 3, 4, 5], value=3)
        zona = st.text_input("Si tienes molestias, ¿en qué zona?")
        
        if st.button("Enviar estado (Mañana)"):
            st.success("¡Datos guardados correctamente! Que tengas un buen día.")
            
    with tab2:
        st.subheader("Carga de la sesión")
        rpe = st.slider("Dureza del entrenamiento (0-10)", 0, 10, 5)
        minutos = st.number_input("Duración de la sesión (minutos)", min_value=0, max_value=150, value=90)
        
        if st.button("Enviar carga (Post-entreno)"):
            st.success(f"Carga registrada: {rpe * minutos} unidades arbitrarias. ¡A descansar!")
            
    st.button("Cerrar sesión", on_click=logout)

def pantalla_staff():
    st.image("logo.png", width=100)
    st.header("Panel de control: cuerpo técnico")
    st.write(f"Bienvenido, {st.session_state['usuario_actual']}")
    
    st.subheader("Alertas de estado (Hoy)")
    
    # mostrar unas métricas de ejemplo para impresionar en la reunión
    col1, col2, col3 = st.columns(3)
    col1.metric("Plantilla", "22 jugadores", "100% completado")
    col2.metric("Fatiga media", "3.2 / 5", "-0.5")
    col3.metric("Alertas rojas", "2 jugadores", "DOMS alto", delta_color="inverse")
    
    st.divider()
    st.write("**Jugadores que requieren atención:**")
    
    # tabla simulada con semáforos
    datos_simulados = pd.DataFrame({
        "Jugador": ["Jesús", "Pablo Céspedes", "Pato"],
        "Sueño": ["🔴 1", "🟡 3", "🟢 5"],
        "DOMS": ["🔴 1 (Aductores)", "🟡 3 (Lumbar)", "🟢 5"],
        "Estado": ["Adaptar sesión", "Normal", "Óptimo"]
    })
    
    st.dataframe(datos_simulados, use_container_width=True, hide_index=True)
    
    st.button("Cerrar sesión", on_click=logout)

# lógica de navegación
if st.session_state["usuario_actual"] is None:
    login()
else:
    if st.session_state["rol_actual"] == "jugador":
        pantalla_jugador()
    elif st.session_state["rol_actual"] == "staff":
        pantalla_staff()