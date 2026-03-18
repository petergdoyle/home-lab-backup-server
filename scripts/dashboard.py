import streamlit as st
import yaml
import os
from pathlib import Path
import pandas as pd

st.set_page_config(page_title="Home-Lab Backup Dashboard", layout="wide")

st.title("🏠 Home-Lab Backup Dashboard")

# --- Sidebar: Configuration Overview ---
st.sidebar.header("Backup Configurations")
config_dir = Path("config")
config_files = list(config_dir.glob("*.yaml"))

if config_files:
    for cf in config_files:
        if cf.name == "example.yaml": continue
        with open(cf, 'r') as f:
            data = yaml.safe_load(f)
            st.sidebar.markdown(f"**{data.get('name', cf.name)}**")
            st.sidebar.text(f"Host: {data.get('host')}")
            st.sidebar.text(f"Mode: {data.get('mode')}")
            st.sidebar.divider()
else:
    st.sidebar.info("No backup jobs found in config/")

# --- Main Content: Backup Stats and Logs ---
col1, col2 = st.columns([1, 1])

with col1:
    st.header("Latest Backups")
    backup_path = Path("/backup")
    if backup_path.exists():
        backups = []
        for d in backup_path.iterdir():
            if d.is_dir() and d.name != "logs":
                size = sum(f.stat().st_size for f in d.glob('**/*') if f.is_file())
                size_mb = float(size) / (1024 * 1024)
                backups.append({
                    "Job": d.name,
                    "Size (MB)": round(size_mb, 2),
                    "Last Updated": pd.to_datetime(d.stat().st_mtime, unit='s')
                })
        
        if backups:
            st.table(pd.DataFrame(backups))
        else:
            st.info("No backups found in data directory.")
    else:
        st.warning("Backup directory not found. Please ensure volume mounts are correct.")

with col2:
    st.header("Backup Logs")
    log_dir = Path("/backup/logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        if log_files:
            selected_log = st.selectbox("Select Log File", [f.name for f in log_files])
            if selected_log:
                with open(log_dir / selected_log, 'r') as f:
                    # Show last 50 lines
                    lines = f.readlines()
                    last_lines = lines[-50:] if len(lines) > 50 else lines
                    st.text_area("Log Content", "".join(last_lines), height=300)
        else:
            st.info("No log files found.")
    else:
        st.info("Log directory not found.")
    
# --- Action Center ---
st.divider()
st.header("Action Center")
if st.button("Refresh Dashboard"):
    st.rerun()
