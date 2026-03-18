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
	@echo "  build         - Build Docker images"
	@echo "  deploy        - Deploy the service using docker-compose"
	@echo "  stop          - Stop the service"
	@echo "  service-logs  - View logs from the backup-server container"
	@echo "  dashboard     - Open the dashboard (http://localhost:8502)"
	@echo "  clean         - Remove logs and temporary files"
	@echo ""
	@echo "Backup Jobs (dynamically discovered from $(CONFIG_DIR)/):"
	@$(if $(JOBS), \
		$(foreach job,$(JOBS),echo "  backup-$(job) - Run backup for job: $(job)";), \
		echo "  (No jobs found in $(CONFIG_DIR)/)")

setup:
	@echo "🔧 Setting up local environment..."
	mkdir -p $(CONFIG_DIR) $(SCRIPTS_DIR) $(DATA_DIR)/backups $(DATA_DIR)/logs $(SSH_DIR)
	@if [ ! -d $(VENV) ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv $(VENV); \
	fi
	@if [ ! -f $(SSH_DIR)/id_rsa ]; then \
		echo "Generating SSH key pair..."; \
		ssh-keygen -t rsa -b 4096 -f $(SSH_DIR)/id_rsa -N ""; \
	fi
	@echo "Installing python dependencies locally..."
	@$(PIP) install -r requirements.txt
	@echo "✅ Setup complete."

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
	$(PYTHON) $(SCRIPTS_DIR)/backup.py $<
