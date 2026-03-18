# Home-Lab Backup Server

A straightforward, containerized backup service for various Linux and macOS containers, VMs, and bare metal machines over SSH. It leverages `rsync` to perform efficient, incremental backups with robust scheduling and custom filtering.

## Key Features

- **Agentless**: Requires no software installation on target machines, just standard SSH access.
- **Interactive Configuration**: Generate backup jobs easily via the CLI prompt.
- **Modular Filtering**: Predefined OS-specific filter rules to prevent backing up caches, temporary files, and cloud-synced folders.
- **Dry-Run Support**: Safely test your configuration to see exactly what files will be copied before any data is written.
- **Built-in Scheduler**: Run jobs on dynamic schedules (daily at HH:MM, or minute/hour intervals).
- **Web Dashboard**: Monitor job configurations, storage usage, and read real-time log outputs via the built-in Streamlit UI.

## Initial Setup

1. **Clone the repository** and navigate to the project directory.
2. **Initialize the local environment**:
   ```bash
   make setup
   ```
   This command creates the required directory structures (`config/`, `data/`, `ssh/`), sets up a Python virtual environment, installs dependencies, and generates a dedicated `ed25519` SSH key pair for the backup service.

## Quick Start

1. **Create a Job**:
   ```bash
   make new-job
   ```
   Follow the interactive prompt to define what you want to backup.
   
2. **Distribute the SSH Key**:
   ```bash
   make copy-key
   ```
   Provide the remote server's address to grant passwordless access.
   
3. **Test the Configuration**:
   ```bash
   make dry-run-<your_job_name>
   ```

4. **Start the Service**:
   Start the automated scheduler and the monitoring dashboard via Docker Compose:
   ```bash
   make build
   make deploy
   ```

Visit `http://localhost:8502` to access the dashboard.

## Dashboard & Logging
Every backup run is logged sequentially to `data/logs/<job_id>.log`. The dashboard allows you to view these logs in real-time, inspect job schedules, and track disk usage per backup.

## Documentation
For a detailed explanation of job creation, filtering logic, and advanced testing, please read the [User Guide](docs/user_guide.md).
