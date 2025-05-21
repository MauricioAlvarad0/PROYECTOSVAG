from flask import Flask, render_template, request, redirect, url_for, flash, session
import database # Tu módulo para la conexión a la base de datos (usa sqlite3)
from werkzeug.security import check_password_hash, generate_password_hash # Para el hashing de contraseñas
from werkzeug.utils import secure_filename # Para manejar nombres de archivo de forma segura
from functools import wraps # For decorators
import sqlite3 # Importante para manejo de errores específicos si es necesario
import os # Necesario para verificar si el archivo de BD existe y para rutas de archivos
from datetime import datetime # Para la fecha de solicitud de justificantes
import traceback # Para imprimir tracebacks completos en errores 500 o excepciones

app = Flask(__name__)
# ¡¡CAMBIA ESTO!! Es crucial para la seguridad. Usa algo como os.urandom(24).hex() para generar una.
app.secret_key = 'tu_clave_secreta_muy_segura_y_dificil_de_adivinar12345!'

# --- INICIALIZACIÓN DE LA BASE DE DATOS (MODO PERSISTENTE) ---
print(f"INFO server.py: CWD actual al inicio: {os.getcwd()}") 
print(f"INFO server.py: DATABASE_NAME según database.py: {database.DATABASE_NAME}") # Debería mostrar la ruta absoluta

if not os.path.exists(database.DATABASE_NAME):
    print(f"INFO: La base de datos '{database.DATABASE_NAME}' no existe. Creándola ahora desde server.py...")
    database.crear_db() # Se llamará solo una vez si la BD no existe
    print(f"INFO: Base de datos '{database.DATABASE_NAME}' creada y poblada por server.py.")
else:
    print(f"INFO: La base de datos '{database.DATABASE_NAME}' ya existe. Usando la base de datos existente.")



"""# En server.py, cerca del inicioTEMPORTAL:
print(f"INFO server.py: CWD actual al inicio: {os.getcwd()}")
print(f"INFO server.py: DATABASE_NAME según database.py: {database.DATABASE_NAME}")
print(f"INFO server.py: Forzando la recreación de la base de datos '{database.DATABASE_NAME}'...")
database.crear_db() # Llama directamente para borrar y repoblar
print(f"INFO server.py: Base de datos '{database.DATABASE_NAME}' recreada y poblada.")"""


# --- CONFIGURACIÓN PARA SUBIDA DE ARCHIVOS DE JUSTIFICANTES ---
# Crea la ruta absoluta a la carpeta de subidas dentro de la carpeta de la aplicación
UPLOAD_FOLDER_JUSTIFICANTES = os.path.join(app.root_path, 'uploads', 'justificantes')
ALLOWED_EXTENSIONS_JUSTIFICANTES = {'png', 'jpg', 'jpeg', 'pdf', 'doc', 'docx'}
app.config['UPLOAD_FOLDER_JUSTIFICANTES'] = UPLOAD_FOLDER_JUSTIFICANTES

# Crear la carpeta de subidas si no existe
if not os.path.exists(UPLOAD_FOLDER_JUSTIFICANTES):
    try:
        os.makedirs(UPLOAD_FOLDER_JUSTIFICANTES)
        print(f"INFO: Carpeta de subidas creada en: {UPLOAD_FOLDER_JUSTIFICANTES}")
    except OSError as e:
        print(f"ERROR: No se pudo crear la carpeta de subidas {UPLOAD_FOLDER_JUSTIFICANTES}: {e}")

def allowed_file_justificante(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_JUSTIFICANTES


# --- INICIALIZACIÓN DE LA BASE DE DATOS (MODO PERSISTENTE) ---
print(f"INFO server.py: CWD actual al inicio: {os.getcwd()}") 
print(f"INFO server.py: DATABASE_NAME según database.py: {database.DATABASE_NAME}") # Muestra la ruta absoluta

if not os.path.exists(database.DATABASE_NAME):
    print(f"INFO: La base de datos '{database.DATABASE_NAME}' no existe. Creándola ahora desde server.py...")
    database.crear_db() # Solo se llama si la BD no existe
    print(f"INFO: Base de datos '{database.DATABASE_NAME}' creada y poblada por server.py.")
else:
    print(f"INFO: La base de datos '{database.DATABASE_NAME}' ya existe. Usando la base de datos existente.")
    # Opcional: Considera una función para verificar/actualizar el esquema sin borrar datos:
    # print("INFO: Verificando/asegurando esquema de la base de datos existente...")
    # database.asegurar_esquema() # Necesitarías crear esta función en database.py


# --- DECORATORS FOR ROUTE PROTECTION ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_role') != 'admin':
            flash('Acceso no autorizado. Se requiere rol de administrador.', 'danger')
            return redirect(url_for('login_unificado', next=request.url if request.method == 'GET' else None))
        return f(*args, **kwargs)
    return decorated_function

def maestro_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_role') not in ['maestro', 'admin']:
            flash('Acceso no autorizado. Se requiere rol de maestro o administrador.', 'danger')
            return redirect(url_for('login_unificado', next=request.url if request.method == 'GET' else None))
        return f(*args, **kwargs)
    return decorated_function

def alumno_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_role') != 'alumno':
            flash('Acceso no autorizado. Se requiere rol de alumno.', 'danger')
            return redirect(url_for('login_unificado', next=request.url if request.method == 'GET' else None))
        return f(*args, **kwargs)
    return decorated_function

# --- RUTAS PRINCIPALES Y DE LOGIN ---
@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('user_role')
        if role == 'admin':
            return redirect(url_for('dashboard_admin'))
        elif role == 'maestro':
            return redirect(url_for('dashboard_maestro'))
        elif role == 'alumno':
            return redirect(url_for('dashboard_alumno'))
    return redirect(url_for('login_unificado'))

@app.route('/login', methods=['GET', 'POST'])
def login_unificado():
    if request.method == 'POST':
        identificador = request.form.get('identificador')
        password_form = request.form.get('password')

        if not identificador or not password_form:
            flash('Por favor, ingresa identificador y contraseña.', 'warning')
            return render_template('index.html')

        conn = None
        try:
            conn = database.get_db()
            admin_user = conn.execute("SELECT * FROM Maestros WHERE usuario = ? AND rol = 'admin'", (identificador,)).fetchone()
            if admin_user and check_password_hash(admin_user['password'], password_form):
                session['user_id'] = admin_user['id']
                session['user_role'] = 'admin'
                session['user_name'] = admin_user['nombre']
                flash('Inicio de sesión como administrador exitoso.', 'success')
                next_url = request.args.get('next')
                return redirect(next_url or url_for('dashboard_admin'))

            alumno = conn.execute("SELECT * FROM Alumnos WHERE matricula = ?", (identificador,)).fetchone()
            if alumno and check_password_hash(alumno['password'], password_form):
                session['user_id'] = alumno['id']
                session['user_role'] = 'alumno'
                session['user_name'] = alumno['nombre']
                flash(f"Bienvenido, {alumno['nombre']}!", 'success')
                next_url = request.args.get('next')
                return redirect(next_url or url_for('dashboard_alumno'))

            maestro = conn.execute("SELECT * FROM Maestros WHERE usuario = ? AND rol = 'maestro'", (identificador,)).fetchone()
            if maestro and check_password_hash(maestro['password'], password_form):
                session['user_id'] = maestro['id']
                session['user_role'] = 'maestro'
                session['user_name'] = maestro['nombre']
                flash(f"Bienvenido, {maestro['nombre']}!", 'success')
                next_url = request.args.get('next')
                return redirect(next_url or url_for('dashboard_maestro'))
            
            flash('Identificador o contraseña incorrecta.', 'danger')
        except sqlite3.Error as e:
            flash(f'Error de base de datos al intentar iniciar sesión: {str(e)}', 'danger')
            print(f"ERROR en login_unificado [sqlite3.Error]: {e}")
        except Exception as e:
            flash(f'Error inesperado al intentar iniciar sesión: {str(e)}', 'danger')
            print(f"ERROR en login_unificado [Exception]: {e}")
            traceback.print_exc()
        finally:
            if conn: conn.close()
    return render_template('index.html')

@app.route('/login_alumno_page')
def login_alumno_page():
    return redirect(url_for('login_unificado', tipo='alumno', next=request.args.get('next')))

@app.route('/login_maestro_page')
def login_maestro_page():
    return redirect(url_for('login_unificado', tipo='maestro', next=request.args.get('next')))

@app.route('/login_admin_page')
def login_admin_page():
    return redirect(url_for('login_unificado', tipo='admin', next=request.args.get('next')))

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('login_unificado'))

