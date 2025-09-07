#!/usr/bin/env python3
"""
StreamDrop Diagnostic Tool
Tests streaming capabilities and recommends optimal configuration for your VPS
"""

import os
import sys
import subprocess
import time
import psutil
import json
from pathlib import Path

class StreamingDiagnostic:
    def __init__(self):
        self.results = {
            'system': {},
            'tests': {},
            'recommendations': []
        }
        
    def check_system_resources(self):
        """Check system memory and resources"""
        print("🔍 Checking system resources...")
        
        # Memory info
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        self.results['system']['memory_mb'] = mem.total // (1024 * 1024)
        self.results['system']['available_mb'] = mem.available // (1024 * 1024)
        self.results['system']['swap_mb'] = swap.total // (1024 * 1024)
        
        # Check /dev/shm size
        try:
            shm_stat = os.statvfs('/dev/shm')
            shm_size_mb = (shm_stat.f_blocks * shm_stat.f_frsize) // (1024 * 1024)
            self.results['system']['shm_size_mb'] = shm_size_mb
        except:
            self.results['system']['shm_size_mb'] = 0
            
        # CPU info
        self.results['system']['cpu_count'] = psutil.cpu_count()
        
        print(f"  ✓ Total Memory: {self.results['system']['memory_mb']}MB")
        print(f"  ✓ Available Memory: {self.results['system']['available_mb']}MB")
        print(f"  ✓ Swap: {self.results['system']['swap_mb']}MB")
        print(f"  ✓ Shared Memory (/dev/shm): {self.results['system']['shm_size_mb']}MB")
        print(f"  ✓ CPU Cores: {self.results['system']['cpu_count']}")
        
        return self.results['system']
        
    def test_chromium_launch(self, memory_optimized=False):
        """Test if Chromium can launch with given settings"""
        print(f"\n🧪 Testing Chromium launch {'(memory optimized)' if memory_optimized else '(standard)'}...")
        
        chrome_cmd = ['chromium-browser', '--version']
        try:
            result = subprocess.run(chrome_cmd, capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                print("  ❌ Chromium not installed")
                return False, 0
        except:
            print("  ❌ Chromium not found")
            return False, 0
            
        # Test actual browser launch
        if memory_optimized:
            chrome_cmd = [
                'chromium-browser',
                '--headless',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-dev-shm-usage',  # Critical for low memory
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-breakpad',
                '--disable-software-rasterizer',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--disable-background-networking',
                '--disable-sync',
                '--metrics-recording-only',
                '--no-first-run',
                '--disable-default-apps',
                '--disable-hang-monitor',
                '--disable-popup-blocking',
                '--disable-prompt-on-repost',
                '--disable-domain-reliability',
                '--disable-component-update',
                '--disable-features=AutofillServerCommunication',
                '--disable-features=CertificateTransparencyComponentUpdater',
                '--single-process',  # Use single process mode for low memory
                '--memory-pressure-off',
                '--max_old_space_size=96',  # Limit V8 heap
                '--js-flags="--max-old-space-size=96 --max-semi-space-size=2"',
                '--aggressive-cache-discard',
                '--aggressive-tab-discard',
                '--window-size=854,480',  # Smaller window for less memory
                'about:blank'
            ]
        else:
            chrome_cmd = [
                'chromium-browser',
                '--headless',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--window-size=1280,720',
                'about:blank'
            ]
            
        try:
            process = subprocess.Popen(chrome_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(3)  # Let it run for 3 seconds
            
            if process.poll() is None:
                # Still running
                memory_used = psutil.Process(process.pid).memory_info().rss // (1024 * 1024)
                process.terminate()
                process.wait(timeout=5)
                print(f"  ✓ Chromium launched successfully (used {memory_used}MB)")
                return True, memory_used
            else:
                # Crashed
                stderr = process.stderr.read().decode() if process.stderr else ""
                print(f"  ❌ Chromium crashed")
                if "Shared memory" in stderr or "shm" in stderr:
                    print("    Issue: Shared memory limit")
                elif "memory" in stderr.lower():
                    print("    Issue: Out of memory")
                return False, 0
        except Exception as e:
            print(f"  ❌ Failed to test Chromium: {e}")
            return False, 0
            
    def test_ffmpeg_streaming(self, low_memory=False):
        """Test FFmpeg streaming capability"""
        print(f"\n🧪 Testing FFmpeg streaming {'(low memory mode)' if low_memory else '(standard)'}...")
        
        # Check FFmpeg
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
            if result.returncode != 0:
                print("  ❌ FFmpeg not installed")
                return False
        except:
            print("  ❌ FFmpeg not found")
            return False
            
        # Test streaming with test pattern
        if low_memory:
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', 'testsrc=size=854x480:rate=24',
                '-f', 'lavfi',
                '-i', 'anullsrc',
                '-t', '5',  # Run for 5 seconds
                '-c:v', 'libx264',
                '-preset', 'ultrafast',  # Fastest preset for low CPU
                '-b:v', '500k',  # Lower bitrate
                '-maxrate', '500k',
                '-bufsize', '250k',  # Smaller buffer
                '-pix_fmt', 'yuv420p',
                '-g', '48',
                '-c:a', 'aac',
                '-b:a', '64k',  # Lower audio bitrate
                '-f', 'null',
                '-'
            ]
        else:
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', 'testsrc=size=1280x720:rate=30',
                '-f', 'lavfi',
                '-i', 'anullsrc',
                '-t', '5',
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-b:v', '2500k',
                '-maxrate', '2500k',
                '-bufsize', '5000k',
                '-pix_fmt', 'yuv420p',
                '-g', '60',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-f', 'null',
                '-'
            ]
            
        try:
            process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate(timeout=10)
            
            if process.returncode == 0:
                print("  ✓ FFmpeg streaming test successful")
                return True
            else:
                print("  ❌ FFmpeg streaming test failed")
                return False
        except subprocess.TimeoutExpired:
            process.kill()
            print("  ⚠️  FFmpeg test timed out (might be too slow)")
            return False
        except Exception as e:
            print(f"  ❌ FFmpeg test error: {e}")
            return False
            
    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        print("\n📊 Generating recommendations...")
        
        memory_mb = self.results['system']['memory_mb']
        shm_mb = self.results['system']['shm_size_mb']
        
        # Memory tier classification
        if memory_mb < 512:
            tier = "ultra_low"
            self.results['recommendations'].append({
                'tier': 'ultra_low',
                'verdict': 'NOT RECOMMENDED',
                'reason': 'Less than 512MB RAM is insufficient for reliable streaming',
                'solution': 'Upgrade to at least 1GB RAM'
            })
        elif memory_mb < 1024:
            tier = "low"
            self.results['recommendations'].append({
                'tier': 'low',
                'verdict': 'CHALLENGING',
                'reason': '512MB-1GB RAM requires special optimization',
                'solution': 'Use test pattern mode or upgrade to 1GB+ RAM'
            })
        elif memory_mb < 2048:
            tier = "medium"
            self.results['recommendations'].append({
                'tier': 'medium',
                'verdict': 'GOOD',
                'reason': '1-2GB RAM is suitable with optimizations',
                'solution': 'Use memory-optimized mode'
            })
        else:
            tier = "high"
            self.results['recommendations'].append({
                'tier': 'high',
                'verdict': 'EXCELLENT',
                'reason': '2GB+ RAM can handle standard streaming',
                'solution': 'All streaming modes available'
            })
            
        # Shared memory check
        if shm_mb < 64:
            self.results['recommendations'].append({
                'issue': 'shared_memory',
                'solution': 'Increase /dev/shm size or use --disable-dev-shm-usage flag'
            })
            
        # Recommended configuration
        if tier == "ultra_low":
            config = {
                'mode': 'none',
                'message': 'System does not meet minimum requirements'
            }
        elif tier == "low":
            config = {
                'mode': 'test_pattern',
                'resolution': '854x480',
                'framerate': '24',
                'bitrate': '500k',
                'preset': 'ultrafast',
                'chrome_flags': ['--single-process', '--disable-dev-shm-usage', '--max_old_space_size=96']
            }
        elif tier == "medium":
            config = {
                'mode': 'memory_optimized',
                'resolution': '1280x720',
                'framerate': '30',
                'bitrate': '1500k',
                'preset': 'veryfast',
                'chrome_flags': ['--disable-dev-shm-usage', '--max_old_space_size=256']
            }
        else:
            config = {
                'mode': 'standard',
                'resolution': '1920x1080',
                'framerate': '30',
                'bitrate': '2500k',
                'preset': 'veryfast',
                'chrome_flags': []
            }
            
        self.results['recommended_config'] = config
        return self.results['recommendations']
        
    def save_results(self):
        """Save diagnostic results to file"""
        with open('streaming_diagnostic.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Results saved to streaming_diagnostic.json")
        
    def print_summary(self):
        """Print summary and recommendations"""
        print("\n" + "="*60)
        print("📋 DIAGNOSTIC SUMMARY")
        print("="*60)
        
        memory_mb = self.results['system']['memory_mb']
        recommendations = self.results['recommendations']
        config = self.results.get('recommended_config', {})
        
        # System tier
        tier_rec = next((r for r in recommendations if 'tier' in r), None)
        if tier_rec:
            verdict = tier_rec['verdict']
            if verdict == 'NOT RECOMMENDED':
                color = '\033[91m'  # Red
            elif verdict == 'CHALLENGING':
                color = '\033[93m'  # Yellow
            elif verdict == 'GOOD':
                color = '\033[92m'  # Green
            else:
                color = '\033[94m'  # Blue
            print(f"\n{color}System Verdict: {verdict}\033[0m")
            print(f"Reason: {tier_rec['reason']}")
            print(f"Solution: {tier_rec['solution']}")
            
        # Recommended configuration
        if config.get('mode') != 'none':
            print(f"\n🔧 RECOMMENDED CONFIGURATION:")
            print(f"  Mode: {config.get('mode')}")
            print(f"  Resolution: {config.get('resolution', 'N/A')}")
            print(f"  Framerate: {config.get('framerate', 'N/A')} fps")
            print(f"  Bitrate: {config.get('bitrate', 'N/A')}")
            print(f"  Preset: {config.get('preset', 'N/A')}")
            
        # Minimum requirements
        print(f"\n📊 MINIMUM VPS REQUIREMENTS FOR STREAMDROP:")
        print(f"  • RAM: 1GB (2GB recommended)")
        print(f"  • CPU: 1 vCPU (2 vCPU recommended)")
        print(f"  • Bandwidth: 10 Mbps upload")
        print(f"  • Storage: 5GB free space")
        
        if memory_mb < 1024:
            print(f"\n⚠️  YOUR SYSTEM HAS {memory_mb}MB RAM")
            print(f"   Recommended action: Upgrade to 1GB+ RAM droplet")
            print(f"   Alternative: Use test pattern mode (limited functionality)")

def main():
    print("🚀 StreamDrop Diagnostic Tool")
    print("="*60)
    
    diag = StreamingDiagnostic()
    
    # Run diagnostics
    diag.check_system_resources()
    
    # Test components based on available memory
    memory_mb = diag.results['system']['memory_mb']
    
    if memory_mb >= 512:
        # Test standard Chromium
        success, memory_used = diag.test_chromium_launch(memory_optimized=False)
        diag.results['tests']['chromium_standard'] = {'success': success, 'memory_used': memory_used}
        
        if not success or memory_used > memory_mb * 0.5:
            # Try memory optimized
            success, memory_used = diag.test_chromium_launch(memory_optimized=True)
            diag.results['tests']['chromium_optimized'] = {'success': success, 'memory_used': memory_used}
    else:
        # Only test memory optimized for very low memory
        success, memory_used = diag.test_chromium_launch(memory_optimized=True)
        diag.results['tests']['chromium_optimized'] = {'success': success, 'memory_used': memory_used}
        
    # Test FFmpeg
    if memory_mb >= 1024:
        success = diag.test_ffmpeg_streaming(low_memory=False)
        diag.results['tests']['ffmpeg_standard'] = success
    else:
        success = diag.test_ffmpeg_streaming(low_memory=True)
        diag.results['tests']['ffmpeg_low_memory'] = success
        
    # Generate recommendations
    diag.generate_recommendations()
    
    # Save and display results
    diag.save_results()
    diag.print_summary()
    
    print("\n✅ Diagnostic complete!")

if __name__ == "__main__":
    main()
