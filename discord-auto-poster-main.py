import requests
import json
import time
import threading
from datetime import datetime
import sys
import os

if sys.platform == 'win32':
    import ctypes

class DiscordAutoPoster:
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        self.token = self.config.get('token', '')
        self.base_url = 'https://discord.com/api/v10'
        self.headers = {
            'Authorization': self.token,
            'Content-Type': 'application/json'
        }
        self.running = True
        self.messages_sent = 0
        self.lock = threading.Lock()
        
    def update_title(self):
        """Update the console window title with message count"""
        title = f"Messages sent: {self.messages_sent}"
        
        if sys.platform == 'win32':
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        elif sys.platform in ['linux', 'darwin']:
            sys.stdout.write(f"\033]0;{title}\007")
            sys.stdout.flush()
        
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Config file '{self.config_file}' not found!")
            exit(1)
    
    def verify_token(self):
        """Verify the token works"""
        response = requests.get(f'{self.base_url}/users/@me', headers=self.headers)
        if response.status_code == 200:
            user_data = response.json()
            print(f"✓ Logged in as: {user_data['username']}#{user_data['discriminator']}")
            print(f"✓ User ID: {user_data['id']}")
            return True
        else:
            print(f"✗ Token verification failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    
    def send_message(self, channel_id, message):
        """Send a message to a channel"""
        url = f'{self.base_url}/channels/{channel_id}/messages'
        data = {'content': message}
        
        response = requests.post(url, headers=self.headers, json=data)
        
        if response.status_code == 200:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] ✓ Posted to channel {channel_id}")
            
            with self.lock:
                self.messages_sent += 1
                self.update_title()
            
            return True
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] ✗ Failed to post to {channel_id}: {response.status_code}")
            if response.status_code == 429:
                retry_after = response.json().get('retry_after', 60)
                print(f"  Rate limited! Retry after {retry_after} seconds")
            elif response.status_code == 403:
                print(f"  No permission to post in this channel")
            elif response.status_code == 404:
                print(f"  Channel not found")
            return False
    
    def post_loop(self, channel_config):
        """Loop for posting to a specific channel"""
        channel_id = channel_config['channel_id']
        message = channel_config['message']
        interval_minutes = channel_config['interval_minutes']
        interval_seconds = interval_minutes * 60
        
        print(f"Started posting task for channel {channel_id} (every {interval_minutes} min)")
        
        self.send_message(channel_id, message)
        
        while self.running:
            for _ in range(interval_seconds):
                if not self.running:
                    break
                time.sleep(1)
            
            if self.running:
                self.send_message(channel_id, message)
    
    def start(self):
        """Start all posting tasks"""
        self.update_title()
        
        print("=" * 50)
        print("Discord Auto-Poster")
        print("=" * 50)
        
        if not self.verify_token():
            print("\n✗ Failed to verify token. Please check your token in config.json")
            return
        
        print(f"\n✓ Starting {len(self.config['channels'])} posting tasks...\n")
        
        threads = []
        for channel_config in self.config['channels']:
            thread = threading.Thread(
                target=self.post_loop,
                args=(channel_config,),
                daemon=True
            )
            thread.start()
            threads.append(thread)
        
        print("\n✓ All tasks started! Press Ctrl+C to stop.\n")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopping all tasks...")
            self.running = False
            time.sleep(2)
            print("✓ Shutdown complete!")

def main():
    poster = DiscordAutoPoster('config.json')
    poster.start()

if __name__ == '__main__':
    main()