import argparse
import datetime
import fcntl
import os
import subprocess
import sys
import time
from pathlib import Path
import yaml

def run_backup(config_path, log_to_file=True, dry_run=False, show_excluded=False):
    if show_excluded:
        dry_run = True

    # Determine basic job info first for logging
    job_id = Path(config_path).stem
    project_root = Path(__file__).parent.parent
    log_dir = os.path.join(str(project_root), "data", "logs")
    log_file = os.path.join(log_dir, f"{job_id}.log")
    
    if log_to_file:
        os.makedirs(log_dir, exist_ok=True)

    def log(msg):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[{timestamp}] {msg}"
        print(formatted_msg)
        if log_to_file and os.path.exists(log_dir):
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(formatted_msg + "\n")

    # Initial log attempt
    log(f"--- Starting session for {job_id} ---")

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        log(f"❌ YAML Error: Could not load configuration {config_path}: {e}")
        return False

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
    max_retries = config.get('retries', 0)
    retry_interval = config.get('retry_interval', 5) # minutes

    # Handle local vs docker pathing
    if backup_root == '/backup' and not os.path.exists('/backup'):
        # If /backup isn't available (running locally), use the 'data/backups' dir in project root
        project_root = Path(__file__).parent.parent
        backup_root = str(project_root / "data" / "backups")
        log(f"ℹ️ Redirecting /backup to local {backup_root}")

    # Ensure backup_root exists for the lock file
    os.makedirs(backup_root, exist_ok=True)
    
    # Global Job Lock
    lock_file_path = os.path.join(backup_root, f".{job_id}.lock")
    lock_file = open(lock_file_path, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log(f"⚠️ [CONCURRENCY BLOCKED] Another backup job for '{job_id}' is already running.")
        return False

    target_dir = os.path.join(backup_root, job_id)
    
    # If dry run, don't create target_dir if it doesn't exist, to avoid side effects
    if not dry_run:
        os.makedirs(target_dir, exist_ok=True)

    if dry_run:
        log(f"🧪 [DRY RUN] Starting dry run backup for {name} ({host})")
    else:
        log(f"🚀 Starting backup for {name} ({host})")

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

    if show_excluded:
        cmd.append("--debug=FILTER")

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
    
    if source_paths is None:
        source_paths = []

    if not source_paths:
        log(f"⚠️ No source paths defined for {name}. Skipping.")
        return

    success = True
    for source in source_paths:
        if host:
            remote_source = f"{user}@{host}:{source}"
            ssh_opts = f"ssh -i {ssh_key} -p {port} -o StrictHostKeyChecking=no"
            current_cmd = cmd + ["-e", ssh_opts, remote_source, target_dir]
        else:
            remote_source = source
            current_cmd = cmd + [remote_source, target_dir]
        
        attempt = 0
        while attempt <= max_retries:
            if attempt > 0:
                log(f"🔄 Retry attempt {attempt}/{max_retries} for {source} (waiting {retry_interval}m)...")
                time.sleep(retry_interval * 60)

            log(f"Executing: {' '.join(current_cmd)}")
            try:
                process = subprocess.Popen(
                    current_cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                for line in process.stdout:
                    if show_excluded:
                        if "[sender] hiding file" in line:
                            msg = line.replace("[sender] hiding file ", "🚫 [EXCLUDED] ")
                            if log_to_file and os.path.exists(log_dir):
                                with open(log_file, 'a', encoding='utf-8') as f:
                                    f.write(msg)
                            print(msg, end='')
                        continue

                    if log_to_file and os.path.exists(log_dir):
                        with open(log_file, 'a', encoding='utf-8') as f:
                            f.write(line)
                    print(line, end='')
                process.wait()
                
                if process.returncode == 0:
                    log(f"✅ Backup successful for {source}")
                    break
                else:
                    log(f"❌ Backup failed for {source} with return code {process.returncode}")
                    attempt += 1
                    if attempt > max_retries:
                        success = False
            except Exception as e:
                log(f"❌ Error executing rsync: {e}")
                attempt += 1
                if attempt > max_retries:
                    success = False

    if success and config.get('snapshot', False) and not dry_run:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{job_id}_{timestamp}.tar.gz"
        
        # Save archives in 'data/archive'
        archive_root = os.path.join(os.path.dirname(backup_root), "archive")
        os.makedirs(archive_root, exist_ok=True)
        archive_path = os.path.join(archive_root, archive_name)
        
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
    parser.add_argument("--show-excluded", action="store_true", help="Dry run showing which files are being excluded")
    args = parser.parse_args()
    
    run_backup(args.config, log_to_file=args.log_to_file, dry_run=args.dry_run, show_excluded=args.show_excluded)
