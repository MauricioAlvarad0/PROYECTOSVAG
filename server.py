from flask import Flask, render_template, request, redirect, session, url_for, flash # CAMBIO REALIZADO: flash añadido
import sqlite3
from datetime import datetime
import sys
sys.path.append('..')
import database

#jhvhjvhjvv
app = Flask(__name__)
app.secret_key = 'clave_secreta' # Importante para que funcionen los mensajes flash

database.crear_db()

def conectar_db():
    return sqlite3.connect('svag.db')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login_maestro', methods=['GET', 'POST'])
def login_maestro():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM maestros WHERE usuario = ? AND password = ?", (usuario, password))
        maestro = cursor.fetchone()
        conn.close()
        if maestro:
            session['maestro_id'] = maestro[0]
            session['nombre_usuario'] = maestro[1] # Opcional: guardar nombre para mostrarlo
            return redirect(url_for('dashboard_maestro'))
        else:
            # CAMBIO REALIZADO: Usar flash y re-renderizar la plantilla
            flash('Usuario o contraseña incorrectos. Por favor, inténtalo de nuevo.', 'error')
            return render_template('login_maestro.html')
    return render_template('login_maestro.html')

@app.route('/dashboard_maestro')
def dashboard_maestro():
    if 'maestro_id' not in session:
        return redirect(url_for('login_maestro'))
    return render_template('dashboard_maestro.html')

@app.route('/login_alumno', methods=['GET', 'POST'])
def login_alumno():
    if request.method == 'POST':
        matricula = request.form['matricula']
        password = request.form['password']
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alumnos WHERE matricula = ? AND password = ?", (matricula, password))
        alumno = cursor.fetchone()
        conn.close()
        if alumno:
            session['alumno_id'] = alumno[0]
            session['nombre_alumno'] = alumno[1] # Suponiendo que el nombre está en la posición 1
            return redirect(url_for('dashboard_alumno'))
        else:
            # CAMBIO REALIZADO: Usar flash y re-renderizar la plantilla
            flash('Matrícula o contraseña incorrectas. Por favor, inténtalo de nuevo.', 'error')
            return render_template('login_alumno.html')
    return render_template('login_alumno.html')

@app.route('/dashboard_alumno')
def dashboard_alumno():
    if 'alumno_id' not in session:
        return redirect(url_for('login_alumno'))

    conn = conectar_db()
    cursor = conn.cursor()

    # Asegúrate de que la tabla alumnos tenga una columna 'nombre' si quieres usar session['nombre_alumno']
    # Por ahora, me baso en la estructura que vi en agregar_alumno.html que pide 'nombre'
    cursor.execute("SELECT matricula, nombre FROM alumnos WHERE id = ?", (session['alumno_id'],))
    alumno_data = cursor.fetchone()
    alumno_matricula = alumno_data[0] if alumno_data else None
    # nombre_alumno = alumno_data[1] if alumno_data else None # Descomentar si quieres usarlo

    cursor.execute('''
        SELECT fecha, hora, estado
        FROM asistencias
        WHERE alumno_id = ?
        ORDER BY fecha DESC
    ''', (session['alumno_id'],))
    asistencias = cursor.fetchall()

    cursor.execute('''
        SELECT id, fecha, motivo, estado
        FROM justificantes
        WHERE alumno_id = ?
        ORDER BY fecha DESC
    ''', (session['alumno_id'],))
    justificantes = cursor.fetchall()

    conn.close()
    return render_template('dashboard_alumno.html', alumno_matricula=alumno_matricula, asistencias=asistencias, justificantes=justificantes)

@app.route('/subir_justificante', methods=['POST'])
def subir_justificante():
    if 'alumno_id' not in session:
        return redirect(url_for('login_alumno'))

    motivo = request.form['motivo']
    fecha = datetime.now().strftime('%Y-%m-%d')

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO justificantes (alumno_id, fecha, motivo, estado) VALUES (?, ?, ?, ?)",
                   (session['alumno_id'], fecha, motivo, 'pendiente'))
    conn.commit()
    conn.close()
    flash('Justificante subido correctamente.', 'success') # CAMBIO OPCIONAL: Mensaje de éxito
    return redirect(url_for('dashboard_alumno'))

