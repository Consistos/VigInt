# Vigint API Services Makefile

.PHONY: help install dev-install test lint format clean build run docker-build docker-run setup

# Default target
help:
	@echo "Vigint API Services - Available commands:"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup          - Complete project setup"
	@echo "  make install        - Install production dependencies"
	@echo "  make dev-install    - Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make run            - Run the application"
	@echo "  make run-api        - Run only API server"
	@echo "  make run-rtsp       - Run only RTSP server"
	@echo "  make test           - Run tests"
	@echo "  make lint           - Run linting"
	@echo "  make format         - Format code"
	@echo ""
	@echo "Database:"
	@echo "  make init-db        - Initialize database"
	@echo "  make migrate        - Run database migrations"
	@echo ""
	@echo "Billing:"
	@echo "  make billing        - Run weekly billing"
	@echo "  make monitor        - Run cost monitoring"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   - Build Docker image"
	@echo "  make docker-run     - Run with Docker Compose"
	@echo "  make docker-stop    - Stop Docker containers"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Clean temporary files"
	@echo "  make logs           - Show application logs"

# Setup
setup: install init-db
	@echo "✅ Project setup complete!"

install:
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	@echo "✅ Dependencies installed"

dev-install: install
	. venv/bin/activate && pip install -e ".[dev]"
	@echo "✅ Development dependencies installed"

# Database
init-db:
	. venv/bin/activate && python3 start_vigint.py --init-db
	@echo "✅ Database initialized"

migrate:
	. venv/bin/activate && python3 -c "from vigint.models import db; db.create_all()"
	@echo "✅ Database migrated"

# Running
run:
	. venv/bin/activate && ./start.sh

run-api:
	. venv/bin/activate && ./start.sh api

run-rtsp:
	. venv/bin/activate && ./start.sh rtsp

# Testing & Quality
test:
	. venv/bin/activate && pytest

test-coverage:
	. venv/bin/activate && pytest --cov=vigint --cov-report=html

lint:
	. venv/bin/activate && flake8 vigint/ *.py
	. venv/bin/activate && mypy vigint/

format:
	. venv/bin/activate && black vigint/ *.py
	@echo "✅ Code formatted"

# Billing
billing:
	. venv/bin/activate && python3 generate_weekly_invoices.py

monitor:
	. venv/bin/activate && python3 cost_monitor.py

# Docker
docker-build:
	docker build -t vigint:latest .
	@echo "✅ Docker image built"

docker-run:
	docker-compose up -d
	@echo "✅ Docker containers started"

docker-stop:
	docker-compose down
	@echo "✅ Docker containers stopped"

docker-logs:
	docker-compose logs -f vigint

# MediaMTX
download-mediamtx:
	@if [ ! -f mediamtx ]; then \
		echo "Downloading MediaMTX..."; \
		wget -O mediamtx.tar.gz https://github.com/bluenviron/mediamtx/releases/latest/download/mediamtx_linux_amd64.tar.gz; \
		tar -xzf mediamtx.tar.gz; \
		chmod +x mediamtx; \
		rm mediamtx.tar.gz; \
		echo "✅ MediaMTX downloaded"; \
	else \
		echo "MediaMTX already exists"; \
	fi

# Maintenance
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete
	find . -type f -name "*.pid" -delete
	find . -type f -name "cost_report.txt" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	@echo "✅ Cleaned temporary files"

logs:
	tail -f vigint.log

rtsp-logs:
	tail -f mediamtx.log

# Configuration
config:
	@if [ ! -f config.ini ]; then \
		cp config.ini.example config.ini; \
		echo "✅ Created config.ini from template"; \
		echo "⚠️  Please edit config.ini with your settings"; \
	else \
		echo "config.ini already exists"; \
	fi

# Cron setup
install-cron:
	@echo "Setting up cron jobs..."
	@echo "# Vigint weekly billing - Mondays at 9 AM" | crontab -
	@echo "0 9 * * 1 $(PWD)/run_weekly_billing.py" | crontab -
	@echo "# Vigint cost monitoring - Daily at 8 AM" | crontab -
	@echo "0 8 * * * $(PWD)/cost_monitor.py" | crontab -
	@echo "✅ Cron jobs installed"

# Health checks
health:
	@echo "Checking application health..."
	@curl -f http://localhost:5000/api/health || echo "❌ API not responding"
	@curl -f http://localhost:9997/v1/config/global/get || echo "❌ RTSP server not responding"

# Development helpers
dev-setup: dev-install config download-mediamtx init-db
	@echo "✅ Development environment ready!"

prod-setup: install config init-db
	@echo "✅ Production environment ready!"

# Backup
backup:
	@echo "Creating backup..."
	@mkdir -p backups
	@tar -czf backups/vigint-backup-$(shell date +%Y%m%d-%H%M%S).tar.gz \
		--exclude=venv \
		--exclude=__pycache__ \
		--exclude=*.log \
		--exclude=backups \
		.
	@echo "✅ Backup created in backups/"