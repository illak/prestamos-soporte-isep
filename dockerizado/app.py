import streamlit as st
import sqlite3
import pandas as pd
import qrcode
from datetime import datetime
import io
import base64
import os

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Préstamos de Equipos",
    page_icon="💻",
    layout="wide"
)

# Configuración de base URL desde variable de entorno
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8501')
DB_PATH = os.getenv('DB_PATH', 'equipos.db')

# Inicializar base de datos
def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabla de equipos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipos (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            tipo TEXT,
            estado TEXT DEFAULT 'Disponible'
        )
    ''')
    
    # Tabla de transacciones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id TEXT,
            empleado TEXT NOT NULL,
            email TEXT,
            area TEXT,
            tipo_operacion TEXT NOT NULL,
            fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            observaciones TEXT,
            responsable TEXT,
            FOREIGN KEY (equipo_id) REFERENCES equipos (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Función para generar QR - versión simplificada y robusta
def generar_qr_url(equipo_id, nombre_equipo):
    """Genera solo la URL del QR, sin imagen"""
    url_qr = f"{BASE_URL}/?equipo_id={equipo_id}&nombre_equipo={nombre_equipo}"
    return url_qr

def crear_qr_imagen(texto):
    """Crea imagen QR y la convierte a formato compatible con Streamlit"""
    try:
        # Crear QR simple
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(texto)
        qr.make(fit=True)
        
        # Crear imagen
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir a bytes inmediatamente
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_bytes = img_buffer.getvalue()
        
        return img_bytes
    except Exception as e:
        st.error(f"Error creando QR: {e}")
        return None

# Función para obtener estado actual del equipo
def obtener_estado_equipo(equipo_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT tipo_operacion, empleado, fecha_hora 
        FROM transacciones 
        WHERE equipo_id = ? 
        ORDER BY fecha_hora DESC 
        LIMIT 1
    ''', (equipo_id,))
    
    resultado = cursor.fetchone()
    conn.close()
    
    if resultado:
        if resultado[0] == 'Entrega':
            return 'Prestado', resultado[1], resultado[2]
        else:
            return 'Disponible', None, resultado[2]
    else:
        return 'Disponible', None, None

# Función para registrar transacción
def registrar_transaccion(equipo_id, empleado, email, area, tipo_operacion, observaciones, responsable):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute('''
        INSERT INTO transacciones 
        (equipo_id, empleado, email, area, tipo_operacion, fecha_hora, observaciones, responsable)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (equipo_id, empleado, email, area, tipo_operacion, fecha_hora, observaciones, responsable))
    
    # Actualizar estado del equipo
    nuevo_estado = 'Prestado' if tipo_operacion == 'Entrega' else 'Disponible'
    cursor.execute('UPDATE equipos SET estado = ? WHERE id = ?', (nuevo_estado, equipo_id))
    
    conn.commit()
    conn.close()

# Función para agregar equipo
def agregar_equipo(equipo_id, nombre, tipo):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('INSERT INTO equipos (id, nombre, tipo) VALUES (?, ?, ?)', 
                      (equipo_id, nombre, tipo))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

# Función para obtener equipos
def obtener_equipos():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query('SELECT * FROM equipos ORDER BY id', conn)
    conn.close()
    
    return df

# Función para obtener transacciones
def obtener_transacciones():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query('''
        SELECT t.*, e.nombre as nombre_equipo
        FROM transacciones t
        LEFT JOIN equipos e ON t.equipo_id = e.id
        ORDER BY t.fecha_hora DESC
    ''', conn)
    conn.close()

    return df

# Función para obtener equipos prestados con información del empleado
def obtener_equipos_prestados():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Obtener todos los equipos prestados
    cursor.execute('SELECT id, nombre FROM equipos WHERE estado = "Prestado" ORDER BY id')
    equipos_prestados = cursor.fetchall()

    # Para cada equipo prestado, obtener el último empleado
    resultado = []
    for equipo_id, nombre_equipo in equipos_prestados:
        cursor.execute('''
            SELECT empleado, email, area, fecha_hora
            FROM transacciones
            WHERE equipo_id = ? AND tipo_operacion = 'Entrega'
            ORDER BY fecha_hora DESC
            LIMIT 1
        ''', (equipo_id,))

        transaccion = cursor.fetchone()
        if transaccion:
            resultado.append({
                'equipo_id': equipo_id,
                'nombre_equipo': nombre_equipo,
                'empleado': transaccion[0],
                'email': transaccion[1],
                'area': transaccion[2],
                'fecha_prestamo': transaccion[3]
            })

    conn.close()
    return resultado

# Función para obtener lista de empleados únicos que han recibido préstamos
def obtener_empleados_activos():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT DISTINCT empleado, email, area
        FROM transacciones
        WHERE tipo_operacion = 'Entrega'
        ORDER BY empleado
    ''')

    empleados = cursor.fetchall()
    conn.close()

    return [{'empleado': e[0], 'email': e[1], 'area': e[2]} for e in empleados]

