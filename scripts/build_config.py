import yaml
import os
from pathlib import Path

def prompt(message, default=None):
    if default is not None:
        if default == "":
            res = input(f"{message}: ").strip()
        else:
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
    
    print("\nSelect Backup Type:")
    print("  1. 'Data'   - Personal files (Documents, Media, etc.)")
    print("                Excludes hidden/system files by default.")
    print("  2. 'System' - Full OS/User restoration.")
    print("                Includes nearly everything for recovery.")
    
    type_choice = prompt("Choose type (1 or 2)", "1")
    config['mode'] = 'system' if type_choice == '2' else 'data'
    
    import platform
    current_os = 'macos' if platform.system() == 'Darwin' else 'linux'
    
    # --- Filter Logic ---
    config['filters'] = ['common-excludes.txt']
    
    print("\nConfigure Group-based Exclusions:")
    is_data = config['mode'] == 'data'
    
    if prompt_bool("Exclude Virtual Machines & Disk Images?", "y" if is_data else "n"):
        config['filters'].append("group-vms.txt")
        
    if prompt_bool("Exclude Developer Junk (node_modules, venv, build folders)?", "y" if is_data else "n"):
        config['filters'].append("group-dev.txt")
        
    if prompt_bool("Exclude Cloud Storage artifacts (iCloud, Google Drive, Dropbox)?", "y" if is_data else "n"):
        config['filters'].append("group-cloud.txt")
        
    if prompt_bool("Exclude Media Library Caches (Spotify, Plex, etc.)?", "y" if is_data else "n"):
        config['filters'].append("group-media.txt")
        
    if prompt_bool("Exclude Communication App Bloat (Slack, Teams, Discord)?", "y" if is_data else "n"):
        config['filters'].append("group-apps.txt")

    if prompt_bool("Exclude all hidden files/directories (.*)?", "y" if is_data else "n"):
        config['filters'].append("group-hidden.txt")

    if is_data:
        config['filters'].append(f"{current_os}-data.txt")
    else:
        full_filter = f"{current_os}-full.txt" if current_os == 'macos' else f"{current_os}-sys.txt"
        config['filters'].append(full_filter)

    print(f"ℹ️ Applied filter groups: {', '.join(config['filters'])}")

    config['includes'] = []
    if config['mode'] == 'data':
        if prompt_bool("\nWould you like to include hidden configuration (like .ssh or shell profiles)?", "y"):
            hidden_inc = prompt("Enter hidden files to include (space separated)", ".ssh .zshrc .bash_profile .bashrc .gitconfig")
            config['includes'] = [item.strip() for item in hidden_inc.split() if item.strip()]

    config['source_paths'] = []
    if config['mode'] == 'data':
        default_home = os.path.expanduser("~")
        path = prompt("\nEnter source path to backup", default_home)
        config['source_paths'].append(path)
    else:
        config['source_paths'] = ["/"]

    config['exclude'] = []
    if prompt_bool("\nDo you want to add additional custom exclude patterns?", "n"):
        print("Enter exclude patterns. Leave blank to finish.")
        while True:
            exc = input("Exclude pattern: ").strip()
            if not exc:
                break
            config['exclude'].append(exc)
            
    config['snapshot'] = prompt_bool("\nDo you want to automatically compress a point-in-time snapshot archive (.tar.gz) after each backup?", "n")
    
    config['delete_excluded'] = prompt_bool("\nShould we purge (delete-excluded) files from the mirror if they are added to filters later?", "n")

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
    job_name = safe_filename.replace('.yaml', '')
    print(f"Run `make local-dry-run-{job_name}` to verify filters.")
    print(f"Run `make local-backup-{job_name}` to start the backup.")

if __name__ == "__main__":
    try:
        build_config()
    except KeyboardInterrupt:
        print("\nConfiguration aborted.")
