"""MEMBER: Ajeet Singh Panwar -- CPU scheduling algorithms + Priority Aging.
FCFS, SJF, Priority and Round Robin are simulated on a job list. No database needed here."""
AGE_STEP = 5  # Priority Aging: every 5 time units of waiting raises priority by 1 (1 = highest)

def effective_priority(job, now):
    """Priority Aging: the longer a job waits, the smaller (better) its priority number. Prevents starvation."""
    return max(1, job["priority"] - max(0, now - job["arrival"]) // AGE_STEP)

def simulate(jobs, algo, quantum=2):
    """jobs: dicts with id, arrival, burst, priority. algo: FCFS | SJF | PRIORITY | RR.
    Returns (timeline [(job_id,start,end)], metrics {job_id: wait/tat/resp})."""
    rem = {j["id"]: j["burst"] for j in jobs}
    first, done, timeline, t, queue = {}, {}, [], 0, []
    arrived = lambda: [j for j in jobs if j["arrival"] <= t and j["id"] not in done]
    while len(done) < len(jobs):
        ready = arrived()
        if not ready:                       # CPU idle: jump to next arrival
            t = min(j["arrival"] for j in jobs if j["id"] not in done); continue
        if algo == "RR":
            for j in sorted(ready, key=lambda j: (j["arrival"], j["id"])):
                if j["id"] not in queue: queue.append(j["id"])
            jid = queue.pop(0); run = min(quantum, rem[jid])
        else:
            key = {"FCFS": lambda j: (j["arrival"], j["id"]),
                   "SJF": lambda j: (j["burst"], j["id"]),
                   "PRIORITY": lambda j: (effective_priority(j, t), j["arrival"], j["id"])}[algo]
            jid = min(ready, key=key)["id"]; run = rem[jid]
        first.setdefault(jid, t); timeline.append((jid, t, t + run)); t += run; rem[jid] -= run
        if rem[jid] == 0: done[jid] = t
        elif algo == "RR":
            for j in arrived():
                if j["id"] not in queue and j["id"] != jid: queue.append(j["id"])
            queue.append(jid)
    metrics = {}
    for j in jobs:
        tat = done[j["id"]] - j["arrival"]
        metrics[j["id"]] = {"wait": tat - j["burst"], "tat": tat, "resp": first[j["id"]] - j["arrival"]}
    return timeline, metrics

def order_ready_queue(waiting, algo, now):
    """Used by the dispatcher: sort waiting jobs according to the chosen algorithm."""
    key = {"FCFS": lambda j: (j["arrival"], j["id"]), "SJF": lambda j: (j["remaining"], j["id"]),
           "PRIORITY": lambda j: (effective_priority(j, now), j["arrival"], j["id"]),
           "RR": lambda j: (j.get("queued_at", j["arrival"]), j["id"])}[algo]
    return sorted(waiting, key=key)
