CONFIG_DIR := config
SCRIPTS_DIR := scripts
DATA_DIR := data
SSH_DIR := ssh
VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip

# Discover backup jobs from YAML files in config/
CONFIG_FILES := $(wildcard $(CONFIG_DIR)/*.yaml)
JOBS := $(patsubst $(CONFIG_DIR)/%.yaml,%,$(CONFIG_FILES))

.PHONY: help setup build deploy stop service-logs dashboard logs clean \
	local-clean docker-clean \
	new-job-config copy-key status remote-cleanup \
	$(addprefix local-backup-,$(JOBS)) $(addprefix local-dry-run-,$(JOBS)) \
	$(addprefix local-tail-,$(JOBS)) $(addprefix local-status-,$(JOBS)) \
	$(addprefix local-kill-,$(JOBS)) \
	$(addprefix docker-backup-,$(JOBS)) $(addprefix docker-dry-run-,$(JOBS)) \
	$(addprefix docker-tail-,$(JOBS)) $(addprefix docker-status-,$(JOBS))

help:
	@echo "🏠 Home-Lab Backup Server"
	@echo "========================="
	@echo "Core Targets:"
	@echo "  setup              - Initialize local development environment"
	@echo "  new-job-config     - Interactive prompt to build a new backup configuration"
	@echo "  copy-key           - Copy the SSH public key to a remote machine"
	@echo "  setup-remote-ssh    - (Advanced) Fix remote permissions and optionally disable passwords"
	@echo "  build              - Build Docker images"
	@echo "  deploy             - Deploy the service using docker-compose"
	@echo "  stop               - Stop the service"
	@echo "  service-logs       - View logs from the backup-server container"
	@echo "  clean              - Full cleanup (local + docker)"
	@echo "  local-clean        - Remove local venv, logs, and locks"
	@echo "  docker-clean       - Stop and remove docker containers and volumes"
	@echo ""
	@echo "Local Execution (Current Machine -> Remote):"
	@echo "  local-backup-peters-imac-data  Run local backup for peters-imac-data"
	@echo "  local-dry-run-peters-imac-data Run dry-run for peters-imac-data"
	@echo "  remote-cleanup     - (Careful!) Remove junk files from remote host"
	@echo "  local-status        - Show status of all local backup processes"
	@echo "  local-tail-[job]    - Tail logs for a local job"
	@echo ""
	@echo "Docker Execution (Inside Container -> Remote):"
	@echo "  docker-backup-[job] - Trigger backup inside the container"
	@echo "  docker-dry-run-[job]- Dry-run backup inside the container"
	@echo "  docker-status       - Show status of all jobs inside the container"
	@echo "  docker-tail-[job]   - Tail logs from the container"
	@echo ""

setup:
	@echo "🔧 Setting up local environment..."
	mkdir -p $(CONFIG_DIR) $(SCRIPTS_DIR) $(DATA_DIR)/backups $(DATA_DIR)/logs $(SSH_DIR)
	@if [ ! -d $(VENV) ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv $(VENV); \
	fi
	@if [ ! -f $(SSH_DIR)/id_ed25519 ]; then \
		echo "Generating SSH key pair..."; \
		ssh-keygen -t ed25519 -f $(SSH_DIR)/id_ed25519 -N ""; \
	fi
	@echo "Installing python dependencies locally..."
	@$(PIP) install -r requirements.txt
	@echo "✅ Setup complete."

new-job-config:
	@if [ ! -d $(VENV) ]; then echo "Error: Virtual environment not found. Run 'make setup' first."; exit 1; fi
	@$(PYTHON) $(SCRIPTS_DIR)/build_config.py

copy-key:
	@echo "This will copy your new public key to a remote server."
	@read -p "Enter user@hostname (e.g., admin@192.168.1.50): " target; \
	if [ -z "$$target" ]; then echo "Target cannot be empty."; exit 1; fi; \
	ssh-copy-id -i $(SSH_DIR)/id_ed25519.pub $$target

remote-cleanup:
	@echo "🧹 Starting remote cleanup..."
	@.venv/bin/python3 scripts/remote_cleanup.py

setup-remote-ssh:
	@read -p "Enter user@host (e.g., peter@192.168.20.12): " target; \
	if [ -z "$$target" ]; then echo "Target cannot be empty."; exit 1; fi; \
	read -p "Disable password authentication? (y/n) [n]: " disable_pass; \
	if [ "$$disable_pass" = "y" ]; then \
		./scripts/setup_remote_ssh.sh $$target disable-password; \
	else \
		./scripts/setup_remote_ssh.sh $$target; \
	fi

build:
	docker-compose build

deploy:
	docker-compose up -d

stop:
	docker-compose stop

service-logs:
	docker-compose logs -f backup-server

dashboard:
	@echo "Opening dashboard..."
	@open http://localhost:8502 || echo "Visit http://localhost:8502"

logs:
	docker-compose logs -f

clean: local-clean docker-clean

local-clean:
	@echo "🧹 Cleaning local environment..."
	@rm -rf data/logs/*.log
	@rm -f data/.backup.lock
	@echo "⚠️  WARNING: This will delete all local backup data (mirror files and archives) in data/."
	@read -p "Are you sure? [y/N]: " confirm1 && [ "$$confirm1" = "y" ] || (echo "Aborted."; exit 1)
	@read -p "Type 'DELETE' to confirm archiving/deletion: " confirm2 && [ "$$confirm2" = "DELETE" ] || (echo "Aborted."; exit 1)
	@# Delete job-specific mirror directories in data/ (except logs, ssh, and backups self-folder)
	@find data -maxdepth 1 -type d ! -name data ! -name logs ! -name backups ! -name ssh -exec rm -rf {} +
	@# ALSO delete everything INSIDE data/backups/ (where snapshots or mis-routed mirrors might be)
	@find data/backups -mindepth 1 ! -name .gitkeep -exec rm -rf {} +
	@echo "✅ Local environment cleaned."

docker-clean:
	@echo "🧹 Cleaning Docker environment..."
	docker-compose down -v
	@echo "✅ Docker environment cleaned."

# --- LOCAL TARGETS ---

$(addprefix local-backup-,$(JOBS)): local-backup-%: $(CONFIG_DIR)/%.yaml
	@if [ ! -d $(VENV) ]; then echo "Error: Virtual environment not found. Run 'make setup' first."; exit 1; fi
	@echo "🚀 Starting local backup job: $*"
	@DELETE_EXCLUDED=$(DELETE_EXCLUDED) $(PYTHON) $(SCRIPTS_DIR)/backup.py $< > /dev/null 2>&1 & \
	echo "✅ Job $* is now running in background."

$(addprefix local-dry-run-,$(JOBS)): local-dry-run-%: $(CONFIG_DIR)/%.yaml
	@if [ ! -d $(VENV) ]; then echo "Error: Virtual environment not found. Run 'make setup' first."; exit 1; fi
	@echo "🧪 Starting local dry-run backup job: $*"
	DELETE_EXCLUDED=$(DELETE_EXCLUDED) $(PYTHON) $(SCRIPTS_DIR)/backup.py $< --dry-run

$(addprefix local-tail-,$(JOBS)): local-tail-%:
	@if [ -f data/logs/$*.log ]; then \
		tail -f data/logs/$*.log; \
	else \
		echo "⚠️ No local log file found for $*."; \
	fi

$(addprefix local-status-,$(JOBS)): local-status-%:
	@PID=$$(pgrep -f "backup.py $(CONFIG_DIR)/$*.yaml" || true); \
	if [ -n "$$PID" ]; then \
		echo "🟢 Local Job $* is RUNNING (PID: $$PID)"; \
	else \
		echo "⚪ Local Job $* is IDLE"; \
	fi

local-status:
	@echo "📊 Local Backup Status"
	@$(foreach job,$(JOBS),$(MAKE) --no-print-directory local-status-$(job);)

$(addprefix local-kill-,$(JOBS)): local-kill-%:
	@echo "🛑 Stopping local backup job: $*"
	@pkill -f "backup.py $(CONFIG_DIR)/$*.yaml" || echo "⚠️ No active local job found for $*"

# --- DOCKER TARGETS ---

$(addprefix docker-backup-,$(JOBS)): docker-backup-%:
	@echo "🚀 Triggering backup job inside container: $*"
	docker exec backup-server python scripts/backup.py $(CONFIG_DIR)/$*.yaml

$(addprefix docker-dry-run-,$(JOBS)): docker-dry-run-%:
	@echo "🧪 Running dry-run inside container: $*"
	docker exec backup-server python scripts/backup.py $(CONFIG_DIR)/$*.yaml --dry-run

$(addprefix docker-tail-,$(JOBS)): docker-tail-%:
	docker exec backup-server tail -f data/logs/$*.log

$(addprefix docker-status-,$(JOBS)): docker-status-%:
	@echo "Checking status of $* inside container..."
	@docker exec backup-server pgrep -f "backup.py $(CONFIG_DIR)/$*.yaml" > /dev/null \
		&& echo "🟢 Docker Job $* is RUNNING" \
		|| echo "⚪ Docker Job $* is IDLE"

docker-status:
	@echo "📊 Docker Container Backup Status"
	@$(foreach job,$(JOBS),$(MAKE) --no-print-directory docker-status-$(job);)
