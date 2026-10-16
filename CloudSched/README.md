# CloudSched
Intelligent cloud resource management and adaptive job scheduling (OS + DBMS + virtualization).

Run: `python server.py` then open http://localhost:8000
(optional real containers: `pip install docker` and set `CLOUDSCHED_DOCKER=1`)

## Who explains which file
| File | Member | What it does |
|---|---|---|
| algorithms.py | Ajeet Singh Panwar | FCFS, SJF, Priority, Round Robin, Priority Aging |
| metrics.py | Piyush Gairola | Waiting/turnaround/response time, CPU utilisation, weighted algorithm recommendation |
| container_runner.py | Piyush + Ajeet | Docker container per job with CPU/memory limits (simulated if no Docker) |
| dispatcher.py | Piyush (Team Lead) | Integration: full job flow in one ACID transaction, time ticks |
| resource_allocation.py | Apeksha Rawat | CPU/RAM/storage availability check, allocation (release is trigger trg_release) |
| hypervisor.py | Rudra + Apeksha | Hypervisor Manager: VM create/start/stop/destroy, job placement |
| deadlock_banker.py | Rudrapratap Singh Bhandari | Banker's Algorithm safe-state check, Max/Allocation/Need matrices |
| job_management.py | Divyanshi Solanki | Job submission, ready queue, status tracking, history |
| database.py + schema.sql | Devansh Thapliyal | 3NF schema, constraints, triggers, views, index, dashboard state |
| server.py + static/index.html | Devansh + Divyanshi | REST API and dashboard (graphs, Gantt chart) |

Uses SQLite so it runs anywhere; schema ports to MySQL.

## Live OS simulation (how it behaves)
- 1 time unit = 1 second. A background clock runs jobs; a workload generator keeps submitting new jobs (toggle "Auto workload").
- **FCFS / SJF**: non-preemptive. **Round Robin**: a running job is preempted after the time quantum (4s) if a waiting job can use its resources.
  **Priority**: a much more urgent waiting job evicts the least urgent running job; Priority Aging raises waiting jobs over time.
- Every preemption is a context switch (counted). All events appear in the Kernel log (admit, complete, preempt, aging, Banker's denies).
- "Banker's demo" button logs the textbook granted/denied (safe/unsafe) example.
