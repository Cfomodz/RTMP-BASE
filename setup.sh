#!/bin/bash
# Interactive setup script for RTMP-BASE - 24/7 HTML Streaming Server

set -e  # Exit on any error

echo "🚀 Setting up RTMP-BASE - 24/7 HTML Streaming Server..."
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Update package lists
echo -e "${BLUE}📦 Updating package lists...${NC}"
sudo apt update

# Install system dependencies
echo -e "${BLUE}🔧 Installing system dependencies...${NC}"
sudo apt install -y xvfb ffmpeg python3-pip curl

# Install Google Chrome
echo -e "${BLUE}🌐 Installing Google Chrome...${NC}"
if ! command -v google-chrome &> /dev/null; then
    curl -fsSL https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/googlechrom-keyring.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrom-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
    sudo apt update
    sudo apt install -y google-chrome-stable
else
    echo -e "${GREEN}✅ Google Chrome already installed${NC}"
fi

# Install Python dependencies
echo -e "${BLUE}🐍 Installing Python dependencies...${NC}"
pip3 install -r requirements.txt

# Interactive configuration
echo ""
echo -e "${YELLOW}⚙️  Configuration Setup${NC}"
echo "=========================================="
echo "Now let's configure your streaming settings..."
echo ""

# Get YouTube Stream Key
while true; do
    echo -e "${BLUE}Enter your YouTube Stream Key:${NC}"
    echo "(You can find this in YouTube Studio > Go Live > Stream Key)"
    read -r STREAM_KEY
    
    if [[ -z "$STREAM_KEY" ]]; then
        echo -e "${RED}❌ Stream key cannot be empty. Please try again.${NC}"
    else
        break
    fi
done

# Get default content path (optional)
echo ""
echo -e "${BLUE}Enter default content URL/path (optional, press Enter for default):${NC}"
echo "Examples: https://example.com, https://clock.zone, file:///path/to/file.html"
read -r CONTENT_PATH

if [[ -z "$CONTENT_PATH" ]]; then
    CONTENT_PATH="https://example.com"
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
sudo tee /etc/systemd/system/rtmp-streamer.service > /dev/null << EOF
[Unit]
Description=RTMP 24/7 HTML Streamer
After=network.target
Wants=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=/usr/local/bin:/usr/bin:/bin
ExecStart=/usr/bin/python3 $CURRENT_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable rtmp-streamer.service

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo "=========================================="
echo ""
echo -e "${BLUE}📋 What's been configured:${NC}"
echo "• System dependencies installed"
echo "• Python packages installed"
echo "• Configuration saved to .env file"
echo "• Auto-startup service created and enabled"
echo ""
echo -e "${BLUE}🚀 Next steps:${NC}"
echo "1. Start the service now: sudo systemctl start rtmp-streamer"
echo "2. Check service status: sudo systemctl status rtmp-streamer"
echo "3. View logs: sudo journalctl -u rtmp-streamer -f"
echo "4. Or run manually: python3 main.py"
echo "5. Open web interface: http://localhost:5000"
echo ""
echo -e "${YELLOW}🔧 Service management commands:${NC}"
echo "• Start:   sudo systemctl start rtmp-streamer"
echo "• Stop:    sudo systemctl stop rtmp-streamer"
echo "• Restart: sudo systemctl restart rtmp-streamer"
echo "• Disable auto-start: sudo systemctl disable rtmp-streamer"
echo ""
echo -e "${GREEN}🎉 Your streamer will now auto-start on boot!${NC}"