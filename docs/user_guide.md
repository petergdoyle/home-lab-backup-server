# 📖 Home-Lab Backup Server - User Guide

This guide provides practical examples for managing your backups, logic for filtering data, and advanced configuration directives.

---

## 🚀 Quick Start

### 1. Initialize the Server
Before running any backups, set up your local environment:
```bash
make setup
```
*This creates required directories (`data/`, `config/`), sets up a Python virtual environment, and generates your SSH key pair.*

### 2. Connect a New Machine
To back up a remote machine, you must first copy your SSH public key to it:
```bash
make copy-key
# Standard format: user@192.168.1.10
```

### 3. Create a Backup Job
Use the interactive wizard to build your configuration:
```bash
make new-job
```
*The wizard will ask for the host, username, folders to back up, and which filter sets (macOS, Linux, etc.) to apply.*

---

## 🛠 Backup Commands

Once you have a job configured (e.g., `peters-imac.yaml`), you can run it using these dynamic targets:

### Run a Standard Backup (Background)
Syncs the remote data to the local mirror. This command runs in the background.
```bash
make backup-<job_name>
```
*By default, this is silent. You can tail the log immediately by adding `TAIL_LOG=true`:*
```bash
make backup-<job_name> TAIL_LOG=true
```

### Monitoring Progress
To view the live log output for an active or previous job:
```bash
make tail-<job_name>
```

### Job Status Overview
To see a high-level report of all jobs and their current state (Idle vs. Running):
```bash
make status
```
*For a specific job only:* `make status-<job_name>`

### Terminating a Running Job
To stop an active backup job immediately:
```bash
make backup-kill-<job_name>
```

### Global Locking
The backup server enforced a **global lock**. If you attempt to start a `make backup-*` job while another is already running, the new attempt will be blocked with a warning. This prevents resource contention on your home-lab bandwidth and disk.

### Run a Dry Run
See exactly what files would be transferred or deleted without actually touching any data.
```bash
make dry-run-<job_name>
```

---

## 🧹 Purge Control (`DELETE_EXCLUDED`)

By default, `rsync` will not delete files from the backup server if they are added to an "Exclude" list later. To force a purge of "junk" files that you've recently filtered out, use the `DELETE_EXCLUDED` directive.

### Option A: Permanent (YAML)
Add this to your `config/your-job.yaml` to always keep the mirror 100% clean:
```yaml
delete_excluded: true
```

### Option B: On-Demand (CLI)
Run a one-time purge without changing your config file:
```bash
make backup-<job_name> DELETE_EXCLUDED=true
```

---

## 📦 Snapshots & Archiving

If you want to keep point-in-time "versions" of your backups rather than just a live mirror:

1.  **Enable Snapshots**: Set `snapshot: true` in your job YAML.
2.  **Run Backup**: Each time the backup completes, the server will create a timestamped `.tar.gz` archive in `data/backups/`.

---

## 🖥 Deployment (Docker)

To run the backup server as a professional background service with an automated scheduler and dashboard:

1.  **Build**: `make build`
2.  **Start**: `make deploy`
3.  **Logs**: `make service-logs`
4.  **Stop**: `make stop`

### The Dashboard
Once deployed, visit the live monitoring UI:
**URL**: `http://localhost:8502`

---

## 📂 Project Structure
- `config/`: Your job YAML files.
- `config/filters/`: Modular filter sets (`macos-data.txt`, `common-excludes.txt`, etc.).
- `data/backups/`: Where your mirrored data and snapshots live.
- `data/logs/`: Detailed execution logs for every job.
- `ssh/`: Your backup server's identity keys.
