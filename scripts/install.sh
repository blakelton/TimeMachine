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

# Install system dependencies
echo "📦 Installing system dependencies..."
apt-get update
apt-get install -y \
  python3 \
  python3-pip \
  python3-venv \
  nginx \
  libcamera-apps \
  gstreamer1.0-tools \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad \
  v4l-utils \
  git \
  libcap-dev \
  libavformat-dev \
  libavcodec-dev \
  libavdevice-dev \
  libavutil-dev \
  libavfilter-dev \
  libswscale-dev \
  libswresample-dev \
  pkg-config

# Create timemachine user
if ! id -u timemachine &>/dev/null; then
  echo "👤 Creating timemachine user..."
  useradd -r -s /bin/false -d /opt/timemachine -m timemachine
  usermod -aG video timemachine
else
  echo "✓ User timemachine already exists"
fi

# Create directory structure
echo "📂 Creating directory structure..."
mkdir -p /opt/timemachine
mkdir -p /var/lib/timemachine/media/{recordings,stills,timelapse}
mkdir -p /var/log/timemachine
mkdir -p /etc/timemachine

# Copy application files
echo "📋 Copying application files..."
cp -r "$PROJECT_ROOT/backend" /opt/timemachine/
if [ -d "$PROJECT_ROOT/frontend/dist" ]; then
  echo "  Copying frontend build..."
  cp -r "$PROJECT_ROOT/frontend/dist" /opt/timemachine/static
else
  echo "  ⚠️  Frontend not built, skipping static files"
  echo "     Run 'cd frontend && npm run build' first"
fi

# Create Python virtual environment
echo "🐍 Setting up Python environment..."
python3 -m venv /opt/timemachine/venv
/opt/timemachine/venv/bin/pip install --upgrade pip
/opt/timemachine/venv/bin/pip install -r /opt/timemachine/backend/requirements.txt

# Initialize database
echo "💾 Initializing database..."
cd /opt/timemachine/backend
/opt/timemachine/venv/bin/python -c "import asyncio; from app.db.session import init_db; asyncio.run(init_db())"

# Copy environment configuration
if [ ! -f /etc/timemachine/timemachine.env ]; then
  echo "⚙️  Creating environment configuration..."
  cp "$PROJECT_ROOT/deploy/timemachine.env.example" /etc/timemachine/timemachine.env
  chmod 640 /etc/timemachine/timemachine.env
  chown root:timemachine /etc/timemachine/timemachine.env
  echo "  ⚠️  Edit /etc/timemachine/timemachine.env to customize settings"
else
  echo "✓ Environment configuration already exists"
fi

# Set permissions
echo "🔐 Setting permissions..."
chown -R timemachine:timemachine /opt/timemachine
chown -R timemachine:timemachine /var/lib/timemachine
chown -R timemachine:timemachine /var/log/timemachine

# Install systemd service
echo "⚡ Installing systemd service..."
cp "$PROJECT_ROOT/deploy/timemachine.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable timemachine.service

# Install nginx configuration
echo "🌐 Installing nginx configuration..."
cp "$PROJECT_ROOT/deploy/nginx.conf" /etc/nginx/sites-available/timemachine
ln -sf /etc/nginx/sites-available/timemachine /etc/nginx/sites-enabled/timemachine
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx

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
