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
  gstreamer1.0-plugins-ugly \
  v4l-utils \
  ffmpeg \
  git \
  curl

# Install Node.js 22.x (required for Vite 6.x which needs Node.js 20.19+ or 22.12+)
NODE_REQUIRED_MAJOR=22

# Check if node is installed and get version
if command -v node &> /dev/null; then
  NODE_CURRENT_VERSION=$(node --version | sed 's/v//')
  NODE_CURRENT_MAJOR=$(echo "$NODE_CURRENT_VERSION" | cut -d. -f1)
else
  NODE_CURRENT_VERSION="not installed"
  NODE_CURRENT_MAJOR=0
fi

if [ "$NODE_CURRENT_MAJOR" -lt "$NODE_REQUIRED_MAJOR" ]; then
  echo "📦 Installing Node.js ${NODE_REQUIRED_MAJOR}.x (current: ${NODE_CURRENT_VERSION})..."
  # Remove old nodejs if present
  apt-get remove -y nodejs npm 2>/dev/null || true
  # Install Node.js 22.x from NodeSource
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
  echo "  ✓ Node.js installed: $(node --version)"
else
  echo "✓ Node.js already meets requirements ($(node --version))"
fi

# Verify npm is available (comes with nodejs from NodeSource)
if ! command -v npm &> /dev/null; then
  echo "❌ Error: npm not found after Node.js installation"
  exit 1
else
  echo "✓ npm available ($(npm --version))"
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

# Ensure /opt/timemachine is world-readable for nginx to serve static files
# useradd -m creates home with 700 permissions by default
chmod 755 /opt/timemachine

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
# BACKEND DEPLOYMENT (needs to be before frontend build for type generation)
# ============================================================================

echo "📋 Deploying backend files..."

# Backup existing backend on upgrade
if [ "$INSTALL_TYPE" = "upgrade" ] && [ -d /opt/timemachine/backend ]; then
  backup_dir="/opt/timemachine/backup/backend.$(date +%Y%m%d_%H%M%S)"
  echo "  📦 Backing up existing backend..."
  mkdir -p "$backup_dir"
  cp -r /opt/timemachine/backend "$backup_dir/"
fi

# Deploy backend code
cp -r "$PROJECT_ROOT/backend" /opt/timemachine/backend.new
chown -R timemachine:timemachine /opt/timemachine/backend.new
rm -rf /opt/timemachine/backend.old
[ -d /opt/timemachine/backend ] && mv /opt/timemachine/backend /opt/timemachine/backend.old
mv /opt/timemachine/backend.new /opt/timemachine/backend
rm -rf /opt/timemachine/backend.old

echo "🐍 Setting up Python environment..."

if [ "$INSTALL_TYPE" = "upgrade" ] && [ -d /opt/timemachine/venv ]; then
  echo "  ♻️  Recreating virtual environment for clean upgrade..."
  rm -rf /opt/timemachine/venv
fi

python3 -m venv /opt/timemachine/venv --system-site-packages
/opt/timemachine/venv/bin/pip install --upgrade pip
/opt/timemachine/venv/bin/pip install -r /opt/timemachine/backend/requirements.txt

# ============================================================================
# FRONTEND TYPE GENERATION
# ============================================================================

echo "📝 Generating frontend TypeScript types from backend OpenAPI schema..."

# Ensure environment file exists FIRST (needed for database init)
if [ ! -f /etc/timemachine/timemachine.env ]; then
  echo "  📝 Creating environment configuration..."
  cp "$PROJECT_ROOT/deploy/timemachine.env.example" /etc/timemachine/timemachine.env
  chown root:timemachine /etc/timemachine/timemachine.env
  chmod 640 /etc/timemachine/timemachine.env
fi

