import sqlite3
from werkzeug.security import generate_password_hash
import random # Para generar datos de prueba más variados
import os

DATABASE_NAME = 'svag_escolar.db'

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
    # Eliminar la base de datos anterior si existe para asegurar una creación limpia con los nuevos datos
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
            nombre TEXT NOT NULL, -- Ej: "A", "B"
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
    conn.commit() # Commit para asegurar que las tablas existan antes de insertar datos
    print("Tablas creadas exitosamente.")

    # --- INSERCIÓN DE DATOS DE PRUEBA ---
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
        grupos_por_grado_letras = ["A", "B"] # Letras para los grupos
        grupo_ids_general = [] # Lista de todos los IDs de grupo para asignar alumnos
        
        for nombre_grado_str, grado_id_val in grado_ids.items(): # nombre_grado_str es el nombre del grado, ej "1er Semestre"
            for letra_grupo in grupos_por_grado_letras:
                try:
                    cursor.execute("INSERT OR IGNORE INTO Grupos (grado_id, nombre) VALUES (?, ?)", (grado_id_val, letra_grupo))
                    conn.commit()
                    # Obtener el ID del grupo recién insertado o ya existente
                    cursor.execute("SELECT id FROM Grupos WHERE grado_id = ? AND nombre = ?", (grado_id_val, letra_grupo))
                    grupo_row = cursor.fetchone()
                    if grupo_row:
                        current_grupo_id = grupo_row['id']
                        # No necesitamos la estructura grupos_por_grado como antes, solo la lista general de IDs
                        grupo_ids_general.append(current_grupo_id)
                        print(f"Grupo procesado/insertado: Grado '{nombre_grado_str}' (ID: {grado_id_val}) - Grupo '{letra_grupo}', Grupo ID: {current_grupo_id}")
                    else:
                        print(f"ERROR: No se pudo obtener el ID para el grupo {letra_grupo} del grado {nombre_grado_str}")
                except sqlite3.Error as e_grupo:
                    print(f"Error al insertar grupo {letra_grupo} para grado ID {grado_id_val}: {e_grupo}")
        
        if not grupo_ids_general:
            print("ADVERTENCIA CRÍTICA: No se crearon grupos. La inserción de alumnos y asignaciones probablemente fallará o estará vacía.")
            # Considerar salir o manejar este error de forma más drástica si los grupos son esenciales.
        else:
            print(f"Grupos procesados. Total de IDs de grupo para alumnos: {len(grupo_ids_general)}")
        
        if not grupo_ids_general:
            print("ADVERTENCIA: No se crearon grupos, la inserción de alumnos fallará.")
            return


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
        print(f"Materias insertadas: {len(materia_ids)} materias.")


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
        print(f"Maestros insertados: {len(maestro_ids)} maestros.")
        if not maestro_ids:
            print("ADVERTENCIA: No se crearon maestros.")


        # Alumnos (aproximadamente 30 por grupo)
        print(f"Intentando generar alumnos para {len(grupo_ids_general)} grupos...")
        alumnos_por_grupo = 30
        matricula_counter = 2025000 # Iniciar contador de matrículas
        alumno_password_hash = generate_password_hash("alumno123")
        alumno_ids_por_grupo = {gid: [] for gid in grupo_ids_general}

        for grupo_id_val in grupo_ids_general:
            print(f"Generando alumnos para Grupo ID: {grupo_id_val}")
            for i in range(alumnos_por_grupo):
                genero = random.choice(["masculino", "femenino"])
                nombre_alumno = generar_nombre_completo(genero)
                matricula_alumno = f"A{matricula_counter}"
                matricula_counter += 1
                try:
                    cursor.execute("INSERT INTO Alumnos (nombre, matricula, password, grupo_id, rol) VALUES (?, ?, ?, ?, ?)",
                                   (nombre_alumno, matricula_alumno, alumno_password_hash, grupo_id_val, 'alumno'))
                    conn.commit()
                    alumno_ids_por_grupo[grupo_id_val].append(cursor.lastrowid)
                except sqlite3.IntegrityError: # En caso de colisión de matrícula (poco probable con este contador)
                    print(f"Error de integridad al insertar alumno con matrícula {matricula_alumno}, intentando con nueva matrícula.")
                    matricula_counter += 1 # Asegurar que la próxima sea diferente
                    matricula_alumno = f"A{matricula_counter}"
                    matricula_counter +=1
                    cursor.execute("INSERT OR IGNORE INTO Alumnos (nombre, matricula, password, grupo_id, rol) VALUES (?, ?, ?, ?, ?)",
                                   (nombre_alumno, matricula_alumno, alumno_password_hash, grupo_id_val, 'alumno'))
                    conn.commit()
                    if cursor.lastrowid:
                         alumno_ids_por_grupo[grupo_id_val].append(cursor.lastrowid)

            print(f"Grupo ID {grupo_id_val}: {len(alumno_ids_por_grupo[grupo_id_val])} alumnos insertados.")

        # Asignaciones Maestros-Materias-Grupos
        asignaciones_insertadas = 0
        list_maestro_keys = [k for k in maestro_ids.keys() if k != 'admin']
        list_materia_keys = list(materia_ids.keys())
        
        if list_maestro_keys and list_materia_keys and grupo_ids_general:
            for grupo_id_val in grupo_ids_general:
                # Asignar 2-3 materias diferentes a cada grupo con diferentes maestros
                materias_asignadas_a_grupo = random.sample(list_materia_keys, min(len(list_materia_keys), random.randint(2,4)))
                maestros_disponibles = list_maestro_keys[:] # Copia para poder remover

                for clave_materia in materias_asignadas_a_grupo:
                    if not maestros_disponibles: break # No más maestros para asignar
                    id_materia_actual = materia_ids[clave_materia]
                    
                    # Seleccionar un maestro que no haya sido asignado a esta materia en este grupo (lógica simplificada)
                    maestro_usuario_actual = random.choice(maestros_disponibles)
                    id_maestro_actual = maestro_ids[maestro_usuario_actual]
                    # maestros_disponibles.remove(maestro_usuario_actual) # Para evitar que el mismo maestro de todas las materias del grupo (opcional)

                    ciclo = "2025-A" # Ciclo escolar de ejemplo
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO Maestros_Materias_Grupos
                            (maestro_id, materia_id, grupo_id, ciclo_escolar)
                            VALUES (?, ?, ?, ?)
                        """, (id_maestro_actual, id_materia_actual, grupo_id_val, ciclo))
                        conn.commit()
                        if cursor.lastrowid:
                            asignaciones_insertadas += 1
                    except sqlite3.Error as e_asig:
                        print(f"Error al insertar asignación: {e_asig}")
            print(f"Asignaciones Maestros-Materias-Grupos insertadas: {asignaciones_insertadas}")
        else:
            print("ADVERTENCIA: No se pudieron crear asignaciones por falta de maestros, materias o grupos.")


        # Asistencias (algunas de ejemplo)
        cursor.execute("SELECT id FROM Maestros_Materias_Grupos")
        todas_las_asignaciones = cursor.fetchall()
        asistencias_insertadas = 0

        if todas_las_asignaciones and any(len(alumnos) > 0 for alumnos in alumno_ids_por_grupo.values()):
            fechas_ejemplo = ["2025-05-01", "2025-05-02", "2025-05-03", "2025-05-06", "2025-05-07"]
            estados_asistencia = ['Presente', 'Ausente', 'Retardo']
            
            for asignacion_row in random.sample(todas_las_asignaciones, min(len(todas_las_asignaciones), 5)): # Tomar 5 asignaciones al azar
                asignacion_id = asignacion_row['id']
                
                # Obtener grupo_id de la asignación para buscar alumnos de ese grupo
                cursor.execute("SELECT grupo_id FROM Maestros_Materias_Grupos WHERE id = ?", (asignacion_id,))
                grupo_de_asignacion_row = cursor.fetchone()
                if not grupo_de_asignacion_row: continue
                grupo_id_de_asignacion = grupo_de_asignacion_row['id'] # Corrección: debe ser grupo_de_asignacion_row['grupo_id']

                if grupo_id_de_asignacion in alumno_ids_por_grupo and alumno_ids_por_grupo[grupo_id_de_asignacion]:
                    alumnos_del_grupo = alumno_ids_por_grupo[grupo_id_de_asignacion]
                    for alumno_id_val in random.sample(alumnos_del_grupo, min(len(alumnos_del_grupo), 10)): # 10 alumnos al azar del grupo
                        for fecha in fechas_ejemplo:
                            estado = random.choice(estados_asistencia)
                            hora = f"{random.randint(7,18):02d}:{random.randint(0,59):02d}"
                            cursor.execute("""
                                INSERT OR IGNORE INTO Asistencias (alumno_id, asignacion_id, fecha, hora, estado)
                                VALUES (?, ?, ?, ?, ?)
                            """, (alumno_id_val, asignacion_id, fecha, hora, estado))
                            conn.commit()
                            if cursor.lastrowid: asistencias_insertadas +=1
            print(f"Asistencias de ejemplo insertadas: {asistencias_insertadas}")
        else:
            print("ADVERTENCIA: No se pudieron crear asistencias por falta de asignaciones o alumnos.")


    except sqlite3.Error as e:
        print(f"Error GENERAL durante la inserción de datos de prueba: {e}")
    except Exception as ex:
        print(f"Excepción inesperada durante la inserción de datos de prueba: {ex}")
    finally:
        conn.close()
        print(f"Base de datos '{DATABASE_NAME}' verificada/creada con el nuevo esquema escolar y datos de prueba masivos.")

if __name__ == '__main__':
    print(f"Creando/Verificando la base de datos '{DATABASE_NAME}' directamente desde database.py...")
    crear_db()
    print("Proceso de base de datos (ejecución directa de database.py) completado.")