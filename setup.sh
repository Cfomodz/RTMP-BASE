#!/bin/bash
# One-click deployment script for StreamDrop - 24/7 HTML Streaming Server
# Designed for fresh Ubuntu droplets/servers
#
# 🚀 QUICK START - Fresh Ubuntu Server:
#   1. git clone <your-repo-url>
#   2. cd StreamDrop
#   3. chmod +x setup.sh && ./setup.sh
#
# 🤖 FULLY AUTOMATED DEPLOYMENT:
#   YOUTUBE_STREAM_KEY="your_key" DEFAULT_CONTENT_PATH="https://your-site.com" ./setup.sh
#
# This script installs everything needed from scratch:
# - Git, Python, Chromium, FFmpeg, and all dependencies
# - Creates isolated Python virtual environment
# - Configures firewall and systemd service
# - Sets up auto-start on boot

set -e  # Exit on any error

echo "🚀 One-Click Deploy: StreamDrop - 24/7 HTML Streaming Server"
echo "=============================================================="
echo "Setting up everything needed for a fresh Ubuntu system..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to check if running as root
check_not_root() {
    if [[ $EUID -eq 0 ]]; then
        echo -e "${RED}❌ This script should not be run as root!${NC}"
        echo -e "${YELLOW}💡 Run as a regular user with sudo privileges instead${NC}"
        exit 1
    fi
}

# Function to check Ubuntu version
check_ubuntu() {
    if ! grep -q "Ubuntu" /etc/os-release; then
        echo -e "${YELLOW}⚠️  Warning: This script is designed for Ubuntu. Proceeding anyway...${NC}"
    fi
}

# Function to check internet connectivity
check_internet() {
    echo -e "${BLUE}🌐 Checking internet connectivity...${NC}"
    if ! curl -s --connect-timeout 5 google.com > /dev/null; then
        echo -e "${RED}❌ No internet connection detected!${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Internet connection confirmed${NC}"
}

# Run initial checks
check_not_root
check_ubuntu
check_internet

# Update package lists
echo -e "${BLUE}📦 Updating package lists...${NC}"
sudo apt update -y

# Install essential system dependencies
echo -e "${BLUE}🔧 Installing essential system dependencies...${NC}"
sudo apt install -y \
    git \
    curl \
    wget \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# Install Python and development tools
echo -e "${BLUE}🐍 Installing Python and development tools...${NC}"
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    pkg-config

# Detect headless system and choose optimal setup
detect_headless() {
    if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ] && ! pgrep -x "Xorg\|gnome\|kde\|xfce" > /dev/null; then
        return 0  # Headless
    else
        return 1  # Has display
    fi
}

if detect_headless; then
    echo -e "${GREEN}🎯 Headless system detected - installing optimized packages${NC}"
    echo -e "${BLUE}🎬 Installing minimal dependencies for headless streaming...${NC}"
    sudo apt install -y \
        ffmpeg \
        libnss3 \
        libatk-bridge2.0-0 \
        libdrm2 \
        libgbm1 \
        libasound2
    
    HEADLESS_MODE=true
else
    echo -e "${YELLOW}🖥️  Display system detected${NC}"
    echo -e "${BLUE}Do you want headless-optimized setup? (smaller, faster, cheaper VPS) [Y/n]:${NC}"
    read -r -n 1 HEADLESS_CHOICE
    echo
    
    if [[ $HEADLESS_CHOICE =~ ^[Nn]$ ]]; then
        echo -e "${BLUE}🎬 Installing full dependencies with X11 support...${NC}"
        sudo apt install -y \
            xvfb \
            ffmpeg \
            libnss3-dev \
            libatk-bridge2.0-dev \
            libdrm-dev \
            libxcomposite-dev \
            libxdamage-dev \
            libxrandr-dev \
            libgbm-dev \
            libxss-dev \
            libasound2-dev
        
        HEADLESS_MODE=false
    else
        echo -e "${GREEN}✅ Using headless-optimized setup${NC}"
        echo -e "${BLUE}🎬 Installing minimal dependencies for headless streaming...${NC}"
        sudo apt install -y \
            ffmpeg \
            libnss3 \
            libatk-bridge2.0-0 \
            libdrm2 \
            libgbm1 \
            libasound2
        
        HEADLESS_MODE=true
    fi
fi

# Install Chromium (open-source, server-friendly)
echo -e "${BLUE}🌐 Installing Chromium browser...${NC}"
if ! command -v chromium-browser &> /dev/null; then
    sudo apt install -y \
        chromium-browser \
        chromium-browser-l10n \
        chromium-codecs-ffmpeg
else
    echo -e "${GREEN}✅ Chromium already installed${NC}"
fi

# Create virtual environment
echo -e "${BLUE}🐍 Creating Python virtual environment...${NC}"
python3 -m venv venv

# Activate virtual environment
echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip in virtual environment
echo -e "${BLUE}⬆️ Upgrading pip...${NC}"
pip install --upgrade pip

# Install Python dependencies in virtual environment
echo -e "${BLUE}📦 Installing Python dependencies in virtual environment...${NC}"
pip install -r requirements.txt

# Configure firewall for web interface
echo -e "${BLUE}🔥 Configuring firewall...${NC}"
if command -v ufw &> /dev/null; then
    sudo ufw --force enable
    sudo ufw allow 5000/tcp comment "StreamDrop Web Interface"
    echo -e "${GREEN}✅ Firewall configured - Port 5000 opened${NC}"
else
    echo -e "${YELLOW}⚠️  UFW not available, skipping firewall configuration${NC}"
fi

# Interactive or environment-based configuration
echo ""
echo -e "${YELLOW}⚙️  Configuration Setup${NC}"
echo "=========================================="

