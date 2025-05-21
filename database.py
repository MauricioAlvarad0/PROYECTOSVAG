import sqlite3
from werkzeug.security import generate_password_hash
import random # Para generar datos de prueba más variados
import os

# --- Definir la ruta absoluta a la base de datos ---
# Obtiene el directorio donde reside este archivo (database.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Define el nombre de la base de datos para que esté en el mismo directorio que database.py
DATABASE_NAME = os.path.join(BASE_DIR, 'svag_escolar.db')
# Ahora DATABASE_NAME será algo como /home/mauricio/PROYECTO/PROYECTOSVAG/svag_escolar.db
# --- Fin de la definición de ruta absoluta ---

# Listas para generar nombres y apellidos aleatorios
NOMBRES_MASCULINOS = [
    "José", "Luis", "Juan", "Carlos", "Miguel", "Ángel", "Jesús", "Antonio", "Francisco", "Pedro",
    "Alejandro", "Manuel", "Ricardo", "Fernando", "Jorge", "Alberto", "Raúl", "David", "Andrés", "Santiago",
    "Emiliano", "Sebastián", "Mateo", "Nicolás", "Daniel", "Samuel", "Diego", "Leonardo", "Gabriel", "Adrián"
]
NOMBRES_FEMENINOS = [
    "María", "Guadalupe", "Sofía", "Ana", "Laura", "Valentina", "Isabella", "Camila", "Valeria", "Mariana",
    "Gabriela", "Daniela", "Paula", "Renata", "Ximena", "Victoria", "Fernanda", "Juana", "Verónica", "Patricia",
    "Elena", "Marta", "Lucía", "Carmen", "Rosa", "Teresa", "Pilar", "Antonia", "Isabel", "Alejandra"
]
APELLIDOS = [
    "Hernández", "García", "Martínez", "López", "González", "Pérez", "Rodríguez", "Sánchez", "Ramírez", "Cruz",
    "Flores", "Gómez", "Morales", "Vázquez", "Jiménez", "Reyes", "Díaz", "Torres", "Ruiz", "Mendoza",
    "Aguilar", "Ortiz", "Moreno", "Castillo", "Romero", "Álvarez", "Chávez", "Rivera", "Juárez", "Domínguez"
]

def generar_nombre_completo(genero):
    if genero == "masculino":
        nombre1 = random.choice(NOMBRES_MASCULINOS)
        if random.random() < 0.4: # 40% de probabilidad de tener un segundo nombre
            nombre2 = random.choice(NOMBRES_MASCULINOS)
            while nombre2 == nombre1: # Evitar el mismo nombre dos veces
                nombre2 = random.choice(NOMBRES_MASCULINOS)
            nombre_completo = f"{nombre1} {nombre2}"
        else:
            nombre_completo = nombre1
    else: # femenino
        nombre1 = random.choice(NOMBRES_FEMENINOS)
        if random.random() < 0.4:
            nombre2 = random.choice(NOMBRES_FEMENINOS)
            while nombre2 == nombre1:
                nombre2 = random.choice(NOMBRES_FEMENINOS)
            nombre_completo = f"{nombre1} {nombre2}"
        else:
            nombre_completo = nombre1

    apellido1 = random.choice(APELLIDOS)
    apellido2 = random.choice(APELLIDOS)
    while apellido2 == apellido1 and len(APELLIDOS) > 1 : # Evitar el mismo apellido dos veces si es posible
        apellido2 = random.choice(APELLIDOS)
    return f"{nombre_completo} {apellido1} {apellido2}"

