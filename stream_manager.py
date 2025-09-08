#!/usr/bin/env python3
"""
Simplified Stream Manager for StreamDrop
Basic streaming functionality without complex features
"""

import os
import sys
import json
import time
import uuid
import logging
import signal
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime
from threading import Thread, Lock
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('stream-manager')

# Global lock for thread-safe operations
stream_lock = Lock()

class StreamDatabase:
    """Simple SQLite database for stream configurations"""
    
    def __init__(self, db_path="streams.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize simple database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS streams (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                platform TEXT NOT NULL,
                stream_key TEXT NOT NULL,
                source TEXT NOT NULL,
                status TEXT DEFAULT 'stopped',
                quality TEXT DEFAULT 'medium',
                title TEXT DEFAULT '',
                description TEXT DEFAULT '',
                rtmp_url TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_stream(self, stream_data):
        """Create a new stream configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stream_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO streams (id, name, type, platform, stream_key, source, 
                               quality, title, description, rtmp_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            stream_id,
            stream_data['name'],
            stream_data['type'],
            stream_data['platform'],
            stream_data['stream_key'],
            stream_data['source'],
            stream_data.get('quality', 'medium'),
            stream_data.get('title', ''),
            stream_data.get('description', ''),
            stream_data.get('rtmp_url', '')
        ))
        
        conn.commit()
        conn.close()
        return stream_id
    
    def get_all_streams(self):
        """Get all stream configurations"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM streams ORDER BY created_at DESC')
        streams = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return streams
    
    def get_stream(self, stream_id):
        """Get a specific stream configuration"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM streams WHERE id = ?', (stream_id,))
        row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None
    
    def update_stream_status(self, stream_id, status):
        """Update stream status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE streams 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, stream_id))
        
        conn.commit()
        conn.close()
    
    def update_stream(self, stream_id, stream_data):
        """Update a stream configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build dynamic update query
        update_fields = []
        values = []
        
        allowed_fields = ['name', 'title', 'description', 'quality', 'source', 'stream_key', 'rtmp_url']
        
        for field in allowed_fields:
            if field in stream_data:
                update_fields.append(f'{field} = ?')
                values.append(stream_data[field])
        
        if not update_fields:
            conn.close()
            return False
        
        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        values.append(stream_id)
        
        query = f'UPDATE streams SET {", ".join(update_fields)} WHERE id = ?'
        cursor.execute(query, values)
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def delete_stream(self, stream_id):
        """Delete a stream configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM streams WHERE id = ?', (stream_id,))
        
        conn.commit()
        conn.close()

class StreamInstance:
    """Simple stream instance with basic process management"""
    
    def __init__(self, stream_config, db):
        self.config = stream_config
        self.db = db
        self.processes = {}
        self.status = "stopped"
        
        # Simple quality settings
        self.quality_presets = {
            'low': {'resolution': '854x480', 'bitrate': '1000k', 'framerate': '24'},
            'medium': {'resolution': '1280x720', 'bitrate': '2500k', 'framerate': '30'},
            'high': {'resolution': '1920x1080', 'bitrate': '4000k', 'framerate': '30'},
            'ultra': {'resolution': '1920x1080', 'bitrate': '6000k', 'framerate': '60'}
        }
        
        # Basic platform configs
        self.platform_configs = {
            'youtube': {'rtmp_url': 'rtmp://a.rtmp.youtube.com/live2/'},
            'custom': {'rtmp_url': ''}  # User provides full URL
        }
    
    def start_streaming(self):
        """Start the streaming process"""
        if self.status == "live":
            return False, "Stream is already running"
        
        try:
            quality = self.quality_presets.get(self.config.get('quality', 'medium'))
            
            # Only pygame streaming is supported
            self._start_pygame_streaming(quality)
            
            self.status = "live"
            self.db.update_stream_status(self.config['id'], 'live')
            
            logger.info(f"Stream {self.config['name']} started successfully")
            return True, "Stream started successfully"
            
        except Exception as e:
            logger.error(f"Error starting stream {self.config['name']}: {e}")
            self.cleanup()
            return False, f"Error starting stream: {e}"
    
    def _start_pygame_streaming(self, quality):
        """Start pygame streaming"""
        logger.info("Starting pygame streaming...")
        
        try:
            from streamer import PygameStreamer
            
            width, height = map(int, quality['resolution'].split('x'))
            fps = int(quality['framerate'])
            
            self.pygame_streamer = PygameStreamer(
                stream_key=self.config['stream_key'],
                game_script=self.config.get('source'),
                width=width,
                height=height,
                fps=fps
            )
            
            success, message = self.pygame_streamer.start_streaming(
                platform=self.config.get('platform', 'youtube'),
                rtmp_url=self.config.get('rtmp_url')
            )
            
            if not success:
                raise Exception(f"Failed to start pygame streaming: {message}")
            
            logger.info("Pygame streaming started successfully")
            
        except Exception as e:
            logger.error(f"Pygame streaming failed: {e}")
            raise e
    
    
    def _build_rtmp_url(self):
        """Build RTMP URL for streaming"""
        platform = self.config.get('platform', 'youtube')
        stream_key = self.config['stream_key']
        
        if platform == 'custom' and self.config.get('rtmp_url'):
            return f"{self.config['rtmp_url']}/{stream_key}"
        
        platform_config = self.platform_configs.get(platform)
        if not platform_config:
            raise Exception(f"Unsupported platform: {platform}")
        
        return f"{platform_config['rtmp_url']}{stream_key}"
    
    def stop_streaming(self):
        """Stop the streaming process"""
        self.cleanup()
        self.status = "stopped"
        self.db.update_stream_status(self.config['id'], 'stopped')
        
        logger.info(f"Stream {self.config['name']} stopped")
        return True, "Stream stopped successfully"
    
    def cleanup(self):
        """Clean up streaming processes"""
        # Stop pygame streamer if it exists
        if hasattr(self, 'pygame_streamer'):
            try:
                self.pygame_streamer.stop_streaming()
                delattr(self, 'pygame_streamer')
            except:
                pass
        
        # Clean up FFmpeg processes
        for process_name, process in self.processes.items():
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        process.kill()
                        process.wait(timeout=2)
                    except:
                        pass
                except:
                    pass
        
        self.processes.clear()