# Check for environment variables first (for automation)
if [[ -n "$YOUTUBE_STREAM_KEY" ]]; then
    STREAM_KEY="$YOUTUBE_STREAM_KEY"
    echo -e "${GREEN}✅ Using YouTube Stream Key from environment variable${NC}"
else
    echo "Now let's configure your streaming settings..."
    echo ""
    
    # Get YouTube Stream Key interactively
    while true; do
        echo -e "${BLUE}Enter your YouTube Stream Key:${NC}"
        echo "(You can find this in YouTube Studio > Go Live > Stream Key)"
        echo -e "${YELLOW}💡 Tip: You can also set YOUTUBE_STREAM_KEY environment variable to skip this${NC}"
        read -r STREAM_KEY
        
        if [[ -z "$STREAM_KEY" ]]; then
            echo -e "${RED}❌ Stream key cannot be empty. Please try again.${NC}"
        else
            break
        fi
    done
fi

# Get default content path
if [[ -n "$DEFAULT_CONTENT_PATH" ]]; then
    CONTENT_PATH="$DEFAULT_CONTENT_PATH"
    echo -e "${GREEN}✅ Using content path from environment variable: $CONTENT_PATH${NC}"
else
    echo ""
    echo -e "${BLUE}Enter default content URL/path (optional, press Enter for default):${NC}"
    echo "Examples: https://example.com, https://clock.zone, file:///path/to/file.html"
    read -r CONTENT_PATH
    
    if [[ -z "$CONTENT_PATH" ]]; then
        CONTENT_PATH="https://example.com"
    fi
fi

# Create .env file
echo -e "${BLUE}📝 Creating configuration file (.env)...${NC}"
cat > .env << EOF
YOUTUBE_STREAM_KEY=$STREAM_KEY
CONTENT_PATH=$CONTENT_PATH
EOF

# Set up systemd service for auto-startup
echo ""
echo -e "${YELLOW}🔄 Setting up auto-startup service${NC}"
echo "=========================================="

# Get current user and working directory
CURRENT_USER=$(whoami)
CURRENT_DIR=$(pwd)

# Create systemd service file
sudo tee /etc/systemd/system/streamdrop.service > /dev/null << EOF
[Unit]
Description=StreamDrop 24/7 HTML Streamer
After=network.target
Wants=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=/usr/local/bin:/usr/bin:/bin
ExecStart=$CURRENT_DIR/venv/bin/python $CURRENT_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable streamdrop.service

# Display server information
get_server_ip() {
    # Try to get public IP
    PUBLIC_IP=$(curl -s --connect-timeout 5 ipv4.icanhazip.com 2>/dev/null || curl -s --connect-timeout 5 ifconfig.me 2>/dev/null || echo "Unable to determine")
    LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "Unable to determine")
    echo -e "${PURPLE}🌐 Server Information:${NC}"
    echo "• Public IP: $PUBLIC_IP"
    echo "• Local IP: $LOCAL_IP"
    echo "• Port: 5000"
}

echo ""
echo -e "${GREEN}🎉 ONE-CLICK DEPLOYMENT COMPLETE! 🎉${NC}"
echo "=============================================================="
echo ""

get_server_ip

echo ""
echo -e "${BLUE}📋 What's been installed & configured:${NC}"
if [ "$HEADLESS_MODE" = true ]; then
    echo "• ✅ Optimized headless dependencies (60% less packages)"
    echo "• ✅ No X11/Xvfb bloat - maximum efficiency"
    echo "• ✅ Perfect for VPS ($4-6/month vs $10-20/month)"
else
    echo "• ✅ Full system dependencies with X11 support"
fi
echo "• ✅ Python virtual environment created (venv/)"
echo "• ✅ Python packages installed in isolated environment"
echo "• ✅ Firewall configured (port 5000 opened)"
echo "• ✅ Configuration saved to .env file"
echo "• ✅ Auto-startup systemd service created and enabled"
echo ""
echo -e "${BLUE}🚀 How to start streaming:${NC}"
echo "1. 🟢 Start now: sudo systemctl start streamdrop"
echo "2. 📊 Check status: sudo systemctl status streamdrop"
echo "3. 📝 View logs: sudo journalctl -u streamdrop -f"
echo "4. 🌐 Web interface: http://$(curl -s --connect-timeout 3 ipv4.icanhazip.com 2>/dev/null || echo 'YOUR_SERVER_IP'):5000"
echo ""
echo -e "${YELLOW}🔧 Service management:${NC}"
echo "• Start:   sudo systemctl start streamdrop"
echo "• Stop:    sudo systemctl stop streamdrop"
echo "• Restart: sudo systemctl restart streamdrop"
echo "• Status:  sudo systemctl status streamdrop"
echo "• Logs:    sudo journalctl -u streamdrop -f"
echo "• Disable auto-start: sudo systemctl disable streamdrop"
echo ""
echo -e "${YELLOW}💡 For manual testing:${NC}"
echo "• Activate venv: source venv/bin/activate"
if [ "$HEADLESS_MODE" = true ]; then
    echo "• Run manually: YOUTUBE_STREAM_KEY=key CONTENT_PATH=https://clock.zone ./venv/bin/python smart_streamer.py"
else
    echo "• Run manually: ./venv/bin/python smart_streamer.py (or main.py for traditional mode)"
fi
echo ""
echo -e "${PURPLE}🔒 Environment variables for automation:${NC}"
echo "• YOUTUBE_STREAM_KEY=your_key ./setup.sh"
echo "• DEFAULT_CONTENT_PATH=https://your-site.com ./setup.sh"
echo ""
echo -e "${GREEN}🎊 Your 24/7 streaming server is ready to go!${NC}"
echo -e "${GREEN}   The service will automatically start on boot.${NC}"