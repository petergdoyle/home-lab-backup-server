import yaml
import subprocess
import sys
import os
import argparse
import datetime
from pathlib import Path

def run_backup(config_path, log_to_file=True):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    name = config.get('name', 'Unknown Job')
    host = config.get('host')
    user = config.get('user', 'root')
    port = config.get('port', 22)
    ssh_key = config.get('ssh_key', 'ssh/id_rsa')
    mode = config.get('mode', 'data')
    source_paths = config.get('source_paths', [])
    excludes = config.get('exclude', [])
    backup_root = config.get('backup_root', '/backup')

    # Handle local vs docker pathing
    if backup_root == '/backup' and not os.path.exists('/backup'):
        # If /backup isn't available (running locally), use the 'data' dir in project root
        project_root = Path(__file__).parent.parent
        backup_root = str(project_root / "data")
        print(f"ℹ️ Redirecting /backup to local {backup_root}")

    job_id = name.replace(' ', '_').lower()
    target_dir = os.path.join(backup_root, job_id)
    log_dir = os.path.join(backup_root, 'logs')
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"{job_id}.log")
    
    def log(msg):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[{timestamp}] {msg}"
        print(formatted_msg)
        if log_to_file:
            with open(log_file, 'a') as f:
                f.write(formatted_msg + "\n")

    log(f"🚀 Starting backup for {name} ({host})")

    # Base rsync command
    ssh_opts = f"ssh -i {ssh_key} -p {port} -o StrictHostKeyChecking=no"
    cmd = [
        "rsync",
        "-avz",
        "--delete",
        "-e", ssh_opts
    ]

    # Add filters
    filter_file = Path("config/filters.txt")
    if filter_file.exists():
        cmd.extend(["--filter", f"merge {filter_file}"])

    for exc in excludes:
        cmd.extend(["--exclude", exc])

    if mode == 'full':
        source_paths = ["/"]
    
    if not source_paths:
        log(f"⚠️ No source paths defined for {name}. Skipping.")
        return

    success = True
    if source_paths is None:
        source_paths = []
        
    for source in source_paths:
        remote_source = f"{user}@{host}:{source}"
        full_cmd = cmd + [remote_source, target_dir]
        
        log(f"Executing: {' '.join(full_cmd)}")
        try:
            process = subprocess.Popen(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                if log_to_file:
                    with open(log_file, 'a') as f:
                        f.write(line)
                print(line, end='')
            process.wait()
            if process.returncode != 0:
                log(f"❌ Backup failed for {source} with return code {process.returncode}")
                success = False
            else:
                log(f"✅ Backup successful for {source}")
        except Exception as e:
            log(f"❌ Error executing rsync: {e}")
            success = False
    
    return success

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Home-Lab Backup Orchestrator")
    parser.add_argument("config", help="Path to the YAML configuration file")
    parser.add_argument("--no-log", action="store_false", dest="log_to_file", help="Disable logging to file")
    args = parser.parse_args()
    
    run_backup(args.config, log_to_file=args.log_to_file)
