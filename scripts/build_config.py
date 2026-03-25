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
    
    # --- Mode-Specific Filter Baseline ---
    is_data = config['mode'] == 'data'
    config['filters'] = ['common-excludes.txt']
    
    if is_data:
        config['filters'].append(f"{current_os}-data.txt")
    else:
        full_filter = f"{current_os}-full.txt" if current_os == 'macos' else f"{current_os}-sys.txt"
        config['filters'].append(full_filter)

    # --- Interactive Group Toggles ---
    print(f"\nConfigure Filter Groups ({'Data: Exclusive' if is_data else 'System: Inclusive'}):")
    
    # Defaults: Data mode EXCLUDES by default (y), System mode INCLUDES by default (n)
    def_exc = "y" if is_data else "n"
    
    groups = [
        ("Exclude Virtual Machines & Disk Images? (group-vms.txt)", "group-vms.txt"),
        ("Exclude Developer Junk? (node_modules, venv, target, .git) (group-dev.txt)", "group-dev.txt"),
        ("Exclude Cloud Storage folders? (iCloud, Dropbox, OneDrive) (group-cloud.txt)", "group-cloud.txt"),
        ("Exclude Heavy Media? (Movies, Music, Pictures, Lightroom) (group-media.txt)", "group-media.txt"),
        ("Exclude Apps & Caches? (Slack, Teams, Discord, ~/Library/Caches) (group-apps.txt)", "group-apps.txt"),
        ("Exclude ALL hidden files/folders? (.*) (group-hidden.txt)", "group-hidden.txt")
    ]
    
    for msg, f in groups:
        if prompt_bool(msg, def_exc):
            config['filters'].append(f)

    # --- Mode-aware User Content Overrides (Data Mode Only) ---
    config['exclude'] = []
    if is_data:
        print("\nUser Content Selection (Optional Exclusions):")
        # In Data mode, we usually WANT these, so default to 'n' (don't exclude)
        content_groups = [
            ("Exclude Desktop folder?", "Desktop/"),
            ("Exclude Documents folder?", "Documents/"),
            ("Exclude Downloads folder?", "Downloads/"),
            ("Exclude Movies folder? (redundant if Media group is active)", "Movies/"),
            ("Exclude Music folder? (redundant if Media group is active)", "Music/"),
            ("Exclude Pictures folder? (redundant if Media group is active)", "Pictures/"),
            ("Exclude Public folder?", "Public/"),
        ]
        
        for msg, pattern in content_groups:
            # Check if it's already excluded by a group (like Movies/Music in group-media)
            already_excluded = any(f == "group-media.txt" and pattern in ["Movies/", "Music/", "Pictures/"] for f in config['filters'])
            if not already_excluded:
                if prompt_bool(msg, "n"):
                    config['exclude'].append(pattern)

    print(f"\nℹ️ Applied filter groups: {', '.join(config['filters'])}")
    if config['exclude']:
        print(f"ℹ️ Additional manual excludes: {', '.join(config['exclude'])}")

    config['includes'] = []
    if is_data:
        if prompt_bool("\nWould you like to include specific hidden config files (e.g., .ssh or .zshrc)?", "y"):
            hidden_inc = prompt("Enter hidden files to include (space separated)", ".ssh .zshrc .bash_profile .bashrc .gitconfig")
            config['includes'].extend([item.strip() for item in hidden_inc.split() if item.strip()])

    if prompt_bool("\nDo you want to add additional custom include patterns (folders or files)?", "n"):
        print("Enter include patterns. Leave blank to finish.")
        while True:
            inc = input("Include pattern: ").strip()
            if not inc:
                break
            config['includes'].append(inc)

    config['source_paths'] = []
    if is_data:
        default_home = os.path.expanduser("~")
        path = prompt("\nEnter source path to backup", default_home)
        # Standardize path: use relative if it's the current user's home
        if path == default_home:
            path = f"{os.path.basename(default_home)}"
        config['source_paths'].append(path)
    else:
        config['source_paths'] = ["/"]

    if prompt_bool("\nDo you want to add additional custom exclude patterns?", "n"):
        print("Enter exclude patterns. Leave blank to finish.")
        while True:
            exc = input("Exclude pattern: ").strip()
            if not exc:
                break
            config['exclude'].append(exc)
            
    config['snapshot'] = prompt_bool("\nDo you want to automatically compress a point-in-time snapshot archive (.tar.gz)?", "n")
    
    config['delete_excluded'] = prompt_bool("\nShould we purge (delete-excluded) files from the mirror?", "n")

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