# --- DASHBOARDS ---
@app.route('/dashboard_alumno')
@alumno_required
def dashboard_alumno():
    # Si necesitas pasar la lista de clases del alumno para el select de justificantes:
    # conn = None
    # mis_clases_asignadas = []
    # try:
    #     conn = database.get_db()
    #     mis_clases_asignadas = conn.execute("""
    #         SELECT mmg.id as asignacion_id, mat.nombre as nombre_materia, mmg.ciclo_escolar
    #         FROM Alumnos a
    #         JOIN Grupos g ON a.grupo_id = g.id
    #         JOIN Maestros_Materias_Grupos mmg ON g.id = mmg.grupo_id
    #         JOIN Materias mat ON mmg.materia_id = mat.id
    #         WHERE a.id = ? ORDER BY mat.nombre
    #     """, (session['user_id'],)).fetchall()
    # except Exception as e:
    #     print(f"Error al cargar clases para dashboard alumno: {e}")
    # finally:
    #     if conn: conn.close()
    # return render_template('dashboard_alumno.html', nombre_usuario=session.get('user_name'), mis_clases_asignadas=mis_clases_asignadas)
    return render_template('dashboard_alumno.html', nombre_usuario=session.get('user_name'))

@app.route('/dashboard_maestro')
@maestro_required
def dashboard_maestro():
    return render_template('dashboard_maestro.html', nombre_usuario=session.get('user_name'))

@app.route('/dashboard_admin')
@admin_required
def dashboard_admin():
    return render_template('dashboard_admin.html', nombre_usuario=session.get('user_name'))

@app.route('/admin/vista_general')
@admin_required
def admin_vista_general():
    conn = None
    lista_maestros_y_admins = [] 
    lista_alumnos = []      
    try:
        conn = database.get_db()
        # Obtener todos los usuarios de la tabla Maestros (que incluye admins)
        lista_maestros_y_admins = conn.execute("SELECT id, nombre, usuario, rol FROM Maestros ORDER BY rol, nombre").fetchall()
        
        lista_alumnos = conn.execute("""
            SELECT a.id, a.nombre, a.matricula,
                   COALESCE(gr.nombre || ' (' || g.nombre || ')', 'Sin grupo asignado') as nombre_grupo_completo
            FROM Alumnos a
            LEFT JOIN Grupos gr ON a.grupo_id = gr.id
            LEFT JOIN Grados g ON gr.grado_id = g.id
            ORDER BY a.nombre
        """).fetchall()

        # ---- PRINTS DE DEPURACIÓN ----
        print(f"DEBUG Vista General: Maestros/Admins recuperados: {lista_maestros_y_admins}")
        if lista_maestros_y_admins:
            print(f"DEBUG Vista General: Total de Maestros/Admins: {len(lista_maestros_y_admins)}")
            print(f"DEBUG Vista General: Ejemplo primer Maestro/Admin: {lista_maestros_y_admins[0]}")
        else:
            print("DEBUG Vista General: La consulta de Maestros/Admins NO DEVOLVIÓ RESULTADOS.")
        
        print(f"DEBUG Vista General: Alumnos recuperados: {lista_alumnos}")
        if lista_alumnos:
            print(f"DEBUG Vista General: Total de Alumnos: {len(lista_alumnos)}")
        else:
            print("DEBUG Vista General: La consulta de Alumnos NO DEVOLVIÓ RESULTADOS.")
        # ---- FIN DE PRINTS ----

    except Exception as e:
        flash(f"Error al cargar la vista general de usuarios: {str(e)}", "danger")
        print(f"ERROR en admin_vista_general: {e}")
        traceback.print_exc()
    finally:
        if conn:
            conn.close()
    
    return render_template(
        'admin/vista_general_usuarios.html',
        maestros_admins=lista_maestros_y_admins,
        alumnos=lista_alumnos
    )

# --- GESTIÓN DE ALUMNOS (ADMIN) ---
@app.route('/admin/alumnos')
@admin_required
def admin_gestionar_alumnos():
    conn = None
    try:
        conn = database.get_db()
        # Usamos el alias 'nombre_alumno' para evitar ambigüedades si Grupos o Grados tuvieran 'nombre'
        alumnos = conn.execute("""
            SELECT a.id, a.nombre AS nombre_alumno, a.matricula, 
                   COALESCE(gr.nombre || ' (' || g.nombre || ')', 'Sin grupo asignado') as nombre_grupo_completo
            FROM Alumnos a
            LEFT JOIN Grupos gr ON a.grupo_id = gr.id
            LEFT JOIN Grados g ON gr.grado_id = g.id
            ORDER BY a.nombre
        """).fetchall()
        print(f"DEBUG: Alumnos recuperados de la BD para la vista: {alumnos}")
        return render_template('admin/admin_gestionar_alumnos.html', alumnos=alumnos)
    except Exception as e:
        flash(f"Error al cargar alumnos: {str(e)}", "danger")
        print(f"ERROR en admin_gestionar_alumnos: {e}")
        traceback.print_exc()
        return redirect(url_for('dashboard_admin'))
    finally:
        if conn: conn.close()

@app.route('/admin/alumnos/agregar', methods=['GET', 'POST'])
def admin_agregar_alumno():
    if 'admin_id' not in session:
        return redirect(url_for('login_unificado'))

    grados = obtener_grados()  # Asumo que ya tienes esta función
    grupos = obtener_grupos()  # Asumo que ya tienes esta función

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellido_paterno = request.form.get('apellido_paterno')
        apellido_materno = request.form.get('apellido_materno')
        fecha_nacimiento = request.form.get('fecha_nacimiento')
        curp = request.form.get('curp')
        direccion = request.form.get('direccion')
        telefono = request.form.get('telefono')
        id_grado = request.form.get('id_grado')
        id_grupo = request.form.get('id_grupo')
        nombre_usuario = request.form.get('nombre_usuario')
        contrasena = request.form.get('contrasena')
        confirmar_contrasena = request.form.get('confirmar_contrasena')

        if not all([nombre, apellido_paterno, fecha_nacimiento, curp, direccion, telefono, id_grado, id_grupo, nombre_usuario, contrasena, confirmar_contrasena]):
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('admin/admin_formulario_alumno.html', grados=grados, grupos=grupos, alumno=request.form, action='agregar')

        if contrasena != confirmar_contrasena:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('admin/admin_formulario_alumno.html', grados=grados, grupos=grupos, alumno=request.form, action='agregar')

        # Verificar si el nombre de usuario ya existe
        if obtener_usuario_por_nombre(nombre_usuario, 'alumno'):
            flash('El nombre de usuario ya existe. Por favor, elige otro.', 'danger')
            return render_template('admin/admin_formulario_alumno.html', grados=grados, grupos=grupos, alumno=request.form, action='agregar')

        # Obtener id_grado_grupo
        id_grado_grupo = obtener_id_grado_grupo(id_grado, id_grupo)

        if id_grado_grupo is None:
            flash('La combinación de grado y grupo seleccionada no es válida. Por favor, crea esta combinación primero o selecciona otra.', 'danger')
            return render_template('admin/admin_formulario_alumno.html', grados=grados, grupos=grupos, alumno=request.form, action='agregar')
        
        hashed_contrasena = generate_password_hash(contrasena)

        try:
            crear_alumno(nombre, apellido_paterno, apellido_materno, fecha_nacimiento, curp, direccion, telefono, id_grado_grupo, nombre_usuario, hashed_contrasena)
            flash('Alumno agregado exitosamente.', 'success')
            return redirect(url_for('admin_gestionar_alumnos'))
        except Exception as e:
            flash(f'Error al agregar el alumno: {str(e)}', 'danger')
            # Podrías querer registrar el error e también
            print(f"Error al crear alumno: {e}") # Para depuración en consola
            return render_template('admin/admin_formulario_alumno.html', grados=grados, grupos=grupos, alumno=request.form, action='agregar')

    return render_template('admin/admin_formulario_alumno.html', grados=grados, grupos=grupos, action='agregar', alumno=None)


