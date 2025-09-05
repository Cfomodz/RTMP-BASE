#!/usr/bin/env python3
"""
Test script for new API endpoints in the RTMP streaming platform
Tests projects, templates, platforms, and multi-stream management APIs
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:5000"

def test_request(method, url, data=None, description=""):
    """Helper function to make API requests and print results"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Method: {method}")
    print(f"URL: {url}")
    if data:
        print(f"Data: {json.dumps(data, indent=2)}")
    print(f"{'='*60}")
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        elif method == "PUT":
            response = requests.put(url, json=data)
        elif method == "DELETE":
            response = requests.delete(url)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    print("🚀 Testing RTMP Platform API Endpoints")
    
    # Test Project Management APIs
    print("\n🏗️ Testing Project Management APIs")
    
    # Create project
    project_data = {
        "name": "Test Gaming Project",
        "description": "Test project for game streaming",
        "settings": {
            "default_quality": "high",
            "auto_record": True
        }
    }
    
    create_response = test_request(
        "POST", 
        f"{BASE_URL}/api/projects",
        project_data,
        "Create new project"
    )
    
    if create_response and create_response.get("success"):
        project_id = create_response.get("project_id")
        
        # Get all projects
        test_request("GET", f"{BASE_URL}/api/projects", description="Get all projects")
        
        # Update project
        update_data = {
            "name": "Updated Gaming Project",
            "description": "Updated description"
        }
        test_request(
            "PUT",
            f"{BASE_URL}/api/projects/{project_id}",
            update_data,
            f"Update project {project_id}"
        )
    
    # Test Template Management APIs
    print("\n📋 Testing Template Management APIs")
    
    # Create template
    template_data = {
        "name": "Gaming Stream Template",
        "description": "Template for gaming streams",
        "default_settings": {
            "content_path": "/path/to/game",
            "content_type": "pygame",
            "quality": "high",
            "platform": "youtube",
            "audio_input": {
                "enabled": True,
                "device": "default"
            }
        }
    }
    
    template_response = test_request(
        "POST",
        f"{BASE_URL}/api/templates",
        template_data,
        "Create stream template"
    )
    
    if template_response and template_response.get("success"):
        template_id = template_response.get("template_id")
        
        # Get all templates
        test_request("GET", f"{BASE_URL}/api/templates", description="Get all templates")
        
        # Get specific template
        test_request("GET", f"{BASE_URL}/api/templates/{template_id}", description=f"Get template {template_id}")
        
        # Update template
        update_template = {
            "name": "Updated Gaming Template",
            "description": "Updated template description"
        }
        test_request(
            "PUT",
            f"{BASE_URL}/api/templates/{template_id}",
            update_template,
            f"Update template {template_id}"
        )
    
    # Test Platform Management APIs
    print("\n🌐 Testing Platform Management APIs")
    
    # Get all platforms
    test_request("GET", f"{BASE_URL}/api/platforms", description="Get all platform configurations")
    
    # Create custom platform
    platform_data = {
        "name": "custom_rtmp",
        "display_name": "Custom RTMP Server",
        "base_url": "rtmp://custom-server.com/live/",
        "requires_stream_key": True,
        "settings": {
            "video_codec": "h264",
            "audio_codec": "aac"
        }
    }
    
    test_request(
        "POST",
        f"{BASE_URL}/api/platforms",
        platform_data,
        "Create custom platform configuration"
    )
    
    # Get specific platform
    test_request("GET", f"{BASE_URL}/api/platforms/youtube", description="Get YouTube platform config")
    
    # Test Stream Creation and Multi-streaming APIs
    print("\n🎥 Testing Multi-Stream Management APIs")
    
    # First, create a test stream
    stream_data = {
        "title": "Multi-Platform Test Stream",
        "description": "Testing multi-platform streaming",
        "content_path": "/home/toor/RTMP-BASE/demo_content.html",
        "content_type": "html",
        "platform": "youtube",
        "stream_key": "test-key-123",
        "quality": "high"
    }
    
    stream_response = test_request(
        "POST",
        f"{BASE_URL}/api/streams",
        stream_data,
        "Create test stream for multi-streaming"
    )
    
    if stream_response and stream_response.get("success"):
        stream_id = stream_response.get("stream_id")
        
        # Add multi-stream targets
        targets = [
            {
                "platform": "twitch",
                "stream_key": "twitch-key-456",
                "enabled": True
            },
            {
                "platform": "facebook",
                "stream_key": "facebook-key-789",
                "enabled": True
            }
        ]
        
        for i, target in enumerate(targets):
            test_request(
                "POST",
                f"{BASE_URL}/api/streams/{stream_id}/multi-targets",
                target,
                f"Add multi-stream target {i+1}"
            )
        
        # Get multi-stream targets
        test_request(
            "GET",
            f"{BASE_URL}/api/streams/{stream_id}/multi-targets",
            description="Get all multi-stream targets"
        )
        
        # Update audio configuration
        audio_config = {
            "enabled": True,
            "device": "pulse",
            "channels": 2,
            "sample_rate": 44100
        }
        
        test_request(
            "PUT",
            f"{BASE_URL}/api/streams/{stream_id}/audio",
            audio_config,
            "Update stream audio configuration"
        )
        
        # Remove a multi-stream target
        test_request(
            "DELETE",
            f"{BASE_URL}/api/streams/{stream_id}/multi-targets/0",
            description="Remove first multi-stream target"
        )
    
    # Test creating stream from template
    if template_response and template_response.get("success") and project_id:
        template_stream_data = {
            "template_id": template_response.get("template_id"),
            "stream_data": {
                "title": "Stream from Template",
                "project_id": project_id,
                "stream_key": "template-stream-key"
            }
        }
        
        test_request(
            "POST",
            f"{BASE_URL}/api/streams/from-template",
            template_stream_data,
            "Create stream from template"
        )
    
    # Test project streams
    if project_id:
        test_request(
            "GET",
            f"{BASE_URL}/api/projects/{project_id}/streams",
            description=f"Get all streams for project {project_id}"
        )
    
    print("\n✅ API Testing Complete!")
    print("Check the output above for any errors or issues.")

if __name__ == "__main__":
    # Check if the server is running
    try:
        response = requests.get(f"{BASE_URL}/api/streams")
        if response.status_code != 200:
            print("❌ Server not responding correctly. Make sure the streaming platform is running.")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to the server. Make sure the streaming platform is running on localhost:5000")
        sys.exit(1)
    
    main()
