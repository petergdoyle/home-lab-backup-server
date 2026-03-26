# Proxmox Deployment Guide: home-lab-backup-server

This guide documents the "best practice" deployment of the `home-lab-backup-server` project within a Proxmox VE homelab environment, including recursive container support (LXC + Docker) and network optimization.

## 1. Create the Proxmox LXC Container

Create a lightweight **LXC Container** for the most efficient deployment.

### Recommended Specifications
- **OS Template**: `debian-13-standard` (Trixie) or `ubuntu-24.04-standard`.
- **Disk**: 32 GB+ (depending on your local backup storage needs).
- **CPU**: 2 Cores (Ample for rsync and dashboard).
- **Memory**: 1024 MiB RAM / 512 MiB Swap (Standard).
- **SSH**: Paste your `id_ed25519.pub` to allow passwordless access.

### Required Features ("Inception" Mode)
After creation, you **must** enable these features for Docker to function inside the LXC:
1. Go to **LXC > Options > Features > Edit**.
2. Check **Nesting** (allows the LXC to run containers).
3. Check **keyctl** (required for Docker's security layer).

> [!TIP]
> **Resource Scaling**: While 1GB RAM is sufficient for most home labs, if you are backing up datasets with millions of files, `rsync`'s memory usage increases (~100MB per 1M files). If the dashboard feels sluggish when calculating directory sizes, consider increasing RAM to 2GB.

---

## 2. Network Strategy (Omada Controller)

Ensure the backup server has a consistent IP for the dashboard and for target machines that may need to report back (if applicable).

### DHCP Partitioning & Fixed IP
1. Navigate to your DHCP server (e.g., Omada Controller).
2. Identify the **MAC address** of the LXC in Proxmox (**Network** tab).
3. Enable **Use Fixed IP Address** for the client.
4. Set the IP to match the Proxmox CT ID (e.g., CT `105` → `192.168.20.105`).

---

## 3. OS & Docker Preparation

SSH into the container (e.g., `ssh root@192.168.20.105`) and run the following:

```bash
# Update System
apt update && apt upgrade -y

# Install Prerequisites
apt install -y curl git make python3-venv

# Install Docker using the official convenience script
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Ensure Docker starts on boot
systemctl enable --now docker
```

---

## 4. Project Deployment

Clone the repository and prepare the environment:

```bash
# Clone the repository
git clone https://github.com/petergdoyle/home-lab-backup-server.git
cd home-lab-backup-server

# Initialize the environment (creates config/, data/, ssh/ directories)
make setup
```

### Important: Storage Mounts
If you are storing backups on a NAS or a separate Proxmox disk, you should mount it to the `data/` directory:
- **Proxmox Bind Mount**: `pct set 105 -mp0 /mnt/pve/backups,mp=/root/home-lab-backup-server/data`
- **NFS/CIFS**: Mount directly inside the LXC using `/etc/fstab`.

---

## 5. Docker Configuration

The `home-lab-backup-server` uses Docker Compose to run the backup scheduler and the Streamlit dashboard.

1. **Build and Deploy**:
   ```bash
   make build
   make deploy
   ```

2. **Dashboard Port**:
   The dashboard runs on port `8502` by default.

---

## 6. Host-Level Automation (Systemd)

To ensure the backup server and dashboard start automatically on LXC boot:

1. Create the service file:
   `nano /etc/systemd/system/backup-server.service`

2. Paste the following configuration:
   ```ini
   [Unit]
   Description=Home-Lab Backup Server Docker Stack
   After=docker.service network-online.target
   Requires=docker.service

   [Service]
   Type=oneshot
   RemainAfterExit=yes
   WorkingDirectory=/root/home-lab-backup-server
   ExecStart=/usr/bin/docker compose up -d
   ExecStop=/usr/bin/docker compose down

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable the service:
   ```bash
   systemctl daemon-reload
   systemctl enable --now backup-server.service
   ```

---

## 7. Access & Proxying

- **Direct Access**: `http://<LXC_IP_ADDRESS>:8502`
- **Streamlit Optimization**: If using a reverse proxy (like Nginx Proxy Manager), ensure **Websockets Support** is enabled.

---

## 8. Updating the Deployment

To pull updates and rebuild:

```bash
cd home-lab-backup-server
git pull
make build
make deploy
```
