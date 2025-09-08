#!/bin/bash
# StreamDrop Health Check Script

echo "=== StreamDrop Health Check ==="
echo "Timestamp: $(date)"
echo

echo "Service Status:"
systemctl is-active streamdrop.service
echo

echo "Recent Errors (last 10 minutes):"
sudo journalctl -u streamdrop.service --since "10 minutes ago" --no-pager | grep -E "(ERROR|WARN|failed)" | tail -5
echo

echo "Stream Statuses:"
curl -s http://localhost:5000/api/streams 2>/dev/null | jq -r '.[] | "\(.name): \(.status) (\(.uptime))"' 2>/dev/null || echo "API not accessible or jq not installed"
echo

echo "Active FFmpeg Processes:"
ffmpeg_count=$(pgrep -f ffmpeg | wc -l)s
echo "Count: $ffmpeg_count"
if [ $ffmpeg_count -gt 0 ]; then
    echo "PIDs: $(pgrep -f ffmpeg | tr '\n' ' ')"
fi
echo

echo "Memory Usage (Top Python Processes):"
ps -o pid,ppid,cmd,%mem,%cpu --sort=-%mem -C python 2>/dev/null | head -5 || echo "No Python processes found"
echo

echo "Disk Space:"
df -h /home/toor/StreamDrop | tail -1
echo

echo "Recent Database Events (last 20):"
sqlite3 /home/toor/StreamDrop/streams.db "
SELECT datetime(timestamp, 'localtime') as time, 
       stream_id, 
       event_type, 
       CASE 
           WHEN length(details) > 50 THEN substr(details, 1, 50) || '...'
           ELSE details
       END as details
FROM stream_events 
WHERE timestamp > datetime('now', '-1 hour') 
ORDER BY timestamp DESC 
LIMIT 10;" 2>/dev/null || echo "Could not access database"

echo
echo "=== End Health Check ==="
