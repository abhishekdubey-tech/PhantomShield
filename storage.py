"""SQLite locally; transactional PostgreSQL for serverless deployments."""
import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

class StorageConfigurationError(RuntimeError):
    pass

def database_url():
    return os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')

def postgres_sql(sql, params=()):
    """Translate this app's fixed, parameterized SQLite queries to psycopg syntax."""
    if isinstance(params, dict):
        return re.sub(r'(?<!:):([a-zA-Z_][a-zA-Z0-9_]*)', r'%(\1)s', sql)
    return sql.replace('?', '%s')

class PostgresConnection:
    def __init__(self, raw): self.raw = raw
    def execute(self, sql, params=()):
        return self.raw.execute(postgres_sql(sql, params), params)
    def executemany(self, sql, params):
        with self.raw.cursor() as cursor:
            cursor.executemany(postgres_sql(sql), params)
    def executescript(self, script):
        for statement in script.split(';'):
            if statement.strip(): self.raw.execute(statement)

@contextmanager
def open_database(local_path):
    url = database_url()
    if not url:
        if os.environ.get('VERCEL') == '1':
            raise StorageConfigurationError(
                'Persistent database not configured. Connect Neon/Postgres and set '
                'DATABASE_URL in Vercel, then redeploy. Local SQLite is only supported offline.')
        connection = sqlite3.connect(Path(local_path), timeout=15)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                # A single transaction owns a simulation step, including reads/correlation.
                connection.execute('BEGIN IMMEDIATE')
                yield connection
        finally: connection.close()
        return
    if not url.startswith(('postgres://', 'postgresql://')):
        raise StorageConfigurationError('DATABASE_URL must be a PostgreSQL connection string.')
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as error:
        raise StorageConfigurationError(
            'PostgreSQL driver missing. Install requirements.txt and redeploy.') from error
    # Transaction-scoped lock also works with pooled PostgreSQL connections.
    # Each demo mutation and its correlated records are atomic across function instances.
    with psycopg.connect(url, row_factory=dict_row, connect_timeout=10,
                         prepare_threshold=None) as connection:
        connection.execute("SET LOCAL statement_timeout = '15s'")
        connection.execute('SELECT pg_advisory_xact_lock(704228733)')
        connection.execute('CREATE SCHEMA IF NOT EXISTS phantomshield')
        connection.execute('SET LOCAL search_path TO phantomshield')
        yield PostgresConnection(connection)
