"""MEMBER: Piyush Gairola and Ajeet Singh Panwar -- Docker container execution with CPU/memory limits.
If Docker is unavailable (or CLOUDSCHED_DOCKER is not 1) containers are simulated so the project still runs."""
import os
try:
    import docker
    _client = docker.from_env() if os.environ.get("CLOUDSCHED_DOCKER") == "1" else None
except Exception:
    _client = None

def enabled(): return _client is not None

def start_container(c, job, vm):
    """Run the job in an isolated container limited to the job's CPU and RAM; record it in Containers table."""
    docker_id = None
    if _client:
        ct = _client.containers.run("alpine", ["sleep", str(job["burst"])], detach=True,
                                    nano_cpus=job["cpu"] * 10**9, mem_limit=f'{job["ram"]}m')
        docker_id = ct.short_id
    c.execute("INSERT INTO Containers(job_id,vm_id,docker_id,cpu_limit,mem_limit) VALUES(?,?,?,?,?)",
              (job["id"], vm["id"], docker_id or f'sim-{job["id"]}', job["cpu"], job["ram"]))
