"""Provision a nonsuperuser application role; only this transient service sees admin secrets."""
import json
from pathlib import Path
import psycopg
from psycopg import sql

config = json.loads((Path(__file__).resolve().parent.parent / '.local/config.json').read_text())
with psycopg.connect(host='db', dbname='delegaciones', user='postgres',
                    password=Path('/run/db-admin/password.txt').read_text(), autocommit=True) as connection:
    with connection.cursor() as cursor:
        cursor.execute('SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=%s', ('delegaciones',))
        role = cursor.fetchone()
        if role is None:
            cursor.execute(sql.SQL('CREATE ROLE delegaciones LOGIN PASSWORD {}').format(sql.Literal(config['POSTGRES_PASSWORD'])))
        elif any(role):
            raise SystemExit('La cuenta de aplicación tiene privilegios administrativos inesperados. Revise sin borrar datos.')
        cursor.execute('ALTER DATABASE delegaciones OWNER TO delegaciones')
        cursor.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')
with psycopg.connect(host='db', dbname='delegaciones', user='delegaciones',
                    password=config['POSTGRES_PASSWORD']):
    pass
print('Cuenta de aplicación sin superusuario preparada y autenticación verificada.')