@app.route('/asistencias')
def mostrar_asistencias():
    if 'maestro_id' not in session: # CAMBIO OPCIONAL: Proteger ruta
        flash('Debes iniciar sesión como maestro para ver esta página.', 'warning')
        return redirect(url_for('login_maestro'))
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT alumnos.matricula, asistencias.fecha, asistencias.hora, asistencias.estado
        FROM asistencias
        JOIN alumnos ON asistencias.alumno_id = alumnos.id
        ORDER BY asistencias.fecha DESC
    ''')
    registros = cursor.fetchall()
    conn.close()
    return render_template('asistencias.html', registros=registros)

@app.route('/justificantes')
def ver_justificantes():
    if 'maestro_id' not in session: # CAMBIO OPCIONAL: Proteger ruta
        flash('Debes iniciar sesión como maestro para ver esta página.', 'warning')
        return redirect(url_for('login_maestro'))
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT justificantes.id, alumnos.matricula, justificantes.fecha, justificantes.motivo, justificantes.estado
        FROM justificantes
        JOIN alumnos ON justificantes.alumno_id = alumnos.id
        ORDER BY justificantes.fecha DESC
    ''')
    justificantes = cursor.fetchall()
    conn.close()
    return render_template('justificantes.html', justificantes=justificantes)

@app.route('/actualizar_justificante/<int:id>/<estado>')
def actualizar_justificante(id, estado):
    if 'maestro_id' not in session: # CAMBIO OPCIONAL: Proteger ruta
        return redirect(url_for('login_maestro'))
    if estado not in ['aprobado', 'rechazado']:
        flash('Estado inválido para el justificante.', 'error')
        return redirect(url_for('ver_justificantes'))
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE justificantes SET estado = ? WHERE id = ?", (estado, id))
    conn.commit()
    conn.close()
    flash(f'Justificante {estado} correctamente.', 'success') # CAMBIO OPCIONAL: Mensaje de éxito
    return redirect(url_for('ver_justificantes'))

# CRUD para alumnos
@app.route('/alumnos')
def alumnos():
    if 'maestro_id' not in session: # CAMBIO OPCIONAL: Proteger ruta
        return redirect(url_for('login_maestro'))
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, matricula FROM alumnos") # Asumiendo que tienes 'nombre'
    alumnos_data = cursor.fetchall()
    conn.close()
    return render_template('alumnos.html', alumnos=alumnos_data)

@app.route('/agregar_alumno', methods=['GET', 'POST'])
def agregar_alumno():
    if 'maestro_id' not in session: # CAMBIO OPCIONAL: Proteger ruta
        return redirect(url_for('login_maestro'))
    if request.method == 'POST':
        nombre = request.form['nombre']
        matricula = request.form['matricula']
        password = request.form['password'] # Idealmente, deberías hashear esta contraseña
        conn = conectar_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO alumnos (nombre, matricula, password) VALUES (?, ?, ?)", (nombre, matricula, password))
            conn.commit()
            flash(f'Alumno {nombre} agregado correctamente.', 'success') # CAMBIO OPCIONAL: Mensaje de éxito
        except sqlite3.IntegrityError:
            flash(f'Error: La matrícula {matricula} ya existe.', 'error') # CAMBIO OPCIONAL: Manejo de error
            conn.rollback()
        finally:
            conn.close()
        return redirect(url_for('alumnos'))
    return render_template('agregar_alumno.html', alumno=None) # Pasar alumno=None para consistencia con editar

@app.route('/editar_alumno/<int:id>', methods=['GET', 'POST'])
def editar_alumno(id):
    if 'maestro_id' not in session:
        return redirect(url_for('login_maestro'))

    conn = conectar_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        nombre = request.form['nombre']
        matricula = request.form['matricula']
        # No actualizamos la contraseña aquí por simplicidad, pero podrías añadir un campo
        try:
            cursor.execute("UPDATE alumnos SET nombre = ?, matricula = ? WHERE id = ?", (nombre, matricula, id))
            conn.commit()
            flash('Alumno actualizado correctamente.', 'success')
        except sqlite3.IntegrityError:
            flash(f'Error: La matrícula {matricula} ya existe para otro alumno.', 'error')
            conn.rollback()
        finally:
            conn.close()
        return redirect(url_for('alumnos'))
    else:
        cursor.execute("SELECT id, nombre, matricula FROM alumnos WHERE id = ?", (id,))
        alumno = cursor.fetchone()
        conn.close()
        if not alumno:
            flash('Alumno no encontrado.', 'error')
            return redirect(url_for('alumnos'))
        return render_template('agregar_alumno.html', alumno=alumno)