def get_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def crear_db():
    if os.path.exists(DATABASE_NAME):
        os.remove(DATABASE_NAME)
        print(f"Base de datos '{DATABASE_NAME}' anterior eliminada para recreación.")

    conn = get_db()
    cursor = conn.cursor()

    # --- TABLAS CATALOGO ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Grados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Grupos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grado_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            FOREIGN KEY (grado_id) REFERENCES Grados (id) ON DELETE CASCADE,
            UNIQUE (grado_id, nombre)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Materias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            clave_materia TEXT UNIQUE
        )
    ''')

    # --- TABLAS DE USUARIOS ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Maestros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            usuario TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'maestro' CHECK(rol IN ('maestro', 'admin'))
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Alumnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            matricula TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            grupo_id INTEGER,
            rol TEXT NOT NULL DEFAULT 'alumno' CHECK(rol = 'alumno'),
            FOREIGN KEY (grupo_id) REFERENCES Grupos (id) ON DELETE SET NULL
        )
    ''')

    # --- TABLA DE UNION / ASIGNACIONES ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Maestros_Materias_Grupos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            maestro_id INTEGER NOT NULL,
            materia_id INTEGER NOT NULL,
            grupo_id INTEGER NOT NULL,
            ciclo_escolar TEXT,
            FOREIGN KEY (maestro_id) REFERENCES Maestros (id) ON DELETE CASCADE,
            FOREIGN KEY (materia_id) REFERENCES Materias (id) ON DELETE CASCADE,
            FOREIGN KEY (grupo_id) REFERENCES Grupos (id) ON DELETE CASCADE,
            UNIQUE (maestro_id, materia_id, grupo_id, ciclo_escolar)
        )
    ''')

    # --- TABLAS DE REGISTROS ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Asistencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alumno_id INTEGER NOT NULL,
            asignacion_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT,
            estado TEXT NOT NULL CHECK(estado IN ('Presente', 'Ausente', 'Retardo', 'Justificado')),
            observaciones TEXT,
            FOREIGN KEY (alumno_id) REFERENCES Alumnos (id) ON DELETE CASCADE,
            FOREIGN KEY (asignacion_id) REFERENCES Maestros_Materias_Grupos (id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Justificantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alumno_id INTEGER NOT NULL,
            fecha_solicitud TEXT NOT NULL,
            fecha_inasistencia_inicio TEXT NOT NULL,
            fecha_inasistencia_fin TEXT NOT NULL,
            asignacion_id INTEGER,
            motivo TEXT NOT NULL,
            archivo_path TEXT,
            estado TEXT DEFAULT 'Pendiente' CHECK(estado IN ('Pendiente', 'Aprobado', 'Rechazado')),
            maestro_revisor_id INTEGER,
            fecha_revision TEXT,
            comentarios_revision TEXT,
            FOREIGN KEY (alumno_id) REFERENCES Alumnos (id) ON DELETE CASCADE,
            FOREIGN KEY (asignacion_id) REFERENCES Maestros_Materias_Grupos (id) ON DELETE SET NULL,
            FOREIGN KEY (maestro_revisor_id) REFERENCES Maestros (id) ON DELETE SET NULL
        )
    ''')
    conn.commit()
    print("Tablas creadas exitosamente.")

    print("Iniciando inserción de datos de prueba...")
    try:
        # Grados
        grados_data = ["1er Semestre", "2do Semestre", "3er Semestre", "4to Semestre"]
        grado_ids = {}
        for nombre_grado in grados_data:
            cursor.execute("INSERT OR IGNORE INTO Grados (nombre) VALUES (?)", (nombre_grado,))
            conn.commit()
            cursor.execute("SELECT id FROM Grados WHERE nombre = ?", (nombre_grado,))
            grado_row = cursor.fetchone()
            if grado_row:
                grado_ids[nombre_grado] = grado_row['id']
        print(f"Grados insertados: {grado_ids}")

        # Grupos
        print("Insertando Grupos...")
        grupos_por_grado_letras = ["A", "B"]
        grupo_ids_general = []
        for nombre_grado_str, grado_id_val in grado_ids.items():
            for letra_grupo in grupos_por_grado_letras:
                try:
                    cursor.execute("INSERT OR IGNORE INTO Grupos (grado_id, nombre) VALUES (?, ?)", (grado_id_val, letra_grupo))
                    conn.commit()
                    cursor.execute("SELECT id FROM Grupos WHERE grado_id = ? AND nombre = ?", (grado_id_val, letra_grupo))
                    grupo_row = cursor.fetchone()
                    if grupo_row:
                        current_grupo_id = grupo_row['id']
                        grupo_ids_general.append(current_grupo_id)
                        # print(f"Grupo procesado/insertado: Grado '{nombre_grado_str}' (ID: {grado_id_val}) - Grupo '{letra_grupo}', Grupo ID: {current_grupo_id}")
                    else:
                        print(f"ERROR: No se pudo obtener el ID para el grupo {letra_grupo} del grado {nombre_grado_str}")
                except sqlite3.Error as e_grupo:
                    print(f"Error al insertar grupo {letra_grupo} para grado ID {grado_id_val}: {e_grupo}")
        if not grupo_ids_general:
            print("ADVERTENCIA CRÍTICA: No se crearon grupos.")
        else:
            print(f"Grupos procesados. Total de IDs de grupo para alumnos: {len(grupo_ids_general)}. IDs: {grupo_ids_general}")
        if not grupo_ids_general:
            print("ADVERTENCIA: No se crearon grupos, la inserción de datos posteriores podría fallar.")
            # No retornamos aquí para que el resto de la inserción pueda intentarse o fallar explícitamente.

        # Materias
        materias_data = [
            ("Matemáticas Discretas", "MD101"), ("Cálculo Diferencial", "CD102"),
            ("Programación Estructurada", "PE103"), ("Fundamentos de Redes", "FR104"),
            ("Álgebra Lineal", "AL201"), ("Cálculo Integral", "CI202"),
            ("Programación Orientada a Objetos", "POO203"), ("Sistemas Operativos", "SO204"),
            ("Probabilidad y Estadística", "PYE301"),("Bases de Datos", "BD302"),
            ("Ingeniería de Software", "IS303"), ("Arquitectura de Computadoras", "AC304")
        ]
        materia_ids = {}
        for nombre_materia, clave_materia in materias_data:
            cursor.execute("INSERT OR IGNORE INTO Materias (nombre, clave_materia) VALUES (?, ?)", (nombre_materia, clave_materia))
            conn.commit()
            cursor.execute("SELECT id FROM Materias WHERE clave_materia = ?", (clave_materia,))
            materia_row = cursor.fetchone()
            if materia_row:
                 materia_ids[clave_materia] = materia_row['id']
        print(f"Materias insertadas: {len(materia_ids)} materias. Claves: {list(materia_ids.keys())}")

        # Maestros
        admin_pass_hash = generate_password_hash('adminpass')
        cursor.execute("INSERT OR IGNORE INTO Maestros (nombre, usuario, password, rol) VALUES (?, ?, ?, ?)",
                       ('Admin Principal', 'admin', admin_pass_hash, 'admin'))
        conn.commit()
        cursor.execute("SELECT id FROM Maestros WHERE usuario = 'admin'")
        admin_row = cursor.fetchone()
        id_admin = admin_row['id'] if admin_row else None

        maestros_data = [
            ("Dr. Alan Turing", "aturing", generate_password_hash("maestro1")),
            ("Dra. Grace Hopper", "ghopper", generate_password_hash("maestro2")),
            ("Ing. Tim Berners-Lee", "tlee", generate_password_hash("maestro3")),
            ("M.C. Ada Lovelace", "alovelace", generate_password_hash("maestro4"))
        ]
        maestro_ids = {}
        if id_admin: maestro_ids['admin'] = id_admin
        for nombre_maestro, user_maestro, pass_maestro in maestros_data:
            cursor.execute("INSERT OR IGNORE INTO Maestros (nombre, usuario, password, rol) VALUES (?, ?, ?, ?)",
                           (nombre_maestro, user_maestro, pass_maestro, 'maestro'))
            conn.commit()
            cursor.execute("SELECT id FROM Maestros WHERE usuario = ?", (user_maestro,))
            maestro_row = cursor.fetchone()
            if maestro_row:
                maestro_ids[user_maestro] = maestro_row['id']
        print(f"Maestros insertados: {len(maestro_ids)} maestros. Usuarios: {list(maestro_ids.keys())}")
        if not maestro_ids or (len(maestros_data) > 0 and len([k for k in maestro_ids if k != 'admin']) == 0) :
            print("ADVERTENCIA: No se crearon maestros de prueba (además del admin) o sus IDs no se recuperaron.")

        # Alumnos
        print(f"Intentando generar alumnos para {len(grupo_ids_general)} grupos...")
        alumnos_por_grupo_target = 30
        matricula_counter = 2025000
        alumno_password_hash = generate_password_hash("alumno123")
        alumno_ids_por_grupo = {gid: [] for gid in grupo_ids_general} # Asegura que todas las claves de grupo existen

        if grupo_ids_general:
            for grupo_id_val in grupo_ids_general:
                # print(f"Generando alumnos para Grupo ID: {grupo_id_val}") # Menos verboso
                alumnos_insertados_en_grupo = 0
                for i in range(alumnos_por_grupo_target):
                    genero = random.choice(["masculino", "femenino"])
                    nombre_alumno = generar_nombre_completo(genero)
                    matricula_alumno = f"A{matricula_counter}"
                    matricula_counter += 1
                    try:
                        cursor.execute("INSERT INTO Alumnos (nombre, matricula, password, grupo_id, rol) VALUES (?, ?, ?, ?, ?)",
                                       (nombre_alumno, matricula_alumno, alumno_password_hash, grupo_id_val, 'alumno'))
                        conn.commit()
                        last_id = cursor.lastrowid
                        if last_id:
                             # La clave grupo_id_val debe existir por la inicialización de alumno_ids_por_grupo
                            alumno_ids_por_grupo[grupo_id_val].append(last_id)
                            alumnos_insertados_en_grupo += 1
                    except sqlite3.IntegrityError:
                        # print(f"Error de integridad al insertar alumno con matrícula {matricula_alumno}, reintentando.") # Menos verboso
                        matricula_counter += random.randint(1,5)
                        matricula_alumno_new = f"A{matricula_counter}"
                        matricula_counter +=1
                        cursor.execute("INSERT OR IGNORE INTO Alumnos (nombre, matricula, password, grupo_id, rol) VALUES (?, ?, ?, ?, ?)",
                                       (nombre_alumno, matricula_alumno_new, alumno_password_hash, grupo_id_val, 'alumno'))
                        conn.commit()
                        last_id_retry = cursor.lastrowid
                        if last_id_retry:
                            alumno_ids_por_grupo[grupo_id_val].append(last_id_retry)
                            alumnos_insertados_en_grupo +=1
                print(f"Grupo ID {grupo_id_val}: {alumnos_insertados_en_grupo} alumnos insertados.")
        else:
            print("ADVERTENCIA: No hay grupos para generar alumnos.")


        # Asignaciones Maestros-Materias-Grupos
        print("DEBUG: Iniciando creación de Asignaciones Maestros-Materias-Grupos...")
        asignaciones_insertadas = 0
        # Excluir 'admin' de la lista de maestros disponibles para enseñar, a menos que quieras que también enseñe.
        list_maestro_keys_para_ensenar = [k for k in maestro_ids.keys() if k != 'admin' and maestro_ids[k] is not None]
        list_materia_keys = list(materia_ids.keys())
        
        print(f"DEBUG: Maestros disponibles para enseñar (claves): {list_maestro_keys_para_ensenar}")
        print(f"DEBUG: Materias disponibles (claves): {list_materia_keys}")
        print(f"DEBUG: Grupos disponibles (IDs): {grupo_ids_general}")

        if list_maestro_keys_para_ensenar and list_materia_keys and grupo_ids_general:
            for grupo_id_val in grupo_ids_general:
                materias_asignadas_a_grupo = random.sample(list_materia_keys, min(len(list_materia_keys), random.randint(2,4)))
                maestros_disponibles_para_grupo = list_maestro_keys_para_ensenar[:] 

                for clave_materia in materias_asignadas_a_grupo:
                    if not maestros_disponibles_para_grupo:
                        print(f"DEBUG: No más maestros disponibles para asignar a materia '{clave_materia}' en grupo {grupo_id_val}")
                        break 
                    
                    print(f"DEBUG: Intentando asignar materia con clave '{clave_materia}' en grupo {grupo_id_val}.")
                    if clave_materia not in materia_ids:
                        print(f"DEBUG ERROR: clave_materia '{clave_materia}' no encontrada en materia_ids. Saltando.")
                        continue
                    id_materia_actual = materia_ids[clave_materia]
                    
                    maestro_usuario_actual = random.choice(maestros_disponibles_para_grupo)
                    print(f"DEBUG: Maestro seleccionado (usuario): '{maestro_usuario_actual}'.")
                    if maestro_usuario_actual not in maestro_ids:
                        print(f"DEBUG ERROR: maestro_usuario_actual '{maestro_usuario_actual}' no encontrado en maestro_ids. Saltando.")
                        continue
                    id_maestro_actual = maestro_ids[maestro_usuario_actual]
                    
                    # Opcional: remover para que no de todas las materias el mismo maestro al mismo grupo
                    # try:
                    #     maestros_disponibles_para_grupo.remove(maestro_usuario_actual)
                    # except ValueError:
                    #     pass # Ya fue removido, no importa

                    ciclo = "2025-A"
                    try:
                        print(f"DEBUG: Insertando asignación MMG: MaestroID={id_maestro_actual}, MateriaID={id_materia_actual}, GrupoID={grupo_id_val}, Ciclo={ciclo}")
                        cursor.execute("""
                            INSERT OR IGNORE INTO Maestros_Materias_Grupos
                            (maestro_id, materia_id, grupo_id, ciclo_escolar)
                            VALUES (?, ?, ?, ?)
                        """, (id_maestro_actual, id_materia_actual, grupo_id_val, ciclo))
                        conn.commit()
                        if cursor.lastrowid:
                            asignaciones_insertadas += 1
                    except sqlite3.Error as e_asig:
                        print(f"Error al insertar asignación: MaestroID={id_maestro_actual}, MateriaID={id_materia_actual}, GrupoID={grupo_id_val}. Error: {e_asig}")
            print(f"Asignaciones Maestros-Materias-Grupos insertadas: {asignaciones_insertadas}")
        else:
            print("ADVERTENCIA: No se pudieron crear asignaciones por falta de maestros (no admin), materias o grupos.")


        # Asistencias (algunas de ejemplo)
        print("DEBUG: Iniciando creación de Asistencias...")
        cursor.execute("SELECT id FROM Maestros_Materias_Grupos")
        todas_las_asignaciones = cursor.fetchall()
        asistencias_insertadas = 0

        print(f"DEBUG: Total de asignaciones MMG encontradas para asistencias: {len(todas_las_asignaciones)}")
        # print(f"DEBUG: Contenido de alumno_ids_por_grupo para Asistencias: {alumno_ids_por_grupo}")


        if todas_las_asignaciones and any(len(alumnos) > 0 for alumnos in alumno_ids_por_grupo.values()):
            fechas_ejemplo = ["2025-05-01", "2025-05-02", "2025-05-03", "2025-05-06", "2025-05-07"]
            estados_asistencia = ['Presente', 'Ausente', 'Retardo']
            
            num_asignaciones_para_asistencia = min(len(todas_las_asignaciones), 5)
            if num_asignaciones_para_asistencia == 0 and len(todas_las_asignaciones) > 0: # Asegurar que se procese al menos una si hay
                 num_asignaciones_para_asistencia = 1
            
            print(f"DEBUG: Se tomarán {num_asignaciones_para_asistencia} asignaciones al azar para generar asistencias.")

            for asignacion_row in random.sample(todas_las_asignaciones, num_asignaciones_para_asistencia):
                asignacion_id = asignacion_row['id']
                print(f"DEBUG Asistencias: Procesando asignacion_id: {asignacion_id}")
                
                cursor.execute("SELECT grupo_id FROM Maestros_Materias_Grupos WHERE id = ?", (asignacion_id,))
                grupo_de_asignacion_row = cursor.fetchone()
                
                if not grupo_de_asignacion_row:
                    print(f"DEBUG Asistencias: No se encontró grupo_id para asignacion_id: {asignacion_id}. Saltando.")
                    continue
                
                grupo_id_de_asignacion = grupo_de_asignacion_row['grupo_id'] # Correcto
                print(f"DEBUG Asistencias: asignacion_id: {asignacion_id}, grupo_id_de_asignacion recuperado: {grupo_id_de_asignacion}")

                if grupo_id_de_asignacion in alumno_ids_por_grupo:
                    if alumno_ids_por_grupo[grupo_id_de_asignacion]:
                        alumnos_del_grupo = alumno_ids_por_grupo[grupo_id_de_asignacion]
                        print(f"DEBUG Asistencias: Grupo {grupo_id_de_asignacion} tiene {len(alumnos_del_grupo)} alumnos. Tomando muestra.")
                        
                        num_alumnos_para_asistencia = min(len(alumnos_del_grupo), 10)
                        if num_alumnos_para_asistencia == 0 and len(alumnos_del_grupo) > 0 :
                             num_alumnos_para_asistencia = 1
                        
                        if not alumnos_del_grupo: # Chequeo extra
                            print(f"DEBUG Asistencias: Lista de alumnos para grupo {grupo_id_de_asignacion} está vacía después de todo. Saltando.")
                            continue

                        for alumno_id_val in random.sample(alumnos_del_grupo, num_alumnos_para_asistencia):
                            for fecha in fechas_ejemplo:
                                estado = random.choice(estados_asistencia)
                                hora = f"{random.randint(7,18):02d}:{random.randint(0,59):02d}"
                                cursor.execute("""
                                    INSERT OR IGNORE INTO Asistencias (alumno_id, asignacion_id, fecha, hora, estado)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (alumno_id_val, asignacion_id, fecha, hora, estado))
                                conn.commit()
                                if cursor.lastrowid: asistencias_insertadas +=1
                    else:
                        print(f"DEBUG Asistencias: Grupo {grupo_id_de_asignacion} no tiene alumnos listados en alumno_ids_por_grupo[{grupo_id_de_asignacion}].")
                else:
                    print(f"DEBUG Asistencias ERROR: grupo_id_de_asignacion {grupo_id_de_asignacion} (de asignacion_id {asignacion_id}) NO ESTÁ en alumno_ids_por_grupo. Claves disponibles: {list(alumno_ids_por_grupo.keys())}")
            print(f"Asistencias de ejemplo insertadas: {asistencias_insertadas}")
        else:
            if not todas_las_asignaciones:
                 print("ADVERTENCIA: No se pudieron crear asistencias por falta de ASIGNACIONES.")
            if not any(len(alumnos) > 0 for alumnos in alumno_ids_por_grupo.values()):
                 print("ADVERTENCIA: No se pudieron crear asistencias por falta de ALUMNOS en los grupos.")

    except sqlite3.Error as e:
        print(f"Error GENERAL de SQLite durante la inserción de datos de prueba: {e}")
    except KeyError as ke:
        print(f"Excepción KeyError durante la inserción de datos de prueba: {ke}. Esto usualmente indica un problema al acceder a un diccionario con una clave inexistente.")
    except Exception as ex:
        # Imprimir el traceback completo para excepciones inesperadas
        import traceback
        print(f"Excepción INESPERADA durante la inserción de datos de prueba: {ex}")
        traceback.print_exc() # Esto dará más detalles de dónde ocurrió el error "No item with that key"
    finally:
        if conn: # Asegurarse de que la conexión se cierre
            conn.close()
        print(f"Proceso de creación/verificación de '{DATABASE_NAME}' completado (con o sin errores en datos de prueba).")

if __name__ == '__main__':
    print(f"Creando/Verificando la base de datos '{DATABASE_NAME}' directamente desde database.py...")
    crear_db()
    print("Proceso de base de datos (ejecución directa de database.py) finalizado.")