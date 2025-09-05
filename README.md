# RTMP-BASE

Stream any website, PyGame, or local HTML file to YouTube Live 24/7.

## Quick Start

**1. Clone & Setup:**
```bash
git clone <your-repo-url>
cd RTMP-BASE
chmod +x setup.sh && ./setup.sh
```

**2. Get your YouTube Stream Key from [YouTube Studio](https://studio.youtube.com) → Go Live**

**3. Start Streaming:**
```bash
YOUTUBE_STREAM_KEY="your_key" python3 smart_streamer.py
```

Your stream is live.

## Web Interface

Open `http://your-server-ip:5000` to control streams.

## Auto-Start Service

```bash
sudo systemctl enable rtmp-streamer
sudo systemctl start rtmp-streamer
```

## Environment Variables

```bash
YOUTUBE_STREAM_KEY="your_key"
CONTENT_PATH="https://example.com"
```

## Examples

**Stream a website:**
```bash
YOUTUBE_STREAM_KEY="key" CONTENT_PATH="https://clock.zone" python3 smart_streamer.py
```

**Stream local HTML:**
```bash
YOUTUBE_STREAM_KEY="key" CONTENT_PATH="file:///path/to/file.html" python3 smart_streamer.py
```

**Stream pygame game:**
```bash
YOUTUBE_STREAM_KEY="key" CONTENT_PATH="example_game.py" python3 smart_streamer.py
```

## Optimization

Auto-detects most efficient setup method (headless/X11). Perfect for cheap VPS ($4-6/mo)

*Questions? The code is self-documenting.*