# Inicializar base de datos
init_database()

# Título principal
st.title("💻 Sistema de Préstamos de Equipos")

# Obtener parámetros de URL (si vienen del QR)
query_params = st.query_params
equipo_id_qr = query_params.get("equipo_id", "")
nombre_equipo_qr = query_params.get("nombre_equipo", "")

# Sidebar para navegación
st.sidebar.title("Navegación")
opcion = st.sidebar.radio(
    "Selecciona una opción:",
    ["📋 Registro de Préstamos/Devoluciones", "📦 Gestión de Equipos", "📊 Reportes", "🔍 QR Codes"]
)

if opcion == "📋 Registro de Préstamos/Devoluciones":
    st.header("Registro de Préstamos y Devoluciones")

    # Obtener lista de equipos registrados
    equipos_df = obtener_equipos()

    if equipos_df.empty:
        st.warning("⚠️ No hay equipos registrados. Por favor, agrega equipos en la sección 'Gestión de Equipos'.")
    else:
        col1, col2 = st.columns(2)

        with col2:
            tipo_operacion = st.selectbox(
                "Tipo de Operación",
                ["Entrega", "Devolución"]
            )

        with col1:
            # Determinar qué equipos mostrar según el tipo de operación
            if tipo_operacion == "Entrega":
                # Para entregas, mostrar solo equipos disponibles
                equipos_disponibles = equipos_df[equipos_df['estado'] == 'Disponible']

                if equipos_disponibles.empty:
                    st.warning("⚠️ No hay equipos disponibles para préstamo.")
                    equipo_id = None
                else:
                    # Si viene del QR, intentar pre-seleccionar
                    if equipo_id_qr and equipo_id_qr in equipos_disponibles['id'].values:
                        indice_default = equipos_disponibles['id'].tolist().index(equipo_id_qr)
                    else:
                        indice_default = 0

                    equipo_seleccionado = st.selectbox(
                        "Selecciona el Equipo",
                        options=equipos_disponibles['id'].tolist(),
                        format_func=lambda x: f"{x} - {equipos_disponibles[equipos_disponibles['id']==x]['nombre'].iloc[0]}",
                        index=indice_default,
                        key="equipo_entrega"
                    )
                    equipo_id = equipo_seleccionado

            else:  # Devolución
                # Para devoluciones, mostrar solo equipos prestados
                equipos_prestados = equipos_df[equipos_df['estado'] == 'Prestado']

                if equipos_prestados.empty:
                    st.warning("⚠️ No hay equipos prestados para devolver.")
                    equipo_id = None
                else:
                    # Si viene del QR, intentar pre-seleccionar
                    if equipo_id_qr and equipo_id_qr in equipos_prestados['id'].values:
                        indice_default = equipos_prestados['id'].tolist().index(equipo_id_qr)
                    else:
                        indice_default = 0

                    equipo_seleccionado = st.selectbox(
                        "Selecciona el Equipo",
                        options=equipos_prestados['id'].tolist(),
                        format_func=lambda x: f"{x} - {equipos_prestados[equipos_prestados['id']==x]['nombre'].iloc[0]}",
                        index=indice_default,
                        key="equipo_devolucion"
                    )
                    equipo_id = equipo_seleccionado

        # Mostrar información del equipo seleccionado
        if equipo_id:
            equipo_info = equipos_df[equipos_df['id'] == equipo_id].iloc[0]
            st.success(f"📦 Equipo: {equipo_info['nombre']} ({equipo_info['tipo']})")

            estado, usuario_actual, fecha_actual = obtener_estado_equipo(equipo_id)

            if estado == 'Prestado':
                st.warning(f"⚠️ Equipo prestado a: {usuario_actual} desde {fecha_actual}")
            else:
                st.info("✅ Equipo disponible")

        # Campos del formulario
        st.markdown("---")

        # Para devoluciones, obtener datos del préstamo activo
        empleado = ""
        email = ""
        area = ""

        if equipo_id and tipo_operacion == "Devolución":
            # Obtener información del préstamo activo
            equipos_prestados_info = obtener_equipos_prestados()
            equipo_prestado_info = next((e for e in equipos_prestados_info if e['equipo_id'] == equipo_id), None)

            if equipo_prestado_info:
                st.info(f"🔍 Préstamo activo a: **{equipo_prestado_info['empleado']}** ({equipo_prestado_info['email']}) - {equipo_prestado_info['area']}")
                # Pre-llenar los campos con los datos del préstamo activo
                empleado = equipo_prestado_info['empleado']
                email = equipo_prestado_info['email'] if equipo_prestado_info['email'] else ""
                area = equipo_prestado_info['area'] if equipo_prestado_info['area'] else ""

        col3, col4 = st.columns(2)

        with col3:
            if tipo_operacion == "Entrega":
                # Para entregas, obtener lista de empleados anteriores para sugerencias
                empleados_anteriores = obtener_empleados_activos()
                empleados_nombres = [""] + [e['empleado'] for e in empleados_anteriores]

                empleado_idx = st.selectbox(
                    "Nombre del Empleado",
                    options=range(len(empleados_nombres)),
                    format_func=lambda x: empleados_nombres[x] if empleados_nombres[x] else "-- Nuevo empleado --",
                    key="empleado_select"
                )

                if empleado_idx > 0:
                    empleado = empleados_nombres[empleado_idx]
                    # Auto-completar email y área si existen
                    empleado_info = empleados_anteriores[empleado_idx - 1]
                    email = empleado_info['email'] if empleado_info['email'] else ""
                    area = empleado_info['area'] if empleado_info['area'] else ""
                else:
                    empleado = st.text_input("Escribe el nombre del empleado", key="empleado_nuevo")
                    email = st.text_input("Email del Empleado", key="email_nuevo")
            else:
                # Para devoluciones, mostrar el empleado del préstamo activo como solo lectura
                st.text_input("Nombre del Empleado", value=empleado, disabled=True, key="empleado_devolucion")
                st.text_input("Email del Empleado", value=email, disabled=True, key="email_devolucion")

        with col4:
            if tipo_operacion == "Entrega":
                area = st.text_input("Área/Departamento", value=area, key="area_entrega")
            else:
                area = st.text_input("Área/Departamento", value=area, disabled=True, key="area_devolucion")

            responsable = st.text_input("Responsable de IT", key="responsable")

        observaciones = st.text_area("Observaciones (opcional)")

        if st.button("✅ Registrar Operación", type="primary"):
            # Verificar que el equipo existe
            if equipo_id:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('SELECT estado FROM equipos WHERE id = ?', (equipo_id,))
                equipo_existe = cursor.fetchone()
                conn.close()

                if equipo_existe:
                    estado_actual = equipo_existe[0]

                    # Validar campos obligatorios según el tipo de operación
                    campos_obligatorios_ok = False

                    if tipo_operacion == 'Entrega':
                        # Para entregas, siempre se requieren empleado y responsable
                        if empleado and responsable:
                            campos_obligatorios_ok = True
                        else:
                            st.error("❌ Para entregas son obligatorios: Empleado y Responsable")

                    elif tipo_operacion == 'Devolución':
                        # Para devoluciones de equipos prestados, solo se requiere responsable
                        if responsable:
                            campos_obligatorios_ok = True
                        else:
                            st.error("❌ Para devoluciones es obligatorio: Responsable")

                    if campos_obligatorios_ok:
                        # Validaciones de estado
                        if tipo_operacion == 'Entrega' and estado_actual == 'Prestado':
                            st.error("❌ No se puede entregar un equipo que ya está prestado")
                        elif tipo_operacion == 'Devolución' and estado_actual == 'Disponible':
                            st.error("❌ No se puede devolver un equipo que no está prestado")
                        else:
                            registrar_transaccion(equipo_id, empleado, email, area, tipo_operacion, observaciones, responsable)
                            st.success(f"✅ {tipo_operacion} registrada exitosamente")
                            st.rerun()
                else:
                    st.error("❌ El equipo no existe en el sistema")
            else:
                st.error("❌ Por favor selecciona un equipo")

