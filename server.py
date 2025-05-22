from flask import Flask, render_template, request, redirect, url_for, flash, session
import database 
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import sqlite3
import os
from datetime import date, datetime 
import traceback

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_muy_segura_y_dificil_de_adivinar12345!' 

# === PROCESADOR DE CONTEXTO PARA 'now' ===
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow} 

# --- INICIALIZACIÓN Y CONFIGURACIÓN ---
print(f"INFO server.py: CWD actual: {os.getcwd()}") 
print(f"INFO server.py: DATABASE_NAME desde database.py: {database.DATABASE_NAME}")

if not os.path.exists(database.DATABASE_NAME):
    print(f"INFO server.py: BD no existe. Creando desde server.py...")
    database.create_tables_and_initialize() 
    print(f"INFO server.py: BD creada.")
else:
    print(f"INFO server.py: BD existe. Verificando/creando tablas...")
    database.create_tables_and_initialize() 
    print(f"INFO server.py: Tablas verificadas.")

UPLOAD_FOLDER_JUSTIFICANTES = os.path.join(app.root_path, 'uploads', 'justificantes')
ALLOWED_EXTENSIONS_JUSTIFICANTES = {'png', 'jpg', 'jpeg', 'pdf', 'doc', 'docx'}
app.config['UPLOAD_FOLDER_JUSTIFICANTES'] = UPLOAD_FOLDER_JUSTIFICANTES
if not os.path.exists(UPLOAD_FOLDER_JUSTIFICANTES):
    try: os.makedirs(UPLOAD_FOLDER_JUSTIFICANTES)
    except OSError as e: print(f"ERROR creando carpeta de subidas: {e}")

