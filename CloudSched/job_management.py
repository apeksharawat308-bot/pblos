"""MEMBER: Divyanshi Solanki -- Job management: submission, ready queue, status tracking, history."""
import database, resource_allocation

def submit_job(c, name, cpu, ram, burst, priority, storage=1, user="admin"):
    """Store a new job (CPU, RAM, run time, priority). Jobs bigger than the whole host are rejected."""
    c.execute("INSERT OR IGNORE INTO Users(name) VALUES(?)", (user,))
    uid = c.execute("SELECT id FROM Users WHERE name=?", (user,)).fetchone()[0]
    total = {r["name"]: r["total"] for r in c.execute("SELECT * FROM Resources")}
    too_big = cpu > total["cpu"] or ram > total["ram"] or storage > total["storage"]
    status = "rejected" if too_big else "waiting"
    cur = c.execute("""INSERT INTO Jobs(user_id,name,cpu,ram,storage,burst,remaining,priority,arrival,queued_at,status)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (uid, name, cpu, ram, storage, burst, burst, priority, database.clock(c), database.clock(c), status))
    database.log(c, "deny" if too_big else "spawn",
                 f"J-{cur.lastrowid} '{name}' by {user}: {cpu} vCPU, {ram/1024:.1f} GB, {burst}s, pri {priority}" + (" REJECTED (bigger than host)" if too_big else ""))
    if not too_big:   # Banker's "Max" row for this job
        c.execute("INSERT INTO BankerMatrices(job_id,max_cpu,max_ram,max_storage) VALUES(?,?,?,?)",
                  (cur.lastrowid, cpu, ram, storage))
    return cur.lastrowid

def waiting_jobs(c):
    """The ready queue."""
    return [dict(r) for r in c.execute("SELECT * FROM Jobs WHERE status='waiting'")]

def running_jobs(c):
    return [dict(r) for r in c.execute("SELECT * FROM Jobs WHERE status='running'")]

def set_status(c, job_id, status, now):
    """Change status; the trigger trg_log_status writes the ExecutionHistory row automatically."""
    c.execute("UPDATE Jobs SET status=?, end_time=CASE WHEN ?='completed' THEN ? ELSE end_time END WHERE id=?",
              (status, status, now, job_id))

def history(c, job_id):
    return [dict(r) for r in c.execute("SELECT * FROM ExecutionHistory WHERE job_id=? ORDER BY id", (job_id,))]

def preempt(c, job, now, why):
    """Context switch: take a running job off the CPU, free its resources, put it back in the ready queue."""
    resource_allocation.release(c, job, now)
    c.execute("UPDATE BankerMatrices SET alloc_cpu=0,alloc_ram=0,alloc_storage=0 WHERE job_id=?", (job["id"],))
    c.execute("UPDATE Jobs SET status='waiting',vm_id=NULL,queued_at=?,slice_used=0 WHERE id=?", (now, job["id"]))
    c.execute("UPDATE Meta SET v=v+1 WHERE k='ctx'")
    database.log(c, "preempt", f"context switch: J-{job['id']} preempted ({why}), {job['remaining']}s left")
