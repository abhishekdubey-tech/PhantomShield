"""Offline PhantomShield REST server. No third party dependencies."""
import json, sqlite3, uuid, os, argparse, logging, threading
from storage import open_database, database_url, StorageConfigurationError
from datetime import datetime, timezone
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get('PHANTOM_DB', str(ROOT / 'phantomshield.db')))
NODES = ['External Client','Web Gateway','Application Server','Finance Server','Database Server','Backup Server']
ASSETS = [( 'employee_payroll_2026.csv','file','Finance Server','confidential'),('confidential_financial_report.pdf','file','Finance Server','confidential'),('internal_strategy.docx','file','Application Server','confidential'),('database_backup.sql','file','Backup Server','confidential'),('admin_credentials.txt','credential','Application Server','restricted'),('database_access_keys.env','credential','Database Server','restricted'),('/internal/admin','endpoint','Application Server','restricted'),('/internal/finance','endpoint','Finance Server','restricted'),('/internal/database','endpoint','Database Server','restricted'),('/internal/backup','endpoint','Backup Server','restricted')]
SCENARIOS = {'file':[None,7,1], 'credential':[None,4,6], 'multi':[None,7,1,4,8]}
def now(): return datetime.now(timezone.utc).isoformat()
def uid(prefix): return prefix+'-'+uuid.uuid4().hex[:8].upper()
def connect():
    return open_database(DB)
_initialized = False
_init_lock = threading.Lock()
def ensure_initialized():
    global _initialized
    if not _initialized:
        with _init_lock:
            if not _initialized:
                init()
                _initialized = True
