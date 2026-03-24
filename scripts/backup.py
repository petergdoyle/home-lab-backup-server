import yaml
import subprocess
import sys
import os
import argparse
import datetime
import fcntl
from pathlib import Path

def run_backup(config_path, log_to_file=True, dry_run=False):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    name = config.get('name', 'Unknown Job')
    host = config.get('host')
    user = config.get('user', 'root')
    port = config.get('port', 22)
    ssh_key = config.get('ssh_key', 'ssh/id_ed25519')
    mode = config.get('mode', 'data')
    source_paths = config.get('source_paths', [])
    excludes = config.get('exclude', [])
    filters = config.get('filters', [])
    backup_root = config.get('backup_root', '/backup')

    # Handle local vs docker pathing
    if backup_root == '/backup' and not os.path.exists('/backup'):
        # If /backup isn't available (running locally), use the 'data' dir in project root
        project_root = Path(__file__).parent.parent
        backup_root = str(project_root / "data")
        print(f"ℹ️ Redirecting /backup to local {backup_root}")

    # Ensure backup_root exists for the lock file
    os.makedirs(backup_root, exist_ok=True)
    
    # Global Job Lock
    lock_file_path = os.path.join(backup_root, ".backup.lock")
    lock_file = open(lock_file_path, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print(f"⚠️ [CONCURRENCY BLOCKED] Another backup job is already running.")
        print(f"Check active processes or the dashboard before trying again.")
        return False

    job_id = Path(config_path).stem
    target_dir = os.path.join(backup_root, job_id)
    
    # Always send logs to the central data/logs directory regardless of backup_root
    project_root = Path(__file__).parent.parent
    log_dir = os.path.join(str(project_root), "data", "logs")
    
    # Always create the log dir if we are logging to file
    if log_to_file:
        os.makedirs(log_dir, exist_ok=True)
        
    # If dry run, don't create target_dir if it doesn't exist, to avoid side effects
    if not dry_run:
        os.makedirs(target_dir, exist_ok=True)

    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{job_id}_{timestamp_str}.log")
    
    def log(msg):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[{timestamp}] {msg}"
        print(formatted_msg)
        if log_to_file and os.path.exists(log_dir):
            with open(log_file, 'a') as f:
                f.write(formatted_msg + "\n")

    if dry_run:
        log(f"🧪 [DRY RUN] Starting dry run backup for {name} ({host})")
    else:
        log(f"🚀 Starting backup for {name} ({host})")

    # Base rsync command
    ssh_opts = f"ssh -i {ssh_key} -p {port} -o StrictHostKeyChecking=no"
    cmd = [
        "rsync",
        "-avz",
        "--delete",
        "-e", ssh_opts
    ]

    # Purge excluded files from mirror if requested in YAML or via ENV
    delete_excluded = config.get('delete_excluded', False)
    if os.environ.get('DELETE_EXCLUDED', 'false').lower() == 'true':
        delete_excluded = True

    if delete_excluded:
        cmd.append("--delete-excluded")
    
    if dry_run:
        cmd.append("--dry-run")

    # Add explicit includes first (highest priority)
    includes = config.get('includes', [])
    for inc in includes:
        # Use unanchored patterns to be more flexible with source path roots
        cmd.extend(["--filter", f"+ {inc}"])
        cmd.extend(["--filter", f"+ {inc}/**"])

    # Add filters from the config list
    for f in filters:
        filter_file = Path("config/filters") / f
        if filter_file.exists():
            # Use rsync merge-file syntax (. file)
            # This correctly handles the +/- prefixes in our filter files.
            cmd.extend(["--filter", f". {filter_file.absolute()}"])
        else:
            log(f"⚠️ Warning: Filter file {filter_file} not found.")

    for exc in excludes:
        cmd.extend(["--exclude", exc])

    if mode == 'system':
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
            process = subprocess.Popen(
                full_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            for line in process.stdout:
                if log_to_file and os.path.exists(log_dir):
                    with open(log_file, 'a', encoding='utf-8') as f:
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

    if success and config.get('snapshot', False) and not dry_run:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{job_id}_{timestamp}.tar.gz"
        archive_path = os.path.join(backup_root, archive_name)
        log(f"📦 Creating snapshot archive: {archive_name} ...")
        
        tar_cmd = ["tar", "-czf", archive_path, "-C", backup_root, job_id]
        try:
            tar_proc = subprocess.Popen(tar_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
            for line in tar_proc.stdout:
                if log_to_file and os.path.exists(log_dir):
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(line)
                print(line, end='')
            tar_proc.wait()
            if tar_proc.returncode != 0:
                log(f"❌ Snapshot archiving failed with return code {tar_proc.returncode}")
                success = False
            else:
                log(f"✅ Snapshot successfully saved at {archive_path}")
        except Exception as e:
            log(f"❌ Error executing tar: {e}")
            success = False
            
    return success

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Home-Lab Backup Orchestrator")
    parser.add_argument("config", help="Path to the YAML configuration file")
    parser.add_argument("--no-log", action="store_false", dest="log_to_file", help="Disable logging to file")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without copying files")
    args = parser.parse_args()
    
    run_backup(args.config, log_to_file=args.log_to_file, dry_run=args.dry_run)
