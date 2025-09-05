#!/usr/bin/env python3
"""
Demo configuration for RTMP-BASE Enhanced Stream Manager
Creates sample streams for testing purposes
"""

import requests
import json

# Sample stream configurations
demo_streams = [
    {
        "name": "Demo Web Clock",
        "type": "html",
        "platform": "youtube", 
        "stream_key": "demo-key-1",
        "source": "https://clock.zone",
        "quality": "medium",
        "title": "24/7 Live Clock Stream",
        "description": "Continuous live clock display"
    },
    {
        "name": "Pygame Bouncing Balls",
        "type": "pygame",
        "platform": "youtube",
        "stream_key": "demo-key-2", 
        "source": "/home/toor/RTMP-BASE/example_game.py",
        "quality": "high",
        "title": "Interactive Pygame Demo",
        "description": "Bouncing balls pygame demonstration"
    },
    {
        "name": "Multi-Platform Test",
        "type": "html",
        "platform": "twitch",
        "stream_key": "demo-twitch-key",
        "source": "/home/toor/RTMP-BASE/demo_content.html",
        "quality": "ultra",
        "title": "Twitch Test Stream",
        "description": "Testing multi-platform capabilities"
    }
]

def create_demo_streams():
    """Create demo stream configurations via API"""
    base_url = "http://localhost:5000"
    
    print("🚀 Creating demo streams...")
    
    for stream_config in demo_streams:
        try:
            response = requests.post(
                f"{base_url}/api/streams",
                headers={"Content-Type": "application/json"},
                json=stream_config
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"✅ Created: {stream_config['name']}")
                else:
                    print(f"❌ Failed: {stream_config['name']} - {result.get('message')}")
            else:
                print(f"❌ HTTP Error {response.status_code} for {stream_config['name']}")
                
        except Exception as e:
            print(f"❌ Error creating {stream_config['name']}: {e}")
    
    print("\n🎯 Demo streams created! Visit http://localhost:5000 to see them.")

def get_streams():
    """Get all current streams"""
    try:
        response = requests.get("http://localhost:5000/api/streams")
        if response.status_code == 200:
            streams = response.json()
            print(f"\n📊 Current Streams ({len(streams)}):")
            for stream in streams:
                print(f"  - {stream['name']} ({stream['platform']}) - Status: {stream['status']}")
        else:
            print("❌ Failed to fetch streams")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        get_streams()
    else:
        create_demo_streams()