elif opcion == "📦 Gestión de Equipos":
    st.header("Gestión de Equipos")
    
    # Agregar nuevo equipo
    st.subheader("Agregar Nuevo Equipo")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        nuevo_id = st.text_input("ID del Equipo")
    with col2:
        nuevo_nombre = st.text_input("Nombre/Modelo")
    with col3:
        nuevo_tipo = st.text_input("Tipo (Laptop, Mouse, etc.)")
    
    if st.button("➕ Agregar Equipo"):
        if nuevo_id and nuevo_nombre and nuevo_tipo:
            if agregar_equipo(nuevo_id, nuevo_nombre, nuevo_tipo):
                st.success("✅ Equipo agregado exitosamente")
            else:
                st.error("❌ Ya existe un equipo con ese ID")
        else:
            st.error("❌ Completa todos los campos")
    
    # Mostrar equipos existentes
    st.subheader("Equipos Registrados")
    equipos_df = obtener_equipos()
    
    if not equipos_df.empty:
        # Agregar información de estado actual
        estados_detallados = []
        for _, equipo in equipos_df.iterrows():
            estado, usuario, fecha = obtener_estado_equipo(equipo['id'])
            estados_detallados.append({
                'ID': equipo['id'],
                'Nombre': equipo['nombre'],
                'Tipo': equipo['tipo'],
                'Estado': estado,
                'Usuario Actual': usuario if usuario else '-',
                'Ult. Fecha. Act.': fecha if fecha else '-'
            })
        
        st.dataframe(pd.DataFrame(estados_detallados), use_container_width=True)
    else:
        st.info("No hay equipos registrados")

