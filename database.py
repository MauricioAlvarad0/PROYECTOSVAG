import sqlite3

def crear_db():
    conn = sqlite3.connect('svag.db')
    cursor = conn.cursor()

    # Crear tabla de maestros
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS maestros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    # Crear tabla de alumnos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alumnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    # Crear tabla de asistencias
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asistencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alumno_id INTEGER,
            fecha TEXT,
            hora TEXT,
            estado TEXT,  -- asistencia, retardo, falta
            FOREIGN KEY(alumno_id) REFERENCES alumnos(id)
        )
    ''')

    # Crear tabla de justificantes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS justificantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alumno_id INTEGER,
            fecha TEXT,
            motivo TEXT,
            estado TEXT,  -- pendiente, aprobado, rechazado
            FOREIGN KEY(alumno_id) REFERENCES alumnos(id)
        )
    ''')

    # Insertar datos de prueba
    cursor.execute("INSERT OR IGNORE INTO maestros (usuario, password) VALUES (?, ?)", ('maestro1', '1234'))
    cursor.execute("INSERT OR IGNORE INTO alumnos (matricula, password) VALUES (?, ?)", ('A001', 'abcd'))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    crear_db()