@app.route('/admin/alumnos/editar/<int:id_alumno>', methods=['GET', 'POST'])
def admin_editar_alumno(id_alumno):
    if 'admin_id' not in session:
        return redirect(url_for('login_admin'))

    alumno = obtener_alumno_por_id_admin(id_alumno) # Necesitarás una función que traiga también id_grado e id_grupo
    if not alumno:
        flash('Alumno no encontrado.', 'danger')
        return redirect(url_for('admin_gestionar_alumnos'))

    grados = obtener_grados()
    grupos = obtener_grupos()

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellido_paterno = request.form.get('apellido_paterno')
        apellido_materno = request.form.get('apellido_materno')
        fecha_nacimiento = request.form.get('fecha_nacimiento')
        curp = request.form.get('curp')
        direccion = request.form.get('direccion')
        telefono = request.form.get('telefono')
        id_grado = request.form.get('id_grado')
        id_grupo = request.form.get('id_grupo')
        nombre_usuario = request.form.get('nombre_usuario')
        # Para la contraseña, solo actualizar si se proporciona una nueva
        contrasena_nueva = request.form.get('contrasena')
        confirmar_contrasena_nueva = request.form.get('confirmar_contrasena')

        if not all([nombre, apellido_paterno, fecha_nacimiento, curp, direccion, telefono, id_grado, id_grupo, nombre_usuario]):
            flash('Todos los campos (excepto contraseña si no se desea cambiar) son obligatorios.', 'danger')
            # Pasa los datos actuales del alumno y los seleccionados para repoblar el formulario
            current_data = {**alumno, **request.form} 
            return render_template('admin/admin_formulario_alumno.html', alumno=current_data, grados=grados, grupos=grupos, action='editar')

        # Verificar si el nombre de usuario ya existe (y no es el del alumno actual)
        usuario_existente = obtener_usuario_por_nombre(nombre_usuario, 'alumno')
        if usuario_existente and usuario_existente['id_usuario'] != alumno['id_usuario']: # Asumiendo que obtener_alumno_por_id_admin devuelve id_usuario
            flash('El nombre de usuario ya existe para otro alumno. Por favor, elige otro.', 'danger')
            current_data = {**alumno, **request.form}
            return render_template('admin/admin_formulario_alumno.html', alumno=current_data, grados=grados, grupos=grupos, action='editar')

        id_grado_grupo = obtener_id_grado_grupo(id_grado, id_grupo)
        if id_grado_grupo is None:
            flash('La combinación de grado y grupo seleccionada no es válida.', 'danger')
            current_data = {**alumno, **request.form}
            return render_template('admin/admin_formulario_alumno.html', alumno=current_data, grados=grados, grupos=grupos, action='editar')

        hashed_contrasena_actualizar = alumno['contrasena'] # Mantener la contraseña actual por defecto
        if contrasena_nueva:
            if contrasena_nueva != confirmar_contrasena_nueva:
                flash('Las nuevas contraseñas no coinciden.', 'danger')
                current_data = {**alumno, **request.form}
                return render_template('admin/admin_formulario_alumno.html', alumno=current_data, grados=grados, grupos=grupos, action='editar')
            hashed_contrasena_actualizar = generate_password_hash(contrasena_nueva)
        
        try:
            actualizar_alumno_admin(id_alumno, nombre, apellido_paterno, apellido_materno, fecha_nacimiento, curp, direccion, telefono, id_grado_grupo, nombre_usuario, hashed_contrasena_actualizar)
            flash('Alumno actualizado exitosamente.', 'success')
            return redirect(url_for('admin_gestionar_alumnos'))
        except Exception as e:
            flash(f'Error al actualizar el alumno: {str(e)}', 'danger')
            print(f"Error al actualizar alumno: {e}") # Para depuración
            current_data = {**alumno, **request.form}
            return render_template('admin/admin_formulario_alumno.html', alumno=current_data, grados=grados, grupos=grupos, action='editar')

    # Para el método GET, necesitamos id_grado e id_grupo por separado para preseleccionar en el formulario
    # Esto asume que obtener_alumno_por_id_admin ya te da id_grado e id_grupo
    # Si no, necesitarás una función adicional o modificar obtener_alumno_por_id_admin
    # Ejemplo:
    # if alumno and alumno.get('id_grado_grupo'):
    #     info_grado_grupo = obtener_info_grado_grupo_por_id(alumno['id_grado_grupo']) # Necesitarás esta función
    #     if info_grado_grupo:
    #         alumno['id_grado'] = info_grado_grupo['id_grado']
    #         alumno['id_grupo'] = info_grado_grupo['id_grupo']

    return render_template('admin/admin_formulario_alumno.html', alumno=alumno, grados=grados, grupos=grupos, action='editar')

@app.route('/admin/alumnos/eliminar/<int:id_alumno>', methods=['POST'])
@admin_required
def admin_eliminar_alumno(id_alumno):
    conn = None
    try:
        conn = database.get_db()
        conn.execute("DELETE FROM Alumnos WHERE id = ?", (id_alumno,))
        conn.commit()
        flash('Alumno eliminado exitosamente.', 'success')
    except sqlite3.IntegrityError as e:
        flash(f'Error al eliminar alumno: {str(e)}. Puede tener registros asociados.', 'danger')
        if conn: conn.rollback()
    except Exception as e:
        flash(f'Error al eliminar alumno: {str(e)}.', 'danger')
        if conn: conn.rollback()
    finally:
        if conn: conn.close()
    return redirect(url_for('admin_gestionar_alumnos'))

# --- GESTIÓN DE MAESTROS (ADMIN) ---
@app.route('/admin/maestros')
@admin_required
def admin_gestionar_maestros():
    conn = None
    try:
        conn = database.get_db()
        maestros = conn.execute("SELECT id, nombre, usuario, rol FROM Maestros ORDER BY nombre").fetchall()

        # ---- PRINTS DE DEPURACIÓN ----
        print(f"DEBUG gestionando maestros: Maestros recuperados: {maestros}")
        if maestros:
            print(f"DEBUG gestionando maestros: Total de maestros recuperados: {len(maestros)}")
            print(f"DEBUG gestionando maestros: Ejemplo primer maestro: {maestros[0]}")
        else:
            print("DEBUG gestionando maestros: La consulta de maestros NO DEVOLVIÓ RESULTADOS.")
        # ---- FIN DE PRINTS ----

        return render_template('admin/admin_gestionar_maestros.html', maestros=maestros)
    except Exception as e:
        flash(f"Error al cargar maestros: {str(e)}", "danger")
        print(f"ERROR en admin_gestionar_maestros: {e}")
        traceback.print_exc()
        return redirect(url_for('dashboard_admin'))
    finally:
        if conn: conn.close()

