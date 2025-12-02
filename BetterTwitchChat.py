"""BetterTwitchChat - A Twitch chat reader with GUI interface.

This script connects to Twitch chat via IRC protocol and displays messages
in a real-time GUI window with sound notifications and user color support.
"""

import base64
import json
import os
import re
import signal
import socket
import ssl
import sys
import threading
import webbrowser
from datetime import datetime

import tkinter as tk
from tkinter import BooleanVar, Checkbutton, scrolledtext, messagebox, simpledialog
import winsound

# Configuration constants
TWITCH_SERVER = 'irc.chat.twitch.tv'
TWITCH_PORT = 6667
TOKEN = 'oauth:__CHANGEME__'  # This will be updated by the token dialog
SOUND_FILE = 'notification.wav'
SETTINGS_FILE = 'chat_settings.json'


class SoundManager:
    """Manages sound playback with thread limiting to prevent audio chaos."""
    
    def __init__(self):
        self.sound_threads = []
        self.max_concurrent_sounds = 5
    
    def play_sound(self):
        """Play notification sound in a separate thread."""
        self.sound_threads = [thread for thread in self.sound_threads if thread.is_alive()]
        
        if len(self.sound_threads) >= self.max_concurrent_sounds:
            return
        
        def _play_sound_thread():
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                sound_path = os.path.join(script_dir, SOUND_FILE)
                
                if os.path.exists(sound_path):
                    winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                else:
                    winsound.Beep(1000, 100)
            except Exception as e:
                print(f"Could not play sound: {e}")
                print("🔊 SOUND TRIGGERED! 🔊")
        
        sound_thread = threading.Thread(target=_play_sound_thread, daemon=True)
        sound_thread.start()
        self.sound_threads.append(sound_thread)


# Global sound manager instance
sound_manager = SoundManager()


