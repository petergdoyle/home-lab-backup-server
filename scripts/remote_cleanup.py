#!/usr/bin/env python3
import os
import sys
import yaml
import subprocess
from pathlib import Path

def get_input(prompt, default=""):
    value = input(f"{prompt} [{default}]: ").strip()
    return value if value else default

def run_remote_cleanup():
    print("✨ Remote Cleanup Tool ✨")
    print("This tool will permanently delete items from a remote host based on a list.")
    
    # Try to find existing configs for convenience
    config_dir = Path("config")
    yaml_files = list(config_dir.glob("*.yaml"))
    
    use_existing = "n"
    if yaml_files:
        print("\nFound existing backup configurations:")
        for i, f in enumerate(yaml_files, 1):
            print(f"  {i}. {f.name}")
        use_existing = get_input("\nWould you like to pull connection details from one of these?", "n").lower()

    host, user, port, ssh_key, remote_home = "", "", "22", "ssh/id_ed25519", ""
    
    if use_existing == 'y' or (use_existing.isdigit() and 1 <= int(use_existing) <= len(yaml_files)):
        idx = int(use_existing) - 1 if use_existing.isdigit() else 0
        with open(yaml_files[idx], 'r') as f:
            config = yaml.safe_load(f)
            host = config.get('host', '')
            user = config.get('user', '')
            port = str(config.get('port', '22'))
            ssh_key = config.get('ssh_key', 'ssh/id_ed25519')
            # remote_home is usually the first source path in our setup
            source_paths = config.get('source_paths', [])
            if source_paths:
                remote_home = source_paths[0]
    
    # Prompt for details (pre-filled with config or defaults)
    host = get_input("Target Host (IP or hostname)", host)
    user = get_input("SSH Username", user)
    port = get_input("SSH Port", port)
    ssh_key = get_input("Path to SSH Private Key", ssh_key)
    remote_home = get_input("Remote Home/Root Directory", remote_home)
    
    # Prompt for cleanup list
    cleanup_lists = list(config_dir.glob("*-cleanup.txt"))
    default_list = cleanup_lists[0].name if cleanup_lists else "cleanup-list.txt"
    list_input = get_input("Cleanup List File (in config/)", default_list)
    
    # Robustness: if they type 'y' but it isn't a file, and default_list exists, use default
    list_file_name = list_input
    if list_input.lower() == 'y' and not (config_dir / list_input).exists():
        list_file_name = default_list
        
    list_file = config_dir / list_file_name
    
    if not list_file.exists():
        print(f"❌ Error: List file '{list_file}' not found.")
        sys.exit(1)

    # Read items
    with open(list_file, 'r') as f:
        items = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    if not items:
        print("⚠️ No items found in the cleanup list. Nothing to do.")
        sys.exit(0)

    print("\n" + "="*50)
    print("🚦 SAFETY VERIFICATION - PHASE 1")
    print("="*50)
    print(f"Target Host:   {user}@{host}:{port}")
    print(f"Remote Home:   {remote_home}")
    print(f"Cleanup List:  {list_file.name}")
    print(f"Number of items to DELETE: {len(items)}")
    print("-" * 50)
    
    confirm1 = get_input("Are these details correct? (y/N)", "n").lower()
    if confirm1 != 'y':
        print("Aborted.")
        sys.exit(0)

    print("\n" + "="*50)
    print("🚦 SAFETY VERIFICATION - PHASE 2")
    print("="*50)
    print("THE FOLLOWING ITEMS WILL BE PERMANENTLY REMOVED:")
    for item in items:
        print(f"  [DELETE] {remote_home}/{item}")
    print("-" * 50)
    
    print("\n⚠️  CAUTION: This action cannot be undone.")
    confirm2 = get_input(f"To confirm deletion, please type 'DELETE' exactly", "").strip()
    
    if confirm2 != 'DELETE':
        print("Verification failed. Aborted.")
        sys.exit(0)

    print("\n🚀 Starting cleanup...")
    
    for item in items:
        print(f"  Removing: {item} ...")
        # Construct path carefully
        remote_path = os.path.join(remote_home, item)
        # Use ssh command
        ssh_cmd = [
            "ssh", "-i", ssh_key,
            "-p", port,
            f"{user}@{host}",
            f"rm -rf \"{remote_path}\""
        ]
        
        try:
            subprocess.run(ssh_cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to remove {item}: {e}")

    print("\n✅ Remote cleanup complete.")

if __name__ == "__main__":
    try:
        run_remote_cleanup()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
