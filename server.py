from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import database # Tu módulo database.py con la nueva estructura

app = Flask(__name__)
app.secret_key = 'esta_es_otra_clave_secreta_super_segura_y_unica_67890_escolar!'

# Es buena idea ejecutar crear_db() solo una vez o cuando sea necesario,
# no necesariamente cada vez que se inicia el servidor si ya está creada y poblada.
# Para desarrollo, llamarlo aquí puede ser conveniente para asegurar que la BD existe.
# Si database.py ya elimina y recrea la BD, entonces está bien.
# Considera mover esta llamada a un script de inicialización si el poblado es muy lento.
try:
    print("Intentando asegurar la creación de la base de datos desde server.py...")
    database.crear_db() # Asegura que la BD exista y esté poblada según database.py
    print("Llamada a database.crear_db() completada.")
except Exception as e:
    print(f"Error al llamar a database.crear_db() desde server.py: {e}")


def conectar_db():
    conn = sqlite3.connect(database.DATABASE_NAME) # Usa el nombre de la BD de database.py
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON") # MUY IMPORTANTE para la integridad referencial
    return conn

# --- DECORADORES DE CONTROL DE ACCESO (sin cambios) ---
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
                    return redirect(url_for('home')) # Ruta de fallback
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
    return redirect(url_for('login')) # Redirigir a login si no hay sesión

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identificador = request.form['identificador'] # Puede ser usuario para maestro/admin o matrícula para alumno
        password_ingresada = request.form['password']
        conn = conectar_db()
        cursor = conn.cursor()
        user_authenticated = False

        # Intentar login como Maestro o Admin
        cursor.execute("SELECT id, nombre, usuario, password, rol FROM Maestros WHERE usuario = ?", (identificador,))
        user_db = cursor.fetchone()
        if user_db and check_password_hash(user_db['password'], password_ingresada):
            session.clear()
            session['user_id'] = user_db['id']
            session['nombre_usuario'] = user_db['nombre'] if user_db['nombre'] else user_db['usuario']
            session['rol'] = user_db['rol']
            user_authenticated = True
            flash(f"Bienvenido, {session.get('rol').capitalize()} {session.get('nombre_usuario')}!", 'success')
            conn.close()
            if session['rol'] == 'admin':
                return redirect(url_for('dashboard_admin'))
            else: # Maestro
                return redirect(url_for('dashboard_maestro'))

        # Si no es Maestro/Admin, intentar login como Alumno
        if not user_authenticated:
            cursor.execute("""
                SELECT a.id, a.nombre, a.matricula, a.password, a.rol, a.grupo_id, g.nombre as nombre_grupo, gr.nombre as nombre_grado
                FROM Alumnos a
                LEFT JOIN Grupos g ON a.grupo_id = g.id
                LEFT JOIN Grados gr ON g.grado_id = gr.id
                WHERE a.matricula = ?
            """, (identificador,))
            user_db = cursor.fetchone()
            if user_db and check_password_hash(user_db['password'], password_ingresada):
                session.clear()
                session['user_id'] = user_db['id']
                session['nombre_usuario'] = user_db['nombre'] if user_db['nombre'] else user_db['matricula']
                session['rol'] = user_db['rol']
                session['grupo_id'] = user_db['grupo_id']
                session['grupo_info'] = f"{user_db['nombre_grado']} - Grupo {user_db['nombre_grupo']}" if user_db['grupo_id'] else "Sin grupo asignado"
                user_authenticated = True
                flash(f"Bienvenido, Alumno {session.get('nombre_usuario')}!", 'success')
                conn.close()
                return redirect(url_for('dashboard_alumno'))

        conn.close()
        if not user_authenticated:
            flash('Identificador o contraseña incorrectos. Por favor, inténtalo de nuevo.', 'error')
        return redirect(url_for('login'))

    # Si ya hay sesión, redirigir al dashboard correspondiente
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('index.html') # Muestra el formulario de login

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
@roles_required(['maestro', 'admin']) # Admin también puede ver este dashboard
def dashboard_maestro():
    # Aquí se podrían cargar las asignaciones del maestro para mostrarlas
    conn = conectar_db()
    cursor = conn.cursor()
    maestro_id = session['user_id']
    try:
        cursor.execute("""
            SELECT mmg.id as asignacion_id, m.nombre as nombre_materia, g.nombre as nombre_grupo, gr.nombre as nombre_grado, mmg.ciclo_escolar
            FROM Maestros_Materias_Grupos mmg
            JOIN Materias m ON mmg.materia_id = m.id
            JOIN Grupos g ON mmg.grupo_id = g.id
            JOIN Grados gr ON g.grado_id = gr.id
            WHERE mmg.maestro_id = ?
            ORDER BY gr.nombre, g.nombre, m.nombre
        """, (maestro_id,))
        asignaciones = cursor.fetchall()
    except sqlite3.Error as e:
        flash(f"Error al cargar asignaciones del maestro: {e}", "error")
        asignaciones = []
    finally:
        conn.close()
    return render_template('dashboard_maestro.html', asignaciones=asignaciones)

