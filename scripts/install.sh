#!/bin/bash
#
# TimeMachine Installation Script
# For Raspberry Pi 3+ running Pi OS
#
set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  TimeMachine Observation Chamber - Installation Script  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Error: Please run as root (use sudo)"
  exit 1
fi

# Check if on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
  echo "⚠️  Warning: This does not appear to be a Raspberry Pi"
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# Detect installation directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "📁 Installation from: $PROJECT_ROOT"
echo ""

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Create timestamped backup of a file
backup_file() {
  local file="$1"
  if [ -f "$file" ]; then
    local backup="${file}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$file" "$backup"
    echo "  📦 Backed up to: $backup"
  fi
}

# Idempotent directory creation with ownership
safe_mkdir() {
  local dir="$1"
  local owner="${2:-timemachine:timemachine}"

  if [ ! -d "$dir" ]; then
    mkdir -p "$dir"
    chown "$owner" "$dir"
    echo "  ✓ Created: $dir"
  fi
}

# Detect installation type
detect_installation_type() {
  if [ -f /opt/timemachine/.installed_version ]; then
    echo "upgrade"
  else
    echo "fresh"
  fi
}

# Check if systemd service exists and is active
service_exists() {
  local service="$1"
  systemctl list-unit-files | grep -q "^${service}"
}

service_is_active() {
  local service="$1"
  systemctl is-active --quiet "$service"
}

# Stop service if running
safe_stop_service() {
  local service="$1"
  if service_exists "$service" && service_is_active "$service"; then
    echo "  ⏸️  Stopping $service..."
    systemctl stop "$service"
  fi
}

# Start or restart service
safe_start_service() {
  local service="$1"
  if service_exists "$service"; then
    if service_is_active "$service"; then
      echo "  🔄 Restarting $service..."
      systemctl restart "$service"
    else
      echo "  ▶️  Starting $service..."
      systemctl start "$service"
    fi
  else
    echo "  ⚠️  Service $service not found, skipping start"
  fi
}

# ============================================================================
# INSTALLATION TYPE DETECTION
# ============================================================================

INSTALL_TYPE=$(detect_installation_type)
CURRENT_VERSION="1.0.0"

if [ "$INSTALL_TYPE" = "upgrade" ]; then
  PREVIOUS_VERSION=$(cat /opt/timemachine/.installed_version 2>/dev/null || echo "unknown")
  echo "🔄 Detected existing installation (version: $PREVIOUS_VERSION)"
  echo "   Upgrading to version: $CURRENT_VERSION"
  echo ""

  # Stop services before upgrade
  echo "⏸️  Stopping services..."
  safe_stop_service timemachine.service
  safe_stop_service nginx.service
  echo ""
else
  echo "🆕 Fresh installation detected"
  echo "   Installing version: $CURRENT_VERSION"
  echo ""
fi

# ============================================================================
# SYSTEM DEPENDENCIES
# ============================================================================

echo "📦 Installing system dependencies..."
apt-get update
apt-get install -y \
  python3 \
  python3-pip \
  python3-venv \
  python3-picamera2 \
  nginx \
  libcamera-apps \
  gstreamer1.0-tools \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  v4l-utils \
  ffmpeg \
  git \
  curl

# Install Node.js and npm (for building frontend)
if ! command -v node &> /dev/null; then
  echo "📦 Installing Node.js LTS..."
  curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
  apt-get install -y nodejs
else
  echo "✓ Node.js already installed ($(node --version))"
fi

# Ensure npm is installed (sometimes missing even with nodejs)
if ! command -v npm &> /dev/null; then
  echo "📦 Installing npm..."
  apt-get install -y npm
else
  echo "✓ npm already installed ($(npm --version))"
fi

# ============================================================================
# USER CREATION
# ============================================================================

if ! id -u timemachine &>/dev/null; then
  echo "👤 Creating timemachine user..."
  useradd -r -s /bin/false -d /opt/timemachine -m timemachine
  usermod -aG video timemachine
else
  echo "✓ User timemachine already exists"
fi

# ============================================================================
# DIRECTORY STRUCTURE
# ============================================================================

echo "📂 Creating directory structure..."
safe_mkdir /opt/timemachine "timemachine:timemachine"
safe_mkdir /var/lib/timemachine "timemachine:timemachine"
safe_mkdir /var/lib/timemachine/media "timemachine:timemachine"
safe_mkdir /var/lib/timemachine/media/recordings "timemachine:timemachine"
safe_mkdir /var/lib/timemachine/media/stills "timemachine:timemachine"
safe_mkdir /var/lib/timemachine/media/timelapse "timemachine:timemachine"
safe_mkdir /var/log/timemachine "timemachine:timemachine"
safe_mkdir /etc/timemachine "root:timemachine"