class StreamManager:
    """Simple stream manager class"""
    
    def __init__(self):
        self.db = StreamDatabase()
        self.active_streams = {}
        self.monitor_thread = None
        self.monitoring = False
    
    def start_monitoring(self):
        """Start basic stream monitoring"""
        self.monitoring = True
        self.monitor_thread = Thread(target=self._monitor_streams, daemon=True)
        self.monitor_thread.start()
        logger.info("Stream monitoring started")
    
    def stop_monitoring(self):
        """Stop stream monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
    
    def _monitor_streams(self):
        """Minimal monitoring - just basic process checking"""
        while self.monitoring:
            try:
                time.sleep(60)  # Check every minute (less aggressive)
                with stream_lock:
                    for stream_id, stream_instance in list(self.active_streams.items()):
                        if stream_instance.status == "live":
                            # Simple check - if FFmpeg process died, mark as stopped
                            for process in stream_instance.processes.values():
                                if process and process.poll() is not None:
                                    logger.info(f"Stream {stream_id} process ended")
                                    stream_instance.status = "stopped"
                                    self.db.update_stream_status(stream_id, 'stopped')
                                    break
                
            except Exception as e:
                logger.error(f"Error in stream monitoring: {e}")
                time.sleep(10)
    
    def create_stream(self, stream_data):
        """Create a new stream"""
        try:
            stream_id = self.db.create_stream(stream_data)
            logger.info(f"Created stream {stream_data['name']} with ID {stream_id}")
            return True, stream_id, "Stream created successfully"
        except Exception as e:
            logger.error(f"Error creating stream: {e}")
            return False, None, f"Error creating stream: {e}"
    
    def start_stream(self, stream_id):
        """Start a specific stream"""
        try:
            with stream_lock:
                if stream_id in self.active_streams:
                    return self.active_streams[stream_id].start_streaming()
                
                stream_config = self.db.get_stream(stream_id)
                if not stream_config:
                    return False, "Stream not found"
                
                stream_instance = StreamInstance(stream_config, self.db)
                self.active_streams[stream_id] = stream_instance
                
                return stream_instance.start_streaming()
                
        except Exception as e:
            logger.error(f"Error starting stream {stream_id}: {e}")
            return False, f"Error starting stream: {e}"
    
    def stop_stream(self, stream_id):
        """Stop a specific stream"""
        try:
            with stream_lock:
                if stream_id not in self.active_streams:
                    # Reset status if needed
                    stream_config = self.db.get_stream(stream_id)
                    if stream_config and stream_config['status'] != 'stopped':
                        self.db.update_stream_status(stream_id, 'stopped')
                        return True, "Stream reset to stopped state"
                    return False, "Stream not active"
                
                result = self.active_streams[stream_id].stop_streaming()
                del self.active_streams[stream_id]
                return result
                
        except Exception as e:
            logger.error(f"Error stopping stream {stream_id}: {e}")
            return False, f"Error stopping stream: {e}"
    
    def update_stream(self, stream_id, stream_data):
        """Update a stream configuration"""
        try:
            with stream_lock:
                existing_stream = self.db.get_stream(stream_id)
                if not existing_stream:
                    return False, "Stream not found"
                
                # Stop stream if running
                was_running = False
                if stream_id in self.active_streams:
                    was_running = True
                    self.stop_stream(stream_id)
                
                # Update stream
                success = self.db.update_stream(stream_id, stream_data)
                if not success:
                    return False, "Failed to update stream"
                
                # Restart if it was running
                if was_running:
                    time.sleep(1)
                    self.start_stream(stream_id)
                
                return True, "Stream updated successfully"
                
        except Exception as e:
            logger.error(f"Error updating stream {stream_id}: {e}")
            return False, f"Error updating stream: {e}"
    
    def delete_stream(self, stream_id):
        """Delete a stream configuration"""
        try:
            with stream_lock:
                if stream_id in self.active_streams:
                    self.stop_stream(stream_id)
                
                self.db.delete_stream(stream_id)
                return True, "Stream deleted successfully"
                
        except Exception as e:
            logger.error(f"Error deleting stream {stream_id}: {e}")
            return False, f"Error deleting stream: {e}"
    
    def get_all_streams(self):
        """Get all streams with current status"""
        streams = self.db.get_all_streams()
        
        # Update with live status
        for stream in streams:
            stream_id = stream['id']
            if stream_id in self.active_streams:
                stream['status'] = self.active_streams[stream_id].status
        
        return streams
    
    def cleanup_all(self):
        """Clean up all active streams"""
        with stream_lock:
            for stream_instance in self.active_streams.values():
                stream_instance.cleanup()
            self.active_streams.clear()
        
        self.stop_monitoring()
        logger.info("All streams cleaned up")

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24).hex())
stream_manager = StreamManager()

def check_auth(username, password):
    """Check if username and password match stored credentials"""
    time.sleep(1)  # Prevent timing attacks
    
    try:
        if os.path.exists('.streamdrop_auth'):
            with open('.streamdrop_auth', 'r') as f:
                stored_auth = f.read().strip()
                stored_username, stored_password = stored_auth.split(':', 1)
                return username == stored_username and password == stored_password
    except Exception as e:
        logger.error(f"Error checking authentication: {e}")
    return False

def requires_auth(f):
    """Decorator to require login via session"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    error = None
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if check_auth(username, password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid username or password'
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash('Successfully logged out!', 'info')
    return redirect(url_for('login'))

@app.route('/')
@requires_auth
def dashboard():
    """Main dashboard"""
    return render_template('dashboard.html')

# Essential API Routes
@app.route('/api/streams', methods=['GET'])
@requires_auth
def api_get_streams():
    """Get all streams"""
    streams = stream_manager.get_all_streams()
    return jsonify(streams)

@app.route('/api/streams', methods=['POST'])
@requires_auth
def api_create_stream():
    """Create new stream"""
    try:
        stream_data = request.json
        success, stream_id, message = stream_manager.create_stream(stream_data)
        return jsonify({"success": success, "stream_id": stream_id, "message": message})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route('/api/streams/<stream_id>/start', methods=['POST'])
@requires_auth
def api_start_stream(stream_id):
    """Start specific stream"""
    success, message = stream_manager.start_stream(stream_id)
    return jsonify({"success": success, "message": message})

@app.route('/api/streams/<stream_id>/stop', methods=['POST'])
@requires_auth
def api_stop_stream(stream_id):
    """Stop specific stream"""
    success, message = stream_manager.stop_stream(stream_id)
    return jsonify({"success": success, "message": message})

@app.route('/api/streams/<stream_id>', methods=['PUT'])
@requires_auth
def api_update_stream(stream_id):
    """Update specific stream"""
    try:
        stream_data = request.json
        success, message = stream_manager.update_stream(stream_id, stream_data)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route('/api/streams/<stream_id>', methods=['DELETE'])
@requires_auth
def api_delete_stream(stream_id):
    """Delete specific stream"""
    success, message = stream_manager.delete_stream(stream_id)
    return jsonify({"success": success, "message": message})

@app.route('/api/platforms', methods=['GET'])
@requires_auth
def api_get_platforms():
    """Get available streaming platforms"""
    platforms = [
        {'platform_name': 'youtube', 'display_name': 'YouTube Live', 'rtmp_url': 'rtmp://a.rtmp.youtube.com/live2/'},
        {'platform_name': 'custom', 'display_name': 'Custom RTMP', 'rtmp_url': ''}
    ]
    return jsonify(platforms)

# Handle graceful shutdown
def signal_handler(sig, frame):
    logger.info("Shutting down stream manager...")
    stream_manager.cleanup_all()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    try:
        # Start stream monitoring
        stream_manager.start_monitoring()
        
        # Run Flask app
        logger.info("Starting Simple Stream Manager on port 5000")
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
        
    except KeyboardInterrupt:
        stream_manager.cleanup_all()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        stream_manager.cleanup_all()
