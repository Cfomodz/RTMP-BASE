<div align="center">
  <img src="logo.png" width="120" height="120" alt="StreamDrop Logo"/>
  <h1>StreamDrop</h1>
  <h3>Stream any website, PyGame, or local HTML file to YouTube 24/7 on a $4/mo Droplet</h2>
</div>
 

**1. Quick Start:**
```bash
git clone https://github.com/Cfomodz/StreamDrop.git
cd StreamDrop
chmod +x setup.sh && ./setup.sh
```

**2. Get your YouTube Stream Key from [YouTube Studio](https://studio.youtube.com)**

**3. Start Streaming:**
```bash
YOUTUBE_STREAM_KEY="your_key" CONTENT_PATH="https://yoursite.com" python3 smart_streamer.py
```
<div align="center">
  <h2>That's it. You're live!</h2>
</div>

### Web Interface

Open `http://your-server-ip:5000` to control streams.

### Auto-Start Service

```bash
sudo systemctl enable streamdrop
sudo systemctl start streamdrop
```


### Environment Variables

```bash
YOUTUBE_STREAM_KEY="your_key"
CONTENT_PATH="https://example.com"
```

### Examples

**Stream a website:**
```bash
YOUTUBE_STREAM_KEY="your_key" CONTENT_PATH="https://clock.zone" python3 smart_streamer.py
```

**Stream local HTML:**
```bash
YOUTUBE_STREAM_KEY="your_key" CONTENT_PATH="file:///path/to/file.html" python3 smart_streamer.py
```

**Stream pygame game:**
```bash
YOUTUBE_STREAM_KEY="your_key" CONTENT_PATH="fun_game.py" python3 smart_streamer.py
```

### Optimization

Auto-detects most efficient setup method (headless/X11). Perfect for cheap VPS ($4-6/mo)

### "Roadmap"

If someone would like to fork this and PR some alternative deployment options instead of just Ubuntu Server and Ubuntu Desktop (or go beyond apt based, or even unix based), I am open to that. If you do, please consider make it autodetecting or at least parameterized.


*Questions? The code is self-documenting.*

---

### Made with <3 by the FOSS community. 100% Funded by devs like you.
