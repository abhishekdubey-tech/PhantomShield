import os
import sqlite3
import tempfile
import unittest
import json
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
from urllib.error import HTTPError
from pathlib import Path
from unittest.mock import patch

from storage import open_database, postgres_sql, StorageConfigurationError

class StorageTests(unittest.TestCase):
    def test_parameter_translation(self):
        self.assertEqual(postgres_sql('SELECT * FROM events WHERE session_id=?',('SES-1',)),
                         'SELECT * FROM events WHERE session_id=%s')
        self.assertEqual(postgres_sql('INSERT INTO events VALUES(:id,:resource)',{'id':'1','resource':'safe'}),
                         'INSERT INTO events VALUES(%(id)s,%(resource)s)')
        self.assertEqual(postgres_sql('SELECT value::text WHERE id=:id',{'id':'1'}),
                         'SELECT value::text WHERE id=%(id)s')

    def test_cloud_requires_persistent_database(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'VERCEL':'1','DATABASE_URL':'','POSTGRES_URL':''}):
            path=Path(folder)/'should-not-exist.db'
            with self.assertRaisesRegex(StorageConfigurationError,'DATABASE_URL'):
                with open_database(path): pass
            self.assertFalse(path.exists())

    def test_invalid_database_url_is_actionable(self):
        with patch.dict(os.environ,{'DATABASE_URL':'sqlite:///tmp/demo.db'}):
            with self.assertRaisesRegex(StorageConfigurationError,'PostgreSQL'):
                with open_database('unused.db'): pass

    def test_local_transactions_rollback_and_persist(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{'VERCEL':'','DATABASE_URL':'','POSTGRES_URL':''}):
            path=Path(folder)/'demo.db'
            with open_database(path) as c:c.execute('CREATE TABLE example(id INTEGER)')
            with self.assertRaises(ValueError):
                with open_database(path) as c:
                    c.execute('INSERT INTO example VALUES(?)',(1,)); raise ValueError('rollback')
            with open_database(path) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM example').fetchone()[0],0)
            with open_database(path) as c:c.execute('INSERT INTO example VALUES(?)',(2,))
            with open_database(path) as c:self.assertEqual(c.execute('SELECT id FROM example').fetchone()[0],2)

    def test_vercel_entrypoint_reports_missing_configuration(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
        command=('from http.server import ThreadingHTTPServer; from api.index import handler; '
                 f'ThreadingHTTPServer(("127.0.0.1",{port}),handler).serve_forever()')
        environment=dict(os.environ,VERCEL='1',DATABASE_URL='',POSTGRES_URL='')
        process=subprocess.Popen([sys.executable,'-c',command],cwd=Path(__file__).parent,
                                 env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for attempt in range(50):
                try:
                    with urlopen(f'http://127.0.0.1:{port}/api/health',timeout=1):
                        self.fail('Unconfigured Vercel function must not report healthy')
                except HTTPError as error:
                    self.assertEqual(error.code,503)
                    with error: result=json.load(error)
                    self.assertEqual(result['code'],'DATABASE_NOT_CONFIGURED')
                    self.assertIn('DATABASE_URL',result['error'])
                    return
                except OSError: time.sleep(.1)
            self.fail('Vercel function did not respond')
        finally:
            process.terminate(); process.wait()

if __name__=='__main__':unittest.main(verbosity=2)