def init():
    with connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS decoys(id INTEGER PRIMARY KEY,name TEXT,type TEXT,node TEXT,sensitivity TEXT,active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,actor_id TEXT,scenario TEXT,step INTEGER DEFAULT 0,status TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,timestamp TEXT,actor_id TEXT,session_id TEXT,source_node TEXT,target_node TEXT,resource TEXT,event_type TEXT,severity TEXT,reason TEXT,rule TEXT);
        CREATE TABLE IF NOT EXISTS alerts(id TEXT PRIMARY KEY,event_id TEXT,severity TEXT,description TEXT,status TEXT,created_at TEXT);
        CREATE TABLE IF NOT EXISTS incidents(id TEXT PRIMARY KEY,session_id TEXT UNIQUE,severity TEXT,started_at TEXT,ended_at TEXT,summary TEXT);''')
        if not c.execute('SELECT 1 FROM decoys').fetchone(): c.executemany('INSERT INTO decoys(id,name,type,node,sensitivity) VALUES(?,?,?,?,?)',[(i,*a) for i,a in enumerate(ASSETS)])
def rows(c, table):
    order={'decoys':'id','sessions':'created_at,id','events':'timestamp,id','alerts':'created_at,id','incidents':'started_at,id'}[table]
    return [dict(r) for r in c.execute('SELECT * FROM '+table+' ORDER BY '+order)]
def snapshot():
    with connect() as c:
        result={t:rows(c,t) for t in ['decoys','events','alerts','incidents','sessions']}
        result['_meta']={'storage':'postgresql' if database_url() else 'sqlite'}
        return result
def session(c,scenario='manual'):
    s={'id':uid('SES'),'actor_id':uid('SIM'),'scenario':scenario,'step':0,'status':'running' if scenario!='manual' else 'complete','created_at':now()}
    c.execute('INSERT INTO sessions VALUES(:id,:actor_id,:scenario,:step,:status,:created_at)',s); return s
RANK={'low':0,'medium':1,'high':2,'critical':3}
def record(c,s,asset_id=None):
    previous=[dict(r) for r in c.execute('SELECT * FROM events WHERE session_id=? ORDER BY timestamp,id',(s['id'],))]
    asset=dict(c.execute('SELECT * FROM decoys WHERE id=?',(asset_id,)).fetchone()) if asset_id is not None else None
    if asset and not asset['active']: raise ValueError('This decoy is disabled. Enable it in Settings first.')
    severity,reason,rule='low','Simulated actor entered the monitored workspace.','Observation'
    if asset:
        if asset['type']=='credential': severity,reason,rule='high','Fictional credential record discovered.','R2 · Credential interaction'
        elif asset['type']=='file': severity,reason,rule='medium','Confidential decoy file opened.','R1 · Confidential file'
        else: reason='Restricted application endpoint accessed in simulation.'
        distinct={p['resource'] for p in previous if p['event_type']!='session_entry'}|{asset['name']}
        if len(distinct)>=2 and RANK[severity]<2: severity,reason,rule='high','Multiple distinct decoys accessed in a single session.','R3 · Session correlation'
        if asset['type']=='endpoint' and any(p['event_type']=='credential_access' for p in previous): severity,reason,rule='critical','Restricted endpoint accessed after fake credential discovery.','R4 · Credential-to-endpoint escalation'
    e={'id':uid('EVT'),'timestamp':now(),'actor_id':s['actor_id'],'session_id':s['id'],'source_node':previous[-1]['target_node'] if previous else NODES[0],'target_node':asset['node'] if asset else NODES[1],'resource':asset['name'] if asset else 'Aegis Dynamics workspace','event_type':{'file':'file_access','credential':'credential_access','endpoint':'endpoint_access'}[asset['type']] if asset else 'session_entry','severity':severity,'reason':reason,'rule':rule}
    c.execute('INSERT INTO events VALUES(:id,:timestamp,:actor_id,:session_id,:source_node,:target_node,:resource,:event_type,:severity,:reason,:rule)',e)
    if severity!='low': c.execute('INSERT INTO alerts VALUES(?,?,?,?,?,?)',(uid('ALT'),e['id'],severity,reason,'open',e['timestamp']))
    all_events=previous+[e]
    if severity!='low':
        peak=max(all_events,key=lambda p:RANK[p['severity']])['severity']; summary=f"Simulated actor {s['actor_id']} accessed {len({p['resource'] for p in all_events if p['event_type']!='session_entry'})} monitored assets. Highest severity: {peak}."
        c.execute('INSERT INTO incidents VALUES(?,?,?,?,?,?) ON CONFLICT(session_id) DO UPDATE SET severity=excluded.severity,ended_at=excluded.ended_at,summary=excluded.summary',(uid('INC'),s['id'],peak,all_events[0]['timestamp'],e['timestamp'],summary))
    return e
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT/'web'),**kw)
    def log_message(self,*a): pass
    def send_json(self,status,data):
        b=json.dumps(data).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        p=urlparse(self.path).path
        if not p.startswith('/api/'): return super().do_GET()
        try:
            ensure_initialized()
            return self.get_api(p)
        except Exception as error: self.storage_error(error)
    def storage_error(self, error):
        # Do not log connection strings or expose database internals to visitors.
        logging.error('PhantomShield database request failed: %s (SQLSTATE %s)',type(error).__name__,getattr(error,'sqlstate','n/a'))
        if isinstance(error, StorageConfigurationError):
            return self.send_json(503,{'error':str(error),'code':'DATABASE_NOT_CONFIGURED'})
        return self.send_json(503,{'error':'Database unavailable. Check the server logs and database connection settings.','code':'DATABASE_UNAVAILABLE'})
    def get_api(self, p):
        if p=='/api/health': return self.send_json(200,{'status':'ok','storage':'postgresql' if database_url() else 'sqlite'})
        state=snapshot(); key=p.split('/')[-1]
        if key in state: return self.send_json(200,state[key])
        if key in ('state','dashboard'): return self.send_json(200,state)
        if p.startswith('/api/reports/'):
            inc=next((i for i in state['incidents'] if i['id']==key),None)
            if not inc: return self.send_json(404,{'error':'Incident not found'})
            events=[e for e in state['events'] if e['session_id']==inc['session_id']]
            return self.send_json(200,dict(inc,events=events,affected_nodes=sorted({e['target_node'] for e in events}),decoys=sorted({e['resource'] for e in events if e['event_type']!='session_entry'}),rules=sorted({e['rule'] for e in events}),recommendations=['Investigate the correlated session and preserve event records.','Rotate any corresponding real credentials if an equivalent exposure exists.','Review endpoint access controls and decoy coverage.']))
        self.send_json(404,{'error':'Unknown endpoint'})
    def do_POST(self): self.mutate()
    def do_PATCH(self): self.mutate()
    def mutate(self):
        try:
            ensure_initialized()
            data=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))) or '{}'); p=urlparse(self.path).path
            with connect() as c:
                if p=='/api/simulations/reset':
                    for t in ['events','alerts','incidents','sessions']: c.execute('DELETE FROM '+t)
                    c.execute('UPDATE decoys SET active=1'); result={'ok':True}
                elif p=='/api/simulations/start':
                    scenario=data.get('scenario','multi')
                    if scenario not in SCENARIOS: raise ValueError('Unknown scenario')
                    if c.execute("SELECT 1 FROM sessions WHERE status IN ('running','paused')").fetchone(): raise ValueError('Finish or reset the active simulation first.')
                    result=session(c,scenario)
                elif p.startswith('/api/simulations/'):
                    sid=data.get('session_id'); r=c.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone()
                    if not r: raise ValueError('Session not found')
                    s=dict(r); action=p.split('/')[-1]
                    if action=='step':
                        if s['status']!='running': raise ValueError('Simulation is not running')
                        steps=SCENARIOS[s['scenario']]; result=record(c,s,steps[s['step']]); step=s['step']+1
                        c.execute('UPDATE sessions SET step=?,status=? WHERE id=?',(step,'complete' if step==len(steps) else 'running',sid))
                    elif action in ('pause','resume'):
                        if s['status']=='complete': raise ValueError('Simulation is complete')
                        c.execute('UPDATE sessions SET status=? WHERE id=?',('paused' if action=='pause' else 'running',sid)); result={'ok':True}
                    else: raise ValueError('Unknown action')
                elif p=='/api/interactions':
                    r=c.execute('SELECT * FROM sessions WHERE id=?',(data.get('session_id'),)).fetchone(); s=dict(r) if r and r['scenario']=='manual' else session(c)
                    result=record(c,s,int(data['asset_id']))
                elif p.startswith('/api/alerts/'):
                    if data.get('status') not in ['open','acknowledged','resolved']: raise ValueError('Invalid alert status')
                    cur=c.execute('UPDATE alerts SET status=? WHERE id=?',(data['status'],p.split('/')[-1]));
                    if not cur.rowcount: raise ValueError('Alert not found')
                    result={'ok':True}
                elif p.startswith('/api/decoys/'):
                    cur=c.execute('UPDATE decoys SET active=? WHERE id=?',(int(bool(data['active'])),int(p.split('/')[-1])))
                    if not cur.rowcount: raise ValueError('Decoy not found')
                    result={'ok':True}
                else: return self.send_json(404,{'error':'Unknown endpoint'})
            self.send_json(200,result)
        except (ValueError,KeyError,TypeError,sqlite3.IntegrityError) as e: self.send_json(400,{'error':str(e)})
        except Exception as error: self.storage_error(error)
if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=8787); args=parser.parse_args(); ensure_initialized()
    print(f'PhantomShield ready at http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()

