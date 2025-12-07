#!/bin/bash
#
# TimeMachine operational script
# Provides commands for managing the TimeMachine service
#

set -e

SCRIPT_NAME="$(basename "$0")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_usage() {
  cat << EOF
TimeMachine Control Script

Usage: $SCRIPT_NAME <command>

Commands:
  start           Start TimeMachine service
  stop            Stop TimeMachine service
  restart         Restart TimeMachine service
  status          Show service status
  logs            Show service logs (follow)
  logs-error      Show only error logs
  enable          Enable service to start on boot
  disable         Disable service from starting on boot
  update          Update TimeMachine (pull latest code)
  backup          Backup database and configuration
  restore <file>  Restore database from backup
  check           Run health checks
  help            Show this help message

Examples:
  $SCRIPT_NAME start
  $SCRIPT_NAME logs
  $SCRIPT_NAME backup
EOF
}

check_root() {
  if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This command requires root privileges${NC}"
    echo "Please run with sudo"
    exit 1
  fi
}

cmd_start() {
  check_root
  echo "Starting TimeMachine..."
  systemctl start timemachine
  systemctl start nginx
  echo -e "${GREEN}✓ Services started${NC}"
}

cmd_stop() {
  check_root
  echo "Stopping TimeMachine..."
  systemctl stop timemachine
  echo -e "${GREEN}✓ Service stopped${NC}"
}

cmd_restart() {
  check_root
  echo "Restarting TimeMachine..."
  systemctl restart timemachine
  systemctl restart nginx
  echo -e "${GREEN}✓ Services restarted${NC}"
}

cmd_status() {
  echo "=== TimeMachine Service Status ==="
  systemctl status timemachine --no-pager || true
  echo ""
  echo "=== Nginx Status ==="
  systemctl status nginx --no-pager || true
}

cmd_logs() {
  echo "Following TimeMachine logs (Ctrl+C to exit)..."
  journalctl -u timemachine -f
}

cmd_logs_error() {
  echo "Showing error logs..."
  journalctl -u timemachine -p err -n 50 --no-pager
}

cmd_enable() {
  check_root
  echo "Enabling TimeMachine to start on boot..."
  systemctl enable timemachine
  systemctl enable nginx
  echo -e "${GREEN}✓ Services enabled${NC}"
}

cmd_disable() {
  check_root
  echo "Disabling TimeMachine from starting on boot..."
  systemctl disable timemachine
  echo -e "${GREEN}✓ Service disabled${NC}"
}

cmd_update() {
  check_root
  echo "Updating TimeMachine..."

  # Check if git repo
  if [ ! -d "/opt/timemachine/.git" ]; then
    echo -e "${RED}Error: /opt/timemachine is not a git repository${NC}"
    echo "Manual update required"
    exit 1
  fi

  cd /opt/timemachine
  git pull

  # Update Python dependencies
  /opt/timemachine/venv/bin/pip install -r /opt/timemachine/backend/requirements.txt

  # Restart service
  systemctl restart timemachine

  echo -e "${GREEN}✓ Update complete${NC}"
}

cmd_backup() {
  check_root
  BACKUP_DIR="/var/backups/timemachine"
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  BACKUP_FILE="$BACKUP_DIR/timemachine_$TIMESTAMP.tar.gz"

  mkdir -p "$BACKUP_DIR"

  echo "Creating backup..."
  tar -czf "$BACKUP_FILE" \
    -C / \
    var/lib/timemachine/timemachine.db \
    var/lib/timemachine/timemachine.db-wal \
    var/lib/timemachine/timemachine.db-shm \
    etc/timemachine/timemachine.env \
    2>/dev/null || true

  echo -e "${GREEN}✓ Backup created: $BACKUP_FILE${NC}"
  echo "  Size: $(du -h "$BACKUP_FILE" | cut -f1)"
}

cmd_restore() {
  check_root
  BACKUP_FILE="$1"

  if [ -z "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file required${NC}"
    echo "Usage: $SCRIPT_NAME restore <backup-file>"
    exit 1
  fi

  if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
  fi

  echo -e "${YELLOW}Warning: This will restore database and configuration${NC}"
  read -p "Continue? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
  fi

  # Stop service
  systemctl stop timemachine

  # Restore
  tar -xzf "$BACKUP_FILE" -C /

  # Restart service
  systemctl start timemachine

  echo -e "${GREEN}✓ Restore complete${NC}"
}

cmd_check() {
  echo "=== TimeMachine Health Check ==="
  echo ""

  # Check service status
  if systemctl is-active --quiet timemachine; then
    echo -e "${GREEN}✓${NC} Service is running"
  else
    echo -e "${RED}✗${NC} Service is not running"
  fi

  # Check API endpoint
  if curl -s http://localhost:8000/api/v1/health > /dev/null; then
    echo -e "${GREEN}✓${NC} API is responding"
  else
    echo -e "${RED}✗${NC} API is not responding"
  fi

  # Check database
  if [ -f /var/lib/timemachine/timemachine.db ]; then
    DB_SIZE=$(du -h /var/lib/timemachine/timemachine.db | cut -f1)
    echo -e "${GREEN}✓${NC} Database exists ($DB_SIZE)"
  else
    echo -e "${RED}✗${NC} Database not found"
  fi

  # Check disk space
  DISK_AVAIL=$(df -h /var/lib/timemachine | tail -1 | awk '{print $4}')
  echo -e "${GREEN}✓${NC} Disk space available: $DISK_AVAIL"

  # Check memory
  MEM_AVAIL=$(free -h | grep Mem | awk '{print $7}')
  echo -e "${GREEN}✓${NC} Memory available: $MEM_AVAIL"

  # Check cameras
  CAMERA_COUNT=$(ls /dev/video* 2>/dev/null | wc -l)
  if [ "$CAMERA_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Cameras detected: $CAMERA_COUNT"
  else
    echo -e "${YELLOW}⚠${NC} No cameras detected"
  fi

  echo ""
}

# Main command dispatcher
case "${1:-}" in
  start)
    cmd_start
    ;;
  stop)
    cmd_stop
    ;;
  restart)
    cmd_restart
    ;;
  status)
    cmd_status
    ;;
  logs)
    cmd_logs
    ;;
  logs-error)
    cmd_logs_error
    ;;
  enable)
    cmd_enable
    ;;
  disable)
    cmd_disable
    ;;
  update)
    cmd_update
    ;;
  backup)
    cmd_backup
    ;;
  restore)
    cmd_restore "$2"
    ;;
  check)
    cmd_check
    ;;
  help|--help|-h)
    print_usage
    ;;
  *)
    echo -e "${RED}Error: Unknown command: ${1:-}${NC}"
    echo ""
    print_usage
    exit 1
    ;;
esac