@app.route('/admin/maestros/agregar', methods=['GET', 'POST'])
@admin_required
def admin_agregar_maestro():
    if request.method == 'POST':
        conn = None
        try:
            nombre = request.form.get('nombre',"").strip()
            usuario = request.form.get('usuario',"").strip()
            contrasena_form = request.form.get('contrasena')
            rol = request.form.get('rol', 'maestro')

            if not nombre or not usuario or not contrasena_form:
                flash("Nombre, usuario y contraseña son requeridos.", "warning")
                return render_template('admin/admin_formulario_maestro.html', accion="Agregar", maestro=None)

            hashed_password = generate_password_hash(contrasena_form)
            conn = database.get_db()
            conn.execute(
                "INSERT INTO Maestros (nombre, usuario, password, rol) VALUES (?, ?, ?, ?)",
                (nombre, usuario, hashed_password, rol)
            )
            conn.commit()
            flash('Maestro agregado exitosamente.', 'success')
            return redirect(url_for('admin_gestionar_maestros'))
        except sqlite3.IntegrityError:
            flash('Error: El nombre de usuario ya existe.', 'danger')
            if conn: conn.rollback()
        except Exception as e:
            flash(f'Error al agregar maestro: {str(e)}', 'danger')
            print(f"ERROR en admin_agregar_maestro (POST): {e}")
            traceback.print_exc()
            if conn: conn.rollback()
        finally:
            if conn: conn.close()
    return render_template('admin/admin_formulario_maestro.html', accion="Agregar", maestro=None)

@app.route('/admin/maestros/editar/<int:id_maestro>', methods=['GET', 'POST'])
@admin_required
def admin_editar_maestro(id_maestro):
    conn_post = None
    if request.method == 'POST':
        try:
            conn_post = database.get_db()
            nombre = request.form.get('nombre',"").strip()
            usuario = request.form.get('usuario',"").strip()
            rol = request.form.get('rol', 'maestro')
            contrasena_form = request.form.get('contrasena')

            if not nombre or not usuario:
                flash("Nombre y usuario son requeridos.", "warning")
                maestro_data_reload = conn_post.execute("SELECT * FROM Maestros WHERE id = ?", (id_maestro,)).fetchone()
                return render_template('admin/admin_formulario_maestro.html', accion="Editar", maestro=maestro_data_reload)

            if contrasena_form:
                hashed_password = generate_password_hash(contrasena_form)
                conn_post.execute(
                    "UPDATE Maestros SET nombre=?, usuario=?, password=?, rol=? WHERE id=?",
                    (nombre, usuario, hashed_password, rol, id_maestro)
                )
            else:
                conn_post.execute(
                    "UPDATE Maestros SET nombre=?, usuario=?, rol=? WHERE id=?",
                    (nombre, usuario, rol, id_maestro)
                )
            conn_post.commit()
            flash('Maestro actualizado exitosamente.', 'success')
            return redirect(url_for('admin_gestionar_maestros'))
        except sqlite3.IntegrityError:
            flash('Error: El nombre de usuario ya existe para otro maestro.', 'danger')
            if conn_post: conn_post.rollback()
        except Exception as e:
            flash(f'Error al actualizar maestro: {str(e)}', 'danger')
            print(f"ERROR en admin_editar_maestro (POST): {e}")
            traceback.print_exc()
            if conn_post: conn_post.rollback()
        finally:
            if conn_post: conn_post.close()

    conn_get = None
    try:
        conn_get = database.get_db()
        maestro_data = conn_get.execute("SELECT * FROM Maestros WHERE id = ?", (id_maestro,)).fetchone()
        if not maestro_data:
            flash('Maestro no encontrado.', 'danger')
            return redirect(url_for('admin_gestionar_maestros'))
        return render_template('admin/admin_formulario_maestro.html', accion="Editar", maestro=maestro_data)
    except Exception as e:
        flash(f"Error al cargar maestro para editar: {str(e)}", "danger")
        print(f"ERROR en admin_editar_maestro (GET): {e}")
        traceback.print_exc()
        return redirect(url_for('admin_gestionar_maestros'))
    finally:
        if conn_get: conn_get.close()

@app.route('/admin/maestros/eliminar/<int:id_maestro>', methods=['POST'])
@admin_required
def admin_eliminar_maestro(id_maestro):
    conn = None
    try:
        conn = database.get_db()
        # Opcional: Verificar si es el admin principal antes de eliminar
        maestro_a_eliminar = conn.execute("SELECT usuario FROM Maestros WHERE id = ?", (id_maestro,)).fetchone()
        if maestro_a_eliminar and maestro_a_eliminar['usuario'] == 'admin':
            # Contar cuántos administradores hay
            num_admins = conn.execute("SELECT COUNT(*) as count FROM Maestros WHERE rol = 'admin'").fetchone()['count']
            if num_admins <= 1:
                flash("No se puede eliminar al único administrador.", "warning")
                return redirect(url_for('admin_gestionar_maestros'))
        
        conn.execute("DELETE FROM Maestros WHERE id = ?", (id_maestro,))
        conn.commit()
        flash('Maestro eliminado exitosamente.', 'success')
    except sqlite3.IntegrityError as e:
        flash(f'Error al eliminar maestro: {str(e)}. Puede tener asignaciones activas.', 'danger')
        if conn: conn.rollback()
    except Exception as e:
        flash(f'Error al eliminar maestro: {str(e)}', 'danger')
        if conn: conn.rollback()
    finally:
        if conn: conn.close()
    return redirect(url_for('admin_gestionar_maestros'))

# --- GESTIÓN DE MATERIAS (ADMIN) ---
@app.route('/admin/materias')
@admin_required
def admin_gestionar_materias():
    conn = None
    try:
        conn = database.get_db()
        materias = conn.execute("SELECT id, nombre, clave_materia FROM Materias ORDER BY nombre").fetchall()
        return render_template('admin/gestionar_materias.html', materias=materias)
    except Exception as e:
        flash(f"Error al cargar materias: {str(e)}", "danger")
        traceback.print_exc()
        return redirect(url_for('dashboard_admin'))
    finally:
        if conn: conn.close()

@app.route('/admin/materias/agregar', methods=['GET', 'POST'])
@admin_required
def admin_agregar_materia():
    if request.method == 'POST':
        conn = None
        try:
            nombre_materia = request.form.get('nombre_materia',"").strip()
            clave_materia = request.form.get('clave_materia',"").strip() or None # NULL si está vacío
            if not nombre_materia:
                flash("El nombre de la materia es requerido.", "warning")
                return render_template('admin/formulario_materia.html', accion="Agregar", materia=None)
            conn = database.get_db()
            conn.execute(
                "INSERT INTO Materias (nombre, clave_materia) VALUES (?, ?)",
                (nombre_materia, clave_materia)
            )
            conn.commit()
            flash('Materia agregada exitosamente.', 'success')
            return redirect(url_for('admin_gestionar_materias'))
        except sqlite3.IntegrityError:
            flash('Error: El nombre o la clave de la materia ya existen.', 'danger')
            if conn: conn.rollback()
        except Exception as e:
            flash(f'Error al agregar materia: {str(e)}', 'danger')
            traceback.print_exc()
            if conn: conn.rollback()
        finally:
            if conn: conn.close()
    return render_template('admin/formulario_materia.html', accion="Agregar", materia=None)