class ChatWindow:
    """Main GUI window for the Twitch chat reader application."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BetterTwitchChat")
        self.root.geometry("600x500")
        self.root.configure(bg='#1a1a1a')
        
        self.connected = False
        self.sock = None
        self.chat_thread = None
        self.ignored_usernames = set()
        
        self._setup_ui()
        self._setup_event_handlers()
        self.load_settings()
        
        if self.auto_connect_var.get():
            self.root.after(1000, self.connect)
    
    def _setup_ui(self):
        """Set up the user interface components."""
        main_frame = tk.Frame(self.root, bg='#1a1a1a')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self._create_connection_frame(main_frame)
        self._create_chat_display(main_frame)
        self._create_bottom_bar(main_frame)
        self._configure_chat_tags()
        
        self.center_window()
    
    def _create_connection_frame(self, parent):
        """Create the connection controls frame."""
        connection_frame = tk.Frame(parent, bg='#1a1a1a')
        connection_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Channel input
        channel_frame = tk.Frame(connection_frame, bg='#1a1a1a')
        channel_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Label(channel_frame, text="Channel:", fg='#ffffff', bg='#1a1a1a',
                font=("Arial", 10)).pack(side=tk.LEFT)
        
        self.channel_var = tk.StringVar(value='rakthegoose')
        self.channel_entry = tk.Entry(channel_frame, textvariable=self.channel_var,
                                     width=15, bg='#2d2d2d', fg='#ffffff',
                                     insertbackground='#ffffff')
        self.channel_entry.pack(side=tk.LEFT, padx=(5, 0))
        self.channel_var.trace('w', lambda *args: self.save_settings())
        
        # Connect button
        self.connect_button = tk.Button(connection_frame, text="Connect",
                                       command=self.toggle_connection,
                                       bg='#28a745', fg='#ffffff',
                                       font=("Arial", 10, "bold"),
                                       width=10, relief=tk.FLAT)
        self.connect_button.pack(side=tk.RIGHT)
        
        # Sound toggle
        self.sound_enabled_var = BooleanVar(value=True)
        self.sound_checkbox = Checkbutton(connection_frame, text="Enable Sound",
                                         variable=self.sound_enabled_var,
                                         fg='#ffffff', bg='#1a1a1a',
                                         selectcolor='#2d2d2d',
                                         font=("Arial", 9),
                                         command=self.save_settings)
        self.sound_checkbox.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Auto-connect toggle
        self.auto_connect_var = BooleanVar()
        self.auto_connect_checkbox = Checkbutton(connection_frame,
                                                text="Auto-connect on launch",
                                                variable=self.auto_connect_var,
                                                fg='#ffffff', bg='#1a1a1a',
                                                selectcolor='#2d2d2d',
                                                font=("Arial", 9),
                                                command=self.save_settings)
        self.auto_connect_checkbox.pack(side=tk.RIGHT, padx=(0, 10))
    
    def _create_chat_display(self, parent):
        """Create the chat message display area."""
        self.chat_display = scrolledtext.ScrolledText(
            parent, wrap=tk.WORD, width=70, height=18,
            font=("Consolas", 10), bg='#2d2d2d', fg='#ffffff',
            insertbackground='#ffffff', selectbackground='#404040',
            state='disabled'
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
    
    def _create_bottom_bar(self, parent):
        """Create the bottom status bar with footer and status indicator."""
        bottom_frame = tk.Frame(parent, bg='#1a1a1a')
        bottom_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Footer
        footer_text = tk.Label(bottom_frame, text="Proudly created by",
                              fg='#888888', bg='#1a1a1a', font=("Arial", 8))
        footer_text.pack(side=tk.LEFT)
        
        github_link = tk.Label(bottom_frame, text="RakTheGoose",
                              fg='#888888', bg='#1a1a1a',
                              font=("Arial", 8, "underline"), cursor="hand2")
        github_link.pack(side=tk.LEFT)
        github_link.bind("<Button-1>",
                        lambda e: webbrowser.open("https://github.com/GooseWithAKnife"))
        
        def on_enter(e):
            github_link.config(fg='#cccccc')
        
        def on_leave(e):
            github_link.config(fg='#888888')
        
        github_link.bind("<Enter>", on_enter)
        github_link.bind("<Leave>", on_leave)
        
        # Spacer
        spacer = tk.Frame(bottom_frame, bg='#1a1a1a')
        spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Ignore list button
        self.ignore_button = tk.Button(bottom_frame, text="Ignore List",
                                       command=self.open_ignore_list_window,
                                       bg='#007bff', fg='#ffffff',
                                       font=("Arial", 9, "bold"),
                                       width=12, relief=tk.FLAT, cursor="hand2")
        self.ignore_button.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Status indicator
        self.status_orb = tk.Label(bottom_frame, text="●", fg='#ff4444',
                                  bg='#1a1a1a', font=("Arial", 16, "bold"))
        self.status_orb.pack(side=tk.RIGHT, padx=(0, 5), pady=(0, 2))
        
        self.status_label = tk.Label(bottom_frame, text="Disconnected",
                                    fg='#888888', bg='#1a1a1a', font=("Arial", 9))
        self.status_label.pack(side=tk.RIGHT)
    
    def open_ignore_list_window(self):
        """Open a window to edit ignored usernames (newline-separated)."""
        win = tk.Toplevel(self.root)
        win.title("Ignore List")
        win.configure(bg='#1a1a1a')
        win.geometry("400x350")
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="Usernames to ignore (no sound):",
                 fg='#ffffff', bg='#1a1a1a', font=("Arial", 10, "bold")).pack(anchor='w', padx=10, pady=(10, 5))

        hint = tk.Label(win, text="Enter one username per line. '@' optional. Case-insensitive.",
                        fg='#aaaaaa', bg='#1a1a1a', font=("Arial", 9))
        hint.pack(anchor='w', padx=10, pady=(0, 8))

        text = scrolledtext.ScrolledText(win, wrap=tk.WORD, width=45, height=12,
                                         font=("Consolas", 10), bg='#2d2d2d', fg='#ffffff',
                                         insertbackground='#ffffff', selectbackground='#404040')
        # Pre-fill with current list
        try:
            current = sorted(self.ignored_usernames)
            text.insert('1.0', "\n".join(current))
        except Exception:
            pass
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        button_frame = tk.Frame(win, bg='#1a1a1a')
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        def save_and_close():
            raw = text.get('1.0', tk.END)
            names = []
            for line in raw.splitlines():
                name = line.strip()
                if not name:
                    continue
                if name.startswith('@'):
                    name = name[1:]
                names.append(name.lower())
            self.ignored_usernames = set(names)
            self.save_settings()
            messagebox.showinfo("Ignore List", "Ignore list saved.", parent=win)
            win.destroy()

        save_btn = tk.Button(button_frame, text="Save", command=save_and_close,
                             bg='#28a745', fg='#ffffff', font=("Arial", 9, "bold"),
                             width=10, relief=tk.FLAT, cursor="hand2")
        save_btn.pack(side=tk.RIGHT, padx=(5, 0))

        cancel_btn = tk.Button(button_frame, text="Cancel", command=win.destroy,
                               bg='#6c757d', fg='#ffffff', font=("Arial", 9, "bold"),
                               width=10, relief=tk.FLAT, cursor="hand2")
        cancel_btn.pack(side=tk.RIGHT)

        # Center the ignore list window on the screen
        try:
            win.update_idletasks()
            screen_width = win.winfo_screenwidth()
            screen_height = win.winfo_screenheight()
            window_width = win.winfo_width()
            window_height = win.winfo_height()
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            win.geometry(f"{window_width}x{window_height}+{x}+{y}")
        except Exception:
            pass
    
    def _configure_chat_tags(self):
        """Configure text tags for different message types."""
        self.chat_display.tag_configure("timestamp", foreground="#888888")
        self.chat_display.tag_configure("username", foreground="#00ff00",
                                       font=("Consolas", 10, "bold"))
        self.chat_display.tag_configure("message", foreground="#ffffff")
        self.chat_display.tag_configure("system", foreground="#ffaa00",
                                       font=("Consolas", 10, "bold"))
    
    def _setup_event_handlers(self):
        """Set up event handlers for the window."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def add_message(self, username, message, color=None):
        """Add a chat message to the display."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
        
        if color:
            tag_name = f"user_{username}"
            self.chat_display.tag_configure(tag_name, foreground=color,
                                           font=("Consolas", 10, "bold"))
            self.chat_display.insert(tk.END, f"{username}: ", tag_name)
        else:
            self.chat_display.insert(tk.END, f"{username}: ", "username")
        
        self.chat_display.insert(tk.END, f"{message}\n", "message")
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)
    
    def add_system_message(self, message):
        """Add a system message to the display."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.chat_display.insert(tk.END, f"{message}\n", "system")
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)
    
    def update_status(self, status):
        """Update the status indicator with text and orb color."""
        self.status_label.config(text=status)
        
        if "Connected" in status:
            self.status_orb.config(fg='#44ff44')
        elif "Connecting" in status:
            self.status_orb.config(fg='#ffaa00')
        else:
            self.status_orb.config(fg='#ff4444')
    
    def load_settings(self):
        """Load settings from the settings file."""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            settings_path = os.path.join(script_dir, SETTINGS_FILE)
            
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                
                if 'channel' in settings:
                    self.channel_var.set(settings['channel'])
                if 'auto_connect' in settings:
                    self.auto_connect_var.set(settings['auto_connect'])
                if 'sound_enabled' in settings:
                    self.sound_enabled_var.set(settings['sound_enabled'])
                if 'token' in settings:
                    global TOKEN
                    saved_token = settings['token']
                    if saved_token and saved_token != 'oauth:__CHANGEME__':
                        TOKEN = saved_token
                if 'ignore_usernames' in settings and isinstance(settings['ignore_usernames'], list):
                    self.ignored_usernames = set([str(u).lower() for u in settings['ignore_usernames'] if str(u).strip()])
        except Exception as e:
            print(f"Could not load settings: {e}")
    
    def save_settings(self):
        """Save current settings to the settings file."""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            settings_path = os.path.join(script_dir, SETTINGS_FILE)
            
            # Load existing settings to preserve token
            settings = {}
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
            
            # Update with current settings
            settings.update({
                'channel': self.channel_var.get(),
                'auto_connect': self.auto_connect_var.get(),
                'sound_enabled': self.sound_enabled_var.get(),
                'ignore_usernames': sorted(list(self.ignored_usernames))
            })
            
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Could not save settings: {e}")
    
    def toggle_connection(self):
        """Toggle between connect and disconnect states."""
        if not self.connected:
            self.connect()
        else:
            self.disconnect()
    
    def connect(self):
        """Connect to Twitch chat."""
        try:
            # Check if token is properly configured
            if TOKEN.strip().lower() == 'oauth:__changeme__':
                self.update_status("Please configure OAuth token first")
                self.add_system_message("OAuth token not configured. Please add your token to chat_settings.json.")
                return
            
            channel = self.channel_var.get().strip()
            
            if not channel:
                self.update_status("Please enter a channel")
                return
            
            if not channel.startswith('#'):
                channel = '#' + channel
            
            print(f"Attempting to connect to {channel}...")
            self.update_status("Connecting...")
            
            self.sock = connect_to_twitch_ssl(TOKEN, channel.lstrip('#'))
            
            self.chat_thread = threading.Thread(target=self.chat_listener, daemon=True)
            self.chat_thread.start()
            
            self.connected = True
            self.connect_button.config(text="Disconnect", bg='#dc3545')
            self.channel_entry.config(state='disabled')
            self.update_status("Connected")
            
            self.add_system_message(f"Connected to {channel.lstrip('#')}")
            
        except Exception as e:
            self.update_status(f"Connection failed: {e}")
    
    def disconnect(self):
        """Disconnect from Twitch chat."""
        try:
            if self.sock:
                self.sock.close()
            
            self.connected = False
            self.connect_button.config(text="Connect", bg='#28a745')
            self.channel_entry.config(state='normal')
            self.update_status("Disconnected")
            
            self.add_system_message("Disconnected from chat")
            
        except Exception as e:
            self.update_status(f"Disconnect error: {e}")
    
    def chat_listener(self):
        """Listen for chat messages in background thread."""
        print("Chat listener thread started")
        try:
            while self.connected:
                if not self.sock:
                    print("Socket is None, breaking")
                    break
                
                print("Waiting for data from Twitch...")
                resp = self.sock.recv(2048).decode('utf-8')
                print(f"Received {len(resp)} characters from Twitch")
                
                if not resp:
                    print("No response received from Twitch")
                    break
                
                if resp.startswith('PING'):
                    print("PING received, sending PONG")
                    self.sock.send("PONG :tmi.twitch.tv\r\n".encode('utf-8'))
                else:
                    for line in resp.split('\r\n'):
                        if not line:
                            continue
                        username, message, color = parse_message(line)
                        if username and message:
                            message = message.rstrip().replace('\uFFFD', '')
                            self.root.after(0, self.add_message, username, message, color)
                            if self.sound_enabled_var.get():
                                try:
                                    if username.lower() not in self.ignored_usernames:
                                        play_sound()
                                except Exception:
                                    # Fallback to playing if any unexpected issue occurs
                                    play_sound()
                        elif 'PRIVMSG' in line:
                            self.root.after(0, self.add_system_message,
                                          f"DEBUG: Could not parse: {line[:50]}...")
        except Exception as e:
            print(f"Connection error: {e}")
            if self.connected:
                self.root.after(0, self.update_status, f"Connection error: {e}")
                self.root.after(0, self.disconnect)
    
    def on_closing(self):
        """Handle window close event - save settings and disconnect."""
        try:
            self.save_settings()
            if self.connected:
                self.disconnect()
            self.root.destroy()
        except Exception as e:
            print(f"Error during shutdown: {e}")
            self.root.destroy()
    
    def run(self):
        """Start the GUI event loop."""
        self.root.mainloop()


