import sqlite3
from werkzeug.security import generate_password_hash # Asegúrate que esta importación esté

DATABASE_NAME = 'svag.db'

def get_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def crear_db():
    conn = get_db()
    cursor = conn.cursor()

    # Crear tabla maestros con columna 'rol'
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS maestros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            usuario TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL, -- Aquí se guardará el HASH de la contraseña
            rol TEXT NOT NULL DEFAULT 'maestro' -- Roles: 'maestro', 'admin'
        )
    ''')

    # Crear tabla alumnos con columna 'rol'
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alumnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            matricula TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL, -- Aquí se guardará el HASH de la contraseña
            maestro_id INTEGER, 
            rol TEXT NOT NULL DEFAULT 'alumno',
            FOREIGN KEY (maestro_id) REFERENCES maestros (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asistencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alumno_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT,
            estado TEXT NOT NULL,
            maestro_id INTEGER, 
            FOREIGN KEY (alumno_id) REFERENCES alumnos (id),
            FOREIGN KEY (maestro_id) REFERENCES maestros (id) 
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS justificantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alumno_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            motivo TEXT NOT NULL,
            archivo_path TEXT, 
            estado TEXT DEFAULT 'Pendiente',
            maestro_id INTEGER, 
            FOREIGN KEY (alumno_id) REFERENCES alumnos (id),
            FOREIGN KEY (maestro_id) REFERENCES maestros (id)
        )
    ''')

    # Insertar datos de prueba CON CONTRASEÑAS HASHEADAS
    try:
        # Administrador de prueba
        admin_pass_hash = generate_password_hash('adminpass')
        cursor.execute("INSERT OR IGNORE INTO maestros (nombre, usuario, password, rol) VALUES (?, ?, ?, ?)", 
                       ('Admin User', 'admin', admin_pass_hash, 'admin'))
        
        # Maestro de prueba normal
        maestro_pass_hash = generate_password_hash('1234')
        cursor.execute("INSERT OR IGNORE INTO maestros (nombre, usuario, password, rol) VALUES (?, ?, ?, ?)", 
                       ('Maestro Prueba', 'maestro1', maestro_pass_hash, 'maestro'))
        
        # Obtener el ID del maestro de prueba para ligar al alumno
        cursor.execute("SELECT id FROM maestros WHERE usuario = ?", ('maestro1',))
        maestro_row = cursor.fetchone()
        maestro_id_prueba = maestro_row['id'] if maestro_row else None

        # Alumno de prueba
        alumno_pass_hash = generate_password_hash('abcd')
        cursor.execute("INSERT OR IGNORE INTO alumnos (nombre, matricula, password, maestro_id, rol) VALUES (?, ?, ?, ?, ?)", 
                       ('Alumno Prueba', 'A001', alumno_pass_hash, maestro_id_prueba, 'alumno'))

    except sqlite3.Error as e:
        print(f"Error al insertar datos de prueba en crear_db: {e}")

    conn.commit()
    conn.close()
    print(f"Base de datos '{DATABASE_NAME}' verificada/creada. Usuarios de prueba insertados con contraseñas hasheadas.")

if __name__ == '__main__':
    print("Creando/Verificando la base de datos directamente desde database.py...")
    crear_db()
    print("Proceso de base de datos (ejecución directa de database.py) completado.")