@app.route('/admin/materias/editar/<int:id_materia>', methods=['GET', 'POST'])
@admin_required
def admin_editar_materia(id_materia):
    conn_post = None
    if request.method == 'POST':
        try:
            conn_post = database.get_db()
            nombre_materia = request.form.get('nombre_materia',"").strip()
            clave_materia = request.form.get('clave_materia',"").strip() or None # NULL si está vacío
            if not nombre_materia:
                flash("El nombre de la materia es requerido.", "warning")
                materia_data_reload = conn_post.execute("SELECT * FROM Materias WHERE id = ?", (id_materia,)).fetchone()
                return render_template('admin/formulario_materia.html', accion="Editar", materia=materia_data_reload)
            conn_post.execute(
                "UPDATE Materias SET nombre=?, clave_materia=? WHERE id=?",
                (nombre_materia, clave_materia, id_materia)
            )
            conn_post.commit()
            flash('Materia actualizada exitosamente.', 'success')
            return redirect(url_for('admin_gestionar_materias'))
        except sqlite3.IntegrityError:
            flash('Error: El nombre o la clave ya existen para otra materia.', 'danger')
            if conn_post: conn_post.rollback()
        except Exception as e:
            flash(f'Error al actualizar materia: {str(e)}', 'danger')
            traceback.print_exc()
            if conn_post: conn_post.rollback()
        finally:
            if conn_post: conn_post.close()
    conn_get = None
    try:
        conn_get = database.get_db()
        materia_data = conn_get.execute("SELECT * FROM Materias WHERE id = ?", (id_materia,)).fetchone()
        if not materia_data:
            flash('Materia no encontrada.', 'danger')
            return redirect(url_for('admin_gestionar_materias'))
        return render_template('admin/formulario_materia.html', accion="Editar", materia=materia_data)
    except Exception as e:
        flash(f"Error al cargar materia: {str(e)}", "danger")
        traceback.print_exc()
        return redirect(url_for('admin_gestionar_materias'))
    finally:
        if conn_get: conn_get.close()

@app.route('/admin/materias/eliminar/<int:id_materia>', methods=['POST'])
@admin_required
def admin_eliminar_materia(id_materia):
    conn = None
    try:
        conn = database.get_db()
        conn.execute("DELETE FROM Materias WHERE id = ?", (id_materia,))
        conn.commit()
        flash('Materia eliminada exitosamente.', 'success')
    except sqlite3.IntegrityError as e:
        flash(f'Error al eliminar materia: {str(e)}. Puede estar asignada.', 'danger')
        if conn: conn.rollback()
    except Exception as e:
        flash(f'Error al eliminar materia: {str(e)}.', 'danger')
        if conn: conn.rollback()
    finally:
        if conn: conn.close()
    return redirect(url_for('admin_gestionar_materias'))

# --- GESTIÓN DE GRADOS (ADMIN) ---
@app.route('/admin/grados')
@admin_required
def admin_gestionar_grados():
    conn = None
    try:
        conn = database.get_db()
        grados = conn.execute("SELECT id, nombre FROM Grados ORDER BY nombre").fetchall()
        return render_template('admin/gestionar_grados.html', grados=grados)
    except Exception as e:
        flash(f"Error al cargar grados: {str(e)}", "danger")
        traceback.print_exc()
        return redirect(url_for('dashboard_admin'))
    finally:
        if conn: conn.close()

@app.route('/admin/grados/agregar', methods=['GET', 'POST'])
@admin_required
def admin_agregar_grado():
    if request.method == 'POST':
        conn = None
        try:
            nombre_grado = request.form.get('nombre_grado',"").strip()
            if not nombre_grado:
                flash("El nombre del grado es requerido.", "warning")
                return render_template('admin/formulario_grado.html', accion="Agregar", grado=None)
            conn = database.get_db()
            conn.execute("INSERT INTO Grados (nombre) VALUES (?)", (nombre_grado,))
            conn.commit()
            flash('Grado agregado exitosamente.', 'success')
            return redirect(url_for('admin_gestionar_grados'))
        except sqlite3.IntegrityError:
            flash('Error: El nombre del grado ya existe.', 'danger')
            if conn: conn.rollback()
        except Exception as e:
            flash(f'Error al agregar grado: {str(e)}', 'danger')
            traceback.print_exc()
            if conn: conn.rollback()
        finally:
            if conn: conn.close()
    return render_template('admin/formulario_grado.html', accion="Agregar", grado=None)

@app.route('/admin/grados/editar/<int:id_grado>', methods=['GET', 'POST'])
@admin_required
def admin_editar_grado(id_grado):
    conn_post = None
    if request.method == 'POST':
        try:
            conn_post = database.get_db()
            nombre_grado = request.form.get('nombre_grado',"").strip()
            if not nombre_grado:
                flash("El nombre del grado es requerido.", "warning")
                grado_data_reload = conn_post.execute("SELECT * FROM Grados WHERE id = ?", (id_grado,)).fetchone()
                return render_template('admin/formulario_grado.html', accion="Editar", grado=grado_data_reload)
            conn_post.execute("UPDATE Grados SET nombre = ? WHERE id = ?", (nombre_grado, id_grado))
            conn_post.commit()
            flash('Grado actualizado exitosamente.', 'success')
            return redirect(url_for('admin_gestionar_grados'))
        except sqlite3.IntegrityError:
            flash('Error: El nombre del grado ya existe.', 'danger')
            if conn_post: conn_post.rollback()
        except Exception as e:
            flash(f'Error al actualizar grado: {str(e)}', 'danger')
            traceback.print_exc()
            if conn_post: conn_post.rollback()
        finally:
            if conn_post: conn_post.close()
    conn_get = None
    try:
        conn_get = database.get_db()
        grado_data = conn_get.execute("SELECT * FROM Grados WHERE id = ?", (id_grado,)).fetchone()
        if not grado_data:
            flash('Grado no encontrado.', 'danger')
            return redirect(url_for('admin_gestionar_grados'))
        return render_template('admin/formulario_grado.html', accion="Editar", grado=grado_data)
    except Exception as e:
        flash(f"Error al cargar grado: {str(e)}", "danger")
        traceback.print_exc()
        return redirect(url_for('admin_gestionar_grados'))
    finally:
        if conn_get: conn_get.close()

@app.route('/admin/grados/eliminar/<int:id_grado>', methods=['POST'])
@admin_required
def admin_eliminar_grado(id_grado):
    conn = None
    try:
        conn = database.get_db()
        conn.execute("DELETE FROM Grados WHERE id = ?", (id_grado,))
        conn.commit()
        flash('Grado eliminado exitosamente.', 'success')
    except sqlite3.IntegrityError as e:
        flash(f'Error al eliminar grado: {str(e)}. Puede tener grupos asociados.', 'danger')
        if conn: conn.rollback()
    except Exception as e:
        flash(f'Error al eliminar grado: {str(e)}', 'danger')
        if conn: conn.rollback()
    finally:
        if conn: conn.close()
    return redirect(url_for('admin_gestionar_grados'))

# --- GESTIÓN DE GRUPOS (ADMIN) ---
@app.route('/admin/grupos')
@admin_required
def admin_gestionar_grupos():
    conn = None
    try:
        conn = database.get_db()
        grupos = conn.execute("""
            SELECT grp.id, grp.nombre as nombre_grupo, g.nombre as nombre_grado 
            FROM Grupos grp
            JOIN Grados g ON grp.grado_id = g.id
            ORDER BY g.nombre, grp.nombre
        """).fetchall()
        return render_template('admin/gestionar_grupos.html', grupos=grupos)
    except Exception as e:
        flash(f"Error al cargar grupos: {str(e)}", "danger")
        traceback.print_exc()
        return redirect(url_for('dashboard_admin'))
    finally:
        if conn: conn.close()

