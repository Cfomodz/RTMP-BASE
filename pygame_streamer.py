#!/usr/bin/env python3
"""
Pygame Streamer - Modified RTMP-BASE for pygame content
"""

import os
import sys
import time
import logging
import signal
import subprocess
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('pygame-streamer')

app = Flask(__name__)

class PygameStreamer:
    def __init__(self):
        self.pygame_process = None
        self.display_process = None
        self.ffmpeg_process = None
        self.status = "stopped"
        self.stream_key = os.environ.get('YOUTUBE_STREAM_KEY', '')
        self.pygame_script = os.environ.get('PYGAME_SCRIPT', 'game.py')
        
    def start_streaming(self):
        """Start streaming pygame content"""
        if not self.stream_key:
            return False, "YouTube stream key not configured"
            
        if self.status == "running":
            return False, "Stream is already running"
            
        try:
            # Set up virtual display
            self.display_process = subprocess.Popen([
                'Xvfb', ':99', '-screen', '0', '1280x720x24', '-ac'
            ])
            
            # Allow Xvfb to start
            time.sleep(2)
            
            # Set display environment variable
            env = os.environ.copy()
            env['DISPLAY'] = ':99'
            
            # Launch your pygame script on the virtual display
            if os.path.exists(self.pygame_script):
                self.pygame_process = subprocess.Popen([
                    'python3', self.pygame_script
                ], env=env)
                
                # Allow pygame to start
                time.sleep(3)
            else:
                logger.warning(f"Pygame script {self.pygame_script} not found, streaming display only")
            
            # Start FFmpeg to capture and stream
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'x11grab',  # Capture X11 display
                '-video_size', '1280x720',
                '-framerate', '30',
                '-i', ':99',
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-b:v', '2500k',
                '-maxrate', '2500k',
                '-bufsize', '5000k',
                '-pix_fmt', 'yuv420p',
                '-g', '60',
                '-f', 'flv',
                f'rtmp://a.rtmp.youtube.com/live2/{self.stream_key}'
            ]
            
            # Start FFmpeg process
            self.ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.status = "running"
            logger.info("Pygame streaming started")
            return True, "Pygame streaming started successfully"
            
        except Exception as e:
            logger.error(f"Error starting stream: {e}")
            self.cleanup()
            return False, f"Error starting stream: {e}"
    
    def stop_streaming(self):
        """Stop the streaming processes"""
        self.cleanup()
        self.status = "stopped"
        logger.info("Streaming stopped")
        return True, "Streaming stopped"
    
    def cleanup(self):
        """Clean up all processes"""
        for proc in [self.pygame_process, self.ffmpeg_process, self.display_process]:
            if proc:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except:
                    try:
                        proc.kill()
                    except:
                        pass
                finally:
                    proc = None
    
    def get_status(self):
        """Get current streaming status"""
        return {
            "status": self.status,
            "stream_key_set": bool(self.stream_key),
            "pygame_script": self.pygame_script
        }

# Create global streamer instance
streamer = PygameStreamer()

@app.route('/')
def index():
    """Main dashboard"""
    status = streamer.get_status()
    return render_template('pygame_index.html', status=status)

@app.route('/api/start', methods=['POST'])
def api_start():
    """API endpoint to start streaming"""
    success, message = streamer.start_streaming()
    return jsonify({"success": success, "message": message})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    """API endpoint to stop streaming"""
    success, message = streamer.stop_streaming()
    return jsonify({"success": success, "message": message})

@app.route('/api/status', methods=['GET'])
def api_status():
    """API endpoint to get status"""
    return jsonify(streamer.get_status())

@app.route('/api/update_script', methods=['POST'])
def api_update_script():
    """API endpoint to update pygame script path"""
    script_path = request.json.get('script_path')
    if script_path:
        streamer.pygame_script = script_path
        # Restart stream if running to apply changes
        if streamer.status == "running":
            streamer.stop_streaming()
            time.sleep(2)
            streamer.start_streaming()
        return jsonify({"success": True, "message": "Pygame script updated"})
    return jsonify({"success": False, "message": "No script path provided"})

# Handle graceful shutdown
def signal_handler(sig, frame):
    logger.info("Shutting down...")
    streamer.cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    # Run the web server
    app.run(host='0.0.0.0', port=5000, debug=True)
