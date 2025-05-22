import sqlite3
from datetime import date, datetime 
import os
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_NAME = os.path.join(BASE_DIR, 'prodDomLot.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def create_tables_and_initialize():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE, -- Email puede ser NULL si el login es solo por matrícula para algunos
            password TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('administrador', 'maestro', 'alumno')),
            apellido_paterno TEXT,
            apellido_materno TEXT,
            fecha_nacimiento TEXT,
            curp TEXT UNIQUE,
            direccion TEXT,
            telefono TEXT,
            matricula TEXT UNIQUE, 
            usuario_login TEXT UNIQUE 
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Materias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            clave_materia TEXT UNIQUE,
            descripcion TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Grados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Grupos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            grado_id INTEGER NOT NULL,
            UNIQUE(nombre, grado_id),
            FOREIGN KEY(grado_id) REFERENCES Grados(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Clases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            materia_id INTEGER NOT NULL,
            maestro_id INTEGER NOT NULL, 
            grupo_id INTEGER NOT NULL,
            grado_id INTEGER NOT NULL, 
            horario TEXT, 
            ciclo_escolar TEXT,
            FOREIGN KEY(materia_id) REFERENCES Materias(id) ON DELETE CASCADE,
            FOREIGN KEY(maestro_id) REFERENCES Usuarios(id) ON DELETE CASCADE, 
            FOREIGN KEY(grupo_id) REFERENCES Grupos(id) ON DELETE CASCADE,
            FOREIGN KEY(grado_id) REFERENCES Grados(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Clases_Alumnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clase_id INTEGER NOT NULL,
            alumno_id INTEGER NOT NULL, 
            UNIQUE(clase_id, alumno_id), 
            FOREIGN KEY(clase_id) REFERENCES Clases(id) ON DELETE CASCADE,
            FOREIGN KEY(alumno_id) REFERENCES Usuarios(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Asistencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clase_id INTEGER NOT NULL,
            alumno_id INTEGER NOT NULL, 
            fecha TEXT NOT NULL, 
            estatus TEXT NOT NULL, 
            observaciones TEXT, 
            hora TEXT, 
            FOREIGN KEY(clase_id) REFERENCES Clases(id) ON DELETE CASCADE,
            FOREIGN KEY(alumno_id) REFERENCES Usuarios(id) ON DELETE CASCADE,
            UNIQUE(clase_id, alumno_id, fecha) 
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Justificantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alumno_id INTEGER NOT NULL, 
            fecha_solicitud TEXT NOT NULL, 
            fecha_inasistencia_inicio TEXT NOT NULL,
            fecha_inasistencia_fin TEXT NOT NULL,
            clase_id INTEGER, 
            motivo TEXT NOT NULL,
            archivo_path TEXT, 
            estado TEXT DEFAULT 'Pendiente' CHECK(estado IN ('Pendiente', 'Aprobado', 'Rechazado')),
            FOREIGN KEY(alumno_id) REFERENCES Usuarios(id) ON DELETE CASCADE,
            FOREIGN KEY(clase_id) REFERENCES Clases(id) ON DELETE SET NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Maestros ( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL, 
            password TEXT NOT NULL,
            rol TEXT CHECK(rol IN ('admin', 'maestro')) DEFAULT 'maestro'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Alumnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido_paterno TEXT,
            apellido_materno TEXT,
            fecha_nacimiento DATE,
            curp TEXT UNIQUE,
            direccion TEXT,
            telefono TEXT,
            grupo_id INTEGER, 
            matricula TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            FOREIGN KEY (grupo_id) REFERENCES Grupos(id) ON DELETE SET NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Maestros_Materias_Grupos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            maestro_id INTEGER, 
            materia_id INTEGER,
            grupo_id INTEGER,
            ciclo_escolar TEXT,
            FOREIGN KEY(maestro_id) REFERENCES Maestros(id) ON DELETE CASCADE,
            FOREIGN KEY(materia_id) REFERENCES Materias(id) ON DELETE CASCADE,
            FOREIGN KEY(grupo_id) REFERENCES Grupos(id) ON DELETE CASCADE, 
            UNIQUE(maestro_id, materia_id, grupo_id, ciclo_escolar)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Asistencias_Original ( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alumno_id INTEGER, 
            asignacion_id INTEGER, 
            fecha DATE,
            estado TEXT,
            observaciones TEXT,
            hora TIME,
            FOREIGN KEY (alumno_id) REFERENCES Alumnos(id) ON DELETE CASCADE,
            FOREIGN KEY (asignacion_id) REFERENCES Maestros_Materias_Grupos(id) ON DELETE CASCADE,
            UNIQUE (alumno_id, asignacion_id, fecha)
        )
    ''')

    conn.commit()
    conn.close()

def add_user(nombre, email, password_hash, tipo, apellido_paterno=None, apellido_materno=None, fecha_nacimiento=None, curp=None, direccion=None, telefono=None, matricula=None, usuario_login=None):
    conn = get_db_connection()
    try:
        conn.execute('''INSERT INTO Usuarios 
                        (nombre, email, password, tipo, apellido_paterno, apellido_materno, fecha_nacimiento, curp, direccion, telefono, matricula, usuario_login) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (nombre, email, password_hash, tipo, apellido_paterno, apellido_materno, fecha_nacimiento, curp, direccion, telefono, matricula, usuario_login))
        conn.commit()
        return True
    except sqlite3.IntegrityError as e: 
        print(f"Error de integridad al añadir usuario '{email if email else matricula}': {e}")
        return False
    finally:
        conn.close()

def update_user(user_id, nombre, email, tipo, apellido_paterno=None, apellido_materno=None, fecha_nacimiento=None, curp=None, direccion=None, telefono=None, matricula=None, usuario_login=None, password_hash=None):
    conn = get_db_connection()
    try:
        if password_hash:
            conn.execute('''UPDATE Usuarios SET
                            nombre=?, email=?, tipo=?, apellido_paterno=?, apellido_materno=?, fecha_nacimiento=?, 
                            curp=?, direccion=?, telefono=?, matricula=?, usuario_login=?, password=?
                            WHERE id=?''',
                         (nombre, email, tipo, apellido_paterno, apellido_materno, fecha_nacimiento, 
                          curp, direccion, telefono, matricula, usuario_login, password_hash, user_id))
        else:
            conn.execute('''UPDATE Usuarios SET
                            nombre=?, email=?, tipo=?, apellido_paterno=?, apellido_materno=?, fecha_nacimiento=?, 
                            curp=?, direccion=?, telefono=?, matricula=?, usuario_login=?
                            WHERE id=?''',
                         (nombre, email, tipo, apellido_paterno, apellido_materno, fecha_nacimiento, 
                          curp, direccion, telefono, matricula, usuario_login, user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError as e:
        print(f"Error de integridad al actualizar usuario ID {user_id}: {e}")
        return False
    except sqlite3.Error as e:
        print(f"Error de BD al actualizar usuario ID {user_id}: {e}")
        return False
    finally:
        conn.close()

def delete_user(user_id):
    conn = get_db_connection()
    try:
        user_to_delete = get_user_by_id(user_id)
        if user_to_delete and user_to_delete['tipo'] == 'administrador':
            admins_count_row = conn.execute("SELECT COUNT(*) as count FROM Usuarios WHERE tipo = 'administrador'").fetchone()
            if admins_count_row and admins_count_row['count'] <= 1:
                print("Intento de eliminar al único administrador. Operación denegada.")
                return False 
        conn.execute('DELETE FROM Usuarios WHERE id = ?', (user_id,))
        conn.commit()
        return True
    except sqlite3.Error as e: 
        print(f"Error de BD al eliminar usuario ID {user_id}: {e}")
        return False
    finally:
        conn.close()

def get_user_by_email(email): # Busca en tabla Usuarios
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM Usuarios WHERE email = ?', (email,)).fetchone()
    conn.close()
    return user

def get_user_by_matricula(matricula): # Busca en tabla Usuarios
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM Usuarios WHERE matricula = ?', (matricula,)).fetchone()
    conn.close()
    return user

def get_user_by_id(user_id): # Busca en tabla Usuarios
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM Usuarios WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user

def get_alumnos(): 
    conn = get_db_connection()
    alumnos = conn.execute("SELECT id, nombre, email, matricula, curp FROM Usuarios WHERE tipo = 'alumno' ORDER BY nombre").fetchall()
    conn.close()
    return alumnos

def get_maestros(): 
    conn = get_db_connection()
    maestros = conn.execute("SELECT id, nombre, email FROM Usuarios WHERE tipo = 'maestro' OR tipo = 'administrador' ORDER BY nombre").fetchall()
    conn.close()
    return maestros

def add_materia(nombre, clave_materia=None, descripcion=None):
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO Materias (nombre, clave_materia, descripcion) VALUES (?, ?, ?)', 
                     (nombre, clave_materia, descripcion))
        conn.commit(); return True
    except sqlite3.IntegrityError as e: print(f"Error de integridad al añadir materia: {e}"); return False
    except sqlite3.Error as e: print(f"Error de BD al añadir materia: {e}"); return False
    finally: conn.close()

def get_materias():
    conn = get_db_connection(); materias = conn.execute('SELECT * FROM Materias ORDER BY nombre').fetchall(); conn.close(); return materias

def add_grado(nombre):
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO Grados (nombre) VALUES (?)', (nombre,)); conn.commit(); return True
    except sqlite3.IntegrityError as e: print(f"Error de integridad al añadir grado: {e}"); return False
    except sqlite3.Error as e: print(f"Error de BD al añadir grado: {e}"); return False
    finally: conn.close()

def get_grados():
    conn = get_db_connection(); grados = conn.execute('SELECT * FROM Grados ORDER BY nombre').fetchall(); conn.close(); return grados

def add_grupo(nombre, grado_id):
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO Grupos (nombre, grado_id) VALUES (?, ?)', (nombre, grado_id)); conn.commit(); return True
    except sqlite3.IntegrityError as e: print(f"Error de integridad al añadir grupo: {e}"); return False
    except sqlite3.Error as e: print(f"Error de BD al añadir grupo: {e}"); return False
    finally: conn.close()

def get_grupos(): 
    conn = get_db_connection()
    grupos = conn.execute('''
        SELECT GRP.id, GRP.nombre as nombre_grupo, GR.nombre as nombre_grado, GRP.grado_id
        FROM Grupos GRP JOIN Grados GR ON GRP.grado_id = GR.id
        ORDER BY GR.nombre, GRP.nombre
    ''').fetchall(); conn.close(); return grupos
    
def add_clase(materia_id, maestro_id, grupo_id, grado_id, horario, ciclo_escolar):
    conn = get_db_connection()
    try:
        conn.execute('''INSERT INTO Clases (materia_id, maestro_id, grupo_id, grado_id, horario, ciclo_escolar) 
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (materia_id, maestro_id, grupo_id, grado_id, horario, ciclo_escolar)); conn.commit(); return True
    except sqlite3.Error as e: print(f"Error al añadir clase: {e}"); return False
    finally: conn.close()

def delete_clase(clase_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM Clases WHERE id = ?', (clase_id,)); conn.commit(); return True
    except sqlite3.Error as e: print(f"Error de BD al eliminar clase ID {clase_id}: {e}"); return False
    finally: conn.close()

def get_clases(): 
    conn = get_db_connection()
    clases = conn.execute('''
        SELECT C.id, M.nombre AS materia_nombre, U.nombre AS maestro_nombre, 
               GRP.nombre AS grupo_nombre, GR.nombre as grado_nombre, C.horario, C.ciclo_escolar
        FROM Clases C
        JOIN Materias M ON C.materia_id = M.id JOIN Usuarios U ON C.maestro_id = U.id
        JOIN Grupos GRP ON C.grupo_id = GRP.id JOIN Grados GR ON C.grado_id = GR.id
        ORDER BY C.ciclo_escolar DESC, M.nombre, GR.nombre, GRP.nombre
    ''').fetchall(); conn.close(); return clases
    
def get_clase_by_id(clase_id):
    conn = get_db_connection()
    clase = conn.execute('''
        SELECT C.id, M.nombre AS materia_nombre, U.nombre AS maestro_nombre, 
               GRP.nombre AS grupo_nombre, GR.nombre as grado_nombre, C.horario, C.ciclo_escolar,
               C.materia_id, C.maestro_id, C.grupo_id, C.grado_id
        FROM Clases C
        JOIN Materias M ON C.materia_id = M.id JOIN Usuarios U ON C.maestro_id = U.id
        JOIN Grupos GRP ON C.grupo_id = GRP.id JOIN Grados GR ON C.grado_id = GR.id
        WHERE C.id = ?
    ''', (clase_id,)).fetchone(); conn.close(); return clase

def get_clases_por_maestro(maestro_id): 
    conn = get_db_connection()
    clases = conn.execute('''
        SELECT C.id, M.nombre AS materia_nombre, GRP.nombre AS grupo_nombre, GR.nombre as grado_nombre, C.horario, C.ciclo_escolar
        FROM Clases C
        JOIN Materias M ON C.materia_id = M.id JOIN Grupos GRP ON C.grupo_id = GRP.id
        JOIN Grados GR ON C.grado_id = GR.id
        WHERE C.maestro_id = ?
        ORDER BY C.ciclo_escolar DESC, M.nombre, GR.nombre, GRP.nombre
    ''', (maestro_id,)).fetchall(); conn.close(); return clases

def inscribir_alumno_a_clase(clase_id, alumno_id): 
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO Clases_Alumnos (clase_id, alumno_id) VALUES (?, ?)', (clase_id, alumno_id)); conn.commit(); return True
    except sqlite3.IntegrityError: print(f"Alumno {alumno_id} ya inscrito en clase {clase_id}."); return True 
    except sqlite3.Error as e: print(f"Error BD al inscribir alumno {alumno_id} a clase {clase_id}: {e}"); return False
    finally: conn.close()

def get_alumnos_inscritos_clase_ids(clase_id): 
    conn = get_db_connection()
    alumnos_ids = [row['alumno_id'] for row in conn.execute('SELECT alumno_id FROM Clases_Alumnos WHERE clase_id = ?', (clase_id,)).fetchall()]
    conn.close(); return alumnos_ids

def get_alumnos_por_clase(clase_id): 
    conn = get_db_connection()
    alumnos = conn.execute('''
        SELECT U.id, U.nombre, U.email, U.matricula
        FROM Usuarios U JOIN Clases_Alumnos CA ON U.id = CA.alumno_id
        WHERE CA.clase_id = ? AND U.tipo = 'alumno' ORDER BY U.nombre
    ''', (clase_id,)).fetchall(); conn.close(); return alumnos

def add_asistencia(clase_id, alumno_id, fecha, estatus, observaciones=None, hora=None):
    conn = get_db_connection()
    if hora is None: hora = datetime.now().strftime('%H:%M:%S')
    try:
        conn.execute('''
            INSERT INTO Asistencias (clase_id, alumno_id, fecha, estatus, observaciones, hora) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(clase_id, alumno_id, fecha) DO UPDATE SET estatus = excluded.estatus, 
            observaciones = excluded.observaciones, hora = excluded.hora
            ''', (clase_id, alumno_id, fecha, estatus, observaciones, hora)); conn.commit(); return True 
    except sqlite3.Error as e: print(f"Error BD al agregar/actualizar asistencia: {e}"); return False 
    finally: conn.close()

def get_asistencia_alumno_clase_fecha(alumno_id, clase_id, fecha):
    conn = get_db_connection()
    asistencia = conn.execute('SELECT * FROM Asistencias WHERE alumno_id = ? AND clase_id = ? AND fecha = ?', (alumno_id, clase_id, fecha)).fetchone()
    conn.close(); return asistencia

def get_clases_inscritas_con_estado_asistencia(alumno_id, fecha_str): 
    conn = get_db_connection(); clases_con_info = []
    try:
        clases_inscritas = conn.execute('''
            SELECT c.id as clase_id, m.nombre as materia_nombre, u_maestro.nombre as maestro_nombre, 
                   c.horario, c.ciclo_escolar, grp.nombre as grupo_nombre, gr.nombre as grado_nombre
            FROM Clases_Alumnos ca
            JOIN Clases c ON ca.clase_id = c.id JOIN Materias m ON c.materia_id = m.id
            JOIN Usuarios u_maestro ON c.maestro_id = u_maestro.id JOIN Grupos grp ON c.grupo_id = grp.id
            JOIN Grados gr ON c.grado_id = gr.id
            WHERE ca.alumno_id = ? AND (u_maestro.tipo = 'maestro' OR u_maestro.tipo = 'administrador')
        ''', (alumno_id,)).fetchall()
        for clase_base in clases_inscritas:
            asistencia_hoy = conn.execute('SELECT estatus FROM Asistencias WHERE alumno_id = ? AND clase_id = ? AND fecha = ?', 
                                          (alumno_id, clase_base['clase_id'], fecha_str)).fetchone()
            clase_dict = dict(clase_base); clase_dict['asistencia_hoy'] = asistencia_hoy['estatus'] if asistencia_hoy else None
            clases_con_info.append(clase_dict)
    except sqlite3.Error as e: print(f"Error BD en get_clases_inscritas_con_estado_asistencia: {e}")
    finally: conn.close()
    return clases_con_info

def is_alumno_inscrito_en_clase(alumno_id, clase_id): 
    conn = get_db_connection();
    try:
        result = conn.execute('SELECT 1 FROM Clases_Alumnos WHERE alumno_id = ? AND clase_id = ?', (alumno_id, clase_id)).fetchone()
        return result is not None
    except sqlite3.Error as e: print(f"Error BD en is_alumno_inscrito_en_clase: {e}"); return False
    finally: conn.close()

def add_justificante(alumno_id, fecha_inicio, fecha_fin, motivo, archivo_path=None, clase_id=None):
    conn = get_db_connection(); fecha_solicitud = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        conn.execute('''INSERT INTO Justificantes (alumno_id, fecha_solicitud, fecha_inasistencia_inicio, fecha_inasistencia_fin, clase_id, motivo, archivo_path, estado)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'Pendiente')''',
                     (alumno_id, fecha_solicitud, fecha_inicio, fecha_fin, clase_id, motivo, archivo_path)); conn.commit(); return True
    except sqlite3.Error as e: print(f"Error al añadir justificante: {e}"); return False
    finally: conn.close()

def get_all_justificantes():
    conn = get_db_connection()
    justificantes = conn.execute('''
        SELECT J.*, U.nombre as alumno_nombre, U.email as alumno_email, 
               C.id as id_clase_justificada, M.nombre as materia_clase_justificada
        FROM Justificantes J JOIN Usuarios U ON J.alumno_id = U.id
        LEFT JOIN Clases C ON J.clase_id = C.id LEFT JOIN Materias M ON C.materia_id = M.id 
        ORDER BY J.fecha_solicitud DESC
    ''').fetchall(); conn.close(); return justificantes

def update_justificante_estado(justificante_id, nuevo_estado):
    conn = get_db_connection();
    try:
        conn.execute("UPDATE Justificantes SET estado = ? WHERE id = ?", (nuevo_estado, justificante_id)); conn.commit(); return True
    except sqlite3.Error as e: print(f"Error al actualizar estado de justificante: {e}"); return False
    finally: conn.close()

def get_maestro_by_usuario_original(usuario): 
    conn = get_db_connection(); user = conn.execute("SELECT * FROM Maestros WHERE usuario = ?", (usuario,)).fetchone(); conn.close(); return user
def get_alumno_by_matricula_original(matricula): 
    conn = get_db_connection(); user = conn.execute("SELECT * FROM Alumnos WHERE matricula = ?", (matricula,)).fetchone(); conn.close(); return user

def crear_alumno_original(nombre, ap, am, fn, curp, direccion, tel, id_grupo_orig, matricula, hash_pass):
    conn = get_db_connection();
    try:
        conn.execute("INSERT INTO Alumnos (nombre, apellido_paterno, apellido_materno, fecha_nacimiento, curp, direccion, telefono, grupo_id, matricula, password) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                     (nombre, ap, am, fn, curp, direccion, tel, id_grupo_orig, matricula, hash_pass)); conn.commit(); return True
    except sqlite3.IntegrityError as e: print(f"Error integridad al crear alumno original: {e}"); return False
    except Exception as e: print(f"Error general crear alumno original: {e}"); return False
    finally: conn.close()

def obtener_alumno_por_id_admin_original(id_alumno): 
    conn = get_db_connection()
    alumno = conn.execute("SELECT a.*, g.grado_id as id_grado FROM Alumnos a LEFT JOIN Grupos g ON a.grupo_id = g.id WHERE a.id = ?", (id_alumno,)).fetchone()
    conn.close(); return alumno

def actualizar_alumno_admin_original(id_a, n, ap, am, fn, curp, d, t, id_g_o, mat, hash_p):
    conn = get_db_connection();
    try:
        conn.execute("UPDATE Alumnos SET nombre=?, apellido_paterno=?, apellido_materno=?, fecha_nacimiento=?, curp=?, direccion=?, telefono=?, grupo_id=?, matricula=?, password=? WHERE id=?", 
                     (n, ap, am, fn, curp, d, t, id_g_o, mat, hash_p, id_a)); conn.commit(); return True
    except sqlite3.Error as e: print(f"Error al actualizar alumno original: {e}"); return False
    finally: conn.close()
        
def obtener_grados_para_form(): return get_grados()
def obtener_grupos_para_form(): 
    conn = get_db_connection()
    grupos = conn.execute('''SELECT GRP.id, GRP.nombre || ' (' || GR.nombre || ')' as nombre_completo, GRP.grado_id
                             FROM Grupos GRP JOIN Grados GR ON GRP.grado_id = GR.id
                             ORDER BY GR.nombre, GRP.nombre''').fetchall()
    conn.close(); return grupos

if __name__ == '__main__':
    print(f"Ejecutando database.py para crear/verificar tablas en {DATABASE_NAME}...")
    create_tables_and_initialize()
    print("Proceso de base de datos completado.")
    conn_main = get_db_connection()
    try:
        admin_default_usuarios = conn_main.execute("SELECT * FROM Usuarios WHERE email = 'admin@sistema.com'").fetchone()
        if not admin_default_usuarios:
            conn_main.execute("INSERT INTO Usuarios (nombre, email, password, tipo) VALUES (?, ?, ?, ?)",
                             ('Admin Principal', 'admin@sistema.com', generate_password_hash('admin123'), 'administrador'))
            conn_main.commit(); print("Admin por defecto 'admin@sistema.com' CREADO en Usuarios.")
        else: print("Admin por defecto 'admin@sistema.com' YA EXISTE en Usuarios.")
        # Opcional: Admin en tabla original Maestros
        admin_original_maestros = conn_main.execute("SELECT * FROM Maestros WHERE usuario = 'admin'").fetchone()
        if not admin_original_maestros:
            conn_main.execute("INSERT INTO Maestros (nombre, usuario, password, rol) VALUES (?, ?, ?, ?)",
                              ('Admin Original', 'admin', generate_password_hash('admin'), 'admin'))
            conn_main.commit(); print("Admin 'admin' CREADO en tabla Maestros (original).")
        else: print("Admin 'admin' YA EXISTE en tabla Maestros (original).")
    except sqlite3.Error as e: print(f"Error al verificar/crear admin(s) por defecto: {e}")
    finally:
        if conn_main: conn_main.close()