@app.route('/admin/grupos/agregar', methods=['GET', 'POST'])
@admin_required
def admin_agregar_grupo():
    grados_data = []
    conn_load_grados = None
    try:
        conn_load_grados = database.get_db()
        grados_data_raw = conn_load_grados.execute("SELECT id, nombre FROM Grados ORDER BY nombre").fetchall()
        grados_data = [{'id': g['id'], 'nombre': g['nombre']} for g in grados_data_raw]
    except Exception as e:
        flash(f"Error al cargar grados para el formulario: {str(e)}", "warning")
        traceback.print_exc()
    finally:
        if conn_load_grados: conn_load_grados.close()

    if request.method == 'POST':
        conn = None
        try:
            nombre_grupo = request.form.get('nombre_grupo',"").strip()
            id_grado_str = request.form.get('id_grado')
            if not nombre_grupo or not id_grado_str:
                flash("Nombre de grupo y grado son requeridos.", "warning")
                return render_template('admin/formulario_grupo.html', accion="Agregar", grupo=None, grados=grados_data)
            id_grado = int(id_grado_str)
            conn = database.get_db()
            conn.execute("INSERT INTO Grupos (nombre, grado_id) VALUES (?, ?)", (nombre_grupo, id_grado))
            conn.commit()
            flash('Grupo agregado exitosamente.', 'success')
            return redirect(url_for('admin_gestionar_grupos'))
        except sqlite3.IntegrityError:
            flash('Error: La combinación de nombre de grupo y grado ya existe.', 'danger')
            if conn: conn.rollback()
        except ValueError:
            flash('Error: ID de grado no válido.', 'danger')
            if conn: conn.rollback()
        except Exception as e:
            flash(f'Error al agregar grupo: {str(e)}', 'danger')
            traceback.print_exc()
            if conn: conn.rollback()
        finally:
            if conn: conn.close()
    return render_template('admin/formulario_grupo.html', accion="Agregar", grupo=None, grados=grados_data)

@app.route('/admin/grupos/editar/<int:id_grupo>', methods=['GET', 'POST'])
@admin_required
def admin_editar_grupo(id_grupo):
    grados_data = []
    conn_load_data = None
    try:
        conn_load_data = database.get_db()
        grados_data_raw = conn_load_data.execute("SELECT id, nombre FROM Grados ORDER BY nombre").fetchall()
        grados_data = [{'id': g['id'], 'nombre': g['nombre']} for g in grados_data_raw]
    except Exception as e:
        flash(f"Error al cargar grados para el formulario: {str(e)}", "warning")
        traceback.print_exc()
    finally:
        if conn_load_data: conn_load_data.close()

    if request.method == 'POST':
        conn_post = None
        try:
            conn_post = database.get_db()
            nombre_grupo = request.form.get('nombre_grupo',"").strip()
            id_grado_str = request.form.get('id_grado')
            if not nombre_grupo or not id_grado_str:
                flash("Nombre de grupo y grado son requeridos.", "warning")
                grupo_data_reload = conn_post.execute("SELECT * FROM Grupos WHERE id = ?", (id_grupo,)).fetchone()
                return render_template('admin/formulario_grupo.html', accion="Editar", grupo=grupo_data_reload, grados=grados_data)
            id_grado = int(id_grado_str)
            conn_post.execute("UPDATE Grupos SET nombre = ?, grado_id = ? WHERE id = ?", (nombre_grupo, id_grado, id_grupo))
            conn_post.commit()
            flash('Grupo actualizado exitosamente.', 'success')
            return redirect(url_for('admin_gestionar_grupos'))
        except sqlite3.IntegrityError:
            flash('Error: La combinación de nombre de grupo y grado ya existe.', 'danger')
            if conn_post: conn_post.rollback()
        except ValueError:
            flash('Error: ID de grado no válido.', 'danger')
            if conn_post: conn_post.rollback()
        except Exception as e:
            flash(f'Error al actualizar grupo: {str(e)}', 'danger')
            traceback.print_exc()
            if conn_post: conn_post.rollback()
        finally:
            if conn_post: conn_post.close()
    
    conn_get_grupo = None
    try:
        conn_get_grupo = database.get_db()
        grupo_data = conn_get_grupo.execute("SELECT * FROM Grupos WHERE id = ?", (id_grupo,)).fetchone()
        if not grupo_data:
            flash('Grupo no encontrado.', 'danger')
            return redirect(url_for('admin_gestionar_grupos'))
        return render_template('admin/formulario_grupo.html', accion="Editar", grupo=grupo_data, grados=grados_data)
    except Exception as e:
        flash(f"Error al cargar grupo para editar: {str(e)}", "danger")
        traceback.print_exc()
        return redirect(url_for('admin_gestionar_grupos'))
    finally:
        if conn_get_grupo: conn_get_grupo.close()

@app.route('/admin/grupos/eliminar/<int:id_grupo>', methods=['POST'])
@admin_required
def admin_eliminar_grupo(id_grupo):
    conn = None
    try:
        conn = database.get_db()
        conn.execute("DELETE FROM Grupos WHERE id = ?", (id_grupo,))
        conn.commit()
        flash('Grupo eliminado exitosamente.', 'success')
    except sqlite3.IntegrityError as e:
        flash(f'Error al eliminar grupo: {str(e)}. Puede tener alumnos o asignaciones.', 'danger')
        if conn: conn.rollback()
    except Exception as e:
        flash(f'Error al eliminar grupo: {str(e)}', 'danger')
        if conn: conn.rollback()
    finally:
        if conn: conn.close()
    return redirect(url_for('admin_gestionar_grupos'))

# --- GESTIÓN DE ASIGNACIONES (MATERIA-MAESTRO-GRUPO) ---
@app.route('/admin/asignaciones')
@admin_required
def admin_gestionar_asignaciones():
    conn = None
    try:
        conn = database.get_db()
        asignaciones = conn.execute("""
            SELECT 
                a.id,
                m.nombre AS nombre_materia,
                ma.nombre AS nombre_maestro,
                grp.nombre AS nombre_grupo_literal,
                g.nombre AS nombre_grado,
                a.ciclo_escolar
            FROM Maestros_Materias_Grupos a
            JOIN Materias m ON a.materia_id = m.id
            JOIN Maestros ma ON a.maestro_id = ma.id
            JOIN Grupos grp ON a.grupo_id = grp.id
            JOIN Grados g ON grp.grado_id = g.id
            ORDER BY g.nombre, grp.nombre, m.nombre
        """).fetchall()
        return render_template('admin/gestionar_asignaciones.html', asignaciones=asignaciones)
    except Exception as e:
        flash(f"Error al cargar asignaciones: {str(e)}", "danger")
        traceback.print_exc()
        return redirect(url_for('dashboard_admin'))
    finally:
        if conn: conn.close()

