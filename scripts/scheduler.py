import schedule
import time
import yaml
import os
from pathlib import Path
from backup import run_backup

CONFIG_DIR = Path("config")

def load_jobs():
    jobs = []
    for config_file in CONFIG_DIR.glob("*.yaml"):
        if config_file.name == "example.yaml": continue
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                config['path'] = str(config_file)
                jobs.append(config)
        except Exception as e:
            print(f"Error loading {config_file}: {e}")
    return jobs

def job_wrapper(config_path):
    print(f"⏰ Scheduled trigger for: {config_path}")
    run_backup(config_path)

def setup_schedule():
    schedule.clear()
    jobs = load_jobs()
    for job in jobs:
        cron_str = job.get('schedule')
        if cron_str:
            # For simplicity in this version, we support basic minute/hour intervals 
            # Or we can use python-crontab for full cron support.
            # Let's start with a simple "every day at HH:MM" or "every X minutes"
            if cron_str.startswith("every"):
                parts = cron_str.split()
                if "minute" in cron_str:
                    schedule.every(int(parts[1])).minutes.do(job_wrapper, job['path'])
                elif "hour" in cron_str:
                    schedule.every(int(parts[1])).hours.do(job_wrapper, job['path'])
            else:
                # Assume HH:MM format for daily
                try:
                    schedule.every().day.at(cron_str).do(job_wrapper, job['path'])
                    print(f"Scheduled {job['name']} daily at {cron_str}")
                except Exception as e:
                    print(f"Invalid schedule format for {job['name']}: {cron_str}. Expected 'HH:MM' or 'every X minutes'")

if __name__ == "__main__":
    print("🕰️ Backup Scheduler Starting...")
    setup_schedule()
    
    # Watch for config changes every minute
    last_mtime = 0
    
    while True:
        # Check if config dir has changed to reload schedules
        current_mtime = os.path.getmtime(CONFIG_DIR)
        if current_mtime > last_mtime:
            print("🔄 Config change detected. Reloading schedules...")
            setup_schedule()
            last_mtime = current_mtime
            
        schedule.run_pending()
        time.sleep(1)
