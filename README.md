# BetterTwitchChat

A Twitch chat reader with GUI interface that connects to Twitch chat via IRC protocol and displays messages in a real-time GUI window with sound notifications and user color support.

## Features

- Real-time Twitch chat display
- Sound notifications for new messages
- User color support
- Auto-connect on launch option
- Persistent settings
- Modern dark-themed GUI

## Requirements

- Python 3.6 or higher
- Windows (uses `winsound` for audio)
- Internet connection

## Installation

1. **Clone or download** this repository
2. **Install required packages**:
   ```bash
   pip install tkinter
   ```
   Note: `tkinter` is usually included with Python installations.

## Setup

### 1. Get Your Twitch OAuth Token

You need a Twitch OAuth token to connect to chat. Here are two methods:

#### How to get your Token

1. Go to [Twitch Developer Console](https://dev.twitch.tv/console)
2. Create a new application:
   - Click "Register Your Application"
   - Name: "BetterTwitchChat" (or your preferred name)
   - OAuth Redirect URLs: `http://localhost`
   - Category: "Application Integration"
3. Get your Client ID from the application details
4. Generate the OAuth URL:
   ```
   https://id.twitch.tv/oauth2/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost&response_type=token&scope=chat:read
   ```
5. Replace `YOUR_CLIENT_ID` with your actual Client ID
6. Open this URL in your browser
7. Authorize the application
8. Copy the token from the URL (after `#access_token=`)

### 2. Configure the Application

1. **Edit `chat_settings.json`** and add your token:
   ```json
   {
     "channel": "RakTheGoose",
     "auto_connect": false,
     "sound_enabled": true,
     "token": "oauth:your_actual_token_here"
   }
   ```

2. **Replace the values**:
   - `RakTheGoose`: The Twitch channel you want to join (without the #)
   - `your_actual_token_here`: The OAuth token you obtained in step 1

## Usage

1. **Run the application**:
   ```bash
   python BetterTwitchChat.py
   ```

2. **Configure settings** (if not already done in chat_settings.json):
   - Enter the channel name
   - Toggle sound notifications
   - Enable auto-connect if desired

3. **Click "Connect"** to join the chat

4. **Enjoy real-time chat messages** with user colors and sound notifications!

## Configuration Options

The `chat_settings.json` file stores your preferences:

- `channel`: Default channel to connect to
- `auto_connect`: Whether to automatically connect on startup
- `sound_enabled`: Whether to play sound notifications
- `token`: Your Twitch OAuth token

## Troubleshooting

### "OAuth token not configured" Error

If you see this message when trying to connect:
1. Make sure your token is properly set in `chat_settings.json`
2. Ensure the token starts with `oauth:`
3. Verify the token is valid and not expired

### Connection Issues

- Check your internet connection
- Verify the channel name is correct
- Ensure your OAuth token is valid
- Try regenerating your token if needed

### Sound Not Working

- Make sure `sound_enabled` is set to `true` in settings
- Check that `notification.wav` exists in the same directory
- Verify your system audio is working

## Security Notes

- Your OAuth token is stored locally in `chat_settings.json`
- Never share your token with others
- The token only has `chat:read` permissions (cannot send messages)
- You can revoke the token from your Twitch account settings if needed

## File Structure

```
BetterTwitchChat/
├── BetterTwitchChat.py    # Main application
├── chat_settings.json     # Configuration file
├── notification.wav       # Sound notification file
└── README.md             # This file
```

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve the application.

## License

This project is open source. Feel free to modify and distribute as needed.

## Credits

Created by RakTheGoose - A Twitch chat reader with a modern GUI interface. 