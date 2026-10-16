"""MEMBER: Apeksha Rawat -- Resource management: availability check, allocation on start, release on completion.
Release itself is done by the database trigger trg_release (see schema.sql); this file does check + allocate."""

def free_resources(c):
    return {r["name"]: r["total"] - r["used"] for r in c.execute("SELECT * FROM Resources")}

def has_capacity(c, job):
    """Admission control: is enough CPU, RAM and storage free right now?"""
    f = free_resources(c)
    return job["cpu"] <= f["cpu"] and job["ram"] <= f["ram"] and job["storage"] <= f["storage"]

def allocate(c, job, vm, now):
    """Reserve resources and mark the job running. Must be called inside the dispatcher's transaction,
    so two jobs can never claim the same resources (ACID + locking)."""
    for name, amount in (("cpu", job["cpu"]), ("ram", job["ram"]), ("storage", job["storage"])):
        c.execute("UPDATE Resources SET used=used+? WHERE name=?", (amount, name))
    c.execute("UPDATE VMs SET used_cpu=used_cpu+?,used_ram=used_ram+?,used_disk=used_disk+? WHERE id=?",
              (job["cpu"], job["ram"], job["storage"], vm["id"]))
    c.execute("INSERT INTO Allocations(job_id,cpu,ram,storage) VALUES(?,?,?,?)",
              (job["id"], job["cpu"], job["ram"], job["storage"]))
    c.execute("INSERT INTO Slices(job_id,vm_id,start_t) VALUES(?,?,?)", (job["id"], vm["id"], now))
    c.execute("UPDATE Jobs SET status='running',start_time=COALESCE(start_time,?),vm_id=?,slice_used=0 WHERE id=?", (now, vm["id"], job["id"]))

def release(c, job, now):
    """Give back a running job's resources without completing it (used when a job is preempted)."""
    for name, amt in (("cpu", job["cpu"]), ("ram", job["ram"]), ("storage", job["storage"])):
        c.execute("UPDATE Resources SET used=used-? WHERE name=?", (amt, name))
    c.execute("UPDATE VMs SET used_cpu=used_cpu-?,used_ram=used_ram-?,used_disk=used_disk-? WHERE id=?",
              (job["cpu"], job["ram"], job["storage"], job["vm_id"]))
    c.execute("UPDATE Allocations SET released=1 WHERE job_id=?", (job["id"],))
    c.execute("UPDATE Containers SET state='stopped' WHERE job_id=? AND state='running'", (job["id"],))
    c.execute("UPDATE Slices SET end_t=? WHERE job_id=? AND end_t IS NULL", (now, job["id"]))
