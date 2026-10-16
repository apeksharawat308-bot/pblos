"""MEMBER: Piyush Gairola (Team Lead) -- Integration: the live OS loop.
submit -> admission control -> Banker's check -> VM placement -> container -> run -> (preempt) -> release -> reallocate."""
import database, algorithms, metrics, job_management, resource_allocation, deadlock_banker, hypervisor, container_runner

DENIED = set()   # jobs already reported as denied by Banker's (avoid log spam)

def dispatch(c):
    """One ACID transaction (BEGIN IMMEDIATE = write lock), so concurrent requests cannot over-allocate."""
    c.execute("BEGIN IMMEDIATE"); now = database.clock(c)
    try:
        queue = algorithms.order_ready_queue(job_management.waiting_jobs(c), database.algo(c), now)
        for job in queue:
            vm = hypervisor.find_vm(c, job)
            if not vm or not resource_allocation.has_capacity(c, job): continue   # stays in the ready queue
            if not deadlock_banker.banker_grant(c, job):
                if job["id"] not in DENIED:
                    DENIED.add(job["id"]); database.log(c, "deny", f"Banker's: J-{job['id']} request denied (unsafe state)")
                continue
            resource_allocation.allocate(c, job, vm, now)
            deadlock_banker.record_allocation(c, job["id"])
            container_runner.start_container(c, job, vm)
            database.log(c, "admit", f"J-{job['id']} dispatched to VM-{vm['id']} in a container "
                                     f"({job['cpu']} vCPU, {job['ram']/1024:.1f} GB) | Banker's: safe state")
        c.execute("COMMIT")
    except Exception:
        c.execute("ROLLBACK"); raise

def _fits_after(c, head, victim):
    f = resource_allocation.free_resources(c)
    return (head["cpu"] <= f["cpu"] + victim["cpu"] and head["ram"] <= f["ram"] + victim["ram"]
            and head["storage"] <= f["storage"] + victim["storage"])

def preempt_step(c, t):
    """Round Robin: quantum expiry. Priority: a much more urgent waiting job evicts the least urgent running job."""
    algo = database.algo(c); waiting = algorithms.order_ready_queue(job_management.waiting_jobs(c), algo, t)
    running = job_management.running_jobs(c)
    if not waiting or not running: return
    head = waiting[0]; q = database.meta(c, "quantum")
    if algo == "RR":
        for j in running:
            if j["slice_used"] >= q:
                if _fits_after(c, head, j): job_management.preempt(c, j, t, f"time quantum {q}s expired"); break
                c.execute("UPDATE Jobs SET slice_used=0 WHERE id=?", (j["id"],))   # nobody can use its CPU: new slice
    elif algo == "PRIORITY":
        victim = max(running, key=lambda j: algorithms.effective_priority(j, t))
        if (algorithms.effective_priority(head, t) + 1 < algorithms.effective_priority(victim, t)
                and _fits_after(c, head, victim)):
            job_management.preempt(c, victim, t, f"higher priority J-{head['id']} arrived")

def age_log(c, t):
    if database.algo(c) != "PRIORITY": return
    for j in job_management.waiting_jobs(c):
        a, b = algorithms.effective_priority(j, t - 1), algorithms.effective_priority(j, t)
        if a != b: database.log(c, "aging", f"Priority Aging: J-{j['id']} priority {a} -> {b} (waiting {t - j['arrival']}s)")

def tick(c, n=1):
    """Advance simulated time by one unit: run, complete, age, preempt, dispatch."""
    for _ in range(n):
        dispatch(c); t = database.clock(c) + 1
        c.execute("UPDATE Meta SET v=? WHERE k='clock'", (t,))
        c.execute("UPDATE Jobs SET remaining=remaining-1, slice_used=slice_used+1 WHERE status='running'")
        for r in c.execute("SELECT id,arrival,burst FROM Jobs WHERE status='running' AND remaining<=0").fetchall():
            job_management.set_status(c, r["id"], "completed", t)      # trigger frees resources
            tat = t - r["arrival"]
            database.log(c, "complete", f"J-{r['id']} finished | turnaround {tat}s, waited {tat - r['burst']}s | resources released")
        age_log(c, t); preempt_step(c, t); dispatch(c)

def compare_workload(c):
    jobs = [dict(r) for r in c.execute("SELECT id,arrival,burst,priority FROM Jobs WHERE status<>'rejected'")]
    if not jobs: return [], None
    results, best = metrics.compare(jobs[-40:])      # most recent 40 jobs keep the comparison fast
    database.save_algorithm_results(c, results)
    return results, best