@app.route('/eliminar_alumno/<int:id>')
def eliminar_alumno(id):
    if 'maestro_id' not in session: # CAMBIO OPCIONAL: Proteger ruta
        return redirect(url_for('login_maestro'))
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM alumnos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash('Alumno eliminado correctamente.', 'info') # CAMBIO OPCIONAL: Mensaje de éxito
    return redirect(url_for('alumnos'))

# CRUD para maestros
@app.route('/maestros')
def maestros():
    if 'maestro_id' not in session: # CAMBIO OPCIONAL: Proteger ruta
        return redirect(url_for('login_maestro'))
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, usuario FROM maestros") # Asumiendo que tienes 'nombre'
    maestros_data = cursor.fetchall()
    conn.close()
    return render_template('maestros.html', maestros=maestros_data)

@app.route('/agregar_maestro', methods=['GET', 'POST'])
def agregar_maestro():
    if 'maestro_id' not in session: # CAMBIO OPCIONAL: Proteger ruta
        return redirect(url_for('login_maestro'))
    if request.method == 'POST':
        nombre = request.form['nombre']
        usuario = request.form['usuario']
        password = request.form['password'] # Idealmente, deberías hashear esta contraseña
        conn = conectar_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO maestros (nombre, usuario, password) VALUES (?, ?, ?)", (nombre, usuario, password))
            conn.commit()
            flash(f'Maestro {nombre} agregado correctamente.', 'success') # CAMBIO OPCIONAL: Mensaje de éxito
        except sqlite3.IntegrityError:
            flash(f'Error: El usuario {usuario} ya existe.', 'error') # CAMBIO OPCIONAL: Manejo de error
            conn.rollback()
        finally:
            conn.close()
        return redirect(url_for('maestros'))
    # Pasar maestro=None para consistencia con editar
    return render_template('agregar_maestro.html', maestro=None)

@app.route('/editar_maestro/<int:id>', methods=['GET', 'POST'])
def editar_maestro(id):
    if 'maestro_id' not in session:
        return redirect(url_for('login_maestro'))

    conn = conectar_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        nombre = request.form['nombre']
        usuario = request.form['usuario']
        # No actualizamos la contraseña aquí
        try:
            cursor.execute("UPDATE maestros SET nombre = ?, usuario = ? WHERE id = ?", (nombre, usuario, id))
            conn.commit()
            flash('Maestro actualizado correctamente.', 'success')
        except sqlite3.IntegrityError:
            flash(f'Error: El usuario {usuario} ya existe para otro maestro.', 'error')
            conn.rollback()
        finally:
            conn.close()
        return redirect(url_for('maestros'))
    else:
        cursor.execute("SELECT id, nombre, usuario FROM maestros WHERE id = ?", (id,))
        maestro = cursor.fetchone()
        conn.close()
        if not maestro:
            flash('Maestro no encontrado.', 'error')
            return redirect(url_for('maestros'))
        return render_template('agregar_maestro.html', maestro=maestro)


@app.route('/eliminar_maestro/<int:id>')
def eliminar_maestro(id):
    if 'maestro_id' not in session: # CAMBIO OPCIONAL: Proteger ruta
        return redirect(url_for('login_maestro'))
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM maestros WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash('Maestro eliminado correctamente.', 'info') # CAMBIO OPCIONAL: Mensaje de éxito
    return redirect(url_for('maestros'))

@app.route('/logout') # CAMBIO OPCIONAL: Ruta de logout
def logout():
    session.clear() # Limpia toda la sesión
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=8004, host='0.0.0.0')