elif opcion == "📊 Reportes":
    st.header("Reportes y Estadísticas")
    
    # Resumen general
    equipos_df = obtener_equipos()
    transacciones_df = obtener_transacciones()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Equipos", len(equipos_df))
    
    with col2:
        equipos_prestados = len(equipos_df[equipos_df['estado'] == 'Prestado'])
        st.metric("Equipos Prestados", equipos_prestados)
    
    with col3:
        st.metric("Total Transacciones", len(transacciones_df))
    
    # Historial de transacciones
    st.subheader("Historial de Transacciones")
    if not transacciones_df.empty:
        # Seleccionar columnas relevantes para mostrar
        columnas_mostrar = ['fecha_hora', 'equipo_id', 'nombre_equipo', 'empleado', 
                          'area', 'tipo_operacion', 'responsable']
        st.dataframe(
            transacciones_df[columnas_mostrar].head(20), 
            use_container_width=True
        )
    else:
        st.info("No hay transacciones registradas")

elif opcion == "🔍 QR Codes":
    st.header("Generador de Códigos QR")
    
    # Seleccionar equipo para generar QR
    equipos_df = obtener_equipos()
    
    if not equipos_df.empty:
        equipo_seleccionado = st.selectbox(
            "Selecciona un equipo:",
            options=equipos_df['id'].tolist(),
            format_func=lambda x: f"{x} - {equipos_df[equipos_df['id']==x]['nombre'].iloc[0]}"
        )
        
        if st.button("🔄 Generar QR"):
            nombre_equipo = equipos_df[equipos_df['id']==equipo_seleccionado]['nombre'].iloc[0]
            
            # Generar URL del QR
            qr_url = generar_qr_url(equipo_seleccionado, nombre_equipo)
            
            # Mostrar URL generada
            st.subheader(f"QR para equipo: {equipo_seleccionado}")
            st.info(f"URL generada: {qr_url}")
            
            # Crear y mostrar imagen QR
            qr_bytes = crear_qr_imagen(qr_url)
            
            if qr_bytes:
                # Mostrar el QR
                st.image(qr_bytes, caption=f"QR - {equipo_seleccionado}", width=300)
                
                # Botón de descarga
                st.download_button(
                    label="📥 Descargar QR",
                    data=qr_bytes,
                    file_name=f"QR_{equipo_seleccionado}.png",
                    mime="image/png"
                )
                
                st.success("✅ QR generado exitosamente")
            else:
                st.error("❌ Error al generar imagen QR")
                st.info(f"Puedes usar esta URL manualmente: {qr_url}")
                
    else:
        st.info("Primero agrega equipos en la sección 'Gestión de Equipos'")

# Información adicional en el sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("### Información")
st.sidebar.info(
    "💡 **Tip:** Escanea el QR de un equipo para acceso rápido al formulario"
)

# Mostrar hora actual del sistema
hora_sistema = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
st.sidebar.markdown(f"🕒 **Hora del sistema:** {hora_sistema}")

# Mostrar información de configuración
st.sidebar.markdown(f"🌐 **Base URL:** {BASE_URL}")

if equipo_id_qr:
    st.sidebar.success(f"🎯 Accediste via QR: {equipo_id_qr}")