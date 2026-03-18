# Home-Lab Backup Server - User Guide

This guide explains how to configure, test, and execute backup jobs using the Home-Lab Backup Server.

## 1. Creating a New Backup Job (`make new-job`)

The easiest way to configure a new backup is to use the interactive configuration builder. 
From your terminal, run:
```bash
make new-job
```

You will be prompted to enter the following information:
- **Job Name**: A human-readable name (e.g., `Remote iMac`).
- **Configuration filename**: The name of the `.yaml` file to save it as (e.g., `remote-imac.yaml`).
- **Target Host**: The IP address or hostname of the machine you want to backup (e.g., `192.168.1.100`).
- **SSH Username**: The username on the remote machine (e.g., `admin`).
- **SSH Port**: Default is `22`.
- **SSH Private Key**: Default is `ssh/id_ed25519`.
- **Backup Mode**: 
  - `1` (Data): Backup specific directories you provide.
  - `2` (Full): Backup the entire OS starting from root `/`.

### Applying Filters
The builder will ask if you want to apply predefined filter sets. These live in the `config/filters/` directory:
- `macos-data.txt`: Excludes macOS-specific caches, trash, and active iCloud Drive files.
- `linux-data.txt`: Excludes Linux user caches and thumbnails.
- `linux-sys.txt`: Excludes temporary OS paths (`/dev`, `/proc`, `/tmp`, etc.).
- `common-excludes.txt`: Excludes browser caches, application locks, and general `.tmp` files.

### Custom Paths and Schedule
- **Source path**: Provide the absolute path(s) you want to backup (e.g., `/Users/yourusername`).
- **Custom Excludes**: Add any specific file extensions or folders you want to ignore.
- **Target Backup Directory**: Where the files will live on the backup server (default is `/backup`).
- **Schedule**: Enter a time (e.g., `02:00` for daily at 2AM) or an interval (`every 60 minutes`). Leave blank for manual on-demand execution only.

---

## 2. Copying the SSH Key (`make copy-key`)

Before `rsync` can connect and pull data, the remote machine must trust the backup server's SSH key.
Run the following convenience command:
```bash
make copy-key
```
You will be prompted for:
- `user@hostname`: (e.g., `admin@192.168.1.100`)

This will run `ssh-copy-id` and ask for the remote machine's password once. Afterward, the backup server will have passwordless access.

---

## 3. Testing with a Dry-Run Backup

Before writing any files to disk, it is highly recommended to perform a dry-run. A dry-run calculates exactly what files `rsync` intends to transfer and highlights any permission or connectivity issues without transferring data.

Run:
```bash
make dry-run-<job_filename>
```
*Note: Exclude the `.yaml` extension. For a file named `remote-imac.yaml`, the command is `make dry-run-remote-imac`.*

Review the console output to ensure the correct files are targeted and that none of your intended exclusions slip through.

---

## 4. Running Backups

### On-Demand Locally
To manually run a backup job right now, run:
```bash
make backup-<job_filename>
```

### Scheduled via Docker
If you've set a `schedule:` in your job configuration, the long-running Docker service will handle it automatically.
Ensure the service is running:
1. `make build`
2. `make deploy`

You can monitor the service status and view logs via the dashboard at `http://localhost:8502`.
