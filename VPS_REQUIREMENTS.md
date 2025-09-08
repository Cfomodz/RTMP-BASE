# StreamDrop VPS Requirements & Troubleshooting Guide

## 🚨 Critical Issue Identified: 512MB RAM is INSUFFICIENT

After thorough analysis, the streaming failures on 512MB droplets are caused by:

1. **Chromium Memory Exhaustion**: Browser alone requires 200-400MB on startup
2. **Shared Memory Limits**: `/dev/shm` is too small (typically 64MB on 512MB systems)
3. **Process Accumulation**: Running Xvfb + Chromium + FFmpeg exceeds available memory
4. **OOM Killer**: Linux kills processes when memory is exhausted

## 📊 Minimum VPS Requirements

### ❌ NOT SUPPORTED: 512MB RAM
- **Verdict**: Insufficient for reliable streaming
- **Issues**: Chromium crashes, FFmpeg buffer overflows, constant OOM kills
- **Alternative**: Use test pattern mode only (very limited)

### ⚠️ CHALLENGING: 512MB-1GB RAM
- **Verdict**: Possible with heavy optimization
- **Requirements**: 
  - Must use memory-optimized mode
  - Test pattern streaming recommended
  - Single stream only
  - Lower quality (480p @ 24fps)
- **Recommended Droplet**: DigitalOcean Basic 1GB ($6/month)

### ✅ RECOMMENDED: 1GB-2GB RAM
- **Verdict**: Good for standard streaming
- **Capabilities**:
  - HTML/Pygame streaming
  - 720p @ 30fps
  - Multi-streaming support
  - Stable operation
- **Recommended Droplet**: DigitalOcean Basic 1GB with swap ($6/month)

### 🌟 OPTIMAL: 2GB+ RAM
- **Verdict**: Excellent performance
- **Capabilities**:
  - All features available
  - 1080p @ 30-60fps
  - Multiple concurrent streams
  - No optimization needed
- **Recommended Droplet**: DigitalOcean Basic 2GB ($12/month)

## 🛠️ Fixes Implemented

### 1. Memory-Optimized Chromium Configuration
```bash
# New flags added for low-memory systems:
--disable-dev-shm-usage      # Critical for small /dev/shm
--single-process             # Run in single process mode
--no-zygote                  # Don't use zygote process
--max_old_space_size=96      # Limit V8 heap
--enable-low-end-device-mode # Enable low-end optimizations
--disable-site-isolation-trials
--disable-features=site-per-process
```

### 2. Automatic Fallback to Test Pattern
When Chromium fails due to memory issues, the system now automatically falls back to test pattern streaming which uses minimal resources.

### 3. Dynamic Memory Detection
The system now detects available memory and applies appropriate optimizations automatically.

## 🔧 Immediate Solutions

### For 512MB Droplets - Choose One:

#### Option 1: Upgrade to 1GB Droplet (RECOMMENDED)
```bash
# Via DigitalOcean Control Panel:
1. Power off droplet
2. Resize > Choose 1GB plan ($6/month)
3. Power on droplet
```

#### Option 2: Add Swap Space (Temporary Fix)
```bash
# Add 1GB swap (helps but doesn't fully solve the issue)
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Optimize swappiness for low memory
echo 'vm.swappiness=60' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

#### Option 3: Use Memory-Optimized Mode
```bash
# Run the diagnostic tool
python3 diagnose_streaming.py

# Use memory-optimized streamer
python3 memory_optimized_streamer.py
```

#### Option 4: Test Pattern Only Mode
```bash
# For ultra-low memory, use test pattern streaming
export YOUTUBE_STREAM_KEY="your-key-here"
export STREAMING_MODE="test_pattern"
python3 memory_optimized_streamer.py
```

## 📈 Digital Ocean Droplet Recommendations

### Budget Option ($6/month)
- **Droplet**: Basic Regular 1GB RAM / 1 vCPU / 25GB SSD
- **Location**: Choose closest to your audience
- **Additional**: Enable backups ($1/month)
- **Performance**: Handles 720p @ 30fps reliably

### Standard Option ($12/month)
- **Droplet**: Basic Regular 2GB RAM / 1 vCPU / 50GB SSD
- **Location**: Choose closest to your audience
- **Additional**: Enable monitoring
- **Performance**: Handles 1080p @ 30fps with headroom

### Performance Option ($18/month)
- **Droplet**: Basic Regular 2GB RAM / 2 vCPUs / 60GB SSD
- **Location**: Choose closest to your audience
- **Additional**: Enable monitoring
- **Performance**: Handles multiple streams or 1080p @ 60fps

## 🧪 Testing Your Configuration

### 1. Run Diagnostic Tool
```bash
cd /path/to/StreamDrop
python3 diagnose_streaming.py
```

This will:
- Check available memory
- Test Chromium launch
- Test FFmpeg streaming
- Provide specific recommendations

### 2. Monitor Memory Usage
```bash
# Watch memory in real-time
watch -n 1 free -h

# Check for OOM kills
sudo dmesg | grep -i "killed process"
```

### 3. Test Streaming
```bash
# Test with reduced quality first
export YOUTUBE_STREAM_KEY="your-key"
export STREAM_QUALITY="low"  # 480p
python3 stream_manager.py
```

## 🚀 Quick Start for New Droplet

### For 1GB+ Droplet:
```bash
# 1. Create new droplet (Ubuntu 22.04, 1GB+ RAM)
# 2. SSH into droplet
# 3. Clone and setup
git clone https://github.com/yourusername/StreamDrop.git
cd StreamDrop
chmod +x setup.sh
./setup.sh

# 4. Configure
cp .env.example .env
nano .env  # Add your stream key

# 5. Run
python3 main.py
```

## 📞 Support

If you continue experiencing issues after following this guide:

1. Run the diagnostic tool and save output
2. Check system logs: `sudo journalctl -xe`
3. Monitor during failure: `htop` or `top`
4. Create an issue with diagnostic output

## 🎯 Summary

**512MB RAM is NOT sufficient for StreamDrop.** The absolute minimum is 1GB RAM with swap space. For reliable operation, 1GB RAM is recommended. The system now includes automatic memory detection and optimization, but hardware limitations cannot be completely overcome by software optimization.

### Recommended Action:
**Upgrade to a 1GB droplet ($6/month on DigitalOcean) for reliable streaming.**