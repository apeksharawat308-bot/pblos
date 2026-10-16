"""MEMBER: Rudrapratap Singh Bhandari -- Deadlock avoidance with Banker's Algorithm (matrices stored in DB)."""
import resource_allocation

def is_safe(available, processes):
    """Safe-state check. processes: list of (allocation_vector, need_vector). Returns True if a safe sequence exists."""
    work, left = list(available), list(processes)
    while left:
        for p in left:
            if all(n <= w for n, w in zip(p[1], work)):   # this process can finish
                work = [w + a for w, a in zip(work, p[0])]; left.remove(p); break
        else:
            return False                                  # nobody can finish -> unsafe
    return True

def banker_grant(c, job):
    """Pretend to grant the job's request; allow it only if the resulting state is still safe."""
    f = resource_allocation.free_resources(c)
    avail = [f["cpu"], f["ram"], f["storage"]]
    need = [job["cpu"], job["ram"], job["storage"]]
    if any(n > a for n, a in zip(need, avail)): return False
    after = [a - n for a, n in zip(avail, need)]
    procs = [([m["alloc_cpu"], m["alloc_ram"], m["alloc_storage"]],            # Allocation matrix
              [m["max_cpu"] - m["alloc_cpu"], m["max_ram"] - m["alloc_ram"],   # Need = Max - Allocation
               m["max_storage"] - m["alloc_storage"]])
             for m in c.execute("SELECT b.* FROM BankerMatrices b JOIN Jobs j ON j.id=b.job_id WHERE j.status='running'")]
    procs.append((need, [0, 0, 0]))
    return is_safe(after, procs)

def record_allocation(c, job_id):
    """Update the Allocation matrix in the DB once a grant is made."""
    c.execute("UPDATE BankerMatrices SET alloc_cpu=max_cpu,alloc_ram=max_ram,alloc_storage=max_storage WHERE job_id=?", (job_id,))

def safe_sequence(avail, alloc, need):
    """Like is_safe but returns the safe order of process indexes (or None)."""
    work, left, order = list(avail), set(range(len(alloc))), []
    while left:
        for i in sorted(left):
            if all(n <= w for n, w in zip(need[i], work)):
                work = [w + a for w, a in zip(work, alloc[i])]; order.append(i); left.remove(i); break
        else: return None
    return order

def demo(c):
    """Textbook Banker's example (5 processes, resources A,B,C) written to the kernel log."""
    import database
    avail = [3, 3, 2]; alloc = [[0,1,0],[2,0,0],[3,0,2],[2,1,1],[0,0,2]]; mx = [[7,5,3],[3,2,2],[9,0,2],[2,2,2],[4,3,3]]
    need = [[m - a for m, a in zip(mx[i], alloc[i])] for i in range(5)]
    database.log(c, "banker", "Banker's demo: 5 processes, resources A,B,C, available (3,3,2)")
    for p, req in ((1, [1,0,2]), (0, [0,2,0])):
        ok = all(r <= n for r, n in zip(req, need[p])) and all(r <= a for r, a in zip(req, avail))
        if ok:
            a2 = [a - r for a, r in zip(avail, req)]
            al2 = [row[:] for row in alloc]; nd2 = [row[:] for row in need]
            al2[p] = [x + r for x, r in zip(al2[p], req)]; nd2[p] = [x - r for x, r in zip(nd2[p], req)]
            seq = safe_sequence(a2, al2, nd2)
            if seq is not None:
                avail, alloc, need = a2, al2, nd2
                database.log(c, "banker", f"P{p} requests {tuple(req)}: GRANTED, safe sequence " + " -> ".join(f"P{i}" for i in seq)); continue
        database.log(c, "deny", f"P{p} requests {tuple(req)}: DENIED, would leave the system in an unsafe state")
