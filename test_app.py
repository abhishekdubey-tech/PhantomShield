"""Acceptance checks against the real HTTP API and a temporary SQLite database."""
import json, os, socket, subprocess, sys, tempfile, time, unittest
from pathlib import Path
from urllib.request import Request, urlopen

class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        with socket.socket() as s: s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
        cls.url=f'http://127.0.0.1:{port}'
        cls.process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('server.py')),'--port',str(port)],env=dict(os.environ,PHANTOM_DB=str(Path(cls.tmp.name)/'test.db')),stdout=subprocess.DEVNULL)
        for _ in range(60):
            try: cls.req('state'); return
            except Exception: time.sleep(.1)
        raise RuntimeError('Server did not start')
    @classmethod
    def tearDownClass(cls): cls.process.terminate(); cls.process.wait(); cls.tmp.cleanup()
    @classmethod
    def req(cls,path,data=None,method='POST'):
        req=Request(cls.url+'/api/'+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'},method=method if data is not None else 'GET')
        with urlopen(req) as r:return json.load(r)
    def setUp(self): self.req('simulations/reset',{})
    def test_manual_decoy_credentials_and_escalation(self):
        e=self.req('interactions',{'asset_id':1}); self.assertEqual(e['severity'],'medium')
        c=self.req('interactions',{'asset_id':4,'session_id':e['session_id']}); self.assertEqual(c['severity'],'high')
        x=self.req('interactions',{'asset_id':8,'session_id':e['session_id']}); self.assertEqual(x['severity'],'critical')
        st=self.req('dashboard');self.assertEqual(len(st['events']),3);self.assertEqual(len(st['incidents']),1)
        self.assertEqual(len({e['session_id'] for e in st['events']}),1)
    def test_multistage_pause_status_report_and_reset(self):
        s=self.req('simulations/start',{'scenario':'multi'}); sid=s['id']
        self.req('simulations/step',{'session_id':sid});self.req('simulations/pause',{'session_id':sid})
        self.assertEqual(self.req('state')['sessions'][0]['status'],'paused')
        self.req('simulations/resume',{'session_id':sid})
        for _ in range(4):self.req('simulations/step',{'session_id':sid})
        st=self.req('state');self.assertEqual(len(st['events']),5);self.assertEqual(st['sessions'][0]['status'],'complete')
        self.assertEqual(st['incidents'][0]['severity'],'critical')
        self.assertEqual([e['timestamp'] for e in st['events']],sorted(e['timestamp'] for e in st['events']))
        self.assertIn('Database Server',{e['target_node'] for e in st['events']})
        alert=st['alerts'][0];self.req('alerts/'+alert['id'],{'status':'acknowledged'},'PATCH')
        self.assertEqual(self.req('alerts')[0]['status'],'acknowledged')
        self.req('alerts/'+alert['id'],{'status':'resolved'},'PATCH');self.assertEqual(self.req('alerts')[0]['status'],'resolved')
        report=self.req('reports/'+st['incidents'][0]['id']);self.assertEqual(report['events'],st['events']);self.assertEqual(len(report['decoys']),4)
        self.req('simulations/reset',{});self.assertEqual(self.req('events'),[]);self.assertEqual(self.req('incidents'),[])
    def test_other_scenarios_and_correlation(self):
        for scenario in ['file','credential']:
            self.req('simulations/reset',{});s=self.req('simulations/start',{'scenario':scenario})
            for _ in range(3):self.req('simulations/step',{'session_id':s['id']})
            st=self.req('state');self.assertEqual(len(st['events']),3);self.assertTrue(st['alerts'])
        self.req('simulations/reset',{});e=self.req('interactions',{'asset_id':0});e=self.req('interactions',{'asset_id':1,'session_id':e['session_id']})
        self.assertEqual(e['severity'],'high');self.assertTrue(e['rule'].startswith('R3'))
    def test_storage_and_static_assets(self):
        self.req('decoys/0',{'active':False},'PATCH');self.assertEqual(self.req('decoys')[0]['active'],0)
        self.assertEqual(len(self.req('decoys')),10)
        for path in ['/','/app.js','/style.css','/experience.js','/experience.css','/mark.svg','/vendor/gsap.min.js','/vendor/ScrollTrigger.min.js']:
            with urlopen(self.url+path) as r:self.assertEqual(r.status,200)
        import sqlite3
        with sqlite3.connect(Path(self.tmp.name)/'test.db') as c:self.assertEqual(c.execute('SELECT active FROM decoys WHERE id=0').fetchone()[0],0)

        c.close()

    def test_story_assets_do_not_mutate_detection_state(self):
        before=self.req('state')
        for path in ['/','/experience.js','/experience.css','/vendor/gsap.min.js','/vendor/ScrollTrigger.min.js']:
            with urlopen(self.url+path) as r: body=r.read().decode('utf-8-sig')
            if path=='/':
                for stage in ['threat','network','deception','detection','defense']:
                    self.assertIn('id="'+stage+'"',body)
                self.assertIn('href="#dashboard"',body)
                self.assertNotIn('<script type="module" src="/app.js">',body)
            if path=='/experience.js':
                self.assertNotIn('fetch(',body)
                self.assertNotIn('/api/',body)
        self.assertEqual(self.req('state'),before)

if __name__=='__main__':unittest.main(verbosity=2)