# Ensure database exists before starting backend
DB_PATH="/var/lib/timemachine/timemachine.db"
if [ ! -f "$DB_PATH" ]; then
  echo "  📦 Initializing database for type generation..."
  cd /opt/timemachine/backend
  sudo -u timemachine bash -c "export \$(grep -v '^#' /etc/timemachine/timemachine.env | xargs) && PYTHONPATH=/opt/timemachine/backend /opt/timemachine/venv/bin/python -c 'import asyncio; from app.db.session import init_db; asyncio.run(init_db())'" 2>/dev/null || true
fi

# Temporarily start backend to generate OpenAPI schema
cd /opt/timemachine/backend
TEMP_PID_FILE="/tmp/timemachine_temp_backend.pid"
TEMP_LOG_FILE="/tmp/timemachine_temp_backend.log"

# Start backend in background with environment (escape $ to prevent expansion in outer shell)
sudo -u timemachine bash -c "export \$(grep -v '^#' /etc/timemachine/timemachine.env | xargs) && /opt/timemachine/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8765" > "$TEMP_LOG_FILE" 2>&1 &
TEMP_BACKEND_PID=$!
echo $TEMP_BACKEND_PID > "$TEMP_PID_FILE"

echo "  ⏳ Waiting for backend to start..."
sleep 3

# Check if backend is running (try up to 10 times with 1 second intervals)
BACKEND_STARTED=false
for i in {1..10}; do
  if curl -s http://127.0.0.1:8765/api/v1/health > /dev/null 2>&1; then
    echo "  ✓ Backend started on port 8765"
    BACKEND_STARTED=true
    break
  fi
  sleep 1
done

if [ "$BACKEND_STARTED" = true ]; then
  # Generate types
  cd "$PROJECT_ROOT/frontend"
  if [ ! -d "node_modules" ]; then
    echo "  Installing frontend dependencies..."
    npm install
  fi

  echo "  Generating TypeScript types (timeout: 60s)..."
  if timeout 60 npx openapi-typescript http://127.0.0.1:8765/api/openapi.json -o src/types/api.ts 2>/dev/null; then
    if [ -f "src/types/api.ts" ]; then
      echo "  ✓ TypeScript types generated successfully"
    else
      echo "  ⚠️  Warning: Type generation may have failed"
    fi
  else
    echo "  ⚠️  Warning: Type generation timed out or failed"
    echo "  ⚠️  Using existing types (if available) or run manually after installation"
  fi
else
  echo "  ⚠️  Warning: Could not start backend temporarily for type generation"
  echo "  ⚠️  Backend logs:"
  [ -f "$TEMP_LOG_FILE" ] && tail -n 10 "$TEMP_LOG_FILE" | sed 's/^/  │ /'
  echo "  ⚠️  You may need to run 'npm run generate-types' manually after installation"
fi

# Stop temporary backend
if [ -f "$TEMP_PID_FILE" ]; then
  TEMP_BACKEND_PID=$(cat "$TEMP_PID_FILE")
  kill $TEMP_BACKEND_PID 2>/dev/null || true
  rm -f "$TEMP_PID_FILE"
  rm -f "$TEMP_LOG_FILE"
  echo "  ⏸️  Stopped temporary backend"
fi

# ============================================================================
# FRONTEND BUILD
# ============================================================================

echo "🔨 Building frontend..."
if [ -d "$PROJECT_ROOT/frontend" ]; then
  cd "$PROJECT_ROOT/frontend"

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
# FRONTEND STATIC FILES DEPLOYMENT
# ============================================================================

echo "📂 Deploying frontend static files..."

# Backup existing static files on upgrade
if [ "$INSTALL_TYPE" = "upgrade" ] && [ -d /opt/timemachine/static ]; then
  backup_dir="/opt/timemachine/backup/static.$(date +%Y%m%d_%H%M%S)"
  echo "  📦 Backing up existing frontend..."
  mkdir -p "$backup_dir"
  cp -r /opt/timemachine/static "$backup_dir/"
fi

# Deploy frontend (atomic operation)
rm -rf /opt/timemachine/static.new
cp -r "$PROJECT_ROOT/frontend/dist" /opt/timemachine/static.new
if [ -d /opt/timemachine/static ]; then
  rm -rf /opt/timemachine/static.old
  mv /opt/timemachine/static /opt/timemachine/static.old