def allowed_file_justificante(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_JUSTIFICANTES

# --- DECORADORES DE AUTENTICACIÓN ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicia sesión para acceder.', 'warning')
            return redirect(url_for('login_unificado_nuevo', next=request.url if request.method == 'GET' else None))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if session.get('user_tipo') != 'administrador':
            flash('Acceso no autorizado. Se requiere rol de administrador.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def maestro_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if session.get('user_tipo') not in ['maestro', 'administrador']: 
            flash('Acceso no autorizado. Se requiere rol de maestro.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def alumno_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if session.get('user_tipo') != 'alumno':
            flash('Acceso no autorizado. Se requiere rol de alumno.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- RUTAS PRINCIPALES Y DE LOGIN ---
@app.route('/')
def index():
    if 'user_id' in session and 'user_tipo' in session:
        tipo = session.get('user_tipo')
        if tipo == 'administrador': return redirect(url_for('dashboard_admin'))
        elif tipo == 'maestro': return redirect(url_for('dashboard_maestro'))
        elif tipo == 'alumno': return redirect(url_for('dashboard_alumno'))
    return redirect(url_for('login_unificado_nuevo'))

@app.route('/login', methods=['GET', 'POST']) 
def login_unificado_nuevo():
    if 'user_id' in session and 'user_tipo' in session: return redirect(url_for('index'))
    if request.method == 'POST':
        identificador_form = request.form.get('matricula_o_email') 
        password_form = request.form.get('password')
        login_error_flag = True # Para resaltar campos en la plantilla si el login falla
        if not identificador_form or not password_form:
            flash('Ingresa identificador y contraseña.', 'warning')
            return render_template('index.html', login_error=login_error_flag)
        
        user = None
        if "@" not in identificador_form: # Asume que si no tiene @, es matrícula u otro login_id
             user = database.get_user_by_matricula(identificador_form) 
             if not user: # Si no es matrícula, podría ser un usuario_login (para maestros/admin)
                 user = database.get_user_by_usuario_login(identificador_form) # Necesitarías esta función en database.py
        
        if not user and "@" in identificador_form: # Si aún no hay usuario y parece email
            user = database.get_user_by_email(identificador_form) 
        
        if user and check_password_hash(user['password'], password_form):
            session['user_id'] = user['id']
            session['user_tipo'] = user['tipo']
            session['user_name'] = user['nombre']
            session['user_email'] = user['email']     
            session['user_matricula'] = user['matricula'] 

            flash(f'Bienvenido, {user["nombre"]}!', 'success'); next_url = request.args.get('next')
            if user['tipo'] == 'administrador': return redirect(next_url or url_for('dashboard_admin'))
            elif user['tipo'] == 'maestro': return redirect(next_url or url_for('dashboard_maestro'))
            elif user['tipo'] == 'alumno': return redirect(next_url or url_for('dashboard_alumno'))
            else: flash('Tipo de usuario desconocido.', 'danger'); session.clear()
        else:
            flash('Identificador o contraseña incorrecta.', 'danger')
        return render_template('index.html', login_error=login_error_flag) # Re-render con error
            
    return render_template('index.html')

@app.route('/logout')
@login_required 
def logout():
    session.clear(); flash('Sesión cerrada exitosamente.', 'info'); return redirect(url_for('login_unificado_nuevo'))

# --- DASHBOARDS ---
@app.route('/dashboard_admin')
@admin_required
def dashboard_admin(): return render_template('dashboard_admin.html', nombre_usuario=session.get('user_name'))

@app.route('/dashboard_maestro')
@maestro_required
def dashboard_maestro():
    maestro_id = session['user_id']
    return render_template('dashboard_maestro.html', nombre_usuario=session.get('user_name'), clases=database.get_clases_por_maestro(maestro_id))

@app.route('/dashboard_alumno')
@alumno_required
def dashboard_alumno():
    alumno_id = session['user_id']; alumno_nombre = session.get('user_name'); clases_con_asistencia = []; mis_clases_para_justificante = []
    try:
        today_str = date.today().strftime('%Y-%m-%d')
        clases_con_asistencia = database.get_clases_inscritas_con_estado_asistencia(alumno_id, today_str)
        conn_temp = database.get_db_connection()
        clases_raw = conn_temp.execute("""
             SELECT c.id as clase_id, m.nombre as materia_nombre, gr.nombre as grado_nombre, grp.nombre as grupo_nombre 
             FROM Clases_Alumnos ca JOIN Clases c ON ca.clase_id = c.id JOIN Materias m ON c.materia_id = m.id
             JOIN Grados gr ON c.grado_id = gr.id JOIN Grupos grp ON c.grupo_id = grp.id
             WHERE ca.alumno_id = ? ORDER BY m.nombre
         """, (alumno_id,)).fetchall()
        mis_clases_para_justificante = [dict(row) for row in clases_raw]; conn_temp.close()
    except Exception as e: flash(f'Error al cargar dashboard alumno: {e}', 'danger'); traceback.print_exc()
    return render_template('dashboard_alumno.html', alumno_nombre=alumno_nombre, clases_hoy=clases_con_asistencia, 
                           fecha_actual=date.today().strftime('%d/%m/%Y'), mis_clases_para_justificante=mis_clases_para_justificante)

# --- FUNCIONALIDAD DE ASISTENCIA ALUMNO ---
@app.route('/alumno/marcar_asistencia/<int:clase_id>', methods=['POST'])
@alumno_required
def alumno_marcar_asistencia(clase_id):
    alumno_id = session['user_id']
    if not database.is_alumno_inscrito_en_clase(alumno_id, clase_id):
        flash('No estás inscrito en esta clase.', 'danger'); return redirect(url_for('dashboard_alumno'))
    fecha = date.today().strftime('%Y-%m-%d'); hora = datetime.now().strftime('%H:%M:%S')
    if database.add_asistencia(clase_id, alumno_id, fecha, 'Presente', hora=hora):
        flash('Asistencia "Presente" registrada/actualizada.', 'success')
    else: flash('Error al registrar asistencia.', 'danger')
    return redirect(url_for('dashboard_alumno'))

# --- GESTIÓN DE ASISTENCIA MAESTRO ---
@app.route('/maestro/clase/<int:clase_id>/asistencia', methods=['GET', 'POST'])
@maestro_required
def registrar_asistencia_maestro(clase_id):
    clase_info = database.get_clase_by_id(clase_id)
    es_maestro = clase_info and clase_info['maestro_id'] == session['user_id']
    es_admin = session.get('user_tipo') == 'administrador'
    if not (clase_info and (es_maestro or es_admin)):
        flash('Permiso denegado o clase no existe.', 'warning'); return redirect(url_for('dashboard_maestro'))
    if request.method == 'POST':
        fecha = request.form.get('fecha', date.today().strftime('%Y-%m-%d')); hora = datetime.now().strftime('%H:%M:%S')
        alumnos_en_clase = database.get_alumnos_por_clase(clase_id)
        for alumno in alumnos_en_clase: # Asegurarse de procesar para todos los alumnos de la clase
            alumno_id = alumno['id']
            estatus = request.form.get(f'asistencia_{alumno_id}')
            observaciones = request.form.get(f'observaciones_{alumno_id}', "").strip()
            if estatus: # Solo registrar/actualizar si se envió un estado
                database.add_asistencia(clase_id, alumno_id, fecha, estatus, observaciones, hora)
        flash('Asistencias actualizadas.', 'success'); return redirect(url_for('registrar_asistencia_maestro', clase_id=clase_id, fecha_seleccionada=fecha))
    
    fecha_sel = request.args.get('fecha_seleccionada', date.today().strftime('%Y-%m-%d'))
    alumnos = database.get_alumnos_por_clase(clase_id); asist_reg = {}
    for al in alumnos:
        asist = database.get_asistencia_alumno_clase_fecha(al['id'], clase_id, fecha_sel)
        if asist: asist_reg[al['id']] = {'estatus': asist['estatus'], 'observaciones': asist['observaciones']}
    return render_template('maestros/registrar_asistencia.html', alumnos=alumnos, clase_id=clase_id, clase_info=clase_info,
                           asistencias_registradas=asist_reg, fecha_seleccionada=fecha_sel, today_date_str=date.today().strftime('%Y-%m-%d'))

# --- VISTA GENERAL ASISTENCIAS ADMIN ---
@app.route('/admin/asistencias_generales') 
@admin_required
def admin_asistencias_generales():
    conn = database.get_db_connection(); asist = []
    try:
        asist = conn.execute('''
            SELECT A.fecha,A.estatus,A.observaciones,A.hora,U_a.nombre alumno_nombre,U_a.email alumno_email,M.nombre materia_nombre,C.id clase_id,C.ciclo_escolar ciclo_escolar,
            U_m.nombre maestro_nombre,GR.nombre grado_nombre,GRP.nombre grupo_nombre FROM Asistencias A JOIN Usuarios U_a ON A.alumno_id=U_a.id
            JOIN Clases C ON A.clase_id=C.id JOIN Materias M ON C.materia_id=M.id JOIN Usuarios U_m ON C.maestro_id=U_m.id
            LEFT JOIN Grados GR ON C.grado_id=GR.id LEFT JOIN Grupos GRP ON C.grupo_id=GRP.id 
            ORDER BY A.fecha DESC,C.ciclo_escolar,M.nombre,U_a.nombre''').fetchall()
    except sqlite3.Error as e: flash(f"Error al cargar asistencias: {e}", "danger"); traceback.print_exc()
    finally: conn.close()
    return render_template('asistencias.html', asistencias=asist)

# --- GESTIÓN DE USUARIOS (ADMIN - Tabla Usuarios Unificada) ---
@app.route('/admin/usuarios') 
@admin_required
def admin_gestionar_usuarios(): 
    conn = database.get_db_connection(); usuarios_list = []
    try:
        usuarios_list = conn.execute("SELECT id, nombre, email, tipo, matricula, curp FROM Usuarios ORDER BY tipo, nombre").fetchall()
    except sqlite3.Error as e: flash(f"Error al cargar usuarios: {e}", "danger"); traceback.print_exc()
    finally: conn.close()
    return render_template('admin/admin_gestionar_usuarios.html', usuarios=usuarios_list) 

@app.route('/admin/usuarios/agregar', methods=['GET', 'POST'])
@admin_required
def admin_agregar_usuario(): 
    if request.method == 'POST':
        nombre=request.form.get('nombre',"").strip(); email=request.form.get('email',"").strip(); pwd=request.form.get('password'); tipo=request.form.get('tipo') 
        ap=request.form.get('apellido_paterno',"").strip(); am=request.form.get('apellido_materno',"").strip(); fn=request.form.get('fecha_nacimiento')
        curp=request.form.get('curp',"").strip() or None; dire=request.form.get('direccion',"").strip(); tel=request.form.get('telefono',"").strip()
        mat=request.form.get('matricula',"").strip() or None; ulog=request.form.get('usuario_login_alt',"").strip() or None
        
        is_valid = True
        if not all([nombre,pwd,tipo]): 
            flash("Nombre, contraseña y tipo son requeridos.", "warning"); is_valid = False
        if tipo not in ['administrador','maestro','alumno']: 
            flash("Tipo de usuario no válido.", "warning"); is_valid = False
        if tipo == 'alumno' and not mat:
            flash("La matrícula es requerida para alumnos.", "warning"); is_valid = False
        if (tipo == 'administrador' or tipo == 'maestro') and not email and not ulog:
            flash("Email o Usuario Login Alternativo es requerido para Administradores/Maestros.", "warning"); is_valid = False
        
        if is_valid:
            if database.add_user(nombre,email if email else None,generate_password_hash(pwd),tipo,ap,am,fn,curp,dire,tel,mat,ulog):
                flash(f'Usuario ({tipo}) agregado.', 'success'); return redirect(url_for('admin_gestionar_usuarios'))
            else: flash('Error al agregar: Email, CURP, Matrícula o Login Alterno ya existen.', 'danger')
        return render_template('admin/admin_formulario_usuario.html', accion="Agregar", usuario_form=request.form)
    return render_template('admin/admin_formulario_usuario.html', accion="Agregar", usuario_form=None)

@app.route('/admin/usuarios/editar/<int:id_usuario>', methods=['GET', 'POST'])
@admin_required
def admin_editar_usuario(id_usuario):
    usr = database.get_user_by_id(id_usuario)
    if not usr: flash("Usuario no encontrado.", "danger"); return redirect(url_for('admin_gestionar_usuarios'))
    if request.method == 'POST':
        nombre=request.form.get('nombre',"").strip(); email=request.form.get('email',"").strip(); tipo=request.form.get('tipo')
        ap=request.form.get('apellido_paterno',"").strip(); am=request.form.get('apellido_materno',"").strip(); fn=request.form.get('fecha_nacimiento')
        curp=request.form.get('curp',"").strip() or None; dire=request.form.get('direccion',"").strip(); tel=request.form.get('telefono',"").strip()
        mat=request.form.get('matricula',"").strip() or None; ulog=request.form.get('usuario_login_alt',"").strip() or None
        
        is_valid = True
        if not all([nombre,tipo]): 
            flash("Nombre y tipo son requeridos.", "warning"); is_valid = False
        if tipo not in ['administrador','maestro','alumno']: 
            flash("Tipo de usuario no válido.", "warning"); is_valid = False
        if tipo == 'alumno' and not mat:
            flash("La matrícula es requerida para alumnos.", "warning"); is_valid = False
        if (tipo == 'administrador' or tipo == 'maestro') and not email and not ulog:
            flash("Email o Usuario Login Alternativo es requerido para Administradores/Maestros.", "warning"); is_valid = False
            
        if is_valid:
            pwd_f = request.form.get('password'); hash_p_upd = generate_password_hash(pwd_f) if pwd_f else None
            if database.update_user(id_usuario,nombre,email if email else None,tipo,ap,am,fn,curp,dire,tel,mat,ulog,hash_p_upd):
                flash(f'Usuario ({tipo}) actualizado.', 'success'); return redirect(url_for('admin_gestionar_usuarios'))
            else: flash('Error al actualizar: Email, CURP, Matrícula o Login podrían ya existir para otro.', 'danger')
        
        # Conservar el ID para el action del form en caso de error de validación
        form_data_with_id = request.form.copy()
        # form_data_with_id['id'] = id_usuario # No es necesario si ya se pasa usuario_id_template
        return render_template('admin/admin_formulario_usuario.html', accion="Editar", usuario_form=form_data_with_id, usuario_id_template=id_usuario)
    
    return render_template('admin/admin_formulario_usuario.html', accion="Editar", usuario_form=dict(usr), usuario_id_template=id_usuario)

@app.route('/admin/usuarios/eliminar/<int:id_usuario>', methods=['POST'])
@admin_required
def admin_eliminar_usuario(id_usuario):
    if database.delete_user(id_usuario): flash('Usuario eliminado.', 'success')
    else: flash('Error al eliminar. Podría ser único admin o tener registros asociados.', 'danger')
    return redirect(url_for('admin_gestionar_usuarios'))

# --- GESTIÓN DE MATERIAS, GRADOS, GRUPOS ---
@app.route('/admin/materias')
@admin_required
def admin_gestionar_materias_page(): return render_template('admin/gestionar_materias.html', materias=database.get_materias())

@app.route('/admin/materias/agregar', methods=['GET','POST'])
@admin_required
def admin_agregar_materia_page():
    if request.method=='POST':
        n=request.form.get('nombre_materia',"").strip(); c=request.form.get('clave_materia',"").strip() or None; d=request.form.get('descripcion',"").strip() or None
        if not n: flash("Nombre de materia requerido.", "warning")
        else: 
            if database.add_materia(n,c,d): flash('Materia agregada.', 'success'); return redirect(url_for('admin_gestionar_materias_page'))
            else: flash('Error al agregar materia (posible duplicado).', 'danger')
        return render_template('admin/formulario_materia.html', accion="Agregar", materia=request.form)
    return render_template('admin/formulario_materia.html', accion="Agregar", materia=None)

@app.route('/admin/materias/editar/<int:id_materia>', methods=['GET','POST'])
@admin_required
def admin_editar_materia_page(id_materia):
    conn=database.get_db_connection()
    if request.method=='POST':
        n=request.form.get('nombre_materia',"").strip(); c=request.form.get('clave_materia',"").strip() or None; d=request.form.get('descripcion',"").strip() or None
        if not n: flash("Nombre de materia requerido.", "warning")
        else:
            try: conn.execute("UPDATE Materias SET nombre=?, clave_materia=?, descripcion=? WHERE id=?",(n,c,d,id_materia)); conn.commit(); flash('Materia actualizada.','success'); return redirect(url_for('admin_gestionar_materias_page'))
            except sqlite3.IntegrityError: flash('Error: Nombre o clave ya existen para otra materia.', 'danger')
            except Exception as e: flash(f'Error al actualizar: {str(e)}','danger'); traceback.print_exc()
        m_data=conn.execute("SELECT * FROM Materias WHERE id = ?",(id_materia,)).fetchone() # Recargar datos para el form
        conn.close()
        return render_template('admin/formulario_materia.html',accion="Editar",materia=m_data) # Pasar datos recargados
    
    m_data=conn.execute("SELECT * FROM Materias WHERE id = ?",(id_materia,)).fetchone()
    conn.close()
    if not m_data: flash('Materia no encontrada.','danger'); return redirect(url_for('admin_gestionar_materias_page'))
    return render_template('admin/formulario_materia.html',accion="Editar",materia=m_data)

@app.route('/admin/materias/eliminar/<int:id_materia>', methods=['POST'])
@admin_required
def admin_eliminar_materia_page(id_materia):
    conn=database.get_db_connection()
    try: conn.execute("DELETE FROM Materias WHERE id = ?",(id_materia,)); conn.commit(); flash('Materia eliminada.','success')
    except sqlite3.IntegrityError as e: flash(f'Error: {e}. Puede estar asignada.','danger')
    except Exception as e: flash(f'Error: {e}.','danger')
    finally: conn.close()
    return redirect(url_for('admin_gestionar_materias_page'))

@app.route('/admin/grados')
@admin_required
def admin_gestionar_grados_page(): return render_template('admin/gestionar_grados.html', grados=database.get_grados())

@app.route('/admin/grados/agregar', methods=['GET','POST'])
@admin_required
def admin_agregar_grado_page():
    if request.method=='POST':
        n=request.form.get('nombre_grado',"").strip()
        if not n: flash("Nombre de grado requerido.","warning")
        else: 
            if database.add_grado(n): flash('Grado agregado.','success'); return redirect(url_for('admin_gestionar_grados_page'))
            else: flash('Error al agregar grado (posible duplicado).','danger')
        return render_template('admin/formulario_grado.html',accion="Agregar",grado=request.form) # Repopulate
    return render_template('admin/formulario_grado.html',accion="Agregar",grado=None)

@app.route('/admin/grados/editar/<int:id_grado>', methods=['GET','POST'])
@admin_required
def admin_editar_grado_page(id_grado):
    conn=database.get_db_connection()
    if request.method=='POST':
        n=request.form.get('nombre_grado',"").strip()
        if not n: flash("Nombre de grado requerido.","warning")
        else:
            try: conn.execute("UPDATE Grados SET nombre=? WHERE id=?",(n,id_grado)); conn.commit(); flash('Grado actualizado.','success'); return redirect(url_for('admin_gestionar_grados_page'))
            except sqlite3.IntegrityError: flash('Error: Nombre de grado ya existe.', 'danger')
            except Exception as e: flash(f'Error: {e}','danger'); traceback.print_exc()
        g_data=conn.execute("SELECT * FROM Grados WHERE id = ?",(id_grado,)).fetchone() # Recargar
        conn.close()
        return render_template('admin/formulario_grado.html',accion="Editar",grado=g_data)
    
    g_data=conn.execute("SELECT * FROM Grados WHERE id = ?",(id_grado,)).fetchone()
    conn.close()
    if not g_data: flash('Grado no encontrado.','danger'); return redirect(url_for('admin_gestionar_grados_page'))
    return render_template('admin/formulario_grado.html',accion="Editar",grado=g_data)

@app.route('/admin/grados/eliminar/<int:id_grado>', methods=['POST'])
@admin_required
def admin_eliminar_grado_page(id_grado):
    conn=database.get_db_connection()
    try: conn.execute("DELETE FROM Grados WHERE id = ?",(id_grado,)); conn.commit(); flash('Grado eliminado.','success')
    except sqlite3.IntegrityError as e: flash(f'Error: {e}. Puede tener grupos.','danger')
    except Exception as e: flash(f'Error: {e}.','danger')
    finally: conn.close()
    return redirect(url_for('admin_gestionar_grados_page'))

@app.route('/admin/grupos')
@admin_required
def admin_gestionar_grupos_page(): return render_template('admin/gestionar_grupos.html', grupos=database.get_grupos())

@app.route('/admin/grupos/agregar', methods=['GET','POST'])
@admin_required
def admin_agregar_grupo_page():
    grados_data=database.get_grados()
    if request.method=='POST':
        n=request.form.get('nombre_grupo',"").strip(); id_g_str=request.form.get('id_grado')
        if not n or not id_g_str: flash("Nombre y grado requeridos.","warning")
        else:
            try: 
                if database.add_grupo(n,int(id_g_str)): flash('Grupo agregado.','success'); return redirect(url_for('admin_gestionar_grupos_page'))
                else: flash('Error al agregar grupo (posible duplicado).','danger')
            except ValueError: flash('ID de grado no válido.','danger')
            except Exception as e: flash(f'Error: {e}','danger'); traceback.print_exc()
        return render_template('admin/formulario_grupo.html',accion="Agregar",grupo_form=request.form,grados=grados_data)
    return render_template('admin/formulario_grupo.html',accion="Agregar",grupo_form=None,grados=grados_data)

@app.route('/admin/grupos/editar/<int:id_grupo>', methods=['GET','POST'])
@admin_required
def admin_editar_grupo_page(id_grupo):
    grados_data=database.get_grados(); conn=database.get_db_connection()
    if request.method=='POST':
        n=request.form.get('nombre_grupo',"").strip(); id_g_str=request.form.get('id_grado')
        if not n or not id_g_str: flash("Nombre y grado requeridos.","warning")
        else:
            try: conn.execute("UPDATE Grupos SET nombre=?, grado_id=? WHERE id=?",(n,int(id_g_str),id_grupo)); conn.commit(); flash('Grupo actualizado.','success'); return redirect(url_for('admin_gestionar_grupos_page'))
            except ValueError: flash('ID de grado no válido.','danger')
            except sqlite3.IntegrityError: flash('Error: Combinación nombre-grado ya existe.','danger')
            except Exception as e: flash(f'Error: {e}','danger'); traceback.print_exc()
        # Renombrar la variable que se pasa a la plantilla a 'grupo_form' para consistencia
        grupo_data_reloaded=conn.execute("SELECT G.*, GR.nombre as nombre_grado FROM Grupos G JOIN Grados GR ON G.grado_id=GR.id WHERE G.id=?",(id_grupo,)).fetchone()
        conn.close()
        return render_template('admin/formulario_grupo.html',accion="Editar",grupo_form=dict(grupo_data_reloaded) if grupo_data_reloaded else None,grados=grados_data,grupo_id_edit=id_grupo)
    
    grp_data=conn.execute("SELECT G.*, GR.nombre as nombre_grado FROM Grupos G JOIN Grados GR ON G.grado_id=GR.id WHERE G.id=?",(id_grupo,)).fetchone(); conn.close()
    if not grp_data: flash('Grupo no encontrado.','danger'); return redirect(url_for('admin_gestionar_grupos_page'))
    return render_template('admin/formulario_grupo.html',accion="Editar",grupo_form=dict(grp_data),grados=grados_data,grupo_id_edit=id_grupo)

@app.route('/admin/grupos/eliminar/<int:id_grupo>', methods=['POST'])
@admin_required
def admin_eliminar_grupo_page(id_grupo):
    conn=database.get_db_connection()
    try: conn.execute("DELETE FROM Grupos WHERE id = ?",(id_grupo,)); conn.commit(); flash('Grupo eliminado.','success')
    except sqlite3.IntegrityError as e: flash(f'Error: {e}. Puede tener alumnos/clases.','danger')
    except Exception as e: flash(f'Error: {e}.','danger')
    finally: conn.close()
    return redirect(url_for('admin_gestionar_grupos_page'))

# --- GESTIÓN DE CLASES (NUEVO SISTEMA ASISTENCIA) ---
@app.route('/admin/gestionar_clases_asistencia', methods=['GET', 'POST'])
@admin_required
def gestionar_clases_asistencia():
    if request.method == 'POST':
        m_id=request.form.get('materia_id'); ma_id=request.form.get('maestro_id'); g_id=request.form.get('grupo_id')
        h=request.form.get('horario',"").strip(); ce=request.form.get('ciclo_escolar',"").strip()
        if not all([m_id,ma_id,g_id,ce,h]): flash("Todos los campos son requeridos.", "warning")
        else:
            try:
                conn_t=database.get_db_connection(); g_info=conn_t.execute("SELECT grado_id FROM Grupos WHERE id=?",(int(g_id),)).fetchone(); conn_t.close()
                if not g_info: flash("Grupo no válido.", "danger")
                else:
                    if database.add_clase(int(m_id),int(ma_id),int(g_id),g_info['grado_id'],h,ce):
                        flash('Clase creada.', 'success'); return redirect(url_for('gestionar_clases_asistencia'))
                    else: flash('Error al crear clase (verifique consola).', 'danger')
            except ValueError: flash("IDs de materia, maestro o grupo son inválidos.", "danger")
            except Exception as e: flash(f"Error al crear clase: {e}", "danger"); traceback.print_exc()
        # Repopular el formulario en caso de error (pasando los datos que el admin ya había llenado)
        return render_template('admin/gestionar_clases_asistencia.html', 
                               materias=database.get_materias(), maestros=database.get_maestros(), 
                               grupos=database.get_grupos(), clases_existentes=database.get_clases(),
                               form_data=request.form) # Pasar form_data para repoblar
                               
    return render_template('admin/gestionar_clases_asistencia.html', materias=database.get_materias(), maestros=database.get_maestros(), 
                           grupos=database.get_grupos(), clases_existentes=database.get_clases(), form_data=None)

@app.route('/admin/clases_asistencia/eliminar/<int:clase_id>', methods=['POST'])
@admin_required
def admin_eliminar_clase_asistencia(clase_id):
    if database.delete_clase(clase_id): flash('Clase eliminada (con inscripciones y asistencias).', 'success')
    else: flash('Error al eliminar la clase (verifique consola).', 'danger')
    return redirect(url_for('gestionar_clases_asistencia'))

@app.route('/admin/clase_asistencia/<int:clase_id>/inscribir_alumnos', methods=['GET', 'POST'])
@admin_required
def inscribir_alumnos_clase_asistencia(clase_id):
    clase_info = database.get_clase_by_id(clase_id)
    if not clase_info: flash("Clase no encontrada.", "danger"); return redirect(url_for('gestionar_clases_asistencia'))
    if request.method == 'POST':
        sel_ids=[int(id_s) for id_s in request.form.getlist('alumno_ids')]; conn=database.get_db_connection()
        try:
            conn.execute('DELETE FROM Clases_Alumnos WHERE clase_id = ?', (clase_id,)) 
            if sel_ids: 
                for aid_i in sel_ids: conn.execute('INSERT INTO Clases_Alumnos (clase_id,alumno_id) VALUES (?,?)',(clase_id,aid_i))
            conn.commit(); flash(f"Inscripciones actualizadas para '{clase_info['materia_nombre']}'.", "success")
        except sqlite3.Error as e: flash(f"Error al actualizar inscripciones: {e}", "danger"); traceback.print_exc(); conn.rollback()
        finally: conn.close()
        return redirect(url_for('inscribir_alumnos_clase_asistencia', clase_id=clase_id))
    return render_template('admin/inscribir_alumnos_clase_asistencia.html', clase_info=clase_info, 
                           todos_los_alumnos=database.get_alumnos(), alumnos_ya_inscritos_ids=database.get_alumnos_inscritos_clase_ids(clase_id), clase_id=clase_id)

# --- GESTIÓN DE JUSTIFICANTES ---
@app.route('/alumno/justificante/subir', methods=['POST'])
@alumno_required
def alumno_subir_justificante():
    fi=request.form.get('fecha_inasistencia_inicio'); ff=request.form.get('fecha_inasistencia_fin')
    cid_str=request.form.get('clase_id_justificante'); mot=request.form.get('motivo_justificante',"").strip()
    arch=request.files.get('archivo_justificante')
    if not fi or not ff or not mot: flash('Fechas y motivo requeridos.', 'warning'); return redirect(url_for('dashboard_alumno'))
    cid_j=int(cid_str) if cid_str and cid_str.isdigit() else None; al_id=session.get('user_id'); arch_path=None
    if arch and arch.filename!='':
        if allowed_file_justificante(arch.filename):
            fn_seg=secure_filename(arch.filename); ts=datetime.now().strftime("%Y%m%d%H%M%S%f")
            uniq_fn=f"justif_{al_id}_{ts}_{fn_seg}"; path_c=os.path.join(app.config['UPLOAD_FOLDER_JUSTIFICANTES'],uniq_fn)
            try: arch.save(path_c); arch_path=uniq_fn
            except Exception as e: flash(f"Error al guardar archivo: {e}","danger"); traceback.print_exc(); return redirect(url_for('dashboard_alumno'))
        else: flash('Tipo de archivo no permitido.','warning'); return redirect(url_for('dashboard_alumno'))
    if database.add_justificante(al_id,fi,ff,mot,arch_path,cid_j): flash('Justificante enviado.','success')
    else: flash("Error al enviar justificante.","danger")
    return redirect(url_for('dashboard_alumno'))

@app.route('/admin/justificantes')
@admin_required 
def admin_gestionar_justificantes(): return render_template('admin/gestionar_justificantes.html', justificantes=database.get_all_justificantes())
@app.route('/admin/justificante/<int:id_justificante>/actualizar_estado', methods=['POST'])
@admin_required 
def admin_actualizar_estado_justificante(id_justificante):
    ne=request.form.get('estado')
    if ne not in ['Aprobado','Rechazado','Pendiente']: flash("Estado no válido.","danger")
    elif database.update_justificante_estado(id_justificante,ne): flash("Estado de justificante actualizado.","success")
    else: flash("Error al actualizar estado.","danger")
    return redirect(url_for('admin_gestionar_justificantes'))

# --- RUTAS ORIGINALES (COEXISTENCIA Y REFERENCIA) ---
@app.route('/login_original_form', methods=['GET', 'POST']) 
def login_unificado_original_form(): 
    if request.method == 'POST':
        identificador = request.form.get('identificador_orig') 
        password_form = request.form.get('password_orig')
        if not identificador or not password_form:
            flash('Ingresa identificador y contraseña (login original).', 'warning')
            return render_template('login_original_form.html') 
        admin_user_orig = database.get_maestro_by_usuario_original(identificador) 
        if admin_user_orig and check_password_hash(admin_user_orig['password'], password_form):
            flash(f'Login original como {admin_user_orig["rol"]}: {admin_user_orig["nombre"]}.', 'info')
            if admin_user_orig['rol'] == 'admin': return redirect(url_for('dashboard_admin_original'))
            else: return redirect(url_for('dashboard_maestro_original'))
        alumno_orig = database.get_alumno_by_matricula_original(identificador) 
        if alumno_orig and check_password_hash(alumno_orig['password'], password_form):
            flash(f"Login original como alumno: {alumno_orig['nombre']}.", 'info')
            return redirect(url_for('dashboard_alumno_original'))
        flash('Identificador o contraseña incorrecta (login original).', 'danger')
    return render_template('login_original_form.html', title="Login Sistema Anterior") 

@app.route('/dashboard_admin_original')
def dashboard_admin_original(): return "Dashboard Admin (Sistema Original) - Contenido original aquí" 
@app.route('/dashboard_maestro_original')
def dashboard_maestro_original(): return "Dashboard Maestro (Sistema Original) - Contenido original aquí"
@app.route('/dashboard_alumno_original')
def dashboard_alumno_original(): return "Dashboard Alumno (Sistema Original) - Contenido original aquí"

@app.route('/admin/vista_general_original') 
@admin_required 
def admin_vista_general_original():
    conn = database.get_db_connection(); lista_maestros_admins_orig = []; lista_alumnos_orig = []      
    try:
        lista_maestros_admins_orig = conn.execute("SELECT id, nombre, usuario, rol FROM Maestros ORDER BY rol, nombre").fetchall()
        lista_alumnos_orig = conn.execute("""
            SELECT a.id, a.nombre, a.matricula, COALESCE(g.nombre || ' (' || gr.nombre || ')', 'Sin grupo') as nombre_grupo_completo
            FROM Alumnos a LEFT JOIN Grupos g ON a.grupo_id = g.id LEFT JOIN Grados gr ON g.grado_id = gr.id 
            ORDER BY a.nombre""").fetchall()
    except Exception as e: flash(f"Error: {str(e)}", "danger"); traceback.print_exc()
    finally: conn.close()
    return render_template('admin/vista_general_usuarios_original.html', maestros_admins=lista_maestros_admins_orig,
                           alumnos=lista_alumnos_orig, nombre_usuario=session.get('user_name'))

@app.route('/admin/alumnos_originales') 
@admin_required 
def admin_gestionar_alumnos_originales():
    conn = database.get_db_connection(); alumnos = []
    try:
        alumnos = conn.execute("""SELECT a.id, a.nombre, a.matricula, grp.nombre as nombre_grupo, g.nombre as nombre_grado
            FROM Alumnos a LEFT JOIN Grupos grp ON a.grupo_id=grp.id LEFT JOIN Grados g ON grp.grado_id=g.id ORDER BY a.nombre""").fetchall()
    except Exception as e: flash(f"Error: {e}", "danger")
    finally: conn.close()
    return render_template('admin/admin_gestionar_alumnos_original.html', alumnos=alumnos)

@app.route('/admin/alumnos_originales/agregar', methods=['GET', 'POST'])
@admin_required 
def admin_agregar_alumno_original():
    grados = database.obtener_grados_para_form(); grupos = database.obtener_grupos_para_form()
    if request.method == 'POST':
        nombre=request.form.get('nombre'); ap=request.form.get('apellido_paterno'); am=request.form.get('apellido_materno')
        fn=request.form.get('fecha_nacimiento'); curp=request.form.get('curp'); dire=request.form.get('direccion')
        tel=request.form.get('telefono'); id_g_f=request.form.get('id_grupo') 
        mat_f=request.form.get('nombre_usuario'); pwd=request.form.get('contrasena'); conf_pwd=request.form.get('confirmar_contrasena')
        if not all([nombre,ap,fn,curp,dire,tel,id_g_f,mat_f,pwd,conf_pwd]): flash('Todos los campos son obligatorios.', 'danger')
        elif pwd!=conf_pwd: flash('Las contraseñas no coinciden.', 'danger')
        else:
            if database.crear_alumno_original(nombre,ap,am,fn,curp,dire,tel,int(id_g_f),mat_f,generate_password_hash(pwd)):
                flash('Alumno (original) agregado.', 'success'); return redirect(url_for('admin_gestionar_alumnos_originales'))
            else: flash('Error al agregar alumno (original).', 'danger')
        return render_template('admin/admin_formulario_alumno_original.html', grados=grados, grupos=grupos, alumno=request.form, action='agregar')
    return render_template('admin/admin_formulario_alumno_original.html', grados=grados, grupos=grupos, action='agregar', alumno=None)

@app.route('/admin/asignaciones_originales') 
@admin_required
def admin_gestionar_asignaciones_originales():
    conn = database.get_db_connection(); asignaciones = []
    try:
        asignaciones = conn.execute("""
            SELECT a.id, m.nombre m_n, ma.nombre ma_n, grp.nombre grp_n, g.nombre g_n, a.ciclo_escolar ce
            FROM Maestros_Materias_Grupos a JOIN Materias m ON a.materia_id=m.id JOIN Maestros ma ON a.maestro_id=ma.id 
            JOIN Grupos grp ON a.grupo_id=grp.id JOIN Grados g ON grp.grado_id=g.id 
            ORDER BY g.nombre, grp.nombre, m.nombre """).fetchall()
    except Exception as e: flash(f"Error: {e}", "danger"); traceback.print_exc()
    finally: conn.close()
    return render_template('admin/gestionar_asignaciones_original.html', asignaciones=asignaciones) 

@app.route('/alumno/mis_calificaciones') 
@alumno_required
def alumno_mis_calificaciones():
    flash("Funcionalidad 'Mis Calificaciones' aún no implementada.", "info")
    return render_template('alumnos/mis_calificaciones.html', calificaciones=[], nombre_usuario=session.get('user_name'))

# --- Manejadores de errores ---
@app.errorhandler(404)
def page_not_found(e): 
    template_path = os.path.join(app.template_folder, 'error_404.html')
    if not os.path.exists(template_path): return "Error 404: Página no encontrada (plantilla error_404.html no existe).", 404
    return render_template('error_404.html',error=e,nombre_usuario=session.get('user_name')),404
@app.errorhandler(500)
def internal_server_error(e): 
    print("ERROR 500:"); traceback.print_exc()
    template_path = os.path.join(app.template_folder, 'error_500.html')
    if not os.path.exists(template_path): return "Error 500: Error interno (plantilla error_500.html no existe).", 500
    return render_template('error_500.html',error="Error interno.",nombre_usuario=session.get('user_name')),500

if __name__ == '__main__':
    print(f"INFO server.py: CWD: {os.getcwd()}")
    print(f"INFO server.py: BD: {database.DATABASE_NAME}")
    print("INFO: Iniciando Flask...")
    app.run(debug=True, port=5001)