@app.route('/dashboard_alumno')
@login_required
@roles_required(['alumno'])
def dashboard_alumno():
    conn = conectar_db()
    cursor = conn.cursor()
    alumno_id = session['user_id']
    asistencias_alumno = []
    justificantes_alumno = []
    try:
        # Cargar asistencias del alumno (simplificado, se puede detallar más)
        cursor.execute("""
            SELECT a.fecha, a.hora, a.estado, mat.nombre as nombre_materia, a.observaciones
            FROM Asistencias a
            JOIN Maestros_Materias_Grupos mmg ON a.asignacion_id = mmg.id
            JOIN Materias mat ON mmg.materia_id = mat.id
            WHERE a.alumno_id = ?
            ORDER BY a.fecha DESC, a.hora DESC
        """, (alumno_id,))
        asistencias_alumno = cursor.fetchall()

        # Cargar justificantes del alumno
        cursor.execute("""
            SELECT j.fecha_solicitud, j.fecha_inasistencia_inicio, j.fecha_inasistencia_fin, j.motivo, j.estado, mat.nombre as nombre_materia
            FROM Justificantes j
            LEFT JOIN Maestros_Materias_Grupos mmg ON j.asignacion_id = mmg.id
            LEFT JOIN Materias mat ON mmg.materia_id = mat.id
            WHERE j.alumno_id = ?
            ORDER BY j.fecha_solicitud DESC
        """, (alumno_id,))
        justificantes_alumno = cursor.fetchall()

    except sqlite3.Error as e:
        flash(f"Error al cargar datos del dashboard del alumno: {e}", "error")
    finally:
        conn.close()
    return render_template('dashboard_alumno.html', asistencias=asistencias_alumno, justificantes=justificantes_alumno)

# --- CRUD GRADOS (Admin) ---
@app.route('/admin/grados')
@login_required
@roles_required(['admin'])
def gestionar_grados():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Grados ORDER BY nombre")
    grados = cursor.fetchall()
    conn.close()
    return render_template('admin/gestionar_grados.html', grados=grados)

@app.route('/admin/grados/agregar', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def agregar_grado():
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        if not nombre:
            flash('El nombre del grado es obligatorio.', 'error')
        else:
            conn = conectar_db()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO Grados (nombre) VALUES (?)", (nombre,))
                conn.commit()
                flash('Grado agregado correctamente.', 'success')
                return redirect(url_for('gestionar_grados'))
            except sqlite3.IntegrityError:
                flash('Error: El nombre del grado ya existe.', 'error')
            except sqlite3.Error as e:
                flash(f'Error al agregar grado: {e}', 'error')
            finally:
                conn.close()
    return render_template('admin/formulario_grado.html', titulo="Agregar Grado", accion_url=url_for('agregar_grado'), grado=None)

@app.route('/admin/grados/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def editar_grado(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Grados WHERE id = ?", (id,))
    grado = cursor.fetchone()
    conn.close()

    if not grado:
        flash('Grado no encontrado.', 'error')
        return redirect(url_for('gestionar_grados'))

    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        if not nombre:
            flash('El nombre del grado es obligatorio.', 'error')
        else:
            conn_update = conectar_db()
            cursor_update = conn_update.cursor()
            try:
                cursor_update.execute("UPDATE Grados SET nombre = ? WHERE id = ?", (nombre, id))
                conn_update.commit()
                flash('Grado actualizado correctamente.', 'success')
                return redirect(url_for('gestionar_grados'))
            except sqlite3.IntegrityError:
                flash('Error: El nombre del grado ya existe.', 'error')
            except sqlite3.Error as e:
                flash(f'Error al actualizar grado: {e}', 'error')
            finally:
                conn_update.close()
        # Para re-popular el formulario con el valor intentado si hay error
        return render_template('admin/formulario_grado.html', titulo="Editar Grado", accion_url=url_for('editar_grado', id=id), grado={'id': id, 'nombre': nombre})


    return render_template('admin/formulario_grado.html', titulo="Editar Grado", accion_url=url_for('editar_grado', id=id), grado=grado)

@app.route('/admin/grados/eliminar/<int:id>')
@login_required
@roles_required(['admin'])
def eliminar_grado(id):
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        # ON DELETE CASCADE en la BD se encargará de los grupos si existen.
        # Si no, tendríamos que verificar que no haya grupos asociados.
        cursor.execute("DELETE FROM Grados WHERE id = ?", (id,))
        conn.commit()
        flash('Grado eliminado correctamente. Los grupos asociados también fueron eliminados.', 'info')
    except sqlite3.IntegrityError: # Podría ocurrir si no hay ON DELETE CASCADE y hay grupos
        flash('Error: No se puede eliminar el grado porque tiene grupos asociados. Elimine los grupos primero.', 'error')
    except sqlite3.Error as e:
        flash(f'Error al eliminar grado: {e}', 'error')
    finally:
        conn.close()
    return redirect(url_for('gestionar_grados'))


# --- CRUD GRUPOS (Admin) ---
@app.route('/admin/grupos')
@login_required
@roles_required(['admin'])
def gestionar_grupos():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT g.id, g.nombre, gr.nombre as nombre_grado
        FROM Grupos g
        JOIN Grados gr ON g.grado_id = gr.id
        ORDER BY gr.nombre, g.nombre
    """)
    grupos = cursor.fetchall()
    conn.close()
    return render_template('admin/gestionar_grupos.html', grupos=grupos)

@app.route('/admin/grupos/agregar', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def agregar_grupo():
    conn_load = conectar_db()
    cursor_load = conn_load.cursor()
    cursor_load.execute("SELECT id, nombre FROM Grados ORDER BY nombre")
    grados = cursor_load.fetchall()
    conn_load.close()

    if request.method == 'POST':
        nombre = request.form['nombre'].strip().upper() # Guardar en mayúsculas (ej. A, B)
        grado_id = request.form.get('grado_id')

        if not nombre or not grado_id:
            flash('El nombre del grupo y el grado son obligatorios.', 'error')
        else:
            conn = conectar_db()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO Grupos (nombre, grado_id) VALUES (?, ?)", (nombre, grado_id))
                conn.commit()
                flash('Grupo agregado correctamente.', 'success')
                return redirect(url_for('gestionar_grupos'))
            except sqlite3.IntegrityError: # UNIQUE(grado_id, nombre)
                flash('Error: Este grupo ya existe para el grado seleccionado.', 'error')
            except sqlite3.Error as e:
                flash(f'Error al agregar grupo: {e}', 'error')
            finally:
                conn.close()
        # Para re-popular el formulario con los valores intentados
        return render_template('admin/formulario_grupo.html', titulo="Agregar Grupo", accion_url=url_for('agregar_grupo'), grados=grados, grupo_actual=request.form)


    return render_template('admin/formulario_grupo.html', titulo="Agregar Grupo", accion_url=url_for('agregar_grupo'), grados=grados, grupo_actual=None)

@app.route('/admin/grupos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def editar_grupo(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Grupos WHERE id = ?", (id,))
    grupo_actual = cursor.fetchone()
    cursor.execute("SELECT id, nombre FROM Grados ORDER BY nombre")
    grados = cursor.fetchall()
    conn.close()

    if not grupo_actual:
        flash('Grupo no encontrado.', 'error')
        return redirect(url_for('gestionar_grupos'))

    if request.method == 'POST':
        nombre = request.form['nombre'].strip().upper()
        grado_id = request.form.get('grado_id')
        if not nombre or not grado_id:
            flash('El nombre del grupo y el grado son obligatorios.', 'error')
        else:
            conn_update = conectar_db()
            cursor_update = conn_update.cursor()
            try:
                cursor_update.execute("UPDATE Grupos SET nombre = ?, grado_id = ? WHERE id = ?", (nombre, grado_id, id))
                conn_update.commit()
                flash('Grupo actualizado correctamente.', 'success')
                return redirect(url_for('gestionar_grupos'))
            except sqlite3.IntegrityError:
                flash('Error: Ya existe un grupo con ese nombre para el grado seleccionado.', 'error')
            except sqlite3.Error as e:
                flash(f'Error al actualizar grupo: {e}', 'error')
            finally:
                conn_update.close()
        # Re-popular con datos intentados
        form_data = {'id': id, 'nombre': nombre, 'grado_id': int(grado_id)}
        return render_template('admin/formulario_grupo.html', titulo="Editar Grupo", accion_url=url_for('editar_grupo', id=id), grados=grados, grupo_actual=form_data)

    return render_template('admin/formulario_grupo.html', titulo="Editar Grupo", accion_url=url_for('editar_grupo', id=id), grados=grados, grupo_actual=grupo_actual)

@app.route('/admin/grupos/eliminar/<int:id>')
@login_required
@roles_required(['admin'])
def eliminar_grupo(id):
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        # ON DELETE SET NULL en Alumnos.grupo_id se encargará de los alumnos.
        # ON DELETE CASCADE en Maestros_Materias_Grupos se encargará de las asignaciones.
        cursor.execute("DELETE FROM Grupos WHERE id = ?", (id,))
        conn.commit()
        flash('Grupo eliminado correctamente. Los alumnos ya no pertenecerán a este grupo y las asignaciones asociadas fueron eliminadas.', 'info')
    except sqlite3.Error as e: # Manejo general
        flash(f'Error al eliminar grupo: {e}. Verifique que no haya dependencias si no se configuró ON DELETE.', 'error')
    finally:
        conn.close()
    return redirect(url_for('gestionar_grupos'))


# --- CRUD MATERIAS (Admin) ---
@app.route('/admin/materias')
@login_required
@roles_required(['admin'])
def gestionar_materias():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Materias ORDER BY nombre")
    materias = cursor.fetchall()
    conn.close()
    return render_template('admin/gestionar_materias.html', materias=materias)

@app.route('/admin/materias/agregar', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def agregar_materia():
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        clave_materia = request.form.get('clave_materia', '').strip() or None # Clave es opcional

        if not nombre:
            flash('El nombre de la materia es obligatorio.', 'error')
        else:
            conn = conectar_db()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO Materias (nombre, clave_materia) VALUES (?, ?)", (nombre, clave_materia))
                conn.commit()
                flash('Materia agregada correctamente.', 'success')
                return redirect(url_for('gestionar_materias'))
            except sqlite3.IntegrityError as e:
                if 'UNIQUE constraint failed: Materias.nombre' in str(e):
                    flash('Error: El nombre de la materia ya existe.', 'error')
                elif 'UNIQUE constraint failed: Materias.clave_materia' in str(e) and clave_materia:
                    flash('Error: La clave de la materia ya existe.', 'error')
                else:
                    flash(f'Error de integridad al agregar materia: {e}', 'error')
            except sqlite3.Error as e:
                flash(f'Error al agregar materia: {e}', 'error')
            finally:
                conn.close()
        return render_template('admin/formulario_materia.html', titulo="Agregar Materia", accion_url=url_for('agregar_materia'), materia=request.form)


    return render_template('admin/formulario_materia.html', titulo="Agregar Materia", accion_url=url_for('agregar_materia'), materia=None)

@app.route('/admin/materias/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def editar_materia(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Materias WHERE id = ?", (id,))
    materia = cursor.fetchone()
    conn.close()

    if not materia:
        flash('Materia no encontrada.', 'error')
        return redirect(url_for('gestionar_materias'))

    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        clave_materia = request.form.get('clave_materia', '').strip() or None

        if not nombre:
            flash('El nombre de la materia es obligatorio.', 'error')
        else:
            conn_update = conectar_db()
            cursor_update = conn_update.cursor()
            try:
                cursor_update.execute("UPDATE Materias SET nombre = ?, clave_materia = ? WHERE id = ?", (nombre, clave_materia, id))
                conn_update.commit()
                flash('Materia actualizada correctamente.', 'success')
                return redirect(url_for('gestionar_materias'))
            except sqlite3.IntegrityError as e:
                if 'UNIQUE constraint failed: Materias.nombre' in str(e):
                    flash('Error: El nombre de la materia ya existe para otra materia.', 'error')
                elif 'UNIQUE constraint failed: Materias.clave_materia' in str(e) and clave_materia:
                    flash('Error: La clave de la materia ya existe para otra materia.', 'error')
                else:
                    flash(f'Error de integridad al actualizar materia: {e}', 'error')
            except sqlite3.Error as e:
                flash(f'Error al actualizar materia: {e}', 'error')
            finally:
                conn_update.close()
        form_data = {'id': id, 'nombre': nombre, 'clave_materia': clave_materia}
        return render_template('admin/formulario_materia.html', titulo="Editar Materia", accion_url=url_for('editar_materia', id=id), materia=form_data)

    return render_template('admin/formulario_materia.html', titulo="Editar Materia", accion_url=url_for('editar_materia', id=id), materia=materia)

@app.route('/admin/materias/eliminar/<int:id>')
@login_required
@roles_required(['admin'])
def eliminar_materia(id):
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        # ON DELETE CASCADE en Maestros_Materias_Grupos se encargará.
        cursor.execute("DELETE FROM Materias WHERE id = ?", (id,))
        conn.commit()
        flash('Materia eliminada correctamente. Las asignaciones asociadas también fueron eliminadas.', 'info')
    except sqlite3.Error as e:
        flash(f'Error al eliminar materia: {e}. Verifique dependencias.', 'error')
    finally:
        conn.close()
    return redirect(url_for('gestionar_materias'))

# --- GESTIÓN DE MAESTROS (Admin) (Adaptado de la versión anterior) ---
@app.route('/admin/maestros')
@login_required
@roles_required(['admin'])
def admin_gestionar_maestros(): # Renombrado de gestionar_maestros a admin_gestionar_maestros para consistencia
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, usuario, rol FROM Maestros ORDER BY nombre ASC")
    maestros = cursor.fetchall()
    conn.close()
    return render_template('admin/admin_gestionar_maestros.html', maestros=maestros) # Plantilla renombrada

@app.route('/admin/maestros/agregar', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def admin_agregar_maestro(): # Renombrado
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        usuario = request.form['usuario'].strip()
        password = request.form['password'] # No quitar strip aquí
        rol = request.form.get('rol', 'maestro')

        if not nombre or not usuario or not password:
            flash('Nombre, usuario y contraseña son obligatorios.', 'error')
        elif rol not in ['maestro', 'admin']:
            flash('Rol inválido.', 'error')
        else:
            password_hash = generate_password_hash(password)
            conn = conectar_db()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO Maestros (nombre, usuario, password, rol) VALUES (?, ?, ?, ?)",
                               (nombre, usuario, password_hash, rol))
                conn.commit()
                flash(f'{rol.capitalize()} {nombre} agregado correctamente.', 'success')
                return redirect(url_for('admin_gestionar_maestros'))
            except sqlite3.IntegrityError:
                flash(f'Error: El nombre de usuario "{usuario}" ya existe.', 'error')
            except sqlite3.Error as e:
                flash(f'Error al agregar usuario: {e}', 'error')
            finally:
                conn.close()
        # Para repopular el formulario
        return render_template('admin/admin_formulario_maestro.html', titulo=f"Agregar {rol.capitalize()}",
                               accion_url=url_for('admin_agregar_maestro'), maestro=request.form, rol_seleccionado=rol)

    return render_template('admin/admin_formulario_maestro.html', titulo="Agregar Usuario (Maestro/Admin)",
                           accion_url=url_for('admin_agregar_maestro'), maestro=None, rol_seleccionado='maestro')

@app.route('/admin/maestros/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def admin_editar_maestro(id): # Renombrado
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Maestros WHERE id = ?", (id,))
    maestro = cursor.fetchone()
    conn.close()

    if not maestro:
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('admin_gestionar_maestros'))

    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        usuario = request.form['usuario'].strip()
        password = request.form['password'] # No strip
        rol = request.form.get('rol', maestro['rol'])

        if not nombre or not usuario:
            flash('Nombre y usuario son obligatorios.', 'error')
        elif rol not in ['maestro', 'admin']:
            flash('Rol inválido.', 'error')
        else:
            conn_update = conectar_db()
            cursor_update = conn_update.cursor()
            try:
                if password: # Si se provee nueva contraseña, hashearla y actualizarla
                    password_hash = generate_password_hash(password)
                    cursor_update.execute("UPDATE Maestros SET nombre=?, usuario=?, password=?, rol=? WHERE id=?",
                                   (nombre, usuario, password_hash, rol, id))
                else: # Si no, mantener la contraseña actual
                    cursor_update.execute("UPDATE Maestros SET nombre=?, usuario=?, rol=? WHERE id=?",
                                   (nombre, usuario, rol, id))
                conn_update.commit()
                flash('Usuario actualizado correctamente.', 'success')
                # Actualizar datos de sesión si el admin se edita a sí mismo
                if session['user_id'] == id and session['rol'] == 'admin':
                    session['nombre_usuario'] = nombre
                    session['rol'] = rol # Si el admin cambia su propio rol
                return redirect(url_for('admin_gestionar_maestros'))
            except sqlite3.IntegrityError:
                flash(f'Error: El nombre de usuario "{usuario}" ya existe para otro usuario.', 'error')
            except sqlite3.Error as e:
                flash(f'Error al actualizar usuario: {e}', 'error')
            finally:
                conn_update.close()
        # Para repopular
        form_data = {'id': id, 'nombre': nombre, 'usuario': usuario, 'rol': rol}
        return render_template('admin/admin_formulario_maestro.html', titulo="Editar Usuario",
                               accion_url=url_for('admin_editar_maestro', id=id), maestro=form_data, rol_seleccionado=rol)

    return render_template('admin/admin_formulario_maestro.html', titulo="Editar Usuario",
                           accion_url=url_for('admin_editar_maestro', id=id), maestro=maestro, rol_seleccionado=maestro['rol'])

@app.route('/admin/maestros/eliminar/<int:id>')
@login_required
@roles_required(['admin'])
def admin_eliminar_maestro(id): # Renombrado
    if session['user_id'] == id and session['rol'] == 'admin': # No permitir auto-eliminación del admin actual
        flash('No puedes eliminar tu propia cuenta de administrador mientras estás en sesión.', 'error')
        return redirect(url_for('admin_gestionar_maestros'))

    conn = conectar_db()
    cursor = conn.cursor()
    try:
        # ON DELETE CASCADE en Maestros_Materias_Grupos se encargará de las asignaciones.
        # ON DELETE SET NULL en Justificantes.maestro_revisor_id también.
        cursor.execute("DELETE FROM Maestros WHERE id = ?", (id,))
        conn.commit()
        flash('Usuario eliminado correctamente. Sus asignaciones y revisiones de justificantes han sido desvinculadas o eliminadas.', 'info')
    except sqlite3.Error as e:
        flash(f'Error al eliminar usuario: {e}.', 'error')
    finally:
        conn.close()
    return redirect(url_for('admin_gestionar_maestros'))

# --- GESTIÓN DE ALUMNOS (Admin) (Adaptado) ---
@app.route('/admin/alumnos')
@login_required
@roles_required(['admin'])
def admin_gestionar_alumnos():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.nombre, a.matricula, g.nombre as nombre_grupo, gr.nombre as nombre_grado
        FROM Alumnos a
        LEFT JOIN Grupos g ON a.grupo_id = g.id
        LEFT JOIN Grados gr ON g.grado_id = gr.id
        ORDER BY gr.nombre, g.nombre, a.nombre
    """)
    alumnos = cursor.fetchall()
    conn.close()
    return render_template('admin/admin_gestionar_alumnos.html', alumnos=alumnos)

@app.route('/admin/alumnos/agregar', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def admin_agregar_alumno():
    conn_load = conectar_db()
    cursor_load = conn_load.cursor()
    cursor_load.execute("""
        SELECT g.id, g.nombre as nombre_grupo, gr.nombre as nombre_grado
        FROM Grupos g
        JOIN Grados gr ON g.grado_id = gr.id
        ORDER BY gr.nombre, g.nombre
    """)
    grupos = cursor_load.fetchall() # Para el selector de grupo
    conn_load.close()

    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        matricula = request.form['matricula'].strip().upper()
        password = request.form['password']
        grupo_id = request.form.get('grupo_id') or None # Puede ser None si no se selecciona

        if not nombre or not matricula or not password:
            flash('Nombre, matrícula y contraseña son obligatorios.', 'error')
        else:
            password_hash = generate_password_hash(password)
            conn = conectar_db()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO Alumnos (nombre, matricula, password, grupo_id, rol) VALUES (?, ?, ?, ?, ?)",
                               (nombre, matricula, password_hash, grupo_id, 'alumno'))
                conn.commit()
                flash('Alumno agregado correctamente.', 'success')
                return redirect(url_for('admin_gestionar_alumnos'))
            except sqlite3.IntegrityError:
                flash(f'Error: La matrícula "{matricula}" ya existe.', 'error')
            except sqlite3.Error as e:
                flash(f'Error al agregar alumno: {e}', 'error')
            finally:
                conn.close()
        # Para repopular
        return render_template('admin/admin_formulario_alumno.html', titulo="Agregar Alumno",
                               accion_url=url_for('admin_agregar_alumno'), alumno=request.form, grupos=grupos)

    return render_template('admin/admin_formulario_alumno.html', titulo="Agregar Alumno",
                           accion_url=url_for('admin_agregar_alumno'), alumno=None, grupos=grupos)


@app.route('/admin/alumnos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def admin_editar_alumno(id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Alumnos WHERE id = ?", (id,))
    alumno = cursor.fetchone()
    cursor.execute("""
        SELECT g.id, g.nombre as nombre_grupo, gr.nombre as nombre_grado
        FROM Grupos g
        JOIN Grados gr ON g.grado_id = gr.id
        ORDER BY gr.nombre, g.nombre
    """)
    grupos = cursor.fetchall()
    conn.close()

    if not alumno:
        flash('Alumno no encontrado.', 'error')
        return redirect(url_for('admin_gestionar_alumnos'))

    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        matricula = request.form['matricula'].strip().upper()
        password = request.form['password']
        grupo_id = request.form.get('grupo_id') or None

        if not nombre or not matricula:
            flash('Nombre y matrícula son obligatorios.', 'error')
        else:
            conn_update = conectar_db()
            cursor_update = conn_update.cursor()
            try:
                if password:
                    password_hash = generate_password_hash(password)
                    cursor_update.execute("UPDATE Alumnos SET nombre=?, matricula=?, password=?, grupo_id=? WHERE id=?",
                                   (nombre, matricula, password_hash, grupo_id, id))
                else:
                    cursor_update.execute("UPDATE Alumnos SET nombre=?, matricula=?, grupo_id=? WHERE id=?",
                                   (nombre, matricula, grupo_id, id))
                conn_update.commit()
                flash('Alumno actualizado correctamente.', 'success')
                return redirect(url_for('admin_gestionar_alumnos'))
            except sqlite3.IntegrityError:
                flash(f'Error: La matrícula "{matricula}" ya existe para otro alumno.', 'error')
            except sqlite3.Error as e:
                flash(f'Error al actualizar alumno: {e}', 'error')
            finally:
                conn_update.close()
        # Para repopular
        form_data = {'id': id, 'nombre': nombre, 'matricula': matricula, 'grupo_id': int(grupo_id) if grupo_id else None}
        return render_template('admin/admin_formulario_alumno.html', titulo="Editar Alumno",
                               accion_url=url_for('admin_editar_alumno', id=id), alumno=form_data, grupos=grupos)

    return render_template('admin/admin_formulario_alumno.html', titulo="Editar Alumno",
                           accion_url=url_for('admin_editar_alumno', id=id), alumno=alumno, grupos=grupos)

@app.route('/admin/alumnos/eliminar/<int:id>')
@login_required
@roles_required(['admin'])
def admin_eliminar_alumno(id):
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        # ON DELETE CASCADE en Asistencias y Justificantes se encargará
        cursor.execute("DELETE FROM Alumnos WHERE id = ?", (id,))
        conn.commit()
        flash('Alumno eliminado correctamente. Sus asistencias y justificantes también fueron eliminados.', 'info')
    except sqlite3.Error as e:
        flash(f'Error al eliminar alumno: {e}.', 'error')
    finally:
        conn.close()
    return redirect(url_for('admin_gestionar_alumnos'))


# --- CRUD ASIGNACIONES (Maestros-Materias-Grupos) (Admin) ---
@app.route('/admin/asignaciones')
@login_required
@roles_required(['admin'])
def gestionar_asignaciones():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mmg.id, ma.nombre as nombre_maestro, mat.nombre as nombre_materia,
               g.nombre as nombre_grupo, gr.nombre as nombre_grado, mmg.ciclo_escolar
        FROM Maestros_Materias_Grupos mmg
        JOIN Maestros ma ON mmg.maestro_id = ma.id
        JOIN Materias mat ON mmg.materia_id = mat.id
        JOIN Grupos g ON mmg.grupo_id = g.id
        JOIN Grados gr ON g.grado_id = gr.id
        ORDER BY mmg.ciclo_escolar DESC, gr.nombre, g.nombre, mat.nombre
    """)
    asignaciones = cursor.fetchall()
    conn.close()
    return render_template('admin/gestionar_asignaciones.html', asignaciones=asignaciones)

@app.route('/admin/asignaciones/agregar', methods=['GET', 'POST'])
@login_required
@roles_required(['admin'])
def agregar_asignacion():
    conn_load = conectar_db()
    cursor_load = conn_load.cursor()
    cursor_load.execute("SELECT id, nombre FROM Maestros WHERE rol='maestro' ORDER BY nombre")
    maestros = cursor_load.fetchall()
    cursor_load.execute("SELECT id, nombre FROM Materias ORDER BY nombre")
    materias = cursor_load.fetchall()
    cursor_load.execute("""
        SELECT g.id, gr.nombre || ' - Grupo ' || g.nombre as nombre_completo_grupo
        FROM Grupos g JOIN Grados gr ON g.grado_id = gr.id
        ORDER BY gr.nombre, g.nombre
    """)
    grupos = cursor_load.fetchall()
    conn_load.close()

    if request.method == 'POST':
        maestro_id = request.form.get('maestro_id')
        materia_id = request.form.get('materia_id')
        grupo_id = request.form.get('grupo_id')
        ciclo_escolar = request.form.get('ciclo_escolar', '').strip() or None

        if not maestro_id or not materia_id or not grupo_id or not ciclo_escolar:
            flash('Todos los campos (Maestro, Materia, Grupo, Ciclo Escolar) son obligatorios.', 'error')
        else:
            conn = conectar_db()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO Maestros_Materias_Grupos (maestro_id, materia_id, grupo_id, ciclo_escolar)
                    VALUES (?, ?, ?, ?)
                """, (maestro_id, materia_id, grupo_id, ciclo_escolar))
                conn.commit()
                flash('Asignación creada correctamente.', 'success')
                return redirect(url_for('gestionar_asignaciones'))
            except sqlite3.IntegrityError:
                flash('Error: Esta asignación (Maestro-Materia-Grupo-Ciclo) ya existe.', 'error')
            except sqlite3.Error as e:
                flash(f'Error al crear asignación: {e}', 'error')
            finally:
                conn.close()
        # Para repopular
        return render_template('admin/formulario_asignacion.html', titulo="Agregar Asignación",
                               accion_url=url_for('agregar_asignacion'), asignacion=request.form,
                               maestros=maestros, materias=materias, grupos=grupos)

    return render_template('admin/formulario_asignacion.html', titulo="Agregar Asignación",
                           accion_url=url_for('agregar_asignacion'), asignacion=None,
                           maestros=maestros, materias=materias, grupos=grupos)

@app.route('/admin/asignaciones/eliminar/<int:id>')
@login_required
@roles_required(['admin'])
def eliminar_asignacion(id):
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        # ON DELETE CASCADE en Asistencias se encargará.
        # ON DELETE SET NULL en Justificantes se encargará.
        cursor.execute("DELETE FROM Maestros_Materias_Grupos WHERE id = ?", (id,))
        conn.commit()
        flash('Asignación eliminada correctamente. Las asistencias y justificantes asociados podrían haber sido afectados.', 'info')
    except sqlite3.Error as e:
        flash(f'Error al eliminar asignación: {e}.', 'error')
    finally:
        conn.close()
    return redirect(url_for('gestionar_asignaciones'))

# --- FUNCIONALIDADES DE MAESTRO (Esbozo/Simplificado) ---
@app.route('/maestro/mis_clases')
@login_required
@roles_required(['maestro'])
def maestro_mis_clases():
    # Similar a dashboard_maestro, lista las asignaciones del maestro
    conn = conectar_db()
    cursor = conn.cursor()
    maestro_id = session['user_id']
    cursor.execute("""
        SELECT mmg.id as asignacion_id, m.nombre as nombre_materia, g.nombre as nombre_grupo, gr.nombre as nombre_grado, mmg.ciclo_escolar
        FROM Maestros_Materias_Grupos mmg
        JOIN Materias m ON mmg.materia_id = m.id
        JOIN Grupos g ON mmg.grupo_id = g.id
        JOIN Grados gr ON g.grado_id = gr.id
        WHERE mmg.maestro_id = ?
        ORDER BY mmg.ciclo_escolar, gr.nombre, g.nombre, m.nombre
    """, (maestro_id,))
    asignaciones = cursor.fetchall()
    conn.close()
    return render_template('maestro/mis_clases.html', asignaciones=asignaciones)

@app.route('/maestro/asistencia/<int:asignacion_id>', methods=['GET', 'POST'])
@login_required
@roles_required(['maestro'])
def maestro_registrar_asistencia(asignacion_id):
    conn = conectar_db()
    cursor = conn.cursor()

    # Verificar que la asignación pertenece al maestro en sesión
    cursor.execute("""
        SELECT mmg.id, m.nombre as nombre_materia, g.nombre as nombre_grupo, gr.nombre as nombre_grado
        FROM Maestros_Materias_Grupos mmg
        JOIN Materias m ON mmg.materia_id = m.id
        JOIN Grupos g ON mmg.grupo_id = g.id
        JOIN Grados gr ON g.grado_id = gr.id
        WHERE mmg.id = ? AND mmg.maestro_id = ?
    """, (asignacion_id, session['user_id']))
    asignacion = cursor.fetchone()

    if not asignacion:
        flash("Asignación no válida o no tiene permiso.", "error")
        conn.close()
        return redirect(url_for('maestro_mis_clases'))

    # Obtener alumnos del grupo de esta asignación
    cursor.execute("""
        SELECT a.id, a.nombre, a.matricula
        FROM Alumnos a
        JOIN Maestros_Materias_Grupos mmg ON a.grupo_id = mmg.grupo_id
        WHERE mmg.id = ?
        ORDER BY a.nombre
    """, (asignacion_id,))
    alumnos = cursor.fetchall()

    fecha_hoy = datetime.now().strftime('%Y-%m-%d')

    if request.method == 'POST':
        fecha_asistencia = request.form.get('fecha_asistencia', fecha_hoy)
        # Eliminar asistencias previas para esta asignación y fecha para evitar duplicados al reenviar
        try:
            cursor.execute("DELETE FROM Asistencias WHERE asignacion_id = ? AND fecha = ?", (asignacion_id, fecha_asistencia))
            # conn.commit() # Commit después del bucle de inserciones
        except sqlite3.Error as e_del:
            flash(f"Error al limpiar asistencias previas: {e_del}", "error")
            # Considerar si continuar o no

        for alumno in alumnos:
            estado = request.form.get(f"asistencia_alumno_{alumno['id']}")
            observaciones = request.form.get(f"observaciones_alumno_{alumno['id']}", "").strip() or None
            if estado: # Solo registrar si se seleccionó un estado
                try:
                    cursor.execute("""
                        INSERT INTO Asistencias (alumno_id, asignacion_id, fecha, hora, estado, observaciones)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (alumno['id'], asignacion_id, fecha_asistencia, datetime.now().strftime('%H:%M'), estado, observaciones))
                except sqlite3.Error as e_ins:
                    flash(f"Error al registrar asistencia para {alumno['nombre']}: {e_ins}", "error")
        try:
            conn.commit()
            flash(f"Asistencia para el {fecha_asistencia} registrada/actualizada.", "success")
        except sqlite3.Error as e_comm:
            flash(f"Error al hacer commit de las asistencias: {e_comm}", "error")
            conn.rollback()

        #return redirect(url_for('maestro_registrar_asistencia', asignacion_id=asignacion_id)) # Redirigir para ver cambios

    # Cargar asistencias ya registradas para esta fecha y asignación
    asistencias_registradas = {}
    cursor.execute("""
        SELECT alumno_id, estado, observaciones FROM Asistencias
        WHERE asignacion_id = ? AND fecha = ?
    """, (asignacion_id, fecha_hoy)) # Por defecto muestra para hoy
    for reg in cursor.fetchall():
        asistencias_registradas[reg['alumno_id']] = {'estado': reg['estado'], 'observaciones': reg['observaciones']}

    conn.close()
    return render_template('maestro/registrar_asistencia.html', asignacion=asignacion, alumnos=alumnos,
                           fecha_hoy=fecha_hoy, asistencias_registradas=asistencias_registradas)


# --- FUNCIONALIDADES DE ALUMNO (Esbozo/Simplificado) ---
@app.route('/alumno/subir_justificante', methods=['POST'])
@login_required
@roles_required(['alumno'])
def alumno_subir_justificante():
    motivo = request.form.get('motivo', '').strip()
    fecha_inasistencia_inicio = request.form.get('fecha_inasistencia_inicio')
    fecha_inasistencia_fin = request.form.get('fecha_inasistencia_fin', fecha_inasistencia_inicio) # Si no hay fin, es la misma que inicio
    # asignacion_id_justificante = request.form.get('asignacion_id') or None # Si se justifica una clase específica

    if not motivo or not fecha_inasistencia_inicio:
        flash('El motivo y la fecha de inicio de inasistencia son obligatorios.', 'error')
        return redirect(url_for('dashboard_alumno'))

    fecha_solicitud = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        # Aquí faltaría la lógica para seleccionar la asignación_id si se quiere justificar una clase específica
        cursor.execute("""
            INSERT INTO Justificantes (alumno_id, fecha_solicitud, fecha_inasistencia_inicio, fecha_inasistencia_fin, motivo, estado)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session['user_id'], fecha_solicitud, fecha_inasistencia_inicio, fecha_inasistencia_fin, motivo, 'Pendiente'))
        conn.commit()
        flash('Justificante subido correctamente.', 'success')
    except sqlite3.Error as e:
        conn.rollback()
        flash(f'Error al subir el justificante: {e}', 'error')
    finally:
        conn.close()
    return redirect(url_for('dashboard_alumno'))


if __name__ == '__main__':
    print("Iniciando la aplicación Flask...")
    app.run(debug=True, port=8004, host='0.0.0.0')