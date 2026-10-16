"""MEMBER: Devansh Thapliyal and Divyanshi Solanki -- REST server + live dashboard (static/index.html).
A background thread advances simulated time every second (1 time unit = 1 second), so jobs run in real time."""
import json, os, random, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import database, dispatcher, job_management, hypervisor, algorithms, deadlock_banker

TEAM = ["Apeksha Rawat", "Piyush Gairola", "Ajeet Panwar", "Rudrapratap Bhandari", "Divyanshi Solanki", "Devansh Thapliyal"]
LOCK = threading.Lock()          # one writer at a time (the DB also locks, this keeps things tidy)
LIVE = {"on": True, "auto": True, "speed": 1.0}  # speed = seconds per time unit
NAMES = ["compile", "backup", "render", "db-query", "ml-train", "web-req", "encode", "index", "unit-test", "etl"]

database.init()
def seed(c):
    random.seed(7)
    for i in range(8):
        job_management.submit_job(c, f"job-{i+1}", random.choice([2, 4, 6]), random.choice([2048, 4096, 8192]),
                                  random.randint(5, 14), random.randint(1, 8), user=TEAM[i % 6])
    dispatcher.dispatch(c)

def snap():
    c = database.conn(); s = database.state(c); s["live"] = LIVE["on"]; s["auto"] = LIVE["auto"]; s["speed"] = LIVE["speed"]
    s["queue"] = [j["id"] for j in algorithms.order_ready_queue(job_management.waiting_jobs(c), s["algo"], s["clock"])]
    return s

def arrivals():
    """Workload generator: new processes keep arriving, like users starting programs on a real machine."""
    c = database.conn(); n = 0
    while True:
        time.sleep(random.uniform(1.5, 3.5) * LIVE["speed"])
        if LIVE["on"] and LIVE["auto"]:
            with LOCK:
                try:
                    if len(job_management.waiting_jobs(c)) < 10:
                        n += 1
                        job_management.submit_job(c, f"{random.choice(NAMES)}-{n}", random.choice([1, 2, 2, 4, 6]),
                            random.choice([1024, 2048, 4096, 8192]), random.randint(4, 14), random.randint(1, 10), user=random.choice(TEAM))
                        dispatcher.dispatch(c)
                except Exception as e: print("arrival error:", e)

def ticker():
    """Real-time loop: every second advance the clock by one unit (finish jobs, free resources, start waiting jobs)."""
    c = database.conn()
    while True:
        time.sleep(LIVE["speed"])
        if LIVE["on"]:
            with LOCK:
                try: dispatcher.tick(c, 1)
                except Exception as e: print("tick error:", e)

class H(BaseHTTPRequestHandler):
    def send(self, obj, code=200, ctype="application/json"):
        body = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path == "/api/state": return self.send(snap())
        if self.path == "/api/compare":
            with LOCK: res, best = dispatcher.compare_workload(database.conn())
            return self.send({"results": res, "best": best})
        self.send(open(os.path.join(os.path.dirname(__file__), "static", "index.html"), "rb").read(), ctype="text/html")
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); d = json.loads(self.rfile.read(n) or "{}")
        try:
            with LOCK:
                c = database.conn()
                if self.path == "/api/submit":
                    job_management.submit_job(c, d["name"], int(d["cpu"]), int(d["ram"]), int(d["burst"]),
                                              int(d["priority"]), int(d.get("storage", 1)), d.get("user") or "admin")
                    dispatcher.dispatch(c)                      # start immediately if resources are free
                elif self.path == "/api/addvm":
                    k = c.execute("SELECT COUNT(*)+1 FROM VMs").fetchone()[0]; hypervisor.create_vm(c, f"vm-{k}", 4, 8192, 100)
                elif self.path == "/api/tick": dispatcher.tick(c, int(d.get("n", 1)))
                elif self.path == "/api/algo": c.execute("UPDATE Meta SET v=? WHERE k='algo'", (d["algo"],))
                elif self.path == "/api/live": LIVE["on"] = bool(d.get("on"))
                elif self.path == "/api/auto": LIVE["auto"] = bool(d.get("on"))
                elif self.path == "/api/speed": LIVE["speed"] = max(0.1, 1.0 / float(d["speed"]))
                elif self.path == "/api/banker_demo": deadlock_banker.demo(c)
                elif self.path == "/api/reset": dispatcher.DENIED.clear(); database.init(reset=True); seed(database.conn())
            self.send(snap())
        except Exception as e: self.send({"error": str(e)}, 400)
    def log_message(self, *a): pass

if __name__ == "__main__":
    c = database.conn()
    if not c.execute("SELECT 1 FROM Jobs").fetchone(): seed(c)
    threading.Thread(target=ticker, daemon=True).start(); threading.Thread(target=arrivals, daemon=True).start()
    print("CloudSched running at http://localhost:8000  (live OS simulation, 1 time unit = 1 second)")
    ThreadingHTTPServer(("", 8000), H).serve_forever()