@app.route('/admin/asignaciones/agregar', methods=['GET', 'POST'])
@admin_required
def admin_agregar_asignacion():
    materias, maestros, grupos = [], [], []
    conn_load_form = None
    try:
        conn_load_form = database.get_db()
        materias_raw = conn_load_form.execute("SELECT id, nombre FROM Materias ORDER BY nombre").fetchall()
        materias = [{'id': m['id'], 'nombre': m['nombre']} for m in materias_raw]
        maestros_raw = conn_load_form.execute("SELECT id, nombre FROM Maestros WHERE rol='maestro' OR rol='admin' ORDER BY nombre").fetchall()
        maestros = [{'id': ma['id'], 'nombre': ma['nombre']} for ma in maestros_raw]
        grupos_raw = conn_load_form.execute("""
            SELECT grp.id, grp.nombre || ' (' || g.nombre || ')' AS nombre_completo_grupo 
            FROM Grupos grp
            JOIN Grados g ON grp.grado_id = g.id 
            ORDER BY g.nombre, grp.nombre
        """).fetchall()
        grupos = [{'id': gr['id'], 'nombre_completo_grupo': gr['nombre_completo_grupo']} for gr in grupos_raw]
    except Exception as e:
        flash(f"Error al cargar datos para el formulario: {str(e)}", "warning")
        traceback.print_exc()
    finally:
        if conn_load_form: conn_load_form.close()
    
    if request.method == 'POST':
        conn = None
        try:
            id_materia_str = request.form.get('id_materia')
            id_maestro_str = request.form.get('id_maestro')
            id_grupo_str = request.form.get('id_grupo')
            ciclo_escolar = request.form.get('ciclo_escolar',"").strip()

            if not id_materia_str or not id_maestro_str or not id_grupo_str or not ciclo_escolar:
                flash("Todos los campos son requeridos.", "warning")
                return render_template('admin/formulario_asignacion.html', accion="Agregar", asignacion=None, materias=materias, maestros=maestros, grupos=grupos)

            id_materia = int(id_materia_str)
            id_maestro = int(id_maestro_str)
            id_grupo = int(id_grupo_str)

            conn = database.get_db()
            conn.execute(
                "INSERT INTO Maestros_Materias_Grupos (materia_id, maestro_id, grupo_id, ciclo_escolar) VALUES (?, ?, ?, ?)",
                (id_materia, id_maestro, id_grupo, ciclo_escolar)
            )
            conn.commit()
            flash('Asignación creada exitosamente.', 'success')
            return redirect(url_for('admin_gestionar_asignaciones'))
        except sqlite3.IntegrityError:
            flash('Error: Esta asignación (Materia-Maestro-Grupo-Ciclo) ya existe.', 'danger')
            if conn: conn.rollback()
        except ValueError:
            flash('Error: IDs no válidos.', 'danger')
            if conn: conn.rollback()
        except Exception as e:
            flash(f'Error al crear asignación: {str(e)}', 'danger')
            traceback.print_exc()
            if conn: conn.rollback()
        finally:
            if conn: conn.close()
    return render_template('admin/formulario_asignacion.html', accion="Agregar", asignacion=None, materias=materias, maestros=maestros, grupos=grupos)

@app.route('/admin/asignaciones/eliminar/<int:id_asignacion>', methods=['POST'])
@admin_required
def admin_eliminar_asignacion(id_asignacion):
    conn = None
    try:
        conn = database.get_db()
        conn.execute("DELETE FROM Maestros_Materias_Grupos WHERE id = ?", (id_asignacion,))
        conn.commit()
        flash('Asignación eliminada exitosamente.', 'success')
    except sqlite3.IntegrityError as e:
        flash(f'Error al eliminar asignación: {str(e)}. Puede tener registros asociados.', 'danger')
        if conn: conn.rollback()
    except Exception as e:
        flash(f'Error al eliminar asignación: {str(e)}', 'danger')
        if conn: conn.rollback()
    finally:
        if conn: conn.close()
    return redirect(url_for('admin_gestionar_asignaciones'))

# --- RUTAS PARA MAESTROS ---
@app.route('/maestro/mis_clases')
@maestro_required
def maestro_mis_clases():
    id_maestro_actual = session.get('user_id')
    conn = None
    try:
        conn = database.get_db()
        clases = conn.execute("""
            SELECT 
                a.id, 
                m.nombre AS nombre_materia, 
                grp.nombre AS nombre_grupo_literal, 
                g.nombre AS nombre_grado,
                a.ciclo_escolar
            FROM Maestros_Materias_Grupos a
            JOIN Materias m ON a.materia_id = m.id
            JOIN Grupos grp ON a.grupo_id = grp.id
            JOIN Grados g ON grp.grado_id = g.id
            WHERE a.maestro_id = ?
            ORDER BY g.nombre, grp.nombre, m.nombre
        """, (id_maestro_actual,)).fetchall()
        return render_template('maestros/mis_clases.html', clases=clases)
    except Exception as e:
        flash(f"Error al cargar mis clases: {str(e)}", "danger")
        traceback.print_exc()
        return redirect(url_for('dashboard_maestro'))
    finally:
        if conn: conn.close()

@app.route('/maestro/registrar_asistencia/<int:id_asignacion>', methods=['GET', 'POST'])
@maestro_required
def maestro_registrar_asistencia(id_asignacion):
    id_maestro_actual = session.get('user_id')
    id_grupo_de_asignacion = None
    nombre_clase = ""
    conn_check = None
    try:
        conn_check = database.get_db()
        asignacion_info = conn_check.execute("""
            SELECT ammg.grupo_id, m.nombre AS nombre_materia, 
                   grp.nombre AS nombre_grupo_literal, g.nombre AS nombre_grado_literal
            FROM Maestros_Materias_Grupos ammg 
            JOIN Materias m ON ammg.materia_id = m.id 
            JOIN Grupos grp ON ammg.grupo_id = grp.id 
            JOIN Grados g ON grp.grado_id = g.id 
            WHERE ammg.id = ? AND ammg.maestro_id = ?
        """, (id_asignacion, id_maestro_actual)).fetchone()
        if not asignacion_info:
            flash("No tienes permiso para esta clase o la clase no existe.", "danger")
            return redirect(url_for('maestro_mis_clases'))
        id_grupo_de_asignacion = asignacion_info['grupo_id']
        nombre_clase = f"{asignacion_info['nombre_materia']} - {asignacion_info['nombre_grado_literal']} {asignacion_info['nombre_grupo_literal']}"
    except Exception as e:
        flash(f"Error al verificar la asignación: {str(e)}", "danger")
        traceback.print_exc()
        if conn_check: conn_check.close()
        return redirect(url_for('maestro_mis_clases'))
    finally:
        if conn_check: conn_check.close()
    
    if request.method == 'POST':
        conn = None
        try:
            conn = database.get_db()
            fecha_asistencia = request.form.get('fecha_asistencia')
            if not fecha_asistencia:
                flash("La fecha de asistencia es requerida.", "warning")
                # Recargar datos para el formulario
                alumnos_recarga = conn.execute("SELECT id, nombre FROM Alumnos WHERE grupo_id = ? ORDER BY nombre", (id_grupo_de_asignacion,)).fetchall()
                asistencias_previas_recarga = {}
                asistencias_raw = conn.execute("SELECT alumno_id, estado, observaciones FROM Asistencias WHERE asignacion_id = ? AND fecha = ?", (id_asignacion, fecha_asistencia if fecha_asistencia else datetime.now().strftime('%Y-%m-%d'))).fetchall()
                for ar in asistencias_raw: asistencias_previas_recarga[ar['alumno_id']] = {'estado': ar['estado'], 'observaciones': ar['observaciones']}
                return render_template('maestros/registrar_asistencia.html', alumnos=alumnos_recarga, id_asignacion=id_asignacion, nombre_clase=nombre_clase, fecha_seleccionada=fecha_asistencia, asistencias_previas=asistencias_previas_recarga)

            alumnos_del_grupo_ids = [row['id'] for row in conn.execute("SELECT id FROM Alumnos WHERE grupo_id = ?", (id_grupo_de_asignacion,)).fetchall()]
            for id_alumno in alumnos_del_grupo_ids:
                estado_asistencia_form = request.form.get(f'asistencia_{id_alumno}')
                observaciones = request.form.get(f'observaciones_{id_alumno}',"").strip()
                if not estado_asistencia_form:
                    continue 
                conn.execute("DELETE FROM Asistencias WHERE alumno_id = ? AND asignacion_id = ? AND fecha = ?", (id_alumno, id_asignacion, fecha_asistencia))
                conn.execute("""
                    INSERT INTO Asistencias (alumno_id, asignacion_id, fecha, estado, observaciones, hora)
                    VALUES (?, ?, ?, ?, ?, strftime('%H:%M', 'now', 'localtime')) 
                """, (id_alumno, id_asignacion, fecha_asistencia, estado_asistencia_form, observaciones))
            conn.commit()
            flash("Asistencia registrada/actualizada exitosamente.", "success")
            return redirect(url_for('maestro_mis_clases')) # O a la misma página con la fecha
        except Exception as e:
            flash(f"Error al registrar asistencia: {str(e)}", "danger")
            traceback.print_exc()
            if conn: conn.rollback()
        finally:
            if conn: conn.close()
    
    alumnos_para_formulario = []
    asistencias_previas = {}
    fecha_seleccionada_get = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d')) # Tomar fecha de URL o hoy
    conn_get_alumnos = None
    try:
        conn_get_alumnos = database.get_db()
        alumnos_para_formulario = conn_get_alumnos.execute("SELECT id, nombre FROM Alumnos WHERE grupo_id = ? ORDER BY nombre", (id_grupo_de_asignacion,)).fetchall()
        asistencias_raw = conn_get_alumnos.execute("SELECT alumno_id, estado, observaciones FROM Asistencias WHERE asignacion_id = ? AND fecha = ?", (id_asignacion, fecha_seleccionada_get)).fetchall()
        for ar in asistencias_raw: asistencias_previas[ar['alumno_id']] = {'estado': ar['estado'], 'observaciones': ar['observaciones']}
    except Exception as e:
        flash(f"Error al cargar alumnos/asistencias: {str(e)}", "danger")
        traceback.print_exc()
    finally:
        if conn_get_alumnos: conn_get_alumnos.close()
            
    return render_template('maestros/registrar_asistencia.html', alumnos=alumnos_para_formulario, id_asignacion=id_asignacion, nombre_clase=nombre_clase, fecha_seleccionada=fecha_seleccionada_get, asistencias_previas=asistencias_previas)

# --- RUTAS PARA ALUMNOS ---
@app.route('/alumno/mis_calificaciones')
@alumno_required
def alumno_mis_calificaciones():
    calificaciones = [] 
    flash("Funcionalidad 'Mis Calificaciones' aún no implementada.", "info")
    return render_template('alumnos/mis_calificaciones.html', calificaciones=calificaciones, nombre_usuario=session.get('user_name'))

@app.route('/alumno/justificante/subir', methods=['GET', 'POST'])
@alumno_required
def alumno_subir_justificante():
    if request.method == 'GET':
        # Si el formulario está en dashboard_alumno.html, no es necesario renderizar nada aquí.
        # Opcionalmente, cargar datos para el select de asignaciones si el form lo requiere:
        conn_get = None
        mis_clases_asignadas_para_form = []
        try:
            conn_get = database.get_db()
            # Esta consulta es un ejemplo, ajústala a tus necesidades para mostrar al alumno
            # las materias/asignaciones a las que puede aplicar un justificante.
            mis_clases_asignadas_para_form = conn_get.execute("""
                SELECT mmg.id as asignacion_id, mat.nombre as nombre_materia, mmg.ciclo_escolar
                FROM Alumnos a
                JOIN Grupos g ON a.grupo_id = g.id
                JOIN Maestros_Materias_Grupos mmg ON g.id = mmg.grupo_id
                JOIN Materias mat ON mmg.materia_id = mat.id
                WHERE a.id = ? ORDER BY mat.nombre
            """, (session['user_id'],)).fetchall()
        except Exception as e:
            print(f"Error cargando asignaciones para form justificante: {e}")
            traceback.print_exc()
        finally:
            if conn_get: conn_get.close()
        
        # Se asume que dashboard_alumno.html es donde vive el formulario.
        # Si tienes una plantilla separada para el formulario, úsala aquí.
        # return render_template('alumno_formulario_justificante.html', mis_clases_asignadas=mis_clases_asignadas_para_form)
        # Si el form está en el dashboard, este GET no es estrictamente necesario o podría redirigir.
        # Por ahora, redirigiremos para evitar confusión, asumiendo que el dashboard ya muestra el formulario.
        return redirect(url_for('dashboard_alumno')) # Redirige si se accede por GET

    # Solo procesar si es POST
    if request.method == 'POST':
        fecha_inasistencia_inicio = request.form.get('fecha_inasistencia_inicio')
        fecha_inasistencia_fin = request.form.get('fecha_inasistencia_fin')
        id_asignacion_str = request.form.get('id_asignacion') 
        motivo = request.form.get('motivo',"").strip()
        archivo = request.files.get('archivo_justificante')

        if not fecha_inasistencia_inicio or not fecha_inasistencia_fin or not motivo:
            flash('Las fechas de inasistencia y el motivo son requeridos.', 'warning')
            return redirect(url_for('dashboard_alumno'))

        id_asignacion = None
        if id_asignacion_str and id_asignacion_str.isdigit():
            id_asignacion = int(id_asignacion_str)
        elif id_asignacion_str == "" or id_asignacion_str is None: # Opción "Justificante General"
             id_asignacion = None # Asegura que sea NULL si está vacío

        conn = None
        try:
            conn = database.get_db()
            alumno_id_actual = session.get('user_id')
            fecha_solicitud_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            archivo_path_guardado = None

            if archivo and archivo.filename != '':
                if allowed_file_justificante(archivo.filename):
                    filename = secure_filename(archivo.filename)
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    unique_filename = f"{alumno_id_actual}_{timestamp}_{filename}"
                    path_completo = os.path.join(app.config['UPLOAD_FOLDER_JUSTIFICANTES'], unique_filename)
                    archivo.save(path_completo)
                    archivo_path_guardado = unique_filename
                else:
                    flash('Tipo de archivo no permitido. Solo: png, jpg, jpeg, pdf, doc, docx.', 'warning')
                    return redirect(url_for('dashboard_alumno'))
            
            sql = """
                INSERT INTO Justificantes 
                (alumno_id, fecha_solicitud, fecha_inasistencia_inicio, fecha_inasistencia_fin, 
                 asignacion_id, motivo, archivo_path, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                alumno_id_actual, fecha_solicitud_actual, fecha_inasistencia_inicio, fecha_inasistencia_fin,
                id_asignacion, motivo, archivo_path_guardado, 'Pendiente'
            )
            conn.execute(sql, params)
            conn.commit()
            flash('Justificante enviado exitosamente. Pendiente de revisión.', 'success')
        
        except sqlite3.Error as e:
            flash(f"Error de BD al enviar justificante: {e}", "danger")
            print(f"ERROR SQLite en alumno_subir_justificante: {e}")
            traceback.print_exc()
            if conn: conn.rollback()
        except Exception as e:
            flash(f"Error inesperado al enviar justificante: {e}", "danger")
            print(f"ERROR Exception en alumno_subir_justificante: {e}")
            traceback.print_exc()
            if conn: conn.rollback()
        finally:
            if conn: conn.close()
        
        return redirect(url_for('dashboard_alumno'))
    
    # Fallback si no es POST (aunque el GET ya redirige)
    return redirect(url_for('dashboard_alumno'))

# --- Manejadores de errores ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error_404.html', error=e, nombre_usuario=session.get('user_name')), 404

@app.errorhandler(500)
def internal_server_error(e):
    print(f"ERROR 500: {e}") 
    traceback.print_exc()
    return render_template('error_500.html', error="Ocurrió un error interno en el servidor.", nombre_usuario=session.get('user_name')), 500

if __name__ == '__main__':
    print(f"INFO: CWD en server.py: {os.getcwd()}") # Para verificar directorio de trabajo
    print("INFO: Iniciando servidor Flask...")
    app.run(debug=True, port=5001)