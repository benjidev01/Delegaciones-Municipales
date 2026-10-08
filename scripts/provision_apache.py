"""Run as PostgreSQL OS user; receive private configuration through stdin."""
import json
import sys
import psycopg
from psycopg import sql

config = json.load(sys.stdin)
role, name = config['POSTGRES_USER'], config['POSTGRES_DB']
with psycopg.connect(dbname='postgres', host='/var/run/postgresql', autocommit=True) as conn:
    flags = conn.execute('SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=%s', (role,)).fetchone()
    if flags and any(flags):
        raise SystemExit('El usuario existente tiene privilegios excesivos; revisar.')
    if not flags:
        conn.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE').format(sql.Identifier(role), sql.Literal(config['POSTGRES_PASSWORD'])))
    owner = conn.execute('SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s', (name,)).fetchone()
    if owner and owner[0] != role:
        raise SystemExit('La base existente pertenece a otro usuario; no se modifica.')
    if not owner:
        conn.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(name), sql.Identifier(role)))
with psycopg.connect(dbname=name, host='/var/run/postgresql', autocommit=True) as conn:
    conn.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')
with psycopg.connect(dbname=name, user=role, password=config['POSTGRES_PASSWORD'], host='127.0.0.1'):
    pass
print('Base y usuario privado verificados.')
