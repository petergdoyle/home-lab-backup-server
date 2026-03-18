import yaml
import os
from pathlib import Path

def prompt(message, default=None):
    if default:
        res = input(f"{message} [{default}]: ").strip()
        return res if res else default
    else:
        res = input(f"{message}: ").strip()
        while not res:
            print("This field is required.")
            res = input(f"{message}: ").strip()
        return res

def prompt_bool(message, default="y"):
    res = input(f"{message} (y/n) [{default}]: ").strip().lower()
    if not res:
        res = default
    return res.startswith('y')

def build_config():
    print("✨ Home-Lab Backup Server - Configuration Builder ✨\n")
    
    config = {}
    
    config['name'] = prompt("Job Name (e.g., 'My Database Server')")
    # Generate a safe filename
    safe_filename = config['name'].lower().replace(" ", "-").replace("/", "-") + ".yaml"
    filename = prompt("Configuration filename", safe_filename)
    
    config['host'] = prompt("Target Host (IP or hostname)")
    config['user'] = prompt("SSH Username", "root")
    config['port'] = int(prompt("SSH Port", "22"))
    config['ssh_key'] = prompt("Path to SSH Private Key", "ssh/id_ed25519")
    
    print("\nSelect Backup Mode:")
    print("  1. 'data' - Backup specific directories only")
    print("  2. 'full' - Backup the entire OS from root (/)")
    mode_choice = prompt("Choose mode (1 or 2)", "1")
    config['mode'] = 'full' if mode_choice == '2' else 'data'
    
    config['filters'] = []
    filter_dir = Path("config/filters")
    if filter_dir.exists():
        print("\nAvailable predefined filter sets:")
        available_filters = [f.name for f in filter_dir.glob("*.txt") if f.is_file()]
        for f in available_filters:
            if prompt_bool(f"Apply '{f}'?", "y" if "common" in f else "n"):
                config['filters'].append(f)
    
    config['source_paths'] = []
    if config['mode'] == 'data':
        print("\nEnter source paths to backup (e.g., /home/user). Leave blank to finish.")
        while True:
            path = input("Source path: ").strip()
            if not path:
                if len(config['source_paths']) > 0:
                    break
                else:
                    print("You must enter at least one source path for 'data' mode.")
                    continue
            config['source_paths'].append(path)
    
    config['exclude'] = []
    if prompt_bool("\nDo you want to add custom exclude patterns? (e.g., '*.tmp', '.cache')", "n"):
        print("Enter exclude patterns. Leave blank to finish.")
        while True:
            exc = input("Exclude pattern: ").strip()
            if not exc:
                break
            config['exclude'].append(exc)
            
    config['backup_root'] = prompt("\nTarget backup directory inside the backup-server", "/backup")
    
    schedule = prompt("Schedule (e.g., '02:00' for daily at 2AM, or 'every 60 minutes'. Leave blank for no schedule)", "")
    if schedule:
        config['schedule'] = schedule

    # Determine save path
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    save_path = config_dir / filename
    
    # Save the YAML
    print(f"\nSaving configuration to {save_path} ...")
    with open(save_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
    print(f"✅ Configuration saved successfully!")
    print(f"Run `make backup-{safe_filename.replace('.yaml', '')}` to test it locally.")

if __name__ == "__main__":
    try:
        build_config()
    except KeyboardInterrupt:
        print("\nConfiguration aborted.")
