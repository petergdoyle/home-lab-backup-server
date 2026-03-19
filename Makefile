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

.PHONY: help setup build deploy stop service-logs dashboard logs clean $(addprefix backup-,$(JOBS))

help:
	@echo "🏠 Home-Lab Backup Server"
	@echo "========================="
	@echo "Available targets:"
	@echo "  setup         - Initialize local development environment (venv, ssh keys, dirs)"
	@echo "  new-job       - Interactive prompt to build a new backup configuration"
	@echo "  copy-key      - Copy the SSH public key to a remote machine"
	@echo "  build         - Build Docker images"
	@echo "  deploy        - Deploy the service using docker-compose"
	@echo "  stop          - Stop the service"
	@echo "  service-logs  - View logs from the backup-server container"
	@echo "  dashboard     - Open the dashboard (http://localhost:8502)"
	@echo "  clean         - Remove logs and temporary files"
	@echo ""
	@echo "Backup Jobs (dynamically discovered from $(CONFIG_DIR)/):"
	@$(if $(JOBS), \
		$(foreach job,$(JOBS),echo "  backup-$(job)  - Run backup for job: $(job)";), \
		echo "  (No jobs found in $(CONFIG_DIR)/)")
	@echo ""
	@$(if $(JOBS), \
		$(foreach job,$(JOBS),echo "  dry-run-$(job) - Dry-run backup for job: $(job)";), \
		echo "  (No jobs found in $(CONFIG_DIR)/)")
	@echo ""
	@echo "Log Tailing Jobs:"
	@$(if $(JOBS), \
		$(foreach job,$(JOBS),echo "  tail-$(job)    - Tail logs for job: $(job)";), \
		echo "  (No jobs found in $(CONFIG_DIR)/)")

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

new-job:
	@if [ ! -d $(VENV) ]; then echo "Error: Virtual environment not found. Run 'make setup' first."; exit 1; fi
	@$(PYTHON) $(SCRIPTS_DIR)/build_config.py

copy-key:
	@echo "This will copy your new public key to a remote server."
	@read -p "Enter user@hostname (e.g., admin@192.168.1.50): " target; \
	if [ -z "$$target" ]; then echo "Target cannot be empty."; exit 1; fi; \
	ssh-copy-id -i $(SSH_DIR)/id_ed25519.pub $$target

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

clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	rm -rf $(VENV)
	@echo "✅ Cleaned."

# Dynamic backup targets
$(addprefix backup-,$(JOBS)): backup-%: $(CONFIG_DIR)/%.yaml
	@if [ ! -d $(VENV) ]; then echo "Error: Virtual environment not found. Run 'make setup' first."; exit 1; fi
	@echo "🚀 Starting backup job: $*"
	@DELETE_EXCLUDED=$(DELETE_EXCLUDED) $(PYTHON) $(SCRIPTS_DIR)/backup.py $< > /dev/null 2>&1 & \
	if [ "$(TAIL_LOG)" = "true" ]; then \
		echo "📊 Tailing log for $*..."; \
		sleep 1; \
		tail -f data/logs/$*.log; \
	else \
		echo "✅ Job $* is now running in background."; \
		echo "   Tail logs with: make tail-$*"; \
	fi

# Dynamic dry-run targets
$(addprefix dry-run-,$(JOBS)): dry-run-%: $(CONFIG_DIR)/%.yaml
	@if [ ! -d $(VENV) ]; then echo "Error: Virtual environment not found. Run 'make setup' first."; exit 1; fi
	@echo "🧪 Starting dry-run backup job: $*"
	DELETE_EXCLUDED=$(DELETE_EXCLUDED) $(PYTHON) $(SCRIPTS_DIR)/backup.py $< --dry-run

# Dynamic tail targets
$(addprefix tail-,$(JOBS)): tail-%:
	@if [ -f data/logs/$*.log ]; then \
		tail -f data/logs/$*.log; \
	else \
		echo "⚠️ No log file found for $*. Run a backup first."; \
	fi

# Dynamic kill targets
$(addprefix backup-kill-,$(JOBS)): backup-kill-%:
	@echo "🛑 Stopping backup job: $*"
	@pkill -f "backup.py $(CONFIG_DIR)/$*.yaml" || echo "⚠️ No active job found for $*"