def play_sound():
    """Play notification sound using the global sound manager."""
    sound_manager.play_sound()


def connect_to_twitch_ssl(token, channel):
    """Connect to Twitch IRC with SSL and tags capability for colors.
    
    Args:
        token: OAuth token for authentication.
        channel: Channel to join (without leading '#').
    
    Returns:
        A connected SSL socket object.
    """
    context = ssl.create_default_context()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock = context.wrap_socket(sock, server_hostname='irc.chat.twitch.tv')
    sock.connect(('irc.chat.twitch.tv', 6697))
    
    commands = [
        f"PASS {token}",
        "NICK chatreader",
        "CAP REQ :twitch.tv/membership twitch.tv/tags twitch.tv/commands",
        "CAP END",
        f"JOIN #{channel}"
    ]
    
    for cmd in commands:
        sock.send(f"{cmd}\r\n".encode('utf-8'))
    
    return sock


def parse_message(irc_message):
    """Parse a raw IRC message and extract username, message text, and color.
    
    Args:
        irc_message: Raw IRC message string.
    
    Returns:
        Tuple of (username, message, color) if a user message, else (None, None, None).
    """
    # Parse PRIVMSG with color information (with @tags)
    match = re.match(r'^@([^ ]+) :([^!]+)!.* PRIVMSG #[^ ]+ :(.*)', irc_message)
    if match:
        tags = match.group(1)
        username = match.group(2)
        message = match.group(3)
        
        color = None
        display_name = username
        
        for tag in tags.split(';'):
            if tag.startswith('color='):
                color_value = tag.split('=')[1]
                if color_value and color_value != '':
                    if color_value.startswith('#'):
                        color = color_value
                    else:
                        color = f'#{color_value}'
            elif tag.startswith('display-name='):
                display_name = tag.split('=')[1]
        
        return display_name, message, color
    
    # Parse PRIVMSG without @tags (fallback)
    match = re.match(r'^:([^!]+)!.* PRIVMSG #[^ ]+ :(.*)', irc_message)
    if match:
        username = match.group(1)
        message = match.group(2)
        return username, message, None
    
    return None, None, None


def signal_handler(signum, frame):
    """Handle termination signals to save settings before exit."""
    print("\nSaving settings before exit...")
    try:
        if hasattr(signal_handler, 'chat_window') and signal_handler.chat_window:
            signal_handler.chat_window.save_settings()
            if signal_handler.chat_window.connected:
                signal_handler.chat_window.disconnect()
    except Exception as e:
        print(f"Error saving settings during shutdown: {e}")
    sys.exit(0)


def main():
    """Main function to start the GUI application."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    chat_window = ChatWindow()
    signal_handler.chat_window = chat_window
    chat_window.run()


if __name__ == '__main__':
    main()