# ============================================================================
# FRONTEND BUILD
# ============================================================================

echo "🔨 Building frontend..."
if [ -d "$PROJECT_ROOT/frontend" ]; then
  cd "$PROJECT_ROOT/frontend"

  if [ ! -d "node_modules" ]; then
    echo "  Installing frontend dependencies..."
    npm install
  fi

  echo "  Building production bundle..."
  npm run build

  if [ -d "dist" ]; then
    echo "  ✓ Frontend built successfully"
  else
    echo "  ❌ Frontend build failed"
    exit 1
  fi
else
  echo "  ❌ Frontend directory not found at $PROJECT_ROOT/frontend"
  exit 1
fi

# ============================================================================
# CODE DEPLOYMENT (with backup for upgrades)
# ============================================================================

echo "📋 Deploying application files..."

# Backup existing backend on upgrade
if [ "$INSTALL_TYPE" = "upgrade" ] && [ -d /opt/timemachine/backend ]; then
  backup_dir="/opt/timemachine/backup/backend.$(date +%Y%m%d_%H%M%S)"
  echo "  📦 Backing up existing backend..."
  mkdir -p "$backup_dir"
  cp -r /opt/timemachine/backend "$backup_dir/"
fi

# Deploy backend (atomic operation)
echo "  📂 Deploying backend..."
rm -rf /opt/timemachine/backend.new
cp -r "$PROJECT_ROOT/backend" /opt/timemachine/backend.new
if [ -d /opt/timemachine/backend ]; then
  rm -rf /opt/timemachine/backend.old
  mv /opt/timemachine/backend /opt/timemachine/backend.old
fi
mv /opt/timemachine/backend.new /opt/timemachine/backend
rm -rf /opt/timemachine/backend.old

# Backup existing static files on upgrade
if [ "$INSTALL_TYPE" = "upgrade" ] && [ -d /opt/timemachine/static ]; then
  backup_dir="/opt/timemachine/backup/static.$(date +%Y%m%d_%H%M%S)"
  echo "  📦 Backing up existing frontend..."
  mkdir -p "$backup_dir"
  cp -r /opt/timemachine/static "$backup_dir/"
fi

# Deploy frontend (atomic operation)
echo "  📂 Deploying frontend..."
rm -rf /opt/timemachine/static.new
cp -r "$PROJECT_ROOT/frontend/dist" /opt/timemachine/static.new
if [ -d /opt/timemachine/static ]; then
  rm -rf /opt/timemachine/static.old
  mv /opt/timemachine/static /opt/timemachine/static.old
fi
mv /opt/timemachine/static.new /opt/timemachine/static
rm -rf /opt/timemachine/static.old

# ============================================================================
# PYTHON ENVIRONMENT
# ============================================================================

echo "🐍 Setting up Python environment..."

if [ "$INSTALL_TYPE" = "upgrade" ] && [ -d /opt/timemachine/venv ]; then
  echo "  ♻️  Recreating virtual environment for clean upgrade..."
  rm -rf /opt/timemachine/venv
fi

python3 -m venv /opt/timemachine/venv --system-site-packages
/opt/timemachine/venv/bin/pip install --upgrade pip
/opt/timemachine/venv/bin/pip install -r /opt/timemachine/backend/requirements.txt

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

DB_PATH="/var/lib/timemachine/timemachine.db"

if [ -f "$DB_PATH" ]; then
  echo "💾 Database already exists, skipping initialization"
  if [ "$INSTALL_TYPE" = "upgrade" ]; then
    echo "  ⚠️  Note: Database migrations not yet implemented"
    echo "  ⚠️  If schema changed, manual migration may be required"
  fi
else
  echo "💾 Initializing database..."
  cd /opt/timemachine/backend
  /opt/timemachine/venv/bin/python -c "import asyncio; from app.db.session import init_db; asyncio.run(init_db())"
fi

# ============================================================================
# CONFIGURATION FILES
# ============================================================================

# Environment configuration
if [ ! -f /etc/timemachine/timemachine.env ]; then
  echo "⚙️  Creating environment configuration..."
  cp "$PROJECT_ROOT/deploy/timemachine.env.example" /etc/timemachine/timemachine.env
  chmod 640 /etc/timemachine/timemachine.env
  chown root:timemachine /etc/timemachine/timemachine.env
  echo "  ⚠️  Edit /etc/timemachine/timemachine.env to customize settings"
