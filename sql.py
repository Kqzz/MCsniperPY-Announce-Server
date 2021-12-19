import sqlite3

conn = None


def create_connection():
    try:
        conn = sqlite3.connect(
            "main.db",
            check_same_thread=False
        )
    except Exception as error:
        return print(f"Sqlite has produced an error (startup) ~ {error}")
    return conn


def execute_sql(command, *parameters):

    cur = conn.cursor()
    try:
        cur.execute(command, parameters)
    except Exception as error:
        return print(f"Sqlite has produced an error ({command}) ~ {error}")
    cur.close()
    conn.commit()


def query_sql(command, one=True, *parameters):

    cur = conn.cursor()
    try:
        cur.execute(command, parameters)
    except Exception as error:
        return print(f"Sqlite has produced an error ({command}) ~ {error}")
    if one:
        data = cur.fetchone()
    else:
        data = cur.fetchall()
    cur.close()
    return data
