#!/usr/bin/env python3
"""
Pure Pygame Streamer - Direct memory rendering to FFmpeg
No X11, no virtual display, just pure frame generation to RTMP
"""

import os
import sys
import subprocess
import pygame
import numpy as np
import time
import logging
import signal
from threading import Thread, Event
from queue import Queue

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PygameStreamer:
    def __init__(self, stream_key, game_script=None, width=1280, height=720, fps=30):
        """
        Initialize pygame streamer
        
        Args:
            stream_key: YouTube/platform stream key
            game_script: Path to pygame script to run (optional)
            width: Stream width
            height: Stream height
            fps: Frames per second
        """
        self.stream_key = stream_key
        self.game_script = game_script
        self.width = width
        self.height = height
        self.fps = fps
        self.running = False
        self.ffmpeg_process = None
        self.frame_queue = Queue(maxsize=30)  # Buffer up to 1 second of frames
        self.stop_event = Event()
        
        # Initialize pygame with dummy video driver (no display needed!)
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
        pygame.init()
        
        # Create surface for rendering (in memory only)
        self.screen = pygame.Surface((width, height))
        self.clock = pygame.time.Clock()
        
        logger.info(f"Initialized pygame streamer: {width}x{height} @ {fps}fps")
    
    def start_ffmpeg(self, platform='youtube', rtmp_url=None):
        """Start FFmpeg process to receive raw frames and stream to RTMP"""
        
        # Build RTMP URL
        if platform == 'youtube':
            output_url = f'rtmp://a.rtmp.youtube.com/live2/{self.stream_key}'
        elif platform == 'twitch':
            output_url = f'rtmp://live.twitch.tv/live/{self.stream_key}'
        elif platform == 'custom' and rtmp_url:
            output_url = f'{rtmp_url}/{self.stream_key}'
        else:
            raise ValueError(f"Unsupported platform: {platform}")
        
        # FFmpeg command to receive raw RGB frames via stdin and encode to RTMP
        ffmpeg_cmd = [
            'ffmpeg',
            '-y',  # Overwrite output
            '-f', 'rawvideo',  # Input format
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'rgb24',  # Pygame uses RGB
            '-s', f'{self.width}x{self.height}',  # Size
            '-r', str(self.fps),  # Input framerate
            '-i', '-',  # Read from stdin
            '-f', 'lavfi',  # Add silent audio (required by YouTube)
            '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
            '-c:v', 'libx264',  # Video codec
            '-preset', 'ultrafast',  # Fast encoding for low latency
            '-tune', 'zerolatency',  # Optimize for streaming
            '-pix_fmt', 'yuv420p',  # Output pixel format
            '-b:v', '2500k',  # Video bitrate
            '-maxrate', '2500k',
            '-bufsize', '5000k',
            '-g', str(self.fps * 2),  # Keyframe interval
            '-c:a', 'aac',  # Audio codec
            '-b:a', '128k',  # Audio bitrate
            '-ar', '44100',  # Audio sample rate
            '-f', 'flv',  # Output format
            output_url
        ]
        
        logger.info(f"Starting FFmpeg: {' '.join(ffmpeg_cmd[:10])}...")
        
        # Start FFmpeg with pipe for stdin
        self.ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        return self.ffmpeg_process.poll() is None
    
    def render_frame(self):
        """Render a frame - requires a game script"""
        if not self.game_script or not os.path.exists(self.game_script):
            raise Exception("Game script is required for pygame streaming")
        
        # Load and execute the game script
        # This is where the actual game/content should render to self.screen
        # The game script must handle all rendering logic
        try:
            # Import and run the game script
            import importlib.util
            spec = importlib.util.spec_from_file_location("game", self.game_script)
            game_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(game_module)
            
            # The game script should have a render function that takes screen as parameter
            if hasattr(game_module, 'render'):
                game_module.render(self.screen)
            else:
                raise Exception("Game script must have a 'render(screen)' function")
        except Exception as e:
            # Fill with error message if game script fails
            self.screen.fill((50, 0, 0))  # Dark red background
            font = pygame.font.Font(None, 36)
            error_text = font.render(f"Game Error: {str(e)}", True, (255, 255, 255))
            text_rect = error_text.get_rect(center=(self.width/2, self.height/2))
            self.screen.blit(error_text, text_rect)
    
    def frame_generator(self):
        """Generate frames and send to FFmpeg"""
        logger.info("Starting frame generation...")
        
        try:
            while self.running:
                # Render frame
                self.render_frame()
                
                # Convert pygame surface to numpy array (RGB format)
                frame = pygame.surfarray.array3d(self.screen)
                # Pygame uses (width, height, 3) but we need (height, width, 3)
                frame = np.transpose(frame, (1, 0, 2))
                # Convert to bytes
                frame_bytes = frame.astype(np.uint8).tobytes()
                
                # Send frame to FFmpeg
                if self.ffmpeg_process and self.ffmpeg_process.stdin:
                    try:
                        self.ffmpeg_process.stdin.write(frame_bytes)
                        self.ffmpeg_process.stdin.flush()
                    except BrokenPipeError:
                        logger.error("FFmpeg pipe broken - process may have died")
                        self.running = False
                        break
                    except Exception as e:
                        logger.error(f"Error writing frame to FFmpeg: {e}")
                        break
                
                # Maintain framerate
                self.clock.tick(self.fps)
                
        except Exception as e:
            logger.error(f"Frame generation error: {e}")
        finally:
            logger.info("Frame generation stopped")
    
    def start_streaming(self, platform='youtube', rtmp_url=None):
        """Start the streaming process"""
        if self.running:
            return False, "Already streaming"
        
        try:
            # Start FFmpeg
            if not self.start_ffmpeg(platform, rtmp_url):
                return False, "Failed to start FFmpeg"
            
            # Start frame generation
            self.running = True
            self.frame_thread = Thread(target=self.frame_generator, daemon=True)
            self.frame_thread.start()
            
            logger.info("✅ Streaming started successfully!")
            return True, "Streaming started"
            
        except Exception as e:
            logger.error(f"Failed to start streaming: {e}")
            self.stop_streaming()
            return False, f"Error: {e}"
    
    def stop_streaming(self):
        """Stop the streaming process"""
        logger.info("Stopping stream...")
        self.running = False
        self.stop_event.set()
        
        # Close FFmpeg stdin to signal end of stream
        if self.ffmpeg_process:
            try:
                if self.ffmpeg_process.stdin:
                    self.ffmpeg_process.stdin.close()
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ffmpeg_process.kill()
            except Exception as e:
                logger.error(f"Error stopping FFmpeg: {e}")
        
        logger.info("✅ Stream stopped")
        return True, "Stream stopped"
    
    def get_status(self):
        """Get streaming status"""
        if self.running and self.ffmpeg_process:
            if self.ffmpeg_process.poll() is None:
                return "running"
            else:
                return "error"
        return "stopped"


def main():
    """Standalone CLI for testing"""
    stream_key = os.environ.get('YOUTUBE_STREAM_KEY')
    if not stream_key:
        logger.error("YOUTUBE_STREAM_KEY environment variable required")
        sys.exit(1)
    
    game_script = os.environ.get('GAME_SCRIPT')
    
    # Create streamer
    streamer = PygameStreamer(stream_key, game_script)
    
    # Handle shutdown
    def signal_handler(sig, frame):
        logger.info("\nShutting down...")
        streamer.stop_streaming()
        pygame.quit()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start streaming
    success, message = streamer.start_streaming()
    if not success:
        logger.error(f"Failed to start: {message}")
        sys.exit(1)
    
    logger.info("🎮 Pygame streaming active!")
    logger.info("📺 Check your YouTube Live dashboard")
    logger.info("Press Ctrl+C to stop")
    
    # Keep running
    try:
        while streamer.get_status() == "running":
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    
    streamer.stop_streaming()
    pygame.quit()

if __name__ == "__main__":
    main()
