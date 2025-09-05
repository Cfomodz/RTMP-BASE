#!/usr/bin/env python3
"""
Optimized Headless Streamer - NO X11 REQUIRED
True headless streaming using direct frame capture methods:
- HTML: Chrome DevTools Protocol for direct screenshots
- Pygame: Surface data directly to FFmpeg stdin
"""

import os
import sys
import json
import time
import signal
import logging
import asyncio
import subprocess
import threading
from pathlib import Path
from io import BytesIO

import requests
from PIL import Image
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HeadlessHTMLStreamer:
    """True headless HTML streaming using Chrome DevTools Protocol"""
    
    def __init__(self, stream_key, content_path="https://example.com"):
        self.stream_key = stream_key
        self.content_path = content_path
        self.chrome_process = None
        self.ffmpeg_process = None
        self.streaming = False
        self.debug_port = 9222
        
    def start_chromium_headless(self):
        """Start Chromium in true headless mode with remote debugging"""
        chromium_cmd = [
            'chromium-browser',
            '--headless=new',  # New headless mode (more efficient)
            '--no-gpu',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=TranslateUI',
            '--disable-sync',  # No Google account sync
            '--disable-background-networking',  # No telemetry
            '--disable-default-apps',
            '--disable-component-update',
            '--remote-debugging-port=' + str(self.debug_port),
            '--remote-debugging-address=127.0.0.1',
            '--window-size=1280,720',
            '--virtual-time-budget=5000',
            self.content_path
        ]
        
        logger.info("Starting Chromium in optimized headless mode...")
        self.chrome_process = subprocess.Popen(
            chromium_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for Chrome to be ready
        time.sleep(3)
        return self.chrome_process.poll() is None
        
    def get_chromium_tab_id(self):
        """Get the tab ID from Chromium DevTools API"""
        try:
            response = requests.get(f'http://127.0.0.1:{self.debug_port}/json/list', timeout=5)
            tabs = response.json()
            if tabs:
                return tabs[0]['id']
        except Exception as e:
            logger.error(f"Failed to get Chromium tab ID: {e}")
        return None
        
    def capture_screenshot(self, tab_id):
        """Capture screenshot using Chromium DevTools Protocol"""
        try:
            # Take screenshot via DevTools
            screenshot_cmd = {
                "id": 1,
                "method": "Page.captureScreenshot",
                "params": {"format": "png", "quality": 90}
            }
            
            response = requests.post(
                f'http://127.0.0.1:{self.debug_port}/json/runtime/evaluate',
                json=screenshot_cmd,
                timeout=2
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'result' in result and 'data' in result['result']:
                    return result['result']['data']
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
        return None
        
    def start_ffmpeg_stream(self):
        """Start FFmpeg with stdin input for direct frame feeding"""
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'image2pipe',           # Input from pipe
            '-vcodec', 'png',             # Input codec
            '-framerate', '30',           # Input framerate
            '-i', '-',                    # Read from stdin
            '-c:v', 'libx264',           # Output video codec
            '-preset', 'veryfast',       # Encoding speed
            '-b:v', '2500k',             # Video bitrate
            '-maxrate', '2500k',         # Max bitrate
            '-bufsize', '5000k',         # Buffer size
            '-pix_fmt', 'yuv420p',       # Pixel format
            '-g', '60',                  # GOP size
            '-f', 'flv',                 # Output format
            f'rtmp://a.rtmp.youtube.com/live2/{self.stream_key}'
        ]
        
        logger.info("Starting optimized FFmpeg stream (no X11 capture)...")
        self.ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        return self.ffmpeg_process.poll() is None
        
    def stream_loop(self):
        """Main streaming loop - captures and feeds frames to FFmpeg"""
        tab_id = self.get_chromium_tab_id()
        if not tab_id:
            logger.error("Could not get Chromium tab ID")
            return
            
        logger.info("Starting headless streaming loop...")
        frame_count = 0
        
        while self.streaming and self.ffmpeg_process.poll() is None:
            try:
                # Capture screenshot from Chromium
                screenshot_data = self.capture_screenshot(tab_id)
                
                if screenshot_data:
                    # Convert base64 to image bytes
                    import base64
                    image_bytes = base64.b64decode(screenshot_data)
                    
                    # Feed directly to FFmpeg stdin
                    self.ffmpeg_process.stdin.write(image_bytes)
                    self.ffmpeg_process.stdin.flush()
                    
                    frame_count += 1
                    if frame_count % 300 == 0:  # Log every 10 seconds at 30fps
                        logger.info(f"Streamed {frame_count} frames (headless)")
                
                # 30 FPS timing
                time.sleep(1/30)
                
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                time.sleep(0.1)
                
    def start_streaming(self):
        """Start the complete headless streaming process"""
        if not self.start_chromium_headless():
            return False, "Failed to start Chromium"
            
        if not self.start_ffmpeg_stream():
            return False, "Failed to start FFmpeg"
            
        self.streaming = True
        
        # Start streaming in separate thread
        stream_thread = threading.Thread(target=self.stream_loop, daemon=True)
        stream_thread.start()
        
        return True, "Headless streaming started successfully"
        
    def stop_streaming(self):
        """Stop all streaming processes"""
        self.streaming = False
        
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            try:
                self.ffmpeg_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ffmpeg_process.kill()
                
        if self.chrome_process:
            self.chrome_process.terminate()
            try:
                self.chrome_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.chrome_process.kill()
                
        logger.info("Headless streaming stopped")


class HeadlessPygameStreamer:
    """True headless Pygame streaming - direct surface capture"""
    
    def __init__(self, stream_key, pygame_script="example_game.py"):
        self.stream_key = stream_key
        self.pygame_script = pygame_script
        self.ffmpeg_process = None
        self.streaming = False
        
    def start_pygame_headless(self):
        """Start Pygame in headless mode using dummy video driver"""
        # Set SDL to use dummy video driver (no display needed)
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        
        # Import pygame after setting video driver
        try:
            import pygame
            pygame.init()
            pygame.display.set_mode((1280, 720))
            return True
        except Exception as e:
            logger.error(f"Failed to initialize headless Pygame: {e}")
            return False
            
    def capture_pygame_surface(self):
        """Capture pygame surface as raw image data"""
        try:
            import pygame
            surface = pygame.display.get_surface()
            if surface:
                # Convert surface to RGB array
                rgb_array = pygame.surfarray.array3d(surface)
                # Transpose for correct orientation
                rgb_array = np.transpose(rgb_array, (1, 0, 2))
                # Convert to PIL Image
                image = Image.fromarray(rgb_array.astype('uint8'), 'RGB')
                
                # Convert to PNG bytes
                img_bytes = BytesIO()
                image.save(img_bytes, format='PNG')
                return img_bytes.getvalue()
        except Exception as e:
            logger.error(f"Surface capture failed: {e}")
        return None
        
    def start_streaming(self):
        """Start headless Pygame streaming"""
        if not self.start_pygame_headless():
            return False, "Failed to initialize headless Pygame"
            
        # Start FFmpeg for direct frame input
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'image2pipe',
            '-vcodec', 'png',
            '-framerate', '60',
            '-i', '-',
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-b:v', '3000k',
            '-maxrate', '3000k',
            '-bufsize', '6000k',
            '-pix_fmt', 'yuv420p',
            '-g', '120',
            '-f', 'flv',
            f'rtmp://a.rtmp.youtube.com/live2/{self.stream_key}'
        ]
        
        self.ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Load and run the pygame script
        if os.path.exists(self.pygame_script):
            exec(open(self.pygame_script).read())
            
        self.streaming = True
        logger.info("Headless Pygame streaming started")
        return True, "Headless Pygame streaming started"


def main():
    """Main function for testing headless streaming"""
    stream_key = os.environ.get('YOUTUBE_STREAM_KEY')
    if not stream_key:
        logger.error("YOUTUBE_STREAM_KEY environment variable required")
        sys.exit(1)
        
    content_path = os.environ.get('CONTENT_PATH')
    if not content_path:
        logger.error("CONTENT_PATH environment variable required")
        logger.error("Example: CONTENT_PATH='https://clock.zone' python3 smart_streamer.py")
        sys.exit(1)
    
    # Auto-detect mode from content path
    if content_path.endswith('.py'):
        mode = 'pygame'
        streamer = HeadlessPygameStreamer(stream_key, content_path)
    else:
        mode = 'html'
        streamer = HeadlessHTMLStreamer(stream_key, content_path)
        
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Stopping headless streaming...")
        streamer.stop_streaming()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start streaming
    success, message = streamer.start_streaming()
    if success:
        logger.info(f"✅ {message}")
        logger.info("🚀 Headless streaming active - no GUI/X11 needed!")
        logger.info("💰 Perfect for cheap VPS instances")
        
        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        logger.error(f"❌ Failed to start: {message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
