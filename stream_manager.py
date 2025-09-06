#!/usr/bin/env python3
"""
Enhanced Stream Manager for StreamDrop
Supports multiple concurrent streams with individual configurations
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
from datetime import datetime, timedelta
from threading import Thread, Lock
from functools import wraps
from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for, flash

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('stream-manager')

# Global lock for thread-safe operations
stream_lock = Lock()

class StreamDatabase:
    """SQLite database manager for stream configurations"""
    
    def __init__(self, db_path="streams.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
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
                thumbnail TEXT DEFAULT '',
                rtmp_url TEXT DEFAULT '',
                custom_settings TEXT DEFAULT '',
                project_id TEXT DEFAULT NULL,
                audio_config TEXT DEFAULT '{}',
                schedule_config TEXT DEFAULT '{}',
                multi_stream_targets TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                uptime_seconds INTEGER DEFAULT 0,
                start_time TIMESTAMP NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stream_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stream_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT,
                data TEXT,
                FOREIGN KEY (stream_id) REFERENCES streams (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stream_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stream_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fps REAL DEFAULT 0,
                bitrate REAL DEFAULT 0,
                frame_drops INTEGER DEFAULT 0,
                cpu_usage REAL DEFAULT 0,
                memory_usage REAL DEFAULT 0,
                bandwidth_mbps REAL DEFAULT 0,
                viewers INTEGER DEFAULT 0,
                duration_seconds INTEGER DEFAULT 0,
                FOREIGN KEY (stream_id) REFERENCES streams (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stream_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stream_id TEXT,
                alert_type TEXT,
                severity TEXT,
                message TEXT,
                acknowledged BOOLEAN DEFAULT FALSE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (stream_id) REFERENCES streams (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stream_recovery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stream_id TEXT,
                failure_type TEXT,
                recovery_strategy TEXT,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 5,
                last_attempt TIMESTAMP,
                success BOOLEAN DEFAULT FALSE,
                recovery_duration REAL DEFAULT 0,
                failure_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (stream_id) REFERENCES streams (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stream_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stream_id TEXT,
                health_score REAL DEFAULT 100,
                connection_quality REAL DEFAULT 100,
                performance_score REAL DEFAULT 100,
                stability_score REAL DEFAULT 100,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (stream_id) REFERENCES streams (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                settings TEXT DEFAULT '{}',
                audio_config TEXT DEFAULT '{}',
                schedule_config TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stream_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                template_config TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS platform_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform_name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                rtmp_url TEXT NOT NULL,
                supports_auth BOOLEAN DEFAULT FALSE,
                max_bitrate INTEGER DEFAULT 6000,
                recommended_settings TEXT DEFAULT '{}',
                active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Initialize platform configurations
        self.initialize_platform_configs()
    
    def create_stream(self, stream_data):
        """Create a new stream configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stream_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO streams (id, name, type, platform, stream_key, source, 
                               quality, title, description, rtmp_url, custom_settings)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            stream_data.get('rtmp_url', ''),
            json.dumps(stream_data.get('custom_settings', {}))
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
        streams = []
        for row in cursor.fetchall():
            stream = dict(row)
            # Parse custom_settings JSON
            if stream.get('custom_settings'):
                try:
                    stream['custom_settings'] = json.loads(stream['custom_settings'])
                except:
                    stream['custom_settings'] = {}
            else:
                stream['custom_settings'] = {}
            streams.append(stream)
        
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
        
        if not row:
            return None
            
        stream = dict(row)
        # Parse custom_settings JSON
        if stream.get('custom_settings'):
            try:
                stream['custom_settings'] = json.loads(stream['custom_settings'])
            except:
                stream['custom_settings'] = {}
        else:
            stream['custom_settings'] = {}
            
        return stream
    
    def update_stream_status(self, stream_id, status, start_time=None):
        """Update stream status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status == 'live' and start_time:
            cursor.execute('''
                UPDATE streams 
                SET status = ?, start_time = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, start_time, stream_id))
        elif status == 'stopped':
            # Calculate uptime when stopping
            cursor.execute('SELECT start_time, uptime_seconds FROM streams WHERE id = ?', (stream_id,))
            result = cursor.fetchone()
            if result and result[0]:
                start_time_db = datetime.fromisoformat(result[0])
                session_uptime = (datetime.now() - start_time_db).total_seconds()
                total_uptime = result[1] + session_uptime
                
                cursor.execute('''
                    UPDATE streams 
                    SET status = ?, start_time = NULL, uptime_seconds = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, int(total_uptime), stream_id))
            else:
                cursor.execute('''
                    UPDATE streams 
                    SET status = ?, start_time = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, stream_id))
        else:
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
        
        # Build dynamic update query based on provided data
        update_fields = []
        values = []
        
        allowed_fields = ['name', 'title', 'description', 'quality', 'source', 'stream_key', 'rtmp_url']
        
        # Handle custom_settings as JSON
        if 'custom_settings' in stream_data:
            update_fields.append('custom_settings = ?')
            values.append(json.dumps(stream_data['custom_settings']))
        for field in allowed_fields:
            if field in stream_data:
                update_fields.append(f'{field} = ?')
                values.append(stream_data[field])
        
        if not update_fields:
            conn.close()
            return False
        
        # Add updated_at timestamp
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
        cursor.execute('DELETE FROM stream_analytics WHERE stream_id = ?', (stream_id,))
        
        conn.commit()
        conn.close()
    
    def log_event(self, stream_id, event_type, data=None):
        """Log stream analytics event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO stream_analytics (stream_id, event_type, data)
            VALUES (?, ?, ?)
        ''', (stream_id, event_type, json.dumps(data) if data else None))
        
        conn.commit()
        conn.close()
    
    def log_metrics(self, stream_id, metrics):
        """Log stream performance metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO stream_metrics 
            (stream_id, fps, bitrate, frame_drops, cpu_usage, memory_usage, 
             bandwidth_mbps, viewers, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            stream_id,
            metrics.get('fps', 0),
            metrics.get('bitrate', 0),
            metrics.get('frame_drops', 0),
            metrics.get('cpu_usage', 0),
            metrics.get('memory_usage', 0),
            metrics.get('bandwidth_mbps', 0),
            metrics.get('viewers', 0),
            metrics.get('duration_seconds', 0)
        ))
        
        conn.commit()
        conn.close()
    
    def create_alert(self, stream_id, alert_type, severity, message):
        """Create a stream alert"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO stream_alerts (stream_id, alert_type, severity, message)
            VALUES (?, ?, ?, ?)
        ''', (stream_id, alert_type, severity, message))
        
        conn.commit()
        conn.close()
    
    def get_recent_metrics(self, stream_id, minutes=30):
        """Get recent metrics for a stream"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM stream_metrics 
            WHERE stream_id = ? AND timestamp > datetime('now', '-{} minutes')
            ORDER BY timestamp DESC
        '''.format(minutes), (stream_id,))
        
        metrics = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return metrics
    
    def get_stream_alerts(self, stream_id=None, acknowledged=False):
        """Get stream alerts"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if stream_id:
            cursor.execute('''
                SELECT * FROM stream_alerts 
                WHERE stream_id = ? AND acknowledged = ?
                ORDER BY timestamp DESC
            ''', (stream_id, acknowledged))
        else:
            cursor.execute('''
                SELECT * FROM stream_alerts 
                WHERE acknowledged = ?
                ORDER BY timestamp DESC
            ''', (acknowledged,))
        
        alerts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return alerts
    
    def create_recovery_attempt(self, stream_id, failure_type, recovery_strategy, failure_reason=""):
        """Create a new recovery attempt record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO stream_recovery (stream_id, failure_type, recovery_strategy, failure_reason)
            VALUES (?, ?, ?, ?)
        ''', (stream_id, failure_type, recovery_strategy, failure_reason))
        
        recovery_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return recovery_id
    
    def update_recovery_attempt(self, recovery_id, retry_count, success, recovery_duration=0):
        """Update a recovery attempt with results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE stream_recovery 
            SET retry_count = ?, success = ?, recovery_duration = ?, last_attempt = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (retry_count, success, recovery_duration, recovery_id))
        
        conn.commit()
        conn.close()
    
    def get_active_recovery(self, stream_id):
        """Get active recovery attempt for a stream"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM stream_recovery 
            WHERE stream_id = ? AND success = FALSE 
            ORDER BY created_at DESC LIMIT 1
        ''', (stream_id,))
        
        recovery = cursor.fetchone()
        conn.close()
        return dict(recovery) if recovery else None
    
    def log_health_score(self, stream_id, health_score, connection_quality=100, performance_score=100, stability_score=100):
        """Log stream health metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO stream_health (stream_id, health_score, connection_quality, performance_score, stability_score)
            VALUES (?, ?, ?, ?, ?)
        ''', (stream_id, health_score, connection_quality, performance_score, stability_score))
        
        conn.commit()
        conn.close()
    
    def get_latest_health(self, stream_id):
        """Get latest health score for a stream"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM stream_health 
            WHERE stream_id = ? 
            ORDER BY timestamp DESC LIMIT 1
        ''', (stream_id,))
        
        health = cursor.fetchone()
        conn.close()
        return dict(health) if health else None
    
    def get_recovery_stats(self, stream_id=None):
        """Get recovery statistics"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if stream_id:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_recoveries,
                    AVG(recovery_duration) as avg_recovery_time,
                    AVG(retry_count) as avg_retry_count
                FROM stream_recovery 
                WHERE stream_id = ?
            ''', (stream_id,))
        else:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_recoveries,
                    AVG(recovery_duration) as avg_recovery_time,
                    AVG(retry_count) as avg_retry_count
                FROM stream_recovery
            ''')
        
        stats = cursor.fetchone()
        conn.close()
        return dict(stats) if stats else {}
    
    def create_project(self, project_data):
        """Create a new project"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        project_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO projects (id, name, description, settings, audio_config, schedule_config)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            project_id,
            project_data['name'],
            project_data.get('description', ''),
            json.dumps(project_data.get('settings', {})),
            json.dumps(project_data.get('audio_config', {})),
            json.dumps(project_data.get('schedule_config', {}))
        ))
        
        conn.commit()
        conn.close()
        return project_id
    
    def get_all_projects(self):
        """Get all projects"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM projects ORDER BY name')
        projects = []
        for row in cursor.fetchall():
            project = dict(row)
            # Parse JSON fields
            for field in ['settings', 'audio_config', 'schedule_config']:
                if project.get(field):
                    try:
                        project[field] = json.loads(project[field])
                    except:
                        project[field] = {}
                else:
                    project[field] = {}
            projects.append(project)
        
        conn.close()
        return projects
    
    def get_project(self, project_id):
        """Get a specific project"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if not row:
            return None
            
        project = dict(row)
        # Parse JSON fields
        for field in ['settings', 'audio_config', 'schedule_config']:
            if project.get(field):
                try:
                    project[field] = json.loads(project[field])
                except:
                    project[field] = {}
            else:
                project[field] = {}
                
        return project
    
    def update_project(self, project_id, project_data):
        """Update a project"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        update_fields = []
        values = []
        
        allowed_fields = ['name', 'description']
        for field in allowed_fields:
            if field in project_data:
                update_fields.append(f'{field} = ?')
                values.append(project_data[field])
        
        # Handle JSON fields
        for field in ['settings', 'audio_config', 'schedule_config']:
            if field in project_data:
                update_fields.append(f'{field} = ?')
                values.append(json.dumps(project_data[field]))
        
        if not update_fields:
            conn.close()
            return False
        
        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        values.append(project_id)
        
        query = f'UPDATE projects SET {", ".join(update_fields)} WHERE id = ?'
        cursor.execute(query, values)
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def delete_project(self, project_id):
        """Delete a project and update associated streams"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update streams to remove project association
        cursor.execute('UPDATE streams SET project_id = NULL WHERE project_id = ?', (project_id,))
        
        # Delete project
        cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        
        conn.commit()
        conn.close()
    
    def create_template(self, template_data):
        """Create a stream template"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        template_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO stream_templates (id, name, description, template_config, category)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            template_id,
            template_data['name'],
            template_data.get('description', ''),
            json.dumps(template_data['template_config']),
            template_data.get('category', 'general')
        ))
        
        conn.commit()
        conn.close()
        return template_id
    
    def get_all_templates(self):
        """Get all stream templates"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM stream_templates ORDER BY category, name')
        templates = []
        for row in cursor.fetchall():
            template = dict(row)
            # Parse template_config JSON
            if template.get('template_config'):
                try:
                    template['template_config'] = json.loads(template['template_config'])
                except:
                    template['template_config'] = {}
            else:
                template['template_config'] = {}
            templates.append(template)
        
        conn.close()
        return templates
    
    def initialize_platform_configs(self):
        """Initialize default platform configurations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if platforms are already initialized
        cursor.execute('SELECT COUNT(*) FROM platform_configs')
        if cursor.fetchone()[0] > 0:
            conn.close()
            return
        
        # Default platform configurations
        platforms = [
            {
                'platform_name': 'youtube',
                'display_name': 'YouTube Live',
                'rtmp_url': 'rtmp://a.rtmp.youtube.com/live2/',
                'supports_auth': True,
                'max_bitrate': 9000,
                'recommended_settings': json.dumps({
                    'resolution': '1920x1080',
                    'framerate': 60,
                    'keyframe_interval': 2
                })
            },
            {
                'platform_name': 'twitch',
                'display_name': 'Twitch',
                'rtmp_url': 'rtmp://live.twitch.tv/live/',
                'supports_auth': True,
                'max_bitrate': 6000,
                'recommended_settings': json.dumps({
                    'resolution': '1920x1080',
                    'framerate': 60,
                    'keyframe_interval': 2
                })
            },
            {
                'platform_name': 'facebook',
                'display_name': 'Facebook Live',
                'rtmp_url': 'rtmps://live-api-s.facebook.com:443/rtmp/',
                'supports_auth': True,
                'max_bitrate': 4000,
                'recommended_settings': json.dumps({
                    'resolution': '1280x720',
                    'framerate': 30,
                    'keyframe_interval': 2
                })
            },
            {
                'platform_name': 'linkedin',
                'display_name': 'LinkedIn Live',
                'rtmp_url': 'rtmps://1-46c2-477-4480.live-video.net/live/',
                'supports_auth': True,
                'max_bitrate': 5000,
                'recommended_settings': json.dumps({
                    'resolution': '1920x1080',
                    'framerate': 30,
                    'keyframe_interval': 2
                })
            },
            {
                'platform_name': 'instagram',
                'display_name': 'Instagram Live',
                'rtmp_url': 'rtmps://live-upload.instagram.com/rtmp/',
                'supports_auth': True,
                'max_bitrate': 3500,
                'recommended_settings': json.dumps({
                    'resolution': '1080x1920',
                    'framerate': 30,
                    'keyframe_interval': 2
                })
            },
            {
                'platform_name': 'tiktok',
                'display_name': 'TikTok Live',
                'rtmp_url': 'rtmp://push.tiktokcdn.com/live/',
                'supports_auth': True,
                'max_bitrate': 4000,
                'recommended_settings': json.dumps({
                    'resolution': '1080x1920',
                    'framerate': 30,
                    'keyframe_interval': 2
                })
            }
        ]
        
        for platform in platforms:
            cursor.execute('''
                INSERT INTO platform_configs 
                (platform_name, display_name, rtmp_url, supports_auth, max_bitrate, recommended_settings)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                platform['platform_name'],
                platform['display_name'],
                platform['rtmp_url'],
                platform['supports_auth'],
                platform['max_bitrate'],
                platform['recommended_settings']
            ))
        
        conn.commit()
        conn.close()
    
    def get_platform_configs(self):
        """Get all platform configurations"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM platform_configs WHERE active = 1 ORDER BY display_name')
        platforms = []
        for row in cursor.fetchall():
            platform = dict(row)
            # Parse recommended_settings JSON
            if platform.get('recommended_settings'):
                try:
                    platform['recommended_settings'] = json.loads(platform['recommended_settings'])
                except:
                    platform['recommended_settings'] = {}
            else:
                platform['recommended_settings'] = {}
            platforms.append(platform)
        
        conn.close()
        return platforms

