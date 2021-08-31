import psycopg2

from config import DATABASE
from config import USER
from config import PASSWORD
from config import HOST


def create_connection():
    conn = None
    try:
        conn = psycopg2.connect(
            f"dbname={DATABASE} user={USER} password={PASSWORD} host={HOST}"
        )
    except (Exception, psycopg2.DatabaseError) as error:
        return print(f"Postgres has produced an error (startup) ~ {error}")
    return conn


def execute_sql(command):
    conn = create_connection()

    cur = conn.cursor()
    try:
        cur.execute(command)
    except (Exception, psycopg2.DatabaseError) as error:
        return print(f"Postgres has produced an error ({command}) ~ {error}")
    cur.close()
    conn.commit()


def query_sql(command, one=True):
    conn = create_connection()

    cur = conn.cursor()
    try:
        cur.execute(command)
    except (Exception, psycopg2.DatabaseError) as error:
        return print(f"Postgres has produced an error ({command}) ~ {error}")
    if one:
        data = cur.fetchone()
    else:
        data = cur.fetchall()
    cur.close()
    return data
