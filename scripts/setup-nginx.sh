#!/bin/bash
#
# Nginx Setup Script for TimeMachine
# Configures nginx as reverse proxy for TimeMachine API and frontend
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "╔══════════════════════════════════════════════════════════╗"
echo "║         TimeMachine - Nginx Configuration Setup         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Error: Please run as root (use sudo)${NC}"
  exit 1
fi

# Detect script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "📁 Project root: $PROJECT_ROOT"
echo ""

# Check if nginx config exists
if [ ! -f "$PROJECT_ROOT/deploy/nginx.conf" ]; then
  echo -e "${RED}Error: nginx.conf not found at $PROJECT_ROOT/deploy/nginx.conf${NC}"
  exit 1
fi

# Install nginx configuration
echo "🌐 Installing nginx configuration..."
cp "$PROJECT_ROOT/deploy/nginx.conf" /etc/nginx/sites-available/timemachine

# Create symlink if it doesn't exist
if [ ! -L /etc/nginx/sites-enabled/timemachine ]; then
  echo "🔗 Creating symlink in sites-enabled..."
  ln -sf /etc/nginx/sites-available/timemachine /etc/nginx/sites-enabled/timemachine
else
  echo "✓ Symlink already exists"
fi

# Remove default nginx site
if [ -L /etc/nginx/sites-enabled/default ]; then
  echo "🗑️  Removing default nginx site..."
  rm -f /etc/nginx/sites-enabled/default
else
  echo "✓ Default site already removed"
fi

# Test nginx configuration
echo "🧪 Testing nginx configuration..."
if nginx -t; then
  echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
else
  echo -e "${RED}✗ Nginx configuration test failed${NC}"
  exit 1
fi

# Reload nginx
echo "🔄 Reloading nginx..."
systemctl reload nginx

# Check nginx status
if systemctl is-active --quiet nginx; then
  echo -e "${GREEN}✓ Nginx is running${NC}"
else
  echo -e "${YELLOW}⚠ Nginx is not running, starting...${NC}"
  systemctl start nginx
fi

# Enable nginx on boot
if systemctl is-enabled --quiet nginx; then
  echo "✓ Nginx is enabled on boot"
else
  echo "⚙️  Enabling nginx on boot..."
  systemctl enable nginx
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              Nginx Setup Complete!                       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "📝 Configuration details:"
echo "  • Config file: /etc/nginx/sites-available/timemachine"
echo "  • Symlink: /etc/nginx/sites-enabled/timemachine"
echo "  • Backend proxy: http://127.0.0.1:8000 → /api/"
echo "  • Media files: /var/lib/timemachine/media → /media/"
echo "  • Preview streams: Proxied on /preview/{port}"
echo ""
echo "🌐 Access points:"
echo "  • API: http://$(hostname -I | awk '{print $1}')/api/v1/docs"
echo "  • Frontend: http://$(hostname -I | awk '{print $1}')/ (when built)"
echo ""
echo "🔍 Verify:"
echo "  sudo nginx -t           # Test configuration"
echo "  sudo systemctl status nginx  # Check nginx status"
echo "  curl http://localhost/api/v1/health  # Test API proxy"
echo ""