else
  echo "✓ Environment configuration already exists"
  if [ "$INSTALL_TYPE" = "upgrade" ]; then
    echo "  ℹ️  Check for new settings in: $PROJECT_ROOT/deploy/timemachine.env.example"
  fi
fi

# Logging configuration
if [ ! -f /etc/timemachine/logging.json ]; then
  echo "⚙️  Creating logging configuration..."
  cat > /etc/timemachine/logging.json <<'EOF'
{
  "version": 1,
  "disable_existing_loggers": false,
  "formatters": {
    "default": {
      "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    },
    "detailed": {
      "format": "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "level": "INFO",
      "formatter": "default",
      "stream": "ext://sys.stdout"
    },
    "file": {
      "class": "logging.handlers.RotatingFileHandler",
      "level": "DEBUG",
      "formatter": "detailed",
      "filename": "/var/log/timemachine/app.log",
      "maxBytes": 10485760,
      "backupCount": 5
    }
  },
  "loggers": {
    "app": {
      "level": "DEBUG",
      "handlers": ["console", "file"],
      "propagate": false
    }
  },
  "root": {
    "level": "INFO",
    "handlers": ["console", "file"]
  }
}
EOF
  chmod 644 /etc/timemachine/logging.json
  chown root:timemachine /etc/timemachine/logging.json
else
  echo "✓ Logging configuration already exists"
fi

# ============================================================================
# PERMISSIONS
# ============================================================================

echo "🔐 Setting permissions..."
chown -R timemachine:timemachine /opt/timemachine
chown -R timemachine:timemachine /var/lib/timemachine
chown -R timemachine:timemachine /var/log/timemachine

# ============================================================================
# SYSTEMD SERVICE
# ============================================================================

echo "⚡ Installing systemd service..."

# Backup existing service file on upgrade
if [ -f /etc/systemd/system/timemachine.service ]; then
  backup_file /etc/systemd/system/timemachine.service
fi

cp "$PROJECT_ROOT/deploy/timemachine.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable timemachine.service

# ============================================================================
# NGINX CONFIGURATION
# ============================================================================

echo "🌐 Installing nginx configuration..."

# Backup existing nginx config on upgrade
if [ -f /etc/nginx/sites-available/timemachine ]; then
  backup_file /etc/nginx/sites-available/timemachine
fi

cp "$PROJECT_ROOT/deploy/nginx.conf" /etc/nginx/sites-available/timemachine
ln -sf /etc/nginx/sites-available/timemachine /etc/nginx/sites-enabled/timemachine
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx

# ============================================================================
# VERSION TRACKING
# ============================================================================

echo "📝 Recording installation version..."
echo "$CURRENT_VERSION" > /opt/timemachine/.installed_version
chown timemachine:timemachine /opt/timemachine/.installed_version

# ============================================================================
# SERVICE STARTUP
# ============================================================================

if [ "$INSTALL_TYPE" = "upgrade" ]; then
  echo ""
  echo "🚀 Starting services..."
  safe_start_service nginx.service
  safe_start_service timemachine.service
  echo ""
  echo "╔══════════════════════════════════════════════════════════╗"
  echo "║              Upgrade Complete!                           ║"
  echo "╚══════════════════════════════════════════════════════════╝"
  echo ""
  echo "📝 Version upgraded: $PREVIOUS_VERSION → $CURRENT_VERSION"
  echo ""
  echo "✓ Services have been restarted"
  echo ""
  echo "📊 Check status:"
  echo "     sudo systemctl status timemachine"
  echo "     sudo journalctl -u timemachine -f"
  echo ""
  echo "🌐 Access web interface:"
  echo "     http://$(hostname -I | awk '{print $1}')"
  echo ""
else
  echo ""
  echo "╔══════════════════════════════════════════════════════════╗"
  echo "║              Installation Complete!                      ║"
  echo "╚══════════════════════════════════════════════════════════╝"
  echo ""
  echo "📝 Next steps:"
  echo "  1. Edit configuration: sudo nano /etc/timemachine/timemachine.env"
  echo "  2. Start services:"
  echo "       sudo systemctl start timemachine"
  echo "       sudo systemctl start nginx"
  echo "  3. Check status:"
  echo "       sudo systemctl status timemachine"
  echo "       sudo journalctl -u timemachine -f"
  echo "  4. Access web interface:"
  echo "       http://$(hostname -I | awk '{print $1}')"
  echo ""
  echo "📚 Documentation: $PROJECT_ROOT/docs/README.md"
  echo ""
fi
