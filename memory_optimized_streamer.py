#!/usr/bin/env python3
"""
Memory-Optimized Streamer for Low-Memory VPS (512MB-1GB)
Implements aggressive memory optimization techniques for streaming on minimal resources
"""

import os
import sys
import subprocess
import time
import signal
import logging
import psutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MemoryOptimizedStreamer:
    """Ultra-low memory streaming implementation"""
    
    def __init__(self, stream_key, platform='youtube', content_type='test_pattern'):
        self.stream_key = stream_key
        self.platform = platform
        self.content_type = content_type
        self.processes = {}
        self.streaming = False
        
        # Platform-specific RTMP URLs
        self.rtmp_urls = {
            'youtube': 'rtmp://a.rtmp.youtube.com/live2/',
            'twitch': 'rtmp://live.twitch.tv/app/',
            'facebook': 'rtmps://live-api-s.facebook.com:443/rtmp/',
            'custom': os.environ.get('RTMP_URL', 'rtmp://localhost/live/')
        }
        
        # Detect system memory
        self.total_memory_mb = psutil.virtual_memory().total // (1024 * 1024)
        self.configure_for_memory()
        
    def configure_for_memory(self):
        """Configure streaming parameters based on available memory"""
        if self.total_memory_mb < 512:
            logger.error("System has less than 512MB RAM - streaming not recommended")
            self.config = None
        elif self.total_memory_mb < 768:
            # Ultra-low memory mode (512-768MB)
            self.config = {
                'resolution': '640x360',
                'framerate': '20',
                'video_bitrate': '400k',
                'audio_bitrate': '64k',
                'preset': 'ultrafast',
                'buffer_size': '200k',
                'gop_size': '40',
                'mode': 'test_pattern_only'
            }
            logger.info("Configured for ULTRA-LOW memory mode (512-768MB)")
        elif self.total_memory_mb < 1024:
            # Low memory mode (768MB-1GB)
            self.config = {
                'resolution': '854x480',
                'framerate': '24',
                'video_bitrate': '800k',
                'audio_bitrate': '96k',
                'preset': 'superfast',
                'buffer_size': '400k',
                'gop_size': '48',
                'mode': 'test_pattern_or_simple'
            }
            logger.info("Configured for LOW memory mode (768MB-1GB)")
        elif self.total_memory_mb < 2048:
            # Medium memory mode (1-2GB)
            self.config = {
                'resolution': '1280x720',
                'framerate': '30',
                'video_bitrate': '1500k',
                'audio_bitrate': '128k',
                'preset': 'veryfast',
                'buffer_size': '1500k',
                'gop_size': '60',
                'mode': 'optimized_browser'
            }
            logger.info("Configured for MEDIUM memory mode (1-2GB)")
        else:
            # Standard mode (2GB+)
            self.config = {
                'resolution': '1920x1080',
                'framerate': '30',
                'video_bitrate': '2500k',
                'audio_bitrate': '128k',
                'preset': 'veryfast',
                'buffer_size': '2500k',
                'gop_size': '60',
                'mode': 'full'
            }
            logger.info("Configured for STANDARD mode (2GB+)")
            
    def check_prerequisites(self):
        """Check if required tools are installed"""
        required_tools = ['ffmpeg']
        missing = []
        
        for tool in required_tools:
            try:
                subprocess.run([tool, '-version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing.append(tool)
                
        if missing:
            logger.error(f"Missing required tools: {', '.join(missing)}")
            return False
            
        return True
        
    def clear_memory(self):
        """Clear system caches to free memory before streaming"""
        logger.info("Clearing memory caches...")
        try:
            # Sync filesystems
            subprocess.run(['sync'], check=False)
            # Clear caches (requires root)
            subprocess.run(['sudo', 'sh', '-c', 'echo 1 > /proc/sys/vm/drop_caches'], check=False)
            time.sleep(1)
        except:
            logger.warning("Could not clear memory caches (requires sudo)")
            
    def start_test_pattern_stream(self):
        """Start ultra-lightweight test pattern streaming"""
        logger.info(f"Starting test pattern stream at {self.config['resolution']} @ {self.config['framerate']}fps")
        
        # Build RTMP URL
        rtmp_url = self.rtmp_urls.get(self.platform, self.rtmp_urls['custom'])
        full_url = f"{rtmp_url}{self.stream_key}"
        
        # Build FFmpeg command with minimal resource usage
        ffmpeg_cmd = [
            'ffmpeg',
            '-re',  # Read input at native frame rate
            '-f', 'lavfi',
            '-i', f'testsrc2=size={self.config["resolution"]}:rate={self.config["framerate"]}',
            '-f', 'lavfi',
            '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
            '-vf', f'drawtext=text="StreamDrop Low Memory Mode":x=10:y=10:fontsize=20:fontcolor=white,'
                   f'drawtext=text="Memory: {self.total_memory_mb}MB":x=10:y=40:fontsize=16:fontcolor=yellow,'
                   f'drawtext=text="%{{localtime\\:%H\\:%M\\:%S}}":x=10:y=70:fontsize=16:fontcolor=lime',
            '-c:v', 'libx264',
            '-preset', self.config['preset'],
            '-tune', 'zerolatency',  # Reduce latency
            '-b:v', self.config['video_bitrate'],
            '-maxrate', self.config['video_bitrate'],
            '-bufsize', self.config['buffer_size'],
            '-pix_fmt', 'yuv420p',
            '-g', self.config['gop_size'],
            '-c:a', 'aac',
            '-b:a', self.config['audio_bitrate'],
            '-ar', '44100',
            '-f', 'flv',
            full_url
        ]
        
        # Add ultra-low memory flags for 512MB systems
        if self.total_memory_mb < 768:
            ffmpeg_cmd.extend([
                '-threads', '1',  # Single thread to reduce memory
                '-thread_queue_size', '32',  # Smaller queue
            ])
            
        logger.info(f"FFmpeg command: {' '.join(ffmpeg_cmd[:10])}...")
        
        try:
            self.processes['ffmpeg'] = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Check if process started successfully
            time.sleep(2)
            if self.processes['ffmpeg'].poll() is not None:
                stderr = self.processes['ffmpeg'].stderr.read().decode()
                logger.error(f"FFmpeg failed to start: {stderr[:500]}")
                return False
                
            self.streaming = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to start FFmpeg: {e}")
            return False
            
    def start_optimized_browser_stream(self):
        """Start browser streaming with aggressive memory optimization"""
        logger.info("Starting memory-optimized browser streaming...")
        
        # Check if Chromium is available
        chrome_binary = None
        for binary in ['chromium-browser', 'chromium', 'google-chrome']:
            try:
                subprocess.run([binary, '--version'], capture_output=True, check=True)
                chrome_binary = binary
                break
            except:
                continue
                
        if not chrome_binary:
            logger.error("No Chrome/Chromium browser found")
            return False
            
        # Build Chrome command with extreme memory optimization
        chrome_cmd = [
            chrome_binary,
            '--headless',
            '--disable-gpu',
            '--no-sandbox',
            '--disable-dev-shm-usage',  # CRITICAL for low memory
            '--disable-setuid-sandbox',
            '--single-process',  # Run in single process mode
            '--no-zygote',  # Don't use zygote process
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--disable-breakpad',
            '--disable-software-rasterizer',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-images',  # Don't load images
            '--disable-javascript',  # Disable JS if possible
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection',
            '--disable-background-networking',
            '--disable-sync',
            '--disable-default-apps',
            '--disable-hang-monitor',
            '--disable-component-update',
            '--memory-pressure-off',
            '--max_old_space_size=64',  # Limit V8 heap to 64MB
            '--js-flags="--max-old-space-size=64 --max-semi-space-size=1"',
            '--aggressive-cache-discard',
            '--aggressive-tab-discard',
            f'--window-size={self.config["resolution"]}',
            '--force-device-scale-factor=0.75',  # Reduce rendering scale
            '--virtual-time-budget=5000',
            '--enable-low-end-device-mode',  # Enable low-end device optimizations
            '--disable-site-isolation-trials',
            '--disable-features=site-per-process',
            '--remote-debugging-port=9222',
            os.environ.get('CONTENT_URL', 'https://example.com')
        ]
        
        logger.info(f"Starting Chrome with {len(chrome_cmd)} optimization flags...")
        
        try:
            # Start Chrome
            self.processes['chrome'] = subprocess.Popen(
                chrome_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait and check if Chrome started
            time.sleep(3)
            if self.processes['chrome'].poll() is not None:
                stderr = self.processes['chrome'].stderr.read().decode()
                logger.error(f"Chrome failed to start: {stderr[:500]}")
                
                # Fall back to test pattern
                logger.info("Falling back to test pattern streaming...")
                return self.start_test_pattern_stream()
                
            # If Chrome started, capture and stream
            # TODO: Implement Chrome DevTools Protocol capture
            logger.warning("Browser streaming not fully implemented - using test pattern")
            return self.start_test_pattern_stream()
            
        except Exception as e:
            logger.error(f"Failed to start Chrome: {e}")
            return self.start_test_pattern_stream()
            
    def start_streaming(self):
        """Start streaming with appropriate method based on memory"""
        if not self.config:
            return False, "System memory too low for streaming"
            
        if not self.check_prerequisites():
            return False, "Missing required tools"
            
        # Clear memory before starting
        self.clear_memory()
        
        # Log memory status
        mem = psutil.virtual_memory()
        logger.info(f"Memory status - Total: {mem.total//1024//1024}MB, Available: {mem.available//1024//1024}MB")
        
        # Choose streaming method based on configuration
        if self.config['mode'] in ['test_pattern_only', 'test_pattern_or_simple']:
            success = self.start_test_pattern_stream()
        elif self.config['mode'] == 'optimized_browser':
            success = self.start_optimized_browser_stream()
        else:
            success = self.start_test_pattern_stream()  # Default fallback
            
        if success:
            self.monitor_stream()
            return True, f"Streaming started in {self.config['mode']} mode"
        else:
            return False, "Failed to start streaming"
            
    def monitor_stream(self):
        """Monitor stream health and memory usage"""
        def monitor_loop():
            while self.streaming:
                try:
                    # Check memory usage
                    mem = psutil.virtual_memory()
                    mem_percent = mem.percent
                    
                    if mem_percent > 90:
                        logger.warning(f"High memory usage: {mem_percent}%")
                        
                    # Check if FFmpeg is still running
                    if 'ffmpeg' in self.processes:
                        if self.processes['ffmpeg'].poll() is not None:
                            logger.error("FFmpeg process died")
                            self.streaming = False
                            break
                            
                    time.sleep(10)  # Check every 10 seconds
                    
                except Exception as e:
                    logger.error(f"Monitor error: {e}")
                    
        import threading
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        
    def stop_streaming(self):
        """Stop all streaming processes"""
        logger.info("Stopping streaming...")
        self.streaming = False
        
        for name, process in self.processes.items():
            if process and process.poll() is None:
                logger.info(f"Terminating {name}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    
        self.processes.clear()
        logger.info("Streaming stopped")
        
def main():
    """Main entry point"""
    print("🚀 Memory-Optimized StreamDrop Streamer")
    print("="*50)
    
    # Get configuration from environment
    stream_key = os.environ.get('YOUTUBE_STREAM_KEY')
    if not stream_key:
        print("❌ YOUTUBE_STREAM_KEY environment variable required")
        sys.exit(1)
        
    platform = os.environ.get('PLATFORM', 'youtube')
    
    # Create streamer
    streamer = MemoryOptimizedStreamer(stream_key, platform)
    
    # Check memory
    mem = psutil.virtual_memory()
    print(f"📊 System Memory: {mem.total//1024//1024}MB total, {mem.available//1024//1024}MB available")
    
    if mem.total < 512 * 1024 * 1024:
        print("❌ ERROR: Less than 512MB RAM detected")
        print("   StreamDrop requires at least 512MB RAM")
        print("   Recommended: Upgrade to 1GB+ droplet")
        sys.exit(1)
        
    # Setup signal handlers
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down...")
        streamer.stop_streaming()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start streaming
    success, message = streamer.start_streaming()
    
    if success:
        print(f"✅ {message}")
        print("📺 Stream is now live!")
        print("💡 Press Ctrl+C to stop")
        
        # Keep running
        try:
            while streamer.streaming:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        print(f"❌ {message}")
        sys.exit(1)
        
if __name__ == "__main__":
    main()
