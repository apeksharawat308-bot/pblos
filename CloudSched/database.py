"""MEMBER: Devansh Thapliyal -- Database layer: connection, schema (3NF), seed data, dashboard views/state.
The SQL itself (tables, constraints, triggers, views, index) is in schema.sql."""
import os, sqlite3, container_runner
BASE = os.path.dirname(__file__)
DB = os.path.join(BASE, "cloudsched.db")
HOST = {"cpu": 16, "ram": 32768, "storage": 500}      # the physical host

def conn():
    c = sqlite3.connect(DB, timeout=10, isolation_level=None); c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON"); return c

def init(reset=False):
    """Create tables/triggers/views; first run also adds host resources, an admin user and two VMs."""
    if reset and os.path.exists(DB): os.remove(DB)
    c = conn(); c.executescript(open(os.path.join(BASE, "schema.sql")).read())
    if not c.execute("SELECT 1 FROM Resources").fetchone():
        for k, v in HOST.items(): c.execute("INSERT INTO Resources(name,total) VALUES(?,?)", (k, v))
        c.execute("INSERT INTO Meta VALUES('clock','0'),('algo','PRIORITY'),('quantum','4'),('ctx','0')")
        c.execute("INSERT INTO Users(name) VALUES('admin')")
        for i in (1, 2): c.execute("INSERT INTO VMs(name,vcpu,vram,vdisk) VALUES(?,?,?,?)", (f"vm-{i}", 8, 16384, 250))
    return c

def clock(c): return int(c.execute("SELECT v FROM Meta WHERE k='clock'").fetchone()[0])
def algo(c):  return c.execute("SELECT v FROM Meta WHERE k='algo'").fetchone()[0]

def log(c, kind, msg):
    """Kernel log line (shown live on the dashboard)."""
    c.execute("INSERT INTO Events(t,kind,msg) VALUES(?,?,?)", (clock(c), kind, msg))

def meta(c, k): return int(c.execute("SELECT v FROM Meta WHERE k=?", (k,)).fetchone()[0])

def state(c):
    """Everything the dashboard needs (reads tables and the v_job_stats view)."""
    q = lambda s: [dict(r) for r in c.execute(s)]
    return {"clock": clock(c), "algo": algo(c), "resources": q("SELECT * FROM Resources"), "vms": q("SELECT * FROM VMs"),
            "jobs": q("SELECT j.*, u.name AS user FROM Jobs j JOIN Users u ON u.id=j.user_id ORDER BY j.id"), "containers": q("SELECT * FROM Containers ORDER BY id DESC LIMIT 12"),
            "history": q("SELECT h.*, j.name FROM ExecutionHistory h JOIN Jobs j ON j.id=h.job_id ORDER BY h.id DESC LIMIT 8"),
            "events": q("SELECT * FROM (SELECT * FROM Events ORDER BY id DESC LIMIT 40) ORDER BY id"),
            "slices": q("SELECT * FROM Slices ORDER BY id DESC LIMIT 300"), "ctx": meta(c, "ctx"), "quantum": meta(c, "quantum"),
            "stats": q("SELECT * FROM v_job_stats"), "docker": container_runner.enabled()}

def save_algorithm_results(c, results):
    for r in results:
        c.execute("INSERT INTO AlgorithmResults(algorithm,avg_wait,avg_tat,avg_resp,cpu_util,score,run_at) VALUES(?,?,?,?,?,?,?)",
                  (r["algorithm"], r["avg_wait"], r["avg_tat"], r["avg_resp"], r["cpu_util"], r["score"], clock(c)))
