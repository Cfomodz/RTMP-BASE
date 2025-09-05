# RTMP Streaming Platform API Documentation

## New API Endpoints

This document describes the new API endpoints added to support advanced multi-stream management, projects, templates, and platform configurations.

## Project Management APIs

### GET /api/projects
Get all projects
- **Returns**: Array of project objects

### POST /api/projects
Create new project
- **Body**: Project data (name, description, settings)
- **Returns**: `{success: true, project_id: string, message: string}`

### PUT /api/projects/{project_id}
Update project
- **Body**: Updated project data
- **Returns**: `{success: boolean, message: string}`

### DELETE /api/projects/{project_id}
Delete project
- **Returns**: `{success: boolean, message: string}`

### GET /api/projects/{project_id}/streams
Get all streams for a project
- **Returns**: Array of stream objects

## Template Management APIs

### GET /api/templates
Get all stream templates
- **Returns**: Array of template objects

### POST /api/templates
Create new template
- **Body**: Template data (name, description, default_settings)
- **Returns**: `{success: true, template_id: string, message: string}`

### GET /api/templates/{template_id}
Get specific template
- **Returns**: Template object or error

### PUT /api/templates/{template_id}
Update template
- **Body**: Updated template data
- **Returns**: `{success: boolean, message: string}`

### DELETE /api/templates/{template_id}
Delete template
- **Returns**: `{success: boolean, message: string}`

### POST /api/streams/from-template
Create stream from template
- **Body**: `{template_id: string, stream_data: object}`
- **Returns**: `{success: true, stream_id: string, message: string}`

## Platform Configuration APIs

### GET /api/platforms
Get all available platforms
- **Returns**: Array of platform configuration objects

### POST /api/platforms
Create new platform configuration
- **Body**: Platform data (name, display_name, base_url, settings)
- **Returns**: `{success: true, platform_id: string, message: string}`

### GET /api/platforms/{platform_name}
Get specific platform configuration
- **Returns**: Platform configuration object

### PUT /api/platforms/{platform_name}
Update platform configuration
- **Body**: Updated platform data
- **Returns**: `{success: boolean, message: string}`

### DELETE /api/platforms/{platform_name}
Delete platform configuration
- **Returns**: `{success: boolean, message: string}`

## Multi-Stream Management APIs

### POST /api/streams/{stream_id}/multi-targets
Add multi-stream target to a stream
- **Body**: Target data (platform, stream_key, enabled)
- **Returns**: `{success: boolean, message: string}`

### GET /api/streams/{stream_id}/multi-targets
Get multi-stream targets for a stream
- **Returns**: Array of target objects

### DELETE /api/streams/{stream_id}/multi-targets/{target_index}
Remove multi-stream target from a stream
- **Returns**: `{success: boolean, message: string}`

## Audio Configuration APIs

### PUT /api/streams/{stream_id}/audio
Update stream audio configuration
- **Body**: Audio config (enabled, device, channels, sample_rate)
- **Returns**: `{success: boolean, message: string}`

## Data Structures

### Project Object
```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "settings": {
    "default_quality": "string",
    "auto_record": "boolean"
  },
  "created_at": "timestamp"
}
```

### Template Object
```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "default_settings": {
    "content_type": "string",
    "quality": "string",
    "platform": "string",
    "audio_input": {
      "enabled": "boolean",
      "device": "string"
    }
  },
  "created_at": "timestamp"
}
```

### Platform Configuration Object
```json
{
  "name": "string",
  "display_name": "string",
  "base_url": "string",
  "requires_stream_key": "boolean",
  "settings": {
    "video_codec": "string",
    "audio_codec": "string"
  }
}
```

### Multi-Stream Target Object
```json
{
  "platform": "string",
  "stream_key": "string",
  "enabled": "boolean"
}
```

### Audio Configuration Object
```json
{
  "enabled": "boolean",
  "device": "string",
  "channels": "number",
  "sample_rate": "number"
}
```

## Usage Examples

### Create a Project
```bash
curl -X POST http://localhost:5000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Gaming Project",
    "description": "Project for game streaming",
    "settings": {
      "default_quality": "high",
      "auto_record": true
    }
  }'
```

### Create a Stream Template
```bash
curl -X POST http://localhost:5000/api/templates \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Gaming Template",
    "description": "Template for gaming streams",
    "default_settings": {
      "content_type": "pygame",
      "quality": "high",
      "platform": "youtube"
    }
  }'
```

### Add Multi-Stream Target
```bash
curl -X POST http://localhost:5000/api/streams/stream123/multi-targets \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "twitch",
    "stream_key": "your-twitch-key",
    "enabled": true
  }'
```

### Configure Audio
```bash
curl -X PUT http://localhost:5000/api/streams/stream123/audio \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "device": "pulse",
    "channels": 2,
    "sample_rate": 44100
  }'
```

## Error Handling

All endpoints return a consistent error format:
```json
{
  "success": false,
  "message": "Error description"
}
```

Common HTTP status codes:
- 200: Success
- 400: Bad Request (invalid data)
- 404: Not Found (resource doesn't exist)
- 500: Internal Server Error

## Testing

Use the provided test script to verify all endpoints:
```bash
./test_new_apis.py
```

This will test all the new API endpoints and provide detailed output for debugging.