class StreamInstance:
    """Individual stream instance with process management"""
    
    def __init__(self, stream_config, db):
        self.config = stream_config
        self.db = db
        self.processes = {}
        self.status = "stopped"
        self.metrics = {}
        self.last_metrics_time = time.time()
        self.frame_count = 0
        self.start_time = None
        self.health_score = 100.0
        self.failure_count = 0
        self.last_recovery_attempt = 0
        self.recovery_in_progress = False
        self.active_recovery_id = None
        
        # Quality settings (horizontal presets)
        self.quality_presets = {
            'low': {'resolution': '854x480', 'bitrate': '1000k', 'framerate': '24'},
            'medium': {'resolution': '1280x720', 'bitrate': '2500k', 'framerate': '30'},
            'high': {'resolution': '1920x1080', 'bitrate': '4000k', 'framerate': '30'},
            'ultra': {'resolution': '1920x1080', 'bitrate': '6000k', 'framerate': '60'}
        }
        
        # Vertical quality presets for mobile platforms
        self.vertical_quality_presets = {
            'low': {'resolution': '480x854', 'bitrate': '1000k', 'framerate': '24'},
            'medium': {'resolution': '720x1280', 'bitrate': '2500k', 'framerate': '30'},
            'high': {'resolution': '1080x1920', 'bitrate': '4000k', 'framerate': '30'},
            'ultra': {'resolution': '1080x1920', 'bitrate': '6000k', 'framerate': '60'}
        }
        
        # Platforms that prefer vertical orientation
        self.vertical_platforms = {'tiktok', 'instagram'}
        
        # Load platform configurations from database
        self.platform_configs = {}
        self._load_platform_configs()
        
        # Audio configuration
        self.audio_config = self.config.get('audio_config', {})
        self.multi_stream_targets = self.config.get('multi_stream_targets', [])
    
    def _load_platform_configs(self):
        """Load platform configurations from database"""
        try:
            platforms = self.db.get_platform_configs()
            for platform in platforms:
                self.platform_configs[platform['platform_name']] = platform
        except Exception as e:
            logger.error(f"Failed to load platform configs: {e}")
            # Fallback to basic configs
            self.platform_configs = {
                'youtube': {'rtmp_url': 'rtmp://a.rtmp.youtube.com/live2/'},
                'twitch': {'rtmp_url': 'rtmp://live.twitch.tv/live/'},
                'facebook': {'rtmp_url': 'rtmps://live-api-s.facebook.com:443/rtmp/'},
                'tiktok': {'rtmp_url': 'rtmp://push.tiktokcdn.com/live/'},
                'instagram': {'rtmp_url': 'rtmps://live-upload.instagram.com/rtmp/'}
            }
    
    def start_streaming(self):
        """Start the streaming process"""
        if self.status == "live":
            return False, "Stream is already running"
        
        try:
            # Handle custom quality settings
            if self.config.get('quality') == 'custom' and 'custom_settings' in self.config:
                custom = self.config['custom_settings']
                quality = {
                    'resolution': custom.get('resolution', '1280x720'),
                    'bitrate': custom.get('bitrate', '2500') + 'k',
                    'framerate': custom.get('framerate', '30')
                }
            else:
                # Choose quality preset based on orientation preference
                orientation = self.config.get('orientation', 'auto')
                platform = self.config.get('platform', '')
                
                # Determine effective orientation
                if orientation == 'auto':
                    use_vertical = platform in self.vertical_platforms
                elif orientation == 'vertical':
                    use_vertical = True
                else:  # horizontal
                    use_vertical = False
                
                if use_vertical:
                    quality = self.vertical_quality_presets.get(self.config.get('quality', 'medium'))
                else:
                    quality = self.quality_presets.get(self.config.get('quality', 'medium'))
            
            # Use smart streaming approach - detects headless vs X11 automatically
            self._start_smart_streaming(quality)
            
            self.status = "live"
            self.start_time = time.time()
            start_time = datetime.now().isoformat()
            self.db.update_stream_status(self.config['id'], 'live', start_time)
            self.db.log_event(self.config['id'], 'stream_started')
            
            logger.info(f"Stream {self.config['name']} started successfully")
            return True, "Stream started successfully"
            
        except Exception as e:
            logger.error(f"Error starting stream {self.config['name']}: {e}")
            self.cleanup()
            return False, f"Error starting stream: {e}"
    
    def _start_smart_streaming(self, quality):
        """Start streaming using smart detection (headless vs X11)"""
        try:
            # Detect if we're on a headless system
            is_headless = self._detect_headless_system()
            
            if is_headless:
                # Use headless streaming approach
                self._start_headless_streaming(quality)
            else:
                # Use traditional X11 approach with Xvfb
                self._start_x11_streaming(quality)
                
        except Exception as e:
            logger.error(f"Error in smart streaming setup: {e}")
            # Fallback to headless if X11 fails
            logger.info("Falling back to headless streaming...")
            self._start_headless_streaming(quality)
    
    def _detect_headless_system(self):
        """Detect if we're running on a headless system"""
        try:
            # Check if DISPLAY is set and accessible
            if os.environ.get('DISPLAY'):
                # Try to connect to X server
                result = subprocess.run(['xset', 'q'], capture_output=True, timeout=5)
                if result.returncode == 0:
                    return False  # X11 available
            
            # Check if we're in a known headless environment
            if os.path.exists('/usr/bin/chromium-browser') and not os.path.exists('/usr/bin/Xorg'):
                return True
                
            # Default to headless if uncertain
            return True
            
        except Exception:
            # If detection fails, assume headless
            return True
    
    def _start_headless_streaming(self, quality):
        """Start true headless streaming (no X11 required)"""
        logger.info("Starting headless streaming...")
        
        if self.config['type'] == 'html':
            # Use Chrome DevTools Protocol for HTML content
            self._start_headless_html_streaming(quality)
        elif self.config['type'] == 'pygame':
            # Use memory surface for Pygame content  
            self._start_headless_pygame_streaming(quality)
        else:
            raise Exception(f"Unsupported content type for headless streaming: {self.config['type']}")
    
    def _start_x11_streaming(self, quality):
        """Start traditional X11 streaming with Xvfb"""
        logger.info("Starting X11 streaming with virtual display...")
        
        # Start virtual display
        display_port = f":9{self.config['id'][-1]}"
        self.processes['display'] = subprocess.Popen([
            'Xvfb', display_port, '-screen', '0', f"{quality['resolution']}x24", '-ac'
        ])
        
        time.sleep(2)  # Allow Xvfb to start
        
        env = os.environ.copy()
        env['DISPLAY'] = display_port
        
        # Start content renderer
        if self.config['type'] == 'html':
            self._start_html_renderer(env, quality)
        elif self.config['type'] == 'pygame':
            self._start_pygame_renderer(env)
        
        time.sleep(3)  # Allow content to start
        
        # Start FFmpeg streaming
        self._start_ffmpeg_stream(env, quality)
    
    def _start_headless_html_streaming(self, quality):
        """Start headless HTML streaming using Chrome DevTools Protocol"""
        try:
            # Start Chrome in headless mode with remote debugging
            chrome_port = 9222 + int(self.config['id'][-1])  # Unique port per stream
            
            chrome_cmd = [
                'chromium-browser',
                '--headless',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',  # Optimize for streaming
                '--mute-audio',
                f'--window-size={quality["resolution"].replace("x", ",")}',
                f'--remote-debugging-port={chrome_port}',
                '--enable-logging',
                '--log-level=0',
                self.config['source']
            ]
            
            logger.info(f"Starting headless Chrome: {' '.join(chrome_cmd[:8])}...")
            self.processes['chrome'] = subprocess.Popen(chrome_cmd)
            
            time.sleep(3)  # Allow Chrome to start
            
            # Start FFmpeg to capture from Chrome via CDP and stream
            self._start_headless_ffmpeg_stream(quality, chrome_port)
            
        except Exception as e:
            logger.error(f"Failed to start headless HTML streaming: {e}")
            raise
    
    def _start_headless_pygame_streaming(self, quality):
        """Start headless Pygame streaming using memory surfaces"""
        try:
            # Set SDL to use dummy video driver (no display needed)
            env = os.environ.copy()
            env['SDL_VIDEODRIVER'] = 'dummy'
            env['SDL_AUDIODRIVER'] = 'dummy'
            
            # Start the pygame application
            pygame_cmd = ['python3', self.config['source']]
            
            logger.info(f"Starting headless Pygame: {' '.join(pygame_cmd)}")
            self.processes['pygame'] = subprocess.Popen(pygame_cmd, env=env)
            
            time.sleep(2)  # Allow pygame to start
            
            # Start FFmpeg to capture pygame output and stream
            self._start_headless_pygame_ffmpeg(quality)
            
        except Exception as e:
            logger.error(f"Failed to start headless Pygame streaming: {e}")
            raise
    
    def _start_headless_ffmpeg_stream(self, quality, chrome_port):
        """Start FFmpeg for headless HTML streaming"""
        # For headless HTML, we'll use a simpler approach - generate test pattern for now
        # TODO: Implement proper Chrome DevTools Protocol screenshot capture
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'lavfi',
            '-i', f'testsrc=size={quality["resolution"]}:rate={quality["framerate"]}',
            '-pix_fmt', 'yuv420p',
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-b:v', quality['bitrate'],
            '-maxrate', quality['bitrate'],
            '-bufsize', str(int(quality['bitrate'].rstrip('k')) * 2) + 'k',
            '-g', '60',
            '-f', 'flv',
            self._build_rtmp_url()
        ]
        
        logger.info(f"Starting headless FFmpeg stream...")
        env = os.environ.copy()
        self.processes['ffmpeg'] = subprocess.Popen(ffmpeg_cmd, env=env)
    
    def _start_headless_pygame_ffmpeg(self, quality):
        """Start FFmpeg for headless Pygame streaming"""
        # For headless pygame, generate test pattern for now  
        # TODO: Implement proper pygame surface capture
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'lavfi',
            '-i', f'testsrc=size={quality["resolution"]}:rate={quality["framerate"]}',
            '-pix_fmt', 'yuv420p',
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-b:v', quality['bitrate'],
            '-maxrate', quality['bitrate'],
            '-bufsize', str(int(quality['bitrate'].rstrip('k')) * 2) + 'k',
            '-g', '60',
            '-f', 'flv',
            self._build_rtmp_url()
        ]
        
        logger.info(f"Starting headless Pygame FFmpeg stream...")
        env = os.environ.copy()
        self.processes['ffmpeg'] = subprocess.Popen(ffmpeg_cmd, env=env)
    
    def _build_rtmp_url(self):
        """Build RTMP URL for the configured platform"""
        platform = self.config['platform']
        stream_key = self.config['stream_key']
        
        if platform == 'custom' and self.config.get('rtmp_url'):
            return f"{self.config['rtmp_url']}/{stream_key}"
        
        platform_config = self.platform_configs.get(platform)
        if not platform_config:
            raise Exception(f"Unsupported platform: {platform}")
        
        return f"{platform_config['rtmp_url']}{stream_key}"
    
    def _start_html_renderer(self, env, quality):
        """Start Chrome for HTML content"""
        chrome_cmd = [
            'google-chrome',
            '--headless',
            '--disable-gpu',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            f'--window-size={quality["resolution"].replace("x", ",")}',
            '--remote-debugging-port=9222',
            '--remote-debugging-address=0.0.0.0',
            self.config['source']
        ]
        
        self.processes['renderer'] = subprocess.Popen(
            chrome_cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    
    def _start_pygame_renderer(self, env):
        """Start pygame script"""
        if not os.path.exists(self.config['source']):
            raise Exception(f"Pygame script not found: {self.config['source']}")
        
        self.processes['renderer'] = subprocess.Popen([
            'python3', self.config['source']
        ], env=env)
    
    def _start_ffmpeg_stream(self, env, quality):
        """Start FFmpeg streaming process with audio and multi-streaming support"""
        display_port = env['DISPLAY']
        
        # Build FFmpeg command
        ffmpeg_cmd = ['ffmpeg']
        
        # Video input - X11 screen capture
        ffmpeg_cmd.extend([
            '-f', 'x11grab',
            '-video_size', quality['resolution'],
            '-framerate', quality['framerate'],
            '-i', display_port
        ])
        
        # Audio input configuration
        audio_enabled = self.audio_config.get('enabled', False)
        if audio_enabled:
            audio_device = self.audio_config.get('device', 'pulse')
            if audio_device == 'pulse':
                ffmpeg_cmd.extend(['-f', 'pulse', '-i', 'default'])
            elif audio_device == 'alsa':
                ffmpeg_cmd.extend(['-f', 'alsa', '-i', 'hw:0'])
            else:
                ffmpeg_cmd.extend(['-f', 'pulse', '-i', audio_device])
        else:
            # No audio - add silent audio track
            ffmpeg_cmd.extend(['-f', 'lavfi', '-i', 'anullsrc'])
        
        # Video encoding settings
        ffmpeg_cmd.extend([
            '-c:v', 'libx264',
            '-preset', self.audio_config.get('video_preset', 'veryfast'),
            '-b:v', quality['bitrate'],
            '-maxrate', quality['bitrate'],
            '-bufsize', str(int(quality['bitrate'].replace('k', '')) * 2) + 'k',
            '-pix_fmt', 'yuv420p',
            '-g', str(int(quality['framerate']) * 2)  # GOP size = 2 * framerate
        ])
        
        # Audio encoding settings
        if audio_enabled:
            ffmpeg_cmd.extend([
                '-c:a', 'aac',
                '-b:a', self.audio_config.get('audio_bitrate', '128k'),
                '-ar', str(self.audio_config.get('sample_rate', 44100))
            ])
        else:
            ffmpeg_cmd.extend(['-c:a', 'aac', '-b:a', '128k'])
        
        # Multi-streaming support
        targets = self._get_stream_targets()
        
        if len(targets) == 1:
            # Single stream
            ffmpeg_cmd.extend(['-f', 'flv', targets[0]])
        else:
            # Multi-streaming using tee muxer
            ffmpeg_cmd.extend(['-f', 'tee'])
            tee_outputs = '|'.join([f'[f=flv]{target}' for target in targets])
            ffmpeg_cmd.append(tee_outputs)
        
        logger.info(f"Starting FFmpeg with command: {' '.join(ffmpeg_cmd[:10])}... (truncated)")
        
        self.processes['ffmpeg'] = subprocess.Popen(
            ffmpeg_cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    
    def _get_stream_targets(self):
        """Get all streaming targets (primary + multi-stream targets)"""
        targets = []
        
        # Primary target
        primary_target = self._build_rtmp_url(self.config['platform'], self.config['stream_key'], self.config.get('rtmp_url'))
        targets.append(primary_target)
        
        # Additional multi-stream targets
        for target in self.multi_stream_targets:
            if target.get('enabled', True):
                target_url = self._build_rtmp_url(target['platform'], target['stream_key'], target.get('rtmp_url'))
                targets.append(target_url)
        
        return targets
    
    def _build_rtmp_url(self, platform, stream_key, custom_url=None):
        """Build RTMP URL for a platform"""
        if platform == 'custom' and custom_url:
            return f"{custom_url}/{stream_key}"
        
        platform_config = self.platform_configs.get(platform)
        if not platform_config:
            raise Exception(f"Unsupported platform: {platform}")
        
        return f"{platform_config['rtmp_url']}{stream_key}"
    
    def stop_streaming(self):
        """Stop the streaming process"""
        self.cleanup()
        self.status = "stopped"
        self.db.update_stream_status(self.config['id'], 'stopped')
        self.db.log_event(self.config['id'], 'stream_stopped')
        
        logger.info(f"Stream {self.config['name']} stopped")
        return True, "Stream stopped successfully"
    
    def cleanup(self):
        """Clean up all processes"""
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
    
    def get_uptime(self):
        """Get current stream uptime"""
        if self.status != "live":
            return "0m"
        
        stream_data = self.db.get_stream(self.config['id'])
        if stream_data and stream_data['start_time']:
            start_time = datetime.fromisoformat(stream_data['start_time'])
            uptime_seconds = (datetime.now() - start_time).total_seconds()
            
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            if hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        
        return "0m"
    
    def collect_metrics(self):
        """Collect current stream performance metrics"""
        if self.status != "live":
            return {}
        
        metrics = {
            'fps': self._get_fps(),
            'bitrate': self._get_bitrate(),
            'frame_drops': self._get_frame_drops(),
            'cpu_usage': self._get_cpu_usage(),
            'memory_usage': self._get_memory_usage(),
            'bandwidth_mbps': self._get_bandwidth(),
            'viewers': 0,  # TODO: Implement viewer tracking
            'duration_seconds': int(time.time() - (self.start_time or time.time()))
        }
        
        # Store metrics for trend analysis
        self.metrics = metrics
        
        return metrics
    
    def _get_fps(self):
        """Calculate current FPS from FFmpeg stats"""
        try:
            if 'ffmpeg' not in self.processes or not self.processes['ffmpeg']:
                return 0
            
            # Try to read FFmpeg stderr for stats
            # This is a simplified implementation
            return float(self.quality_presets.get(self.config.get('quality', 'medium'), {}).get('framerate', '30'))
        except:
            return 0
    
    def _get_bitrate(self):
        """Get current bitrate from FFmpeg stats"""
        try:
            quality_preset = self.quality_presets.get(self.config.get('quality', 'medium'), {})
            bitrate_str = quality_preset.get('bitrate', '2500k')
            return float(bitrate_str.replace('k', '')) if 'k' in bitrate_str else float(bitrate_str)
        except:
            return 0
    
    def _get_frame_drops(self):
        """Get frame drop count"""
        # TODO: Parse actual FFmpeg stats
        return 0
    
    def _get_cpu_usage(self):
        """Get CPU usage for stream processes"""
        try:
            import psutil
            total_cpu = 0
            process_count = 0
            
            for proc_name, proc in self.processes.items():
                if proc and proc.poll() is None:
                    try:
                        p = psutil.Process(proc.pid)
                        total_cpu += p.cpu_percent()
                        process_count += 1
                    except:
                        pass
            
            return total_cpu / max(process_count, 1)
        except ImportError:
            return 0
    
    def _get_memory_usage(self):
        """Get memory usage for stream processes in MB"""
        try:
            import psutil
            total_memory = 0
            
            for proc_name, proc in self.processes.items():
                if proc and proc.poll() is None:
                    try:
                        p = psutil.Process(proc.pid)
                        total_memory += p.memory_info().rss / 1024 / 1024  # Convert to MB
                    except:
                        pass
            
            return total_memory
        except ImportError:
            return 0
    
    def _get_bandwidth(self):
        """Estimate bandwidth usage in Mbps"""
        try:
            bitrate_kbps = self._get_bitrate()
            return bitrate_kbps / 1000  # Convert kbps to Mbps
        except:
            return 0
    
    def calculate_health_score(self):
        """Calculate overall stream health score (0-100)"""
        if self.status != "live":
            return 100.0
        
        try:
            metrics = self.collect_metrics()
            
            # Performance score (CPU, Memory)
            cpu_score = max(0, 100 - (metrics.get('cpu_usage', 0) - 50))  # Penalty above 50%
            memory_penalty = max(0, (metrics.get('memory_usage', 0) - 500) / 10)  # Penalty above 500MB
            performance_score = max(0, min(100, cpu_score - memory_penalty))
            
            # Connection score (frame drops, bitrate stability)
            frame_drops = metrics.get('frame_drops', 0)
            connection_score = max(0, 100 - frame_drops * 2)  # 2 points per frame drop
            
            # Stability score (based on failure history)
            stability_score = max(0, 100 - (self.failure_count * 10))
            
            # Overall health (weighted average)
            health_score = (
                performance_score * 0.4 +
                connection_score * 0.4 +
                stability_score * 0.2
            )
            
            self.health_score = health_score
            
            # Log health metrics
            self.db.log_health_score(
                self.config['id'],
                health_score,
                connection_score,
                performance_score,
                stability_score
            )
            
            return health_score
            
        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
            return 50.0  # Default to moderate health on error
    
    def detect_failure_type(self):
        """Detect the type of failure occurring"""
        failure_types = []
        
        # Check process health
        for process_name, process in self.processes.items():
            if process and process.poll() is not None:
                failure_types.append(f"process_failure_{process_name}")
        
        # Check performance metrics
        metrics = self.collect_metrics()
        if metrics.get('cpu_usage', 0) > 90:
            failure_types.append("high_cpu")
        if metrics.get('memory_usage', 0) > 2000:  # > 2GB
            failure_types.append("memory_exhaustion")
        if metrics.get('frame_drops', 0) > 50:
            failure_types.append("connection_issues")
        
        # Check health score
        if self.health_score < 30:
            failure_types.append("critical_health")
        
        return failure_types if failure_types else ["unknown_failure"]
    
    def attempt_recovery(self, failure_types):
        """Attempt to recover from detected failures"""
        if self.recovery_in_progress:
            return False, "Recovery already in progress"
        
        self.recovery_in_progress = True
        recovery_start_time = time.time()
        
        try:
            # Determine recovery strategy based on failure types
            primary_failure = failure_types[0] if failure_types else "unknown_failure"
            strategy = self._select_recovery_strategy(primary_failure)
            
            # Create recovery attempt record
            self.active_recovery_id = self.db.create_recovery_attempt(
                self.config['id'],
                primary_failure,
                strategy,
                f"Failures detected: {', '.join(failure_types)}"
            )
            
            logger.info(f"Starting recovery for {self.config['name']} using strategy: {strategy}")
            
            # Execute recovery strategy
            success = self._execute_recovery_strategy(strategy, failure_types)
            
            recovery_duration = time.time() - recovery_start_time
            
            # Update recovery record
            if self.active_recovery_id:
                self.db.update_recovery_attempt(
                    self.active_recovery_id,
                    1,  # retry count
                    success,
                    recovery_duration
                )
            
            if success:
                logger.info(f"Recovery successful for {self.config['name']} in {recovery_duration:.1f}s")
                self.failure_count = max(0, self.failure_count - 1)  # Reduce failure count on success
                self.db.log_event(self.config['id'], 'recovery_success', {
                    'strategy': strategy,
                    'duration': recovery_duration,
                    'failure_types': failure_types
                })
            else:
                logger.error(f"Recovery failed for {self.config['name']}")
                self.failure_count += 1
                self.db.create_alert(
                    self.config['id'],
                    'recovery_failed',
                    'critical',
                    f'Failed to recover from {primary_failure} using {strategy}'
                )
            
            self.recovery_in_progress = False
            self.active_recovery_id = None
            
            return success, f"Recovery {'successful' if success else 'failed'}"
            
        except Exception as e:
            self.recovery_in_progress = False
            self.active_recovery_id = None
            logger.error(f"Recovery attempt failed with exception: {e}")
            return False, f"Recovery exception: {e}"
    
    def _select_recovery_strategy(self, failure_type):
        """Select appropriate recovery strategy based on failure type"""
        strategy_map = {
            'process_failure_ffmpeg': 'restart_ffmpeg',
            'process_failure_renderer': 'restart_renderer',
            'process_failure_display': 'restart_display',
            'high_cpu': 'reduce_quality',
            'memory_exhaustion': 'restart_all',
            'connection_issues': 'reconnect_stream',
            'critical_health': 'full_restart',
            'unknown_failure': 'full_restart'
        }
        
        return strategy_map.get(failure_type, 'full_restart')
    
    def _execute_recovery_strategy(self, strategy, failure_types):
        """Execute the selected recovery strategy"""
        try:
            if strategy == 'restart_ffmpeg':
                return self._restart_ffmpeg()
            elif strategy == 'restart_renderer':
                return self._restart_renderer()
            elif strategy == 'restart_display':
                return self._restart_display()
            elif strategy == 'reduce_quality':
                return self._reduce_quality()
            elif strategy == 'reconnect_stream':
                return self._reconnect_stream()
            elif strategy in ['restart_all', 'full_restart']:
                return self._full_restart()
            else:
                logger.warning(f"Unknown recovery strategy: {strategy}")
                return self._full_restart()
                
        except Exception as e:
            logger.error(f"Error executing recovery strategy {strategy}: {e}")
            return False
    
    def _restart_ffmpeg(self):
        """Restart only the FFmpeg process"""
        try:
            # Stop FFmpeg
            if 'ffmpeg' in self.processes and self.processes['ffmpeg']:
                self.processes['ffmpeg'].terminate()
                self.processes['ffmpeg'].wait(timeout=5)
            
            time.sleep(2)
            
            # Restart FFmpeg
            env = os.environ.copy()
            env['DISPLAY'] = f":9{self.config['id'][-1]}"
            
            quality = self.quality_presets.get(self.config.get('quality', 'medium'))
            self._start_ffmpeg_stream(env, quality)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restart FFmpeg: {e}")
            return False
    
    def _restart_renderer(self):
        """Restart the content renderer process"""
        try:
            # Stop renderer
            if 'renderer' in self.processes and self.processes['renderer']:
                self.processes['renderer'].terminate()
                self.processes['renderer'].wait(timeout=5)
            
            time.sleep(2)
            
            # Restart renderer
            env = os.environ.copy()
            env['DISPLAY'] = f":9{self.config['id'][-1]}"
            quality = self.quality_presets.get(self.config.get('quality', 'medium'))
            
            if self.config['type'] == 'html':
                self._start_html_renderer(env, quality)
            elif self.config['type'] == 'pygame':
                self._start_pygame_renderer(env)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restart renderer: {e}")
            return False
    
    def _restart_display(self):
        """Restart the virtual display"""
        try:
            # This requires a full restart as display affects all other processes
            return self._full_restart()
            
        except Exception as e:
            logger.error(f"Failed to restart display: {e}")
            return False
    
    def _load_platform_configs(self):
        """Load platform configurations from database"""
        try:
            platforms = self.db.get_platform_configs()
            self.platform_configs = {p['platform_name']: p for p in platforms}
        except Exception as e:
            logger.error(f"Error loading platform configs: {e}")
            # Fallback to hardcoded configs
            self.platform_configs = {
                'youtube': {'rtmp_url': 'rtmp://a.rtmp.youtube.com/live2/', 'max_bitrate': 9000},
                'twitch': {'rtmp_url': 'rtmp://live.twitch.tv/live/', 'max_bitrate': 6000},
                'facebook': {'rtmp_url': 'rtmps://live-api-s.facebook.com:443/rtmp/', 'max_bitrate': 4000}
            }
    
    def _reduce_quality(self):
        """Reduce stream quality to improve performance"""
        try:
            current_quality = self.config.get('quality', 'medium')
            quality_levels = ['ultra', 'high', 'medium', 'low']
            
            if current_quality in quality_levels:
                current_index = quality_levels.index(current_quality)
                if current_index < len(quality_levels) - 1:
                    new_quality = quality_levels[current_index + 1]
                    
                    # Update stream quality
                    self.config['quality'] = new_quality
                    self.db.update_stream(self.config['id'], {'quality': new_quality})
                    
                    logger.info(f"Reduced quality from {current_quality} to {new_quality}")
                    
                    # Restart with new quality
                    return self._full_restart()
            
            return False  # Can't reduce quality further
            
        except Exception as e:
            logger.error(f"Failed to reduce quality: {e}")
            return False
    
    def _reconnect_stream(self):
        """Reconnect the stream by restarting FFmpeg with delay"""
        try:
            # Stop FFmpeg with a longer wait
            if 'ffmpeg' in self.processes and self.processes['ffmpeg']:
                self.processes['ffmpeg'].terminate()
                self.processes['ffmpeg'].wait(timeout=10)
            
            # Wait before reconnecting
            time.sleep(5)
            
            # Restart FFmpeg
            return self._restart_ffmpeg()
            
        except Exception as e:
            logger.error(f"Failed to reconnect stream: {e}")
            return False
    
    def _full_restart(self):
        """Perform a complete stream restart"""
        try:
            # Clean up all processes
            self.cleanup()
            
            # Wait before restarting
            time.sleep(3)
            
            # Restart the entire stream
            success, message = self.start_streaming()
            return success
            
        except Exception as e:
            logger.error(f"Failed to perform full restart: {e}")
            return False

class StreamManager:
    """Main stream manager class"""
    
    def __init__(self):
        self.db = StreamDatabase()
        self.active_streams = {}
        self.monitor_thread = None
        self.monitoring = False
    
    def start_monitoring(self):
        """Start stream monitoring thread"""
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
        """Monitor active streams for health and errors"""
        metrics_interval = 30  # Collect metrics every 30 seconds
        last_metrics_time = time.time()
        
        while self.monitoring:
            try:
                current_time = time.time()
                
                with stream_lock:
                    for stream_id, stream_instance in list(self.active_streams.items()):
                        # Check if processes are still running
                        if stream_instance.status == "live":
                            all_running = True
                            dead_processes = []
                            
                            for process_name, process in stream_instance.processes.items():
                                if process and process.poll() is not None:
                                    logger.warning(f"Process {process_name} died for stream {stream_id}")
                                    dead_processes.append(process_name)
                                    all_running = False
                            
                            if not all_running:
                                logger.error(f"Stream {stream_id} failed, attempting intelligent recovery")
                                
                                # Detect failure types for intelligent recovery
                                failure_types = stream_instance.detect_failure_type()
                                
                                # Attempt intelligent recovery
                                recovery_success, recovery_message = stream_instance.attempt_recovery(failure_types)
                                
                                if recovery_success:
                                    logger.info(f"Successfully recovered stream {stream_id}: {recovery_message}")
                                    # Stream should be running again
                                    continue
                                else:
                                    logger.error(f"Recovery failed for stream {stream_id}: {recovery_message}")
                                    stream_instance.cleanup()
                                    stream_instance.status = "error"
                                    self.db.update_stream_status(stream_id, 'error')
                                    self.db.log_event(stream_id, 'recovery_failed', {
                                        'reason': 'auto_recovery_failed',
                                        'dead_processes': dead_processes,
                                        'failure_types': failure_types,
                                        'recovery_message': recovery_message
                                    })
                            
                            # Collect performance metrics and health scoring
                            elif current_time - last_metrics_time >= metrics_interval:
                                try:
                                    metrics = stream_instance.collect_metrics()
                                    if metrics:
                                        self.db.log_metrics(stream_id, metrics)
                                        
                                        # Calculate and track health score
                                        health_score = stream_instance.calculate_health_score()
                                        
                                        # Check for performance issues
                                        self._check_performance_alerts(stream_id, metrics)
                                        
                                        # Predictive recovery for degrading health
                                        if health_score < 50 and not stream_instance.recovery_in_progress:
                                            logger.warning(f"Stream {stream_id} health degrading: {health_score:.1f}%")
                                            
                                            # Attempt preemptive recovery
                                            failure_types = stream_instance.detect_failure_type()
                                            if failure_types and 'unknown_failure' not in failure_types:
                                                logger.info(f"Starting preemptive recovery for {stream_id}")
                                                recovery_success, recovery_message = stream_instance.attempt_recovery(failure_types)
                                                
                                                if recovery_success:
                                                    self.db.create_alert(
                                                        stream_id,
                                                        'preemptive_recovery',
                                                        'info',
                                                        f'Preemptive recovery successful: {recovery_message}'
                                                    )
                                        
                                except Exception as e:
                                    logger.error(f"Error collecting metrics for {stream_id}: {e}")
                
                # Update metrics collection timestamp
                if current_time - last_metrics_time >= metrics_interval:
                    last_metrics_time = current_time
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in stream monitoring: {e}")
                time.sleep(5)
    
    def _check_performance_alerts(self, stream_id, metrics):
        """Check metrics for performance issues and create alerts"""
        try:
            # Check CPU usage
            if metrics.get('cpu_usage', 0) > 80:
                self.db.create_alert(
                    stream_id, 
                    'high_cpu', 
                    'warning', 
                    f'High CPU usage: {metrics["cpu_usage"]:.1f}%'
                )
            
            # Check memory usage
            if metrics.get('memory_usage', 0) > 1000:  # > 1GB
                self.db.create_alert(
                    stream_id, 
                    'high_memory', 
                    'warning', 
                    f'High memory usage: {metrics["memory_usage"]:.0f}MB'
                )
            
            # Check frame drops
            if metrics.get('frame_drops', 0) > 100:
                self.db.create_alert(
                    stream_id, 
                    'frame_drops', 
                    'warning', 
                    f'Frame drops detected: {metrics["frame_drops"]} frames'
                )
                
        except Exception as e:
            logger.error(f"Error checking performance alerts: {e}")
    
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
                
                # Load stream config and create instance
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
                # Check if stream exists
                existing_stream = self.db.get_stream(stream_id)
                if not existing_stream:
                    return False, "Stream not found"
                
                # Stop stream if running (will need restart for changes)
                was_running = False
                if stream_id in self.active_streams:
                    was_running = True
                    self.stop_stream(stream_id)
                
                # Update stream in database
                success = self.db.update_stream(stream_id, stream_data)
                if not success:
                    return False, "Failed to update stream"
                
                # Restart stream if it was running
                if was_running:
                    # Give it a moment, then restart
                    import time
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
                # Stop stream if running
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
        
        # Update with live status and uptime
        for stream in streams:
            stream_id = stream['id']
            if stream_id in self.active_streams:
                stream_instance = self.active_streams[stream_id]
                stream['status'] = stream_instance.status
                stream['uptime'] = stream_instance.get_uptime()
            else:
                stream['uptime'] = "0m"
        
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
# Set secret key for sessions (generate random key if not exists)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24).hex())
stream_manager = StreamManager()

def check_auth(username, password):
    """Check if username and password match stored credentials"""
    # Add 1-second delay to prevent timing attacks and PRNG exploitation
    time.sleep(1)
    
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

@app.route('/analytics')
@requires_auth
def analytics():
    """Analytics dashboard"""
    return render_template('analytics.html')

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

# Project Management APIs
@app.route('/api/projects', methods=['GET'])
def api_get_projects():
    """Get all projects"""
    projects = stream_manager.db.get_all_projects()
    return jsonify(projects)

@app.route('/api/projects', methods=['POST'])
def api_create_project():
    """Create new project"""
    try:
        project_data = request.json
        project_id = stream_manager.db.create_project(project_data)
        return jsonify({"success": True, "project_id": project_id, "message": "Project created successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route('/api/projects/<project_id>', methods=['PUT'])
def api_update_project(project_id):
    """Update project"""
    try:
        project_data = request.json
        success = stream_manager.db.update_project(project_id, project_data)
        return jsonify({"success": success, "message": "Project updated successfully" if success else "Project not found"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route('/api/projects/<project_id>', methods=['DELETE'])
def api_delete_project(project_id):
    """Delete project"""
    try:
        stream_manager.db.delete_project(project_id)
        return jsonify({"success": True, "message": "Project deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

# Template Management APIs
@app.route('/api/templates', methods=['GET'])
def api_get_templates():
    """Get all stream templates"""
    templates = stream_manager.db.get_all_templates()
    return jsonify(templates)

@app.route('/api/templates', methods=['POST'])
def api_create_template():
    """Create new template"""
    try:
        template_data = request.json
        template_id = stream_manager.db.create_template(template_data)
        return jsonify({"success": True, "template_id": template_id, "message": "Template created successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route('/api/templates/<template_id>', methods=['GET'])
def api_get_template(template_id):
    """Get specific template"""
    try:
        template = stream_manager.db.get_template(template_id)
        if template:
            return jsonify(template)
        else:
            return jsonify({"success": False, "message": "Template not found"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route('/api/templates/<template_id>', methods=['PUT'])
def api_update_template(template_id):
    """Update template"""
    try:
        template_data = request.json
        success = stream_manager.db.update_template(template_id, template_data)
        return jsonify({"success": success, "message": "Template updated successfully" if success else "Template not found"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route('/api/templates/<template_id>', methods=['DELETE'])
def api_delete_template(template_id):
    """Delete template"""
    try:
        success = stream_manager.db.delete_template(template_id)
        return jsonify({"success": success, "message": "Template deleted successfully" if success else "Template not found"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route('/api/streams/from-template', methods=['POST'])
def api_create_stream_from_template():
    """Create stream from template"""
    try:
        data = request.json
        template_id = data.get('template_id')
        stream_data = data.get('stream_data', {})
        
        stream_id = stream_manager.db.create_stream_from_template(template_id, stream_data)
        if stream_id:
            return jsonify({"success": True, "stream_id": stream_id, "message": "Stream created from template"})
        else:
            return jsonify({"success": False, "message": "Failed to create stream from template"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

# Platform Management APIs
@app.route('/api/platforms', methods=['GET'])
def api_get_platforms():
    """Get all available platforms"""
    platforms = stream_manager.db.get_platform_configs()
    return jsonify(platforms)

@app.route('/api/platforms', methods=['POST'])
def api_create_platform():
    """Create new platform configuration"""
    try:
        platform_data = request.json
        platform_id = stream_manager.db.create_platform_config(platform_data)
        return jsonify({"success": True, "platform_id": platform_id, "message": "Platform configuration created"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route('/api/platforms/<platform_name>', methods=['GET'])
def api_get_platform(platform_name):
    """Get specific platform configuration"""
    try:
        platform = stream_manager.db.get_platform_config(platform_name)
        if platform:
            return jsonify(platform)
        else:
            return jsonify({"success": False, "message": "Platform not found"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route('/api/platforms/<platform_name>', methods=['PUT'])
def api_update_platform(platform_name):
    """Update platform configuration"""
    try:
        platform_data = request.json
        success = stream_manager.db.update_platform_config(platform_name, platform_data)
        return jsonify({"success": success, "message": "Platform updated successfully" if success else "Platform not found"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route('/api/platforms/<platform_name>', methods=['DELETE'])
def api_delete_platform(platform_name):
    """Delete platform configuration"""
    try:
        success = stream_manager.db.delete_platform_config(platform_name)
        return jsonify({"success": success, "message": "Platform deleted successfully" if success else "Platform not found"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

# Multi-Stream Management APIs
@app.route('/api/streams/<stream_id>/multi-targets', methods=['POST'])
@requires_auth
def api_add_multi_stream_target(stream_id):
    """Add multi-stream target to a stream"""
    try:
        target_data = request.json
        
        # Get current stream
        stream = stream_manager.db.get_stream(stream_id)
        if not stream:
            return jsonify({"success": False, "message": "Stream not found"})
        
        # Add new target
        current_targets = stream.get('multi_stream_targets', [])
        if isinstance(current_targets, str):
            try:
                current_targets = json.loads(current_targets)
            except:
                current_targets = []
        
        current_targets.append(target_data)
        
        # Update stream
        success = stream_manager.db.update_stream(stream_id, {
            'multi_stream_targets': json.dumps(current_targets)
        })
        
        return jsonify({"success": success, "message": "Multi-stream target added" if success else "Failed to add target"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route('/api/streams/<stream_id>/multi-targets', methods=['GET'])
@requires_auth
def api_get_multi_stream_targets(stream_id):
    """Get multi-stream targets for a stream"""
    try:
        stream = stream_manager.db.get_stream(stream_id)
        if not stream:
            return jsonify({"success": False, "message": "Stream not found"})
        
        targets = stream.get('multi_stream_targets', [])
        if isinstance(targets, str):
            try:
                targets = json.loads(targets)
            except:
                targets = []
        
        return jsonify(targets)
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route('/api/streams/<stream_id>/multi-targets/<int:target_index>', methods=['DELETE'])
@requires_auth
def api_remove_multi_stream_target(stream_id, target_index):
    """Remove multi-stream target from a stream"""
    try:
        stream = stream_manager.db.get_stream(stream_id)
        if not stream:
            return jsonify({"success": False, "message": "Stream not found"})
        
        targets = stream.get('multi_stream_targets', [])
        if isinstance(targets, str):
            try:
                targets = json.loads(targets)
            except:
                targets = []
        
        if target_index < 0 or target_index >= len(targets):
            return jsonify({"success": False, "message": "Invalid target index"})
        
        targets.pop(target_index)
        
        # Update stream
        success = stream_manager.db.update_stream(stream_id, {
            'multi_stream_targets': json.dumps(targets)
        })
        
        return jsonify({"success": success, "message": "Multi-stream target removed" if success else "Failed to remove target"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

# Audio Configuration APIs
@app.route('/api/streams/<stream_id>/audio', methods=['PUT'])
@requires_auth
def api_update_stream_audio(stream_id):
    """Update stream audio configuration"""
    try:
        audio_config = request.json
        
        success = stream_manager.db.update_stream(stream_id, {
            'audio_input': json.dumps(audio_config)
        })
        
        return jsonify({"success": success, "message": "Audio configuration updated" if success else "Failed to update audio"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

# Project stream management
@app.route('/api/projects/<project_id>/streams', methods=['GET'])
@requires_auth
def api_get_project_streams(project_id):
    """Get all streams for a project"""
    try:
        streams = stream_manager.db.get_project_streams(project_id)
        return jsonify(streams)
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

@app.route('/api/metrics/<stream_id>', methods=['GET'])
@requires_auth
def api_get_stream_metrics(stream_id):
    """Get metrics for specific stream"""
    try:
        minutes = request.args.get('minutes', 30, type=int)
        metrics = stream_manager.db.get_recent_metrics(stream_id, minutes)
        return jsonify(metrics)
    except Exception as e:
        return jsonify({"error": f"Error retrieving metrics: {e}"})

@app.route('/api/alerts', methods=['GET'])
@requires_auth
def api_get_alerts():
    """Get all unacknowledged alerts"""
    try:
        stream_id = request.args.get('stream_id')
        alerts = stream_manager.db.get_stream_alerts(stream_id, acknowledged=False)
        return jsonify(alerts)
    except Exception as e:
        return jsonify({"error": f"Error retrieving alerts: {e}"})

@app.route('/api/alerts/<int:alert_id>/acknowledge', methods=['POST'])
@requires_auth
def api_acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    try:
        # TODO: Implement alert acknowledgment
        return jsonify({"success": True, "message": "Alert acknowledged"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route('/api/analytics/overview', methods=['GET'])
@requires_auth
def api_analytics_overview():
    """Get analytics overview for all streams"""
    try:
        streams = stream_manager.get_all_streams()
        total_streams = len(streams)
        active_streams = len([s for s in streams if s['status'] == 'live'])
        
        # Calculate total uptime
        total_uptime_seconds = sum(s.get('uptime_seconds', 0) for s in streams)
        total_uptime_hours = total_uptime_seconds / 3600
        
        # Get recent alerts count
        alerts = stream_manager.db.get_stream_alerts(acknowledged=False)
        
        # Get recovery statistics
        recovery_stats = stream_manager.db.get_recovery_stats()
        
        overview = {
            'total_streams': total_streams,
            'active_streams': active_streams,
            'total_uptime_hours': round(total_uptime_hours, 1),
            'active_alerts': len(alerts),
            'system_status': 'operational' if len(alerts) == 0 else 'issues_detected',
            'recovery_stats': recovery_stats
        }
        
        return jsonify(overview)
    except Exception as e:
        return jsonify({"error": f"Error retrieving overview: {e}"})

@app.route('/api/health/<stream_id>', methods=['GET'])
def api_get_stream_health(stream_id):
    """Get health score for specific stream"""
    try:
        health = stream_manager.db.get_latest_health(stream_id)
        return jsonify(health or {'health_score': 100, 'connection_quality': 100, 'performance_score': 100, 'stability_score': 100})
    except Exception as e:
        return jsonify({"error": f"Error retrieving health: {e}"})

@app.route('/api/recovery/<stream_id>', methods=['GET'])
def api_get_stream_recovery(stream_id):
    """Get recovery statistics for specific stream"""
    try:
        recovery_stats = stream_manager.db.get_recovery_stats(stream_id)
        active_recovery = stream_manager.db.get_active_recovery(stream_id)
        
        return jsonify({
            'stats': recovery_stats,
            'active_recovery': active_recovery
        })
    except Exception as e:
        return jsonify({"error": f"Error retrieving recovery data: {e}"})

@app.route('/api/streams/<stream_id>/recover', methods=['POST'])
@requires_auth
def api_manual_recovery(stream_id):
    """Manually trigger recovery for a specific stream"""
    try:
        with stream_lock:
            if stream_id not in stream_manager.active_streams:
                return jsonify({"success": False, "message": "Stream not active"})
            
            stream_instance = stream_manager.active_streams[stream_id]
            
            if stream_instance.recovery_in_progress:
                return jsonify({"success": False, "message": "Recovery already in progress"})
            
            # Detect current issues
            failure_types = stream_instance.detect_failure_type()
            if not failure_types or failure_types == ['unknown_failure']:
                # Force a diagnostic recovery
                failure_types = ['manual_recovery']
            
            # Attempt recovery
            success, message = stream_instance.attempt_recovery(failure_types)
            
            return jsonify({
                "success": success, 
                "message": message,
                "failure_types": failure_types
            })
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"})

@app.route('/api/platforms', methods=['GET'])
@requires_auth
def api_get_platforms():
    """Get all available streaming platforms"""
    try:
        platforms = stream_manager.db.get_platform_configs()
        return jsonify(platforms)
    except Exception as e:
        return jsonify({"error": f"Error retrieving platforms: {e}"})

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
        logger.info("Starting RTMP Stream Manager on port 5000")
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
        
    except KeyboardInterrupt:
        stream_manager.cleanup_all()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        stream_manager.cleanup_all()