fi
mv /opt/timemachine/static.new /opt/timemachine/static
rm -rf /opt/timemachine/static.old

# ============================================================================
# DATABASE INITIALIZATION AND MIGRATIONS
# ============================================================================

DB_PATH="/var/lib/timemachine/timemachine.db"
ALEMBIC="/opt/timemachine/venv/bin/alembic"
BACKEND_DIR="/opt/timemachine/backend"

# Ensure alembic is installed
if [ ! -f "$ALEMBIC" ]; then
  echo "📦 Installing alembic for database migrations..."
  /opt/timemachine/venv/bin/pip install alembic
fi

# Helper function to run alembic with proper PYTHONPATH and environment
run_alembic() {
  cd "$BACKEND_DIR"
  sudo -u timemachine bash -c "export \$(grep -v '^#' /etc/timemachine/timemachine.env | xargs) && PYTHONPATH='$BACKEND_DIR' '$ALEMBIC' $*"
}

if [ -f "$DB_PATH" ]; then
  echo "💾 Database already exists"

  # Check if database has been stamped with alembic version
  CURRENT_REV=$(run_alembic current 2>/dev/null || echo "")

  if [ -z "$CURRENT_REV" ] || echo "$CURRENT_REV" | grep -q "(head)"; then
    if [ -z "$CURRENT_REV" ]; then
      echo "  🔖 Stamping existing database with initial migration..."
      # Stamp database as having initial schema (created via create_all)
      run_alembic stamp 0001_initial
    fi
    echo "  🔄 Checking for pending migrations..."
    run_alembic upgrade head
    echo "  ✓ Database migrations complete"
  else
    echo "  🔄 Running database migrations..."
    run_alembic upgrade head
    echo "  ✓ Database migrations complete"
  fi
else
  echo "💾 Initializing database..."
  cd "$BACKEND_DIR"

  # Create tables via SQLAlchemy (ensures all tables exist) - run as timemachine user
  sudo -u timemachine bash -c "export \$(grep -v '^#' /etc/timemachine/timemachine.env | xargs) && PYTHONPATH='$BACKEND_DIR' /opt/timemachine/venv/bin/python -c 'import asyncio; from app.db.session import init_db; asyncio.run(init_db())'"

  # Stamp with latest migration so future upgrades work correctly
  echo "  🔖 Stamping database with current migration version..."
  run_alembic stamp head
  echo "  ✓ Database initialized and stamped"
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

# Test and reload nginx
if nginx -t; then
  echo "  ✓ Nginx configuration valid"
  systemctl reload nginx || systemctl restart nginx
  echo "  ✓ Nginx reloaded"
else
  echo "  ❌ Nginx configuration test failed"
  exit 1
fi
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

echo ""
echo "🚀 Starting services..."
safe_start_service nginx.service
safe_start_service timemachine.service

if [ "$INSTALL_TYPE" = "upgrade" ]; then
  echo ""
  echo "╔══════════════════════════════════════════════════════════╗"
  echo "║              Upgrade Complete!                           ║"
  echo "╚══════════════════════════════════════════════════════════╝"
  echo ""
  echo "📝 Version upgraded: $PREVIOUS_VERSION → $CURRENT_VERSION"
else
  echo ""
  echo "╔══════════════════════════════════════════════════════════╗"
  echo "║              Installation Complete!                      ║"
  echo "╚══════════════════════════════════════════════════════════╝"
  echo ""
  echo "📝 Version installed: $CURRENT_VERSION"
fi

echo ""
echo "✓ Services are running"
echo ""
echo "📊 Check status:"
echo "     sudo systemctl status timemachine"
echo "     sudo journalctl -u timemachine -f"
echo ""
echo "🌐 Access web interface:"
echo "     http://$(hostname -I | awk '{print $1}')"
echo ""

