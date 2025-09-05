#!/usr/bin/env python3
"""
Database migration script for RTMP-BASE
Adds new columns to existing streams table
"""

import sqlite3
import os

def migrate_database():
    db_path = "streams.db"
    
    print("🔄 Starting database migration...")
    
    if not os.path.exists(db_path):
        print("✅ No existing database found. New schema will be created automatically.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get current table schema
    cursor.execute("PRAGMA table_info(streams)")
    columns = [row[1] for row in cursor.fetchall()]
    
    migrations = []
    
    # Check and add new columns
    if 'rtmp_url' not in columns:
        migrations.append("ALTER TABLE streams ADD COLUMN rtmp_url TEXT DEFAULT ''")
        
    if 'custom_settings' not in columns:
        migrations.append("ALTER TABLE streams ADD COLUMN custom_settings TEXT DEFAULT ''")
    
    # Check for analytics tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stream_metrics'")
    if not cursor.fetchone():
        migrations.append('''
            CREATE TABLE stream_metrics (
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
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stream_alerts'")
    if not cursor.fetchone():
        migrations.append('''
            CREATE TABLE stream_alerts (
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
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stream_recovery'")
    if not cursor.fetchone():
        migrations.append('''
            CREATE TABLE stream_recovery (
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
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stream_health'")
    if not cursor.fetchone():
        migrations.append('''
            CREATE TABLE stream_health (
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
    
    # Execute migrations
    if migrations:
        print(f"📝 Applying {len(migrations)} migration(s)...")
        for migration in migrations:
            print(f"   - {migration}")
            cursor.execute(migration)
        
        conn.commit()
        print("✅ Database migration completed successfully!")
    else:
        print("✅ Database is already up to date!")
    
    conn.close()

if __name__ == "__main__":
    migrate_database()
