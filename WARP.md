# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview
RTMP-BASE is a 24/7 HTML streaming server that captures web content and streams it directly to YouTube Live using RTMP. It features automatic startup on boot, persistent configuration management, and supports both HTML content streaming and Pygame game streaming.

## Common Development Commands

### Setup and Installation
```bash
# Interactive setup (installs dependencies and configures streaming)
chmod +x setup.sh && ./setup.sh

# Manual dependency installation
sudo apt install -y xvfb ffmpeg python3-pip curl google-chrome-stable
pip3 install -r requirements.txt
```

### Running the Application
```bash
# Run HTML streamer (main application)
python3 main.py

# Run Pygame streamer variant
python3 pygame_streamer.py

# Run example game locally (for testing)
python3 example_game.py
```

### Service Management
```bash
# Service control
sudo systemctl start rtmp-streamer     # Start service
sudo systemctl stop rtmp-streamer      # Stop service  
sudo systemctl restart rtmp-streamer   # Restart service
sudo systemctl status rtmp-streamer    # Check status

# Auto-startup control
sudo systemctl enable rtmp-streamer    # Enable auto-start on boot
sudo systemctl disable rtmp-streamer   # Disable auto-start

# View logs
sudo journalctl -u rtmp-streamer -f    # Follow service logs
sudo journalctl -u rtmp-streamer       # View all service logs
```

### Development and Testing
```bash
# Test system dependencies
ffmpeg -version        # Verify FFmpeg installation
google-chrome --version # Verify Chrome installation
Xvfb -help             # Verify virtual display support

# Test streaming setup (without actually streaming)
python3 -c "from main import HTMLStreamer; s = HTMLStreamer(); print('Stream key configured:', bool(s.stream_key))"

# Run with debugging
FLASK_ENV=development python3 main.py
```

## Architecture Overview

### Core Components

#### 1. HTMLStreamer Class (`main.py`)
- **Purpose**: Main streaming engine for HTML/web content
- **Key Methods**: `start_streaming()`, `stop_streaming()`, `cleanup()`
- **Process Management**: Handles Xvfb (virtual display), Chrome (content rendering), and FFmpeg (streaming)
- **Configuration**: Uses `.env` file for YouTube stream key and content path

#### 2. PygameStreamer Class (`pygame_streamer.py`)
- **Purpose**: Alternative streaming engine for Pygame applications
- **Key Difference**: Runs Python/Pygame scripts instead of Chrome browser
- **Use Case**: Stream games, interactive applications, or custom Python graphics

#### 3. Flask Web Interface
- **Routes**: 
  - `/` - Main dashboard
  - `/api/start` - Start streaming
  - `/api/stop` - Stop streaming  
  - `/api/status` - Get current status
  - `/api/update_content` - Change content (HTML mode)
  - `/api/update_script` - Change script (Pygame mode)

### Streaming Pipeline
1. **Xvfb**: Creates virtual X11 display (`:99`) at 1280x720 resolution
2. **Content Renderer**: Either Chrome (HTML mode) or Python/Pygame (game mode)
3. **FFmpeg**: Captures X11 display and streams to YouTube via RTMP
4. **YouTube**: Receives H.264 encoded stream at 2500k bitrate

### Configuration Management
- **Environment File**: `.env` stores YouTube stream key and default content
- **Systemd Service**: `/etc/systemd/system/rtmp-streamer.service` for auto-startup
- **Templates**: `templates/index.html` and `templates/pygame_index.html` for web UI

### System Dependencies
- **Xvfb**: Virtual display server for headless operation
- **FFmpeg**: Video processing and RTMP streaming
- **Google Chrome**: Web content rendering (HTML mode)
- **Python packages**: Flask, pygame, python-dotenv (see `requirements.txt`)

## File Structure Notes
- `main.py`: Primary HTML streaming application
- `pygame_streamer.py`: Alternative for Pygame content streaming  
- `example_game.py`: Demo Pygame application for testing
- `setup.sh`: Interactive setup script with dependency installation
- `demo_content.html`: Example HTML content for streaming
- `templates/`: Flask HTML templates for web interface
- `.env`: Configuration file (created by setup, contains secrets)

## Development Patterns
- **Process Management**: All streaming components use subprocess management with proper cleanup
- **Error Handling**: Graceful process termination with timeout and force-kill fallback
- **Signal Handling**: SIGINT/SIGTERM handlers ensure clean shutdown
- **Logging**: Structured logging using Python's logging module
- **Virtual Display**: All rendering happens on Xvfb display `:99` for headless operation
