from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
from datetime import datetime
from functools import wraps # Para los decoradores
from werkzeug.security import generate_password_hash, check_password_hash # Para contraseñas seguras
import database # Tu módulo database.py

app = Flask(__name__)
# ¡MUY IMPORTANTE! Cambia esto por una clave secreta realmente fuerte y única.
app.secret_key = 'esta_es_otra_clave_secreta_super_segura_y_unica_67890!'

database.crear_db() 

def conectar_db():
    conn = sqlite3.connect(database.DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# --- DECORADORES DE CONTROL DE ACCESO ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def roles_required(roles_permitidos):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Debes iniciar sesión para acceder a esta página.', 'warning')
                return redirect(url_for('login'))
            if session.get('rol') not in roles_permitidos:
                flash('No tienes permiso para acceder a esta página.', 'danger')
                current_rol = session.get('rol')
                if current_rol == 'admin':
                    return redirect(url_for('dashboard_admin'))
                elif current_rol == 'maestro':
                    return redirect(url_for('dashboard_maestro'))
                elif current_rol == 'alumno':
                    return redirect(url_for('dashboard_alumno'))
                else:
                    return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- RUTAS PRINCIPALES Y LOGIN/LOGOUT ---
@app.route('/')
def home():
    if 'user_id' in session:
        rol = session.get('rol')
        if rol == 'admin':
            return redirect(url_for('dashboard_admin'))
        elif rol == 'maestro':
            return redirect(url_for('dashboard_maestro'))
        elif rol == 'alumno':
            return redirect(url_for('dashboard_alumno'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identificador = request.form['identificador']
        password_ingresada = request.form['password']
        conn = conectar_db()
        cursor = conn.cursor()
        user_authenticated = False

        cursor.execute("SELECT id, nombre, usuario, password, rol FROM maestros WHERE usuario = ?", (identificador,))
        user_db = cursor.fetchone()
        if user_db and check_password_hash(user_db['password'], password_ingresada):
            session.clear()
            session['user_id'] = user_db['id']
            session['nombre_usuario'] = user_db['nombre'] if user_db['nombre'] else user_db['usuario']
            session['rol'] = user_db['rol']
            user_authenticated = True
            flash(f"Bienvenido, {session.get('rol').capitalize()} {session.get('nombre_usuario')}!", 'success')
            if session['rol'] == 'admin':
                conn.close()
                return redirect(url_for('dashboard_admin'))
            else:
                conn.close()
                return redirect(url_for('dashboard_maestro'))
        
        if not user_authenticated:
            cursor.execute("SELECT id, nombre, matricula, password, rol, maestro_id FROM alumnos WHERE matricula = ?", (identificador,))
            user_db = cursor.fetchone()
            if user_db and check_password_hash(user_db['password'], password_ingresada):
                session.clear()
                session['user_id'] = user_db['id']
                session['nombre_usuario'] = user_db['nombre'] if user_db['nombre'] else user_db['matricula']
                session['rol'] = user_db['rol']
                session['maestro_asignado_id'] = user_db['maestro_id']
                user_authenticated = True
                conn.close()
                flash(f"Bienvenido, Alumno {session.get('nombre_usuario')}!", 'success')
                return redirect(url_for('dashboard_alumno'))

        conn.close()
        if not user_authenticated:
            flash('Identificador o contraseña incorrectos. Por favor, inténtalo de nuevo.', 'error')
        return redirect(url_for('login'))

    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('index.html')

@app.route('/logout')
@login_required 
def logout():
    session.clear()
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('login'))

# --- DASHBOARDS ---
@app.route('/dashboard_admin')
@login_required
@roles_required(['admin'])
def dashboard_admin():
    return render_template('dashboard_admin.html')

@app.route('/dashboard_maestro')
@login_required
@roles_required(['maestro', 'admin'])
def dashboard_maestro():
    return render_template('dashboard_maestro.html')

@app.route('/dashboard_alumno')
@login_required
@roles_required(['alumno'])
def dashboard_alumno():
    conn = conectar_db()
    cursor = conn.cursor()
    asistencias = []
    justificantes = []
    try:
        cursor.execute("SELECT fecha, hora, estado FROM asistencias WHERE alumno_id = ? ORDER BY fecha DESC, hora DESC", (session['user_id'],))
        asistencias = cursor.fetchall()
        cursor.execute("SELECT id, fecha, motivo, estado FROM justificantes WHERE alumno_id = ? ORDER BY fecha DESC", (session['user_id'],))
        justificantes = cursor.fetchall()
    except sqlite3.Error as e:
        flash(f"Error al cargar datos del dashboard: {e}", "error")
    finally:
        conn.close()
    return render_template('dashboard_alumno.html', asistencias=asistencias, justificantes=justificantes)

# --- FUNCIONALIDADES MAESTRO (Y ADMIN si tiene acceso) ---
@app.route('/asistencias')
@login_required
@roles_required(['maestro', 'admin'])
def mostrar_asistencias():
    conn = conectar_db()
    cursor = conn.cursor()
    registros = []
    try:
        cursor.execute('''
            SELECT al.nombre AS alumno_nombre, al.matricula, a.fecha, a.hora, a.estado
            FROM asistencias a
            JOIN alumnos al ON a.alumno_id = al.id
            ORDER BY a.fecha DESC, a.hora DESC, al.nombre ASC
        ''')
        registros = cursor.fetchall()
    except sqlite3.Error as e:
        flash(f"Error al cargar asistencias: {e}", "error")
    finally:
        conn.close()
    return render_template('asistencias.html', registros=registros)

@app.route('/justificantes')
@login_required
@roles_required(['maestro', 'admin'])
def ver_justificantes():
    conn = conectar_db()
    cursor = conn.cursor()
    justificantes_data = []
    try:
        cursor.execute('''
            SELECT j.id, al.nombre AS alumno_nombre, al.matricula, j.fecha, j.motivo, j.estado
            FROM justificantes j
            JOIN alumnos al ON j.alumno_id = al.id
            ORDER BY j.fecha DESC, al.nombre ASC
        ''')
        justificantes_data = cursor.fetchall()
    except sqlite3.Error as e:
        flash(f"Error al cargar justificantes: {e}", "error")
    finally:
        conn.close()
    return render_template('justificantes.html', justificantes=justificantes_data)

@app.route('/actualizar_justificante/<int:id>/<estado>')
@login_required
@roles_required(['maestro', 'admin'])
def actualizar_justificante(id, estado):
    if estado not in ['aprobado', 'rechazado']:
        flash('Estado inválido para el justificante.', 'error')
        return redirect(url_for('ver_justificantes'))
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE justificantes SET estado = ? WHERE id = ?", (estado, id))
        conn.commit()
        flash(f'Justificante {estado.capitalize()} correctamente.', 'success')
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Error al actualizar el justificante: {e}', 'error')
    finally:
        conn.close()
    return redirect(url_for('ver_justificantes'))

# --- FUNCIONALIDADES ALUMNO ---
@app.route('/subir_justificante', methods=['POST'])
@login_required
@roles_required(['alumno'])
def subir_justificante():
    motivo = request.form.get('motivo', '').strip()
    if not motivo:
        flash('El motivo del justificante no puede estar vacío.', 'error')
        return redirect(url_for('dashboard_alumno'))
    fecha = datetime.now().strftime('%Y-%m-%d')
    maestro_id_justificante = session.get('maestro_asignado_id') 
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO justificantes (alumno_id, fecha, motivo, estado, maestro_id) VALUES (?, ?, ?, ?, ?)",
                       (session['user_id'], fecha, motivo, 'pendiente', maestro_id_justificante))
        conn.commit()
        flash('Justificante subido correctamente. Será revisado por un maestro.', 'success')
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Error al subir el justificante: {e}', 'error')
    finally:
        conn.close()
    return redirect(url_for('dashboard_alumno'))

# --- GESTIÓN DE USUARIOS POR ADMIN ---

# == GESTIÓN DE MAESTROS POR ADMIN ==
@app.route('/admin/maestros')
@login_required
@roles_required(['admin'])
def admin_gestionar_maestros():
    conn = conectar_db()
    cursor = conn.cursor()
    lista_maestros = []
    try:
        cursor.execute("SELECT id, nombre, usuario, rol FROM maestros ORDER BY nombre ASC")
        lista_maestros = cursor.fetchall()
    except sqlite3.Error as e:
        flash(f"Error al cargar lista de maestros: {e}", "error")
    finally:
        conn.close()
    return render_template('admin_gestionar_maestros.html', maestros=lista_maestros)

@app.route('/admin/maestros/agregar', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def admin_agregar_maestro():
    maestro_form_data = {'rol': 'maestro'} 
    if request.method == 'POST':
        nombre = request.form.get('nombre','').strip()
        usuario = request.form.get('usuario','').strip()
        password = request.form.get('password','').strip()
        rol = request.form.get('rol','maestro').strip()
        maestro_form_data = {'nombre': nombre, 'usuario': usuario, 'rol': rol}
        if not nombre or not usuario or not password or not rol:
            flash('Todos los campos son obligatorios (Nombre, Usuario, Contraseña, Rol).', 'error')
            return render_template('admin_formulario_maestro.html', maestro=maestro_form_data, titulo="Agregar Maestro", accion=url_for('admin_agregar_maestro'))
        if rol not in ['maestro', 'admin']:
            flash('Rol inválido seleccionado.', 'error')
            return render_template('admin_formulario_maestro.html', maestro=maestro_form_data, titulo="Agregar Maestro", accion=url_for('admin_agregar_maestro'))
        password_hash = generate_password_hash(password)
        conn = conectar_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO maestros (nombre, usuario, password, rol) VALUES (?, ?, ?, ?)", (nombre, usuario, password_hash, rol))
            conn.commit()
            flash(f'Maestro {nombre} ({rol}) agregado correctamente.', 'success')
            return redirect(url_for('admin_gestionar_maestros'))
        except sqlite3.IntegrityError:
            flash(f'Error: El nombre de usuario "{usuario}" ya existe.', 'error')
        except sqlite3.Error as e:
            flash(f'Error al agregar maestro: {e}', 'error')
        finally:
            conn.close()
        return render_template('admin_formulario_maestro.html', maestro=maestro_form_data, titulo="Agregar Maestro", accion=url_for('admin_agregar_maestro'))
    return render_template('admin_formulario_maestro.html', maestro=maestro_form_data, titulo="Agregar Maestro", accion=url_for('admin_agregar_maestro'))

@app.route('/admin/maestros/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def admin_editar_maestro(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, usuario, rol FROM maestros WHERE id = ?", (id,))
    maestro_actual = cursor.fetchone()
    if not maestro_actual:
        flash('Maestro no encontrado.', 'error')
        conn.close()
        return redirect(url_for('admin_gestionar_maestros'))

    if request.method == 'POST':
        nombre = request.form.get('nombre','').strip()
        usuario = request.form.get('usuario','').strip()
        password = request.form.get('password','').strip() 
        rol = request.form.get('rol','maestro').strip()
        maestro_form_data = {'id': id, 'nombre': nombre, 'usuario': usuario, 'rol': rol} 
        if not nombre or not usuario or not rol:
            flash('Los campos Nombre, Usuario y Rol son obligatorios.', 'error')
            conn.close() 
            return render_template('admin_formulario_maestro.html', maestro=maestro_form_data, titulo="Editar Maestro", accion=url_for('admin_editar_maestro', id=id))
        if rol not in ['maestro', 'admin']:
            flash('Rol inválido seleccionado.', 'error')
            conn.close()
            return render_template('admin_formulario_maestro.html', maestro=maestro_form_data, titulo="Editar Maestro", accion=url_for('admin_editar_maestro', id=id))
        try:
            if password: 
                password_hash = generate_password_hash(password)
                cursor.execute("UPDATE maestros SET nombre = ?, usuario = ?, password = ?, rol = ? WHERE id = ?", (nombre, usuario, password_hash, rol, id))
            else: 
                cursor.execute("UPDATE maestros SET nombre = ?, usuario = ?, rol = ? WHERE id = ?", (nombre, usuario, rol, id))
            conn.commit()
            flash('Maestro actualizado correctamente.', 'success')
            if session['user_id'] == id and session['rol'] == 'admin':
                session['nombre_usuario'] = nombre
            return redirect(url_for('admin_gestionar_maestros'))
        except sqlite3.IntegrityError:
            flash(f'Error: El nombre de usuario "{usuario}" ya existe para otro maestro.', 'error')
        except sqlite3.Error as e:
            flash(f'Error al actualizar maestro: {e}', 'error')
        finally:
            conn.close() 
        return render_template('admin_formulario_maestro.html', maestro=maestro_form_data, titulo="Editar Maestro", accion=url_for('admin_editar_maestro', id=id))
    conn.close()
    return render_template('admin_formulario_maestro.html', maestro=maestro_actual, titulo="Editar Maestro", accion=url_for('admin_editar_maestro', id=id))

@app.route('/admin/maestros/eliminar/<int:id>')
@login_required
@roles_required(['admin'])
def admin_eliminar_maestro(id):
    if session['user_id'] == id and session['rol'] == 'admin':
        flash('No puedes eliminar tu propia cuenta de administrador mientras estás en sesión.', 'error')
        return redirect(url_for('admin_gestionar_maestros'))
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM maestros WHERE id = ?", (id,))
        conn.commit()
        flash('Maestro eliminado correctamente.', 'info')
    except sqlite3.IntegrityError as e:
        flash(f'Error al eliminar maestro: {e}. Podría tener alumnos u otros registros asociados.', 'error')
    except sqlite3.Error as e:
        flash(f'Error al eliminar maestro: {e}.', 'error')
    finally:
        conn.close()
    return redirect(url_for('admin_gestionar_maestros'))

# == GESTIÓN DE ALUMNOS POR ADMIN (Implementación completa) ==
@app.route('/admin/alumnos')
@login_required
@roles_required(['admin'])
def admin_gestionar_alumnos():
    conn = conectar_db()
    cursor = conn.cursor()
    lista_alumnos = []
    try:
        cursor.execute("SELECT id, nombre, matricula, rol, maestro_id FROM alumnos ORDER BY nombre ASC")
        lista_alumnos = cursor.fetchall()
    except sqlite3.Error as e:
        flash(f"Error al cargar lista de alumnos: {e}", "error")
    finally:
        conn.close()
    return render_template('admin_gestionar_alumnos.html', alumnos=lista_alumnos)

@app.route('/admin/alumnos/agregar', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def admin_agregar_alumno():
    maestros_disponibles = []
    conn_load = conectar_db() # Conexión para cargar maestros
    cursor_load = conn_load.cursor()
    try:
        cursor_load.execute("SELECT id, nombre FROM maestros WHERE rol = 'maestro' ORDER BY nombre ASC")
        maestros_disponibles = cursor_load.fetchall()
    except sqlite3.Error as e:
        flash(f"Error al cargar lista de maestros para el formulario: {e}", "error")
    finally:
        conn_load.close()

    alumno_form_data = {} # Para mantener datos del formulario en caso de error
    if request.method == 'POST':
        nombre = request.form.get('nombre','').strip()
        matricula = request.form.get('matricula','').strip()
        password = request.form.get('password','').strip()
        maestro_id_str = request.form.get('maestro_id')

        alumno_form_data = {'nombre': nombre, 'matricula': matricula, 'maestro_id': maestro_id_str}

        if not nombre or not matricula or not password:
            flash('Los campos Nombre, Matrícula y Contraseña son obligatorios.', 'error')
            return render_template('admin_formulario_alumno.html', titulo="Agregar Alumno", accion=url_for('admin_agregar_alumno'), alumno=alumno_form_data, maestros=maestros_disponibles)

        password_hash = generate_password_hash(password)
        
        maestro_id_int = None
        if maestro_id_str and maestro_id_str.isdigit():
            maestro_id_int = int(maestro_id_str)
        elif maestro_id_str: # Si no está vacío pero no es dígito (no debería pasar con select)
             flash("ID de maestro seleccionado inválido.", "warning")


        conn_insert = conectar_db() # Nueva conexión para la inserción
        cursor_insert = conn_insert.cursor()
        try:
            cursor_insert.execute("INSERT INTO alumnos (nombre, matricula, password, rol, maestro_id) VALUES (?, ?, ?, ?, ?)",
                           (nombre, matricula, password_hash, 'alumno', maestro_id_int))
            conn_insert.commit()
            flash(f'Alumno {nombre} agregado correctamente.', 'success')
            return redirect(url_for('admin_gestionar_alumnos'))
        except sqlite3.IntegrityError:
            flash(f'Error: La matrícula "{matricula}" ya existe.', 'error')
        except sqlite3.Error as e:
            flash(f'Error al agregar alumno: {e}', 'error')
        finally:
            conn_insert.close()
        # Si hay error, re-renderizar con los datos y la lista de maestros
        return render_template('admin_formulario_alumno.html', titulo="Agregar Alumno", accion=url_for('admin_agregar_alumno'), alumno=alumno_form_data, maestros=maestros_disponibles)

    # Método GET
    return render_template('admin_formulario_alumno.html', titulo="Agregar Alumno", accion=url_for('admin_agregar_alumno'), alumno={}, maestros=maestros_disponibles)

@app.route('/admin/alumnos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def admin_editar_alumno(id):
    conn = conectar_db()
    cursor = conn.cursor()
    
    maestros_disponibles = []
    try:
        cursor.execute("SELECT id, nombre FROM maestros WHERE rol = 'maestro' ORDER BY nombre ASC")
        maestros_disponibles = cursor.fetchall()
    except sqlite3.Error as e:
        flash(f"Error al cargar lista de maestros: {e}", "error")
        # Podríamos redirigir si esto falla, pero intentemos continuar para mostrar el form

    cursor.execute("SELECT id, nombre, matricula, maestro_id FROM alumnos WHERE id = ?", (id,))
    alumno_actual = cursor.fetchone()
    
    if not alumno_actual:
        flash("Alumno no encontrado.", "error")
        conn.close()
        return redirect(url_for('admin_gestionar_alumnos'))

    if request.method == 'POST':
        nombre = request.form.get('nombre','').strip()
        matricula = request.form.get('matricula','').strip()
        password = request.form.get('password','').strip()
        maestro_id_str = request.form.get('maestro_id')

        alumno_form_data = {'id': id, 'nombre': nombre, 'matricula': matricula, 'maestro_id': maestro_id_str}

        if not nombre or not matricula:
            flash('Los campos Nombre y Matrícula son obligatorios.', 'error')
            conn.close()
            return render_template('admin_formulario_alumno.html', titulo="Editar Alumno", accion=url_for('admin_editar_alumno', id=id), alumno=alumno_form_data, maestros=maestros_disponibles)

        maestro_id_int = None
        if maestro_id_str and maestro_id_str.isdigit():
            maestro_id_int = int(maestro_id_str)
        elif maestro_id_str:
             flash("ID de maestro seleccionado inválido.", "warning")

        try:
            if password: 
                password_hash = generate_password_hash(password)
                cursor.execute("UPDATE alumnos SET nombre = ?, matricula = ?, password = ?, maestro_id = ? WHERE id = ?",
                               (nombre, matricula, password_hash, maestro_id_int, id))
            else: 
                cursor.execute("UPDATE alumnos SET nombre = ?, matricula = ?, maestro_id = ? WHERE id = ?",
                               (nombre, matricula, maestro_id_int, id))
            conn.commit()
            flash('Alumno actualizado correctamente.', 'success')
            return redirect(url_for('admin_gestionar_alumnos'))
        except sqlite3.IntegrityError:
            flash(f'Error: La matrícula "{matricula}" ya existe para otro alumno.', 'error')
        except sqlite3.Error as e:
            flash(f'Error al actualizar alumno: {e}', 'error')
        finally:
            conn.close()
        
        return render_template('admin_formulario_alumno.html', titulo="Editar Alumno", accion=url_for('admin_editar_alumno', id=id), alumno=alumno_form_data, maestros=maestros_disponibles)
    
    conn.close()
    return render_template('admin_formulario_alumno.html', titulo="Editar Alumno", accion=url_for('admin_editar_alumno', id=id), alumno=alumno_actual, maestros=maestros_disponibles)

@app.route('/admin/alumnos/eliminar/<int:id>')
@login_required
@roles_required(['admin'])
def admin_eliminar_alumno(id):
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        # Considerar borrar registros dependientes (asistencias, justificantes)
        # O configurar ON DELETE CASCADE en la BD
        cursor.execute("DELETE FROM asistencias WHERE alumno_id = ?", (id,)) # Ejemplo de borrado de dependencias
        cursor.execute("DELETE FROM justificantes WHERE alumno_id = ?", (id,)) # Ejemplo de borrado de dependencias
        cursor.execute("DELETE FROM alumnos WHERE id = ?", (id,))
        conn.commit()
        flash('Alumno y sus registros asociados eliminados correctamente.', 'info')
    except sqlite3.IntegrityError as e:
        # Este error no debería ocurrir si borras las dependencias primero,
        # a menos que haya otras dependencias no consideradas.
        flash(f'Error de integridad al eliminar alumno: {e}.', 'error')
    except sqlite3.Error as e:
        flash(f'Error al eliminar alumno: {e}.', 'error')
    finally:
        conn.close()
    return redirect(url_for('admin_gestionar_alumnos'))

# --- VISTAS LEGADAS O PARA ROLES ESPECÍFICOS (REVISAR Y AJUSTAR) ---
@app.route('/alumnos') 
@login_required
@roles_required(['maestro', 'admin'])
def alumnos_vista_maestro():
    conn = conectar_db()
    cursor = conn.cursor()
    alumnos_data = []
    try:
        if session['rol'] == 'maestro':
             # Un maestro ve solo sus alumnos asignados
            cursor.execute("SELECT id, nombre, matricula FROM alumnos WHERE maestro_id = ? ORDER BY nombre ASC", (session['user_id'],))
        else: # Admin ve todos
            cursor.execute("SELECT id, nombre, matricula FROM alumnos ORDER BY nombre ASC")
        alumnos_data = cursor.fetchall()
    except sqlite3.Error as e:
        flash(f"Error al cargar alumnos: {e}", "error")
    finally:
        conn.close()
    return render_template('alumnos.html', alumnos=alumnos_data, es_admin=(session.get('rol') == 'admin'))

if __name__ == '__main__':
    app.run(debug=True, port=8004, host='0.0.0.0')