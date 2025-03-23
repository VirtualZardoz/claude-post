# ClaudePost (Enhanced Fork)

> This is a fork of [ZilongXue/claude-post](https://github.com/ZilongXue/claude-post) with additional features and bug fixes.

A Model Context Protocol (MCP) server that provides a seamless email management interface through Claude. This integration allows you to handle emails directly through natural language conversations with Claude, supporting features like searching, reading, and sending emails securely.

## Enhancements in this Fork

* 🔍 **Complete Folder Access**: Added ability to browse and search all email folders
* 🛠️ **Bug Fixes**: Fixed IMAP state errors when fetching email content
* 📋 **Improved Logging**: Enhanced logging for better troubleshooting
* 🔄 **Robust Email Operations**: Better handling of mailbox selection across all operations

## Features & Demo

### Email Search and Reading

<p align="center">
  <img src="assets/gif1.gif" width="800"/>
</p>

* 📧 Search emails by date range and keywords
* 📅 View daily email statistics
* 📝 Read full email content with threading support

### Email Composition and Sending

<p align="center">
  <img src="assets/gif2.gif" width="800"/>
</p>

* ✉️ Send emails with CC recipients support
* 🔒 Secure email handling with TLS

## Prerequisites

* Python 3.12 or higher
* A Gmail account (or other email provider)
* If using Gmail:
  * Two-factor authentication enabled
  * [App-specific password](https://support.google.com/mail/answer/185833?hl=en) generated
* Claude Desktop application

## Setup

1. Install uv:

   ```bash
   # MacOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Remember to restart your terminal after installation
   ```

2. Clone and set up the project:

   ```bash
   # Clone the repository
   git clone https://github.com/YOUR-USERNAME/claude-post.git
   cd claude-post

   # Create and activate virtual environment
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

   # Install dependencies
   uv pip install -e .
   ```

3. Create a `.env` file in the project root:

   ```env
   EMAIL_ADDRESS=your.email@gmail.com
   EMAIL_PASSWORD=your-app-specific-password
   IMAP_SERVER=imap.gmail.com
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   ```

4. Configure Claude Desktop:

   First, make sure you have Claude for Desktop installed. You can install the latest version [here](https://claude.ai/download). If you already have Claude for Desktop, make sure it's updated to the latest version.

   Open your Claude Desktop configuration file:

   ```bash
   # MacOS
   ~/Library/Application Support/Claude/claude_desktop_config.json

   # Windows
   %APPDATA%\Claude\claude_desktop_config.json

   # Create the file if it doesn't exist
   ```

   Add the following configuration:

   ```json
   {
     "mcpServers": {
       "email": {
         "command": "python",
         "args": [
           "-m",
           "email_client"
         ],
         "cwd": "/path/to/claude-post"
       }
     }
   }
   ```

   Replace `/path/to/claude-post` with your actual path.
   
   For Windows, use a configuration like:
   
   ```json
   {
     "mcpServers": {
       "email": {
         "command": "C:/path/to/claude-post/.venv/Scripts/python.exe",
         "args": [
           "-m",
           "email_client"
         ],
         "cwd": "C:/path/to/claude-post"
       }
     }
   }
   ```

   After updating the configuration, restart Claude Desktop for the changes to take effect.

## Running the Server

The server runs automatically through Claude Desktop:

* The server will start when Claude launches if configured correctly
* No manual server management needed
* Server stops when Claude is closed

## Usage Through Claude

You can interact with your emails using natural language commands. Here are some examples:

### View Folder Structure
* "What folders are available in my email account?"
* "List all my email folders"

### Search Emails

* "Show me emails from last week"
* "Find emails with subject containing 'meeting'"
* "Search for emails from recruiting@linkedin.com between 2024-01-01 and 2024-01-07"
* "Search sent emails from last month"
* "Search for emails with keyword 'invoice' in my 'Archive' folder"

### Read Email Content

* "Show me the content of email #12345"
* "What's the full message of the last email from HR?"
* "Get the content of email #678 from the 'Projects' folder"

### Email Statistics

* "How many emails did I receive today?"
* "Show me daily email counts for the past week"
* "Count emails in my 'Newsletters' folder from 2023-01-01 to 2023-01-31"

### Send Emails

* "I want to send an email to john@example.com"
* "Send a meeting confirmation to team@company.com"

Note: For security reasons, Claude will always show you the email details for confirmation before actually sending.

## Project Structure

```
claude-post/
├── pyproject.toml
├── README.md
├── LICENSE
├── .env                    # Not included in repo
├── .python-version        # Python version specification
└── src/
    └── email_client/
        ├── __init__.py
        ├── __main__.py
        └── server.py       # Main implementation
```

## Security Notes

* Use app-specific passwords instead of your main account password
* For Gmail users:
  1. Enable 2-Step Verification in your Google Account
  2. Generate an App Password for this application
  3. Use the App Password in your `.env` file

## Logging

The application logs detailed information to `email_client.log`. Check this file for debugging information and error messages.

## Troubleshooting

If you encounter issues:
1. Check the `email_client.log` file for detailed error messages
2. Ensure your email server supports IMAP and SMTP access
3. Verify your credentials in the `.env` file
4. Make sure the proper mailbox is selected before operations

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

* Original project by [ZilongXue](https://github.com/ZilongXue/claude-post)
* Uses the [Model Context Protocol (MCP)](https://github.com/anthropics/anthropic-cookbook/tree/main/mcp) for integration with Claude
