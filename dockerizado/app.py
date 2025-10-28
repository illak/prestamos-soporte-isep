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

    # Tabla de empleados
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            area TEXT NOT NULL,
            email TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

# ===== FUNCIONES DE GESTIÓN DE EMPLEADOS =====

def obtener_empleados():
    """Obtiene todos los empleados de la BD"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query('SELECT * FROM empleados ORDER BY area, apellido, nombre', conn)
    conn.close()
    return df

def obtener_areas():
    """Obtiene lista única de áreas/departamentos"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT area FROM empleados ORDER BY area')
    areas = [row[0] for row in cursor.fetchall()]
    conn.close()
    return areas

def agregar_empleado(nombre, apellido, area, email=""):
    """Agrega un nuevo empleado a la BD"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO empleados (nombre, apellido, area, email) VALUES (?, ?, ?, ?)',
            (nombre, apellido, area, email)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        return False

def importar_empleados_csv(df_csv):
    """
    Importa empleados desde un DataFrame de pandas.
    Espera columnas: area, nombre, apellido (email es opcional)
    Retorna: (total_importados, errores)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    importados = 0
    errores = []

    for idx, row in df_csv.iterrows():
        try:
            # Validar que existan las columnas requeridas
            area = str(row.get('area', row.get('Area', row.get('AREA', ''))).strip()
            nombre = str(row.get('nombre', row.get('Nombre', row.get('NOMBRE', ''))).strip()
            apellido = str(row.get('apellido', row.get('Apellido', row.get('APELLIDO', ''))).strip()
            email = str(row.get('email', row.get('Email', row.get('EMAIL', ''))).strip()

            if not area or not nombre or not apellido:
                errores.append(f"Fila {idx + 2}: Faltan datos requeridos (área, nombre o apellido)")
                continue

            cursor.execute(
                'INSERT INTO empleados (nombre, apellido, area, email) VALUES (?, ?, ?, ?)',
                (nombre, apellido, area, email)
            )
            importados += 1

        except Exception as e:
            errores.append(f"Fila {idx + 2}: {str(e)}")

    conn.commit()
    conn.close()

    return importados, errores

def eliminar_empleado(empleado_id):
    """Elimina un empleado por su ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM empleados WHERE id = ?', (empleado_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        return False

def buscar_empleado_por_nombre_completo(nombre_completo):
    """Busca un empleado por su nombre completo y retorna sus datos"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Intentar buscar como "Nombre Apellido"
    partes = nombre_completo.strip().split(maxsplit=1)
    if len(partes) == 2:
        nombre, apellido = partes
        cursor.execute(
            'SELECT id, nombre, apellido, area, email FROM empleados WHERE nombre = ? AND apellido = ?',
            (nombre, apellido)
        )
    else:
        # Si no hay apellido, buscar solo por nombre
        cursor.execute(
            'SELECT id, nombre, apellido, area, email FROM empleados WHERE nombre = ?',
            (nombre_completo,)
        )

    resultado = cursor.fetchone()
    conn.close()

    if resultado:
        return {
            'id': resultado[0],
            'nombre': resultado[1],
            'apellido': resultado[2],
            'area': resultado[3],
            'email': resultado[4]
        }
    return None

# Inicializar base de datos
init_database()

# Inicializar session_state para navegación y precarga
if 'navegar_a_registro' not in st.session_state:
    st.session_state.navegar_a_registro = False
if 'equipo_precargado' not in st.session_state:
    st.session_state.equipo_precargado = None
if 'operacion_precargada' not in st.session_state:
    st.session_state.operacion_precargada = None

# Título principal
st.title("💻 Sistema de Préstamos de Equipos")

# Obtener parámetros de URL (si vienen del QR)
query_params = st.query_params
equipo_id_qr = query_params.get("equipo_id", "")
nombre_equipo_qr = query_params.get("nombre_equipo", "")

# Sidebar para navegación
st.sidebar.title("Navegación")

opciones_menu = ["📋 Registro de Préstamos/Devoluciones", "📦 Gestión de Equipos", "👥 Gestión de Empleados", "📊 Reportes", "🔍 QR Codes"]

# Inicializar el menú en session_state si no existe
if 'menu_principal' not in st.session_state:
    st.session_state.menu_principal = opciones_menu[0]

# Si hay solicitud de navegación programática desde Gestión de Equipos
if st.session_state.navegar_a_registro:
    st.session_state.menu_principal = opciones_menu[0]  # Forzar "Registro de Préstamos/Devoluciones"
    st.session_state.navegar_a_registro = False

# Radio button - el key hace que Streamlit maneje automáticamente el estado
opcion = st.sidebar.radio(
    "Selecciona una opción:",
    opciones_menu,
    key='menu_principal'
)

if opcion == "📋 Registro de Préstamos/Devoluciones":
    st.header("Registro de Préstamos y Devoluciones")

    # Obtener lista de equipos registrados
    equipos_df = obtener_equipos()

    if equipos_df.empty:
        st.warning("⚠️ No hay equipos registrados. Por favor, agrega equipos en la sección 'Gestión de Equipos'.")
    else:
        # Verificar si hay datos precargados desde Gestión de Equipos
        # NO limpiarlos aún - mantenerlos hasta que se complete la operación
        if st.session_state.equipo_precargado:
            st.info(f"🎯 Operación precargada desde Gestión de Equipos")

        col1, col2 = st.columns(2)

        with col2:
            # Si hay operación precargada, usarla como default
            if st.session_state.operacion_precargada:
                operacion_index = 0 if st.session_state.operacion_precargada == "Entrega" else 1
            else:
                operacion_index = 0

            tipo_operacion = st.selectbox(
                "Tipo de Operación",
                ["Entrega", "Devolución"],
                index=operacion_index
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
                    # Prioridad: 1. Precargado desde Gestión, 2. QR, 3. Primero de la lista
                    if st.session_state.equipo_precargado and st.session_state.equipo_precargado in equipos_disponibles['id'].values:
                        indice_default = equipos_disponibles['id'].tolist().index(st.session_state.equipo_precargado)
                    elif equipo_id_qr and equipo_id_qr in equipos_disponibles['id'].values:
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
                    # Prioridad: 1. Precargado desde Gestión, 2. QR, 3. Primero de la lista
                    if st.session_state.equipo_precargado and st.session_state.equipo_precargado in equipos_prestados['id'].values:
                        indice_default = equipos_prestados['id'].tolist().index(st.session_state.equipo_precargado)
                    elif equipo_id_qr and equipo_id_qr in equipos_prestados['id'].values:
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
                # Para entregas, obtener lista de empleados desde la BD
                empleados_bd = obtener_empleados()
                empleado_de_bd = False  # Flag para saber si seleccionó un empleado de BD

                if not empleados_bd.empty:
                    # Crear lista de empleados con formato "Nombre Apellido (Área)"
                    empleados_opciones = ["-- Nuevo empleado --"] + [
                        f"{row['nombre']} {row['apellido']} ({row['area']})"
                        for _, row in empleados_bd.iterrows()
                    ]

                    empleado_seleccionado = st.selectbox(
                        "Nombre del Empleado",
                        options=empleados_opciones,
                        key="empleado_select"
                    )

                    if empleado_seleccionado != "-- Nuevo empleado --":
                        # Extraer índice del empleado seleccionado
                        idx_emp = empleados_opciones.index(empleado_seleccionado) - 1
                        emp_data = empleados_bd.iloc[idx_emp]

                        # Auto-completar datos
                        empleado = f"{emp_data['nombre']} {emp_data['apellido']}"
                        email = emp_data['email'] if pd.notna(emp_data['email']) else ""
                        area = emp_data['area']
                        empleado_de_bd = True

                        # Mostrar info del empleado seleccionado
                        st.info(f"📧 {email if email else 'Sin email'}")
                    else:
                        # Modo manual - nuevo empleado
                        st.markdown("**Agregar nuevo empleado:**")
                        empleado_nombre = st.text_input("Nombre", key="empleado_nuevo_nombre")
                        empleado_apellido = st.text_input("Apellido", key="empleado_nuevo_apellido")
                        empleado = f"{empleado_nombre} {empleado_apellido}".strip() if empleado_nombre or empleado_apellido else ""
                        email = st.text_input("Email (opcional)", key="email_nuevo")
                else:
                    # No hay empleados en la BD, usar modo manual
                    st.warning("⚠️ No hay empleados registrados. Agrégalos en 'Gestión de Empleados'")
                    empleado_nombre = st.text_input("Nombre", key="empleado_nuevo_nombre_alt")
                    empleado_apellido = st.text_input("Apellido", key="empleado_nuevo_apellido_alt")
                    empleado = f"{empleado_nombre} {empleado_apellido}".strip() if empleado_nombre or empleado_apellido else ""
                    email = st.text_input("Email (opcional)", key="email_nuevo_alt")
                    area = ""
            else:
                # Para devoluciones, mostrar el empleado del préstamo activo como solo lectura
                st.text_input("Nombre del Empleado", value=empleado, disabled=True, key="empleado_devolucion")
                st.text_input("Email del Empleado", value=email, disabled=True, key="email_devolucion")

        with col4:
            if tipo_operacion == "Entrega":
                # Obtener áreas desde la BD de empleados
                areas_disponibles = obtener_areas()

                # Si seleccionó empleado de BD, mostrar área como solo lectura
                if 'empleado_de_bd' in locals() and empleado_de_bd:
                    st.text_input("Área/Departamento", value=area, disabled=True, key="area_readonly")
                elif areas_disponibles:
                    # Hay áreas disponibles, mostrar selectbox con opción de nueva
                    usar_area_existente = st.checkbox("Usar área existente", value=True, key="usar_area_existente")

                    if usar_area_existente:
                        area = st.selectbox(
                            "Área/Departamento",
                            options=areas_disponibles,
                            key="area_select"
                        )
                    else:
                        area = st.text_input("Nueva Área/Departamento", key="area_nueva")
                else:
                    # No hay áreas, campo de texto libre
                    area = st.text_input("Área/Departamento", value=area if 'area' in locals() else "", key="area_entrega")
            else:
                # Para devoluciones, área es solo lectura
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
                            # Limpiar datos precargados después de registro exitoso
                            st.session_state.equipo_precargado = None
                            st.session_state.operacion_precargada = None
                            st.success(f"✅ {tipo_operacion} registrada exitosamente")
                            st.rerun()
                else:
                    st.error("❌ El equipo no existe en el sistema")
            else:
                st.error("❌ Por favor selecciona un equipo")

elif opcion == "📦 Gestión de Equipos":
    # Limpiar datos precargados si el usuario cambió manualmente de vista
    if st.session_state.equipo_precargado or st.session_state.operacion_precargada:
        st.session_state.equipo_precargado = None
        st.session_state.operacion_precargada = None

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
        st.markdown("📋 **Listado de equipos** - Usa los botones de acción para prestar o devolver")
        st.markdown("---")

        # Mostrar cada equipo con botones de acción
        for idx, equipo in equipos_df.iterrows():
            estado, usuario, fecha = obtener_estado_equipo(equipo['id'])

            # Crear columnas para mostrar información y botón
            col_info, col_action = st.columns([4, 1])

            with col_info:
                # Mostrar información del equipo
                if estado == 'Disponible':
                    st.success(f"**{equipo['id']}** - {equipo['nombre']} ({equipo['tipo']}) - ✅ **Disponible**")
                else:
                    st.warning(f"**{equipo['id']}** - {equipo['nombre']} ({equipo['tipo']}) - ⚠️ **Prestado a:** {usuario}")
                    if fecha:
                        st.caption(f"Desde: {fecha}")

            with col_action:
                # Botón de acción según el estado
                if estado == 'Disponible':
                    if st.button("🔄 Prestar", key=f"prestar_{equipo['id']}"):
                        # Guardar datos en session_state y cambiar de vista
                        st.session_state.equipo_precargado = equipo['id']
                        st.session_state.operacion_precargada = "Entrega"
                        st.session_state.navegar_a_registro = True
                        st.rerun()
                else:
                    if st.button("↩️ Devolver", key=f"devolver_{equipo['id']}"):
                        # Guardar datos en session_state y cambiar de vista
                        st.session_state.equipo_precargado = equipo['id']
                        st.session_state.operacion_precargada = "Devolución"
                        st.session_state.navegar_a_registro = True
                        st.rerun()

            st.markdown("---")
    else:
        st.info("No hay equipos registrados")

elif opcion == "👥 Gestión de Empleados":
    # Limpiar datos precargados si el usuario cambió manualmente de vista
    if st.session_state.equipo_precargado or st.session_state.operacion_precargada:
        st.session_state.equipo_precargado = None
        st.session_state.operacion_precargada = None

    st.header("Gestión de Empleados")

    # Crear tabs para organizar mejor
    tab1, tab2, tab3 = st.tabs(["📥 Importar CSV", "➕ Agregar Manualmente", "📋 Lista de Empleados"])

    with tab1:
        st.subheader("Importar Empleados desde CSV")

        st.markdown("""
        **Formato del archivo CSV:**
        - Debe contener las siguientes columnas: `area`, `nombre`, `apellido`
        - Opcionalmente puede incluir: `email`
        - Las columnas pueden estar en mayúsculas, minúsculas o capitalizado
        - Ejemplo:

        ```
        area,nombre,apellido,email
        Sistemas,Juan,Pérez,juan.perez@empresa.com
        Recursos Humanos,María,González,maria.gonzalez@empresa.com
        Contabilidad,Carlos,Rodríguez,
        ```
        """)

        archivo_csv = st.file_uploader(
            "Selecciona el archivo CSV",
            type=['csv'],
            help="El archivo debe tener las columnas: area, nombre, apellido (email es opcional)"
        )

        if archivo_csv is not None:
            try:
                # Leer el CSV
                df_csv = pd.read_csv(archivo_csv)

                # Mostrar vista previa
                st.info(f"📄 Archivo cargado: **{archivo_csv.name}** - {len(df_csv)} filas detectadas")
                st.dataframe(df_csv.head(10), use_container_width=True)

                # Botón para importar
                if st.button("📤 Importar Empleados", type="primary"):
                    importados, errores = importar_empleados_csv(df_csv)

                    if importados > 0:
                        st.success(f"✅ Se importaron {importados} empleados exitosamente")

                    if errores:
                        st.warning(f"⚠️ Se encontraron {len(errores)} errores:")
                        with st.expander("Ver detalles de errores"):
                            for error in errores:
                                st.error(error)

                    st.rerun()

            except Exception as e:
                st.error(f"❌ Error al leer el archivo CSV: {str(e)}")
                st.info("Verifica que el archivo tenga el formato correcto y las columnas requeridas.")

    with tab2:
        st.subheader("Agregar Empleado Manualmente")

        col1, col2 = st.columns(2)

        with col1:
            nombre = st.text_input("Nombre *", key="nuevo_emp_nombre")
            apellido = st.text_input("Apellido *", key="nuevo_emp_apellido")

        with col2:
            # Obtener áreas existentes para el desplegable
            areas_existentes = obtener_areas()

            if areas_existentes:
                usar_existente = st.checkbox("Usar área existente", value=True)

                if usar_existente:
                    area = st.selectbox(
                        "Área/Departamento *",
                        options=areas_existentes,
                        key="nuevo_emp_area_select"
                    )
                else:
                    area = st.text_input(
                        "Nueva Área/Departamento *",
                        key="nuevo_emp_area_text"
                    )
            else:
                area = st.text_input("Área/Departamento *", key="nuevo_emp_area_nueva")

            email = st.text_input("Email (opcional)", key="nuevo_emp_email")

        if st.button("➕ Agregar Empleado", type="primary"):
            if nombre and apellido and area:
                if agregar_empleado(nombre, apellido, area, email):
                    st.success(f"✅ Empleado {nombre} {apellido} agregado exitosamente")
                    st.rerun()
                else:
                    st.error("❌ Error al agregar el empleado")
            else:
                st.error("❌ Por favor completa todos los campos obligatorios (*)")

    with tab3:
        st.subheader("Lista de Empleados Registrados")

        empleados_df = obtener_empleados()

        if not empleados_df.empty:
            # Estadísticas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Empleados", len(empleados_df))
            with col2:
                st.metric("Total Áreas", len(empleados_df['area'].unique()))
            with col3:
                area_mayor = empleados_df['area'].value_counts().index[0]
                st.metric("Área con más empleados", area_mayor)

            st.markdown("---")

            # Filtros
            col_filtro1, col_filtro2 = st.columns(2)

            with col_filtro1:
                areas_filtro = ["Todas"] + list(empleados_df['area'].unique())
                area_seleccionada = st.selectbox("Filtrar por Área", areas_filtro)

            with col_filtro2:
                busqueda = st.text_input("🔍 Buscar por nombre o apellido", "")

            # Aplicar filtros
            df_filtrado = empleados_df.copy()

            if area_seleccionada != "Todas":
                df_filtrado = df_filtrado[df_filtrado['area'] == area_seleccionada]

            if busqueda:
                df_filtrado = df_filtrado[
                    df_filtrado['nombre'].str.contains(busqueda, case=False, na=False) |
                    df_filtrado['apellido'].str.contains(busqueda, case=False, na=False)
                ]

            # Mostrar tabla
            st.dataframe(
                df_filtrado[['area', 'nombre', 'apellido', 'email']],
                use_container_width=True,
                hide_index=True
            )

            # Opción para eliminar empleados
            if st.checkbox("🗑️ Modo Eliminación"):
                st.warning("⚠️ **Atención**: Selecciona un empleado para eliminarlo")

                # Crear lista de empleados para seleccionar
                empleados_lista = []
                for _, emp in empleados_df.iterrows():
                    empleados_lista.append(
                        f"{emp['id']} - {emp['nombre']} {emp['apellido']} ({emp['area']})"
                    )

                empleado_eliminar = st.selectbox(
                    "Selecciona el empleado a eliminar",
                    options=empleados_lista
                )

                if st.button("🗑️ Eliminar Empleado", type="secondary"):
                    # Extraer ID del string seleccionado
                    emp_id = int(empleado_eliminar.split(" - ")[0])
                    if eliminar_empleado(emp_id):
                        st.success("✅ Empleado eliminado exitosamente")
                        st.rerun()
                    else:
                        st.error("❌ Error al eliminar el empleado")

        else:
            st.info("📭 No hay empleados registrados. Usa las pestañas superiores para agregar empleados.")

elif opcion == "📊 Reportes":
    # Limpiar datos precargados si el usuario cambió manualmente de vista
    if st.session_state.equipo_precargado or st.session_state.operacion_precargada:
        st.session_state.equipo_precargado = None
        st.session_state.operacion_precargada = None

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
    # Limpiar datos precargados si el usuario cambió manualmente de vista
    if st.session_state.equipo_precargado or st.session_state.operacion_precargada:
        st.session_state.equipo_precargado = None
        st.session_state.operacion_precargada = None

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