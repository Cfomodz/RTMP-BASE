sudo nano /etc/systemd/system/youtube-streamer.service

[Unit]
Description=24/7 YouTube HTML Streamer
After=network.target

[Service]
Type=simple
User=your_username
Environment=YOUTUBE_STREAM_KEY=your_stream_key
Environment=CONTENT_PATH=your_content_url
WorkingDirectory=/path/to/script/directory
ExecStart=/usr/bin/python3 /path/to/script/html_streamer.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target


sudo systemctl enable youtube-streamer
sudo systemctl start youtube-streamer