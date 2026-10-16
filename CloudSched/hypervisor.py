"""MEMBER: Rudrapratap Singh Bhandari and Apeksha Rawat -- Hypervisor Manager and VM lifecycle.
The physical host is partitioned into VMs with fixed vCPU / vRAM / vDisk shares (simulated partitions)."""

def create_vm(c, name, vcpu, vram, vdisk):
    return c.execute("INSERT INTO VMs(name,vcpu,vram,vdisk) VALUES(?,?,?,?)", (name, vcpu, vram, vdisk)).lastrowid

def stop_vm(c, vm_id):    c.execute("UPDATE VMs SET state='stopped' WHERE id=?", (vm_id,))
def start_vm(c, vm_id):   c.execute("UPDATE VMs SET state='running' WHERE id=?", (vm_id,))
def destroy_vm(c, vm_id):
    """Only an empty VM can be destroyed."""
    if c.execute("SELECT 1 FROM Jobs WHERE vm_id=? AND status='running'", (vm_id,)).fetchone():
        raise ValueError("VM still has running jobs")
    c.execute("DELETE FROM VMs WHERE id=? AND state='stopped'", (vm_id,))

def find_vm(c, job):
    """Placement: the running VM with the most free vCPU that still fits the job, or None."""
    return c.execute("""SELECT * FROM VMs WHERE state='running' AND vcpu-used_cpu>=? AND vram-used_ram>=? AND vdisk-used_disk>=?
                        ORDER BY vcpu-used_cpu DESC""", (job["cpu"], job["ram"], job["storage"])).fetchone()
