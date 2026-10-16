-- CloudSched schema (3NF). SQLite dialect; for MySQL swap AUTOINCREMENT->AUTO_INCREMENT.
CREATE TABLE IF NOT EXISTS Users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS Resources(name TEXT PRIMARY KEY, total INTEGER NOT NULL CHECK(total>0),
  used INTEGER NOT NULL DEFAULT 0 CHECK(used>=0 AND used<=total));
CREATE TABLE IF NOT EXISTS VMs(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
  vcpu INTEGER NOT NULL CHECK(vcpu>0), vram INTEGER NOT NULL CHECK(vram>0), vdisk INTEGER NOT NULL CHECK(vdisk>0),
  used_cpu INTEGER NOT NULL DEFAULT 0, used_ram INTEGER NOT NULL DEFAULT 0, used_disk INTEGER NOT NULL DEFAULT 0,
  state TEXT NOT NULL DEFAULT 'running' CHECK(state IN('running','stopped')));
CREATE TABLE IF NOT EXISTS Jobs(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES Users(id),
  name TEXT NOT NULL, cpu INTEGER NOT NULL CHECK(cpu>0), ram INTEGER NOT NULL CHECK(ram>0), storage INTEGER NOT NULL DEFAULT 1 CHECK(storage>0),
  burst INTEGER NOT NULL CHECK(burst>0), remaining INTEGER NOT NULL, priority INTEGER NOT NULL CHECK(priority BETWEEN 1 AND 10),
  arrival INTEGER NOT NULL DEFAULT 0, queued_at INTEGER NOT NULL DEFAULT 0, slice_used INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'waiting' CHECK(status IN('waiting','running','completed','rejected')),
  start_time INTEGER, end_time INTEGER, vm_id INTEGER REFERENCES VMs(id));
CREATE TABLE IF NOT EXISTS Allocations(id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL REFERENCES Jobs(id),
  cpu INTEGER NOT NULL, ram INTEGER NOT NULL, storage INTEGER NOT NULL, released INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS Containers(id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL REFERENCES Jobs(id),
  vm_id INTEGER NOT NULL REFERENCES VMs(id), docker_id TEXT, cpu_limit INTEGER, mem_limit INTEGER,
  state TEXT NOT NULL DEFAULT 'running' CHECK(state IN('running','stopped')));
CREATE TABLE IF NOT EXISTS ExecutionHistory(id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL REFERENCES Jobs(id),
  old_status TEXT, new_status TEXT NOT NULL, at_time INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS BankerMatrices(job_id INTEGER PRIMARY KEY REFERENCES Jobs(id),
  max_cpu INT, max_ram INT, max_storage INT, alloc_cpu INT DEFAULT 0, alloc_ram INT DEFAULT 0, alloc_storage INT DEFAULT 0);
CREATE TABLE IF NOT EXISTS AlgorithmResults(id INTEGER PRIMARY KEY AUTOINCREMENT, algorithm TEXT NOT NULL,
  avg_wait REAL, avg_tat REAL, avg_resp REAL, cpu_util REAL, score REAL, run_at INTEGER);
CREATE TABLE IF NOT EXISTS Slices(id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL REFERENCES Jobs(id), vm_id INTEGER NOT NULL, start_t INTEGER NOT NULL, end_t INTEGER);
CREATE TABLE IF NOT EXISTS Events(id INTEGER PRIMARY KEY AUTOINCREMENT, t INTEGER NOT NULL, kind TEXT NOT NULL, msg TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS Meta(k TEXT PRIMARY KEY, v TEXT);
CREATE INDEX IF NOT EXISTS idx_jobs_status_pri ON Jobs(status, priority);

CREATE TRIGGER IF NOT EXISTS trg_log_status AFTER UPDATE OF status ON Jobs WHEN OLD.status<>NEW.status
BEGIN INSERT INTO ExecutionHistory(job_id,old_status,new_status,at_time)
  VALUES(NEW.id,OLD.status,NEW.status,CAST((SELECT v FROM Meta WHERE k='clock') AS INTEGER)); END;

CREATE TRIGGER IF NOT EXISTS trg_release AFTER UPDATE OF status ON Jobs WHEN NEW.status='completed'
BEGIN
  UPDATE Resources SET used=used-(SELECT IFNULL(SUM(cpu),0) FROM Allocations WHERE job_id=NEW.id AND released=0) WHERE name='cpu';
  UPDATE Resources SET used=used-(SELECT IFNULL(SUM(ram),0) FROM Allocations WHERE job_id=NEW.id AND released=0) WHERE name='ram';
  UPDATE Resources SET used=used-(SELECT IFNULL(SUM(storage),0) FROM Allocations WHERE job_id=NEW.id AND released=0) WHERE name='storage';
  UPDATE VMs SET used_cpu=used_cpu-NEW.cpu, used_ram=used_ram-NEW.ram, used_disk=used_disk-NEW.storage WHERE id=NEW.vm_id;
  UPDATE Allocations SET released=1 WHERE job_id=NEW.id;
  UPDATE Containers SET state='stopped' WHERE job_id=NEW.id;
  UPDATE BankerMatrices SET alloc_cpu=0,alloc_ram=0,alloc_storage=0 WHERE job_id=NEW.id;
  UPDATE Slices SET end_t=CAST((SELECT v FROM Meta WHERE k='clock') AS INTEGER) WHERE job_id=NEW.id AND end_t IS NULL;
END;

CREATE VIEW IF NOT EXISTS v_job_stats AS SELECT status, COUNT(*) AS jobs FROM Jobs GROUP BY status;
CREATE VIEW IF NOT EXISTS v_avg_wait AS SELECT algorithm, AVG(avg_wait) AS avg_wait FROM AlgorithmResults GROUP BY algorithm;
