# RTMP-BASE

A 24/7 HTML streaming server that captures web content and streams it directly to YouTube Live using RTMP. Features automatic startup on boot and persistent configuration management.

## Features

- 🔴 **24/7 Live Streaming** - Stream any HTML content or website to YouTube Live
- 🌐 **Web Control Interface** - Easy-to-use dashboard for stream management
- 🚀 **Auto-Startup** - Automatically starts streaming on system boot
- ⚙️ **Persistent Configuration** - Secure `.env` file configuration
- 🔄 **Hot Content Switching** - Change content without stopping the stream

## Quick Start

1. **Clone and enter the directory:**
   ```bash
   git clone <your-repo>
   cd RTMP-BASE
   ```

2. **Run the interactive setup:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```


4. **Access the web interface:**
   Open `http://localhost:5000` in your browser


## Auto-Startup Management

```bash
# Service management
sudo systemctl start rtmp-streamer    # Start now
sudo systemctl stop rtmp-streamer     # Stop now
sudo systemctl restart rtmp-streamer  # Restart
sudo systemctl status rtmp-streamer   # Check status

# Auto-startup control
sudo systemctl enable rtmp-streamer   # Enable auto-start
sudo systemctl disable rtmp-streamer  # Disable auto-start

# View logs
sudo journalctl -u rtmp-streamer -f   # Follow logs
```

## Usage

Navigate to `http://localhost:5000`, enter a URL or file path to stream, and click "Start Streaming" or "Update Content".