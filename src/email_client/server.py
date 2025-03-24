from typing import Any
import asyncio
from datetime import datetime, timedelta
import email
import imaplib
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='email_client.log'
)

# Load environment variables from .env file
load_dotenv()

# Email configuration
EMAIL_CONFIG = {
    "email": os.getenv("EMAIL_ADDRESS", "your.email@gmail.com"),
    "password": os.getenv("EMAIL_PASSWORD", "your-app-specific-password"),
    "imap_server": os.getenv("IMAP_SERVER", "imap.gmail.com"),
    "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("SMTP_PORT", "587"))
}

# Constants
SEARCH_TIMEOUT = 60  # seconds
MAX_EMAILS = 100

server = Server("email")

def decode_header_safely(header_value: str) -> str:
    """Safely decode email headers that may contain encoded words or special characters."""
    try:
        decoded_parts = email.header.decode_header(header_value or "")
        result = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                if encoding:
                    try:
                        part = part.decode(encoding, errors='replace')
                    except (LookupError, UnicodeDecodeError):
                        part = part.decode('utf-8', errors='replace')
                else:
                    part = part.decode('utf-8', errors='replace')
            result += str(part)
        return result
    except Exception as e:
        logging.error(f"Error decoding header: {str(e)}")
        return header_value or ""

def format_email_summary(msg_data: tuple) -> dict:
    """Format an email message into a summary dict with basic information."""
    email_body = email.message_from_bytes(msg_data[0][1])
    
    return {
        "id": msg_data[0][0].split()[0].decode(),  # Get the email ID
        "from": decode_header_safely(email_body.get("From", "Unknown")),
        "date": email_body.get("Date", "Unknown"),
        "subject": decode_header_safely(email_body.get("Subject", "No Subject")),
    }

def format_email_content(msg_data: tuple) -> dict:
    """Format an email message into a dict with full content."""
    email_body = email.message_from_bytes(msg_data[0][1])
    
    # Extract body content
    body = ""
    if email_body.is_multipart():
        # Handle multipart messages
        for part in email_body.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    break
                except Exception as e:
                    logging.error(f"Error decoding email body: {str(e)}")
                    body = part.get_payload(decode=True).decode('utf-8', errors='replace')
            elif part.get_content_type() == "text/html":
                # If no plain text found, use HTML content
                if not body:
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                    except Exception as e:
                        logging.error(f"Error decoding HTML body: {str(e)}")
                        body = part.get_payload(decode=True).decode('utf-8', errors='replace')
    else:
        # Handle non-multipart messages
        try:
            body = email_body.get_payload(decode=True).decode('utf-8', errors='replace')
        except Exception as e:
            logging.error(f"Error decoding non-multipart body: {str(e)}")
            body = email_body.get_payload(decode=True).decode('utf-8', errors='replace')
    
    # Replace any potentially problematic characters
    body = body.replace('\ufeff', '')
    
    return {
        "from": decode_header_safely(email_body.get("From", "Unknown")),
        "to": decode_header_safely(email_body.get("To", "Unknown")),
        "date": email_body.get("Date", "Unknown"),
        "subject": decode_header_safely(email_body.get("Subject", "No Subject")),
        "content": body
    }

async def search_emails_async(mail: imaplib.IMAP4_SSL, search_criteria: str) -> list[dict]:
    """Asynchronously search emails with timeout."""
    loop = asyncio.get_event_loop()
    try:
        logging.debug(f"Searching emails with criteria: {search_criteria}")
        _, messages = await loop.run_in_executor(None, lambda: mail.search(None, search_criteria))
        if not messages[0]:
            logging.debug("No emails found matching the search criteria")
            return []
            
        logging.debug(f"Found {len(messages[0].split())} emails matching the criteria")
        email_list = []
        for num in messages[0].split()[:MAX_EMAILS]:  # Limit to MAX_EMAILS
            _, msg_data = await loop.run_in_executor(None, lambda: mail.fetch(num, '(RFC822)'))
            email_list.append(format_email_summary(msg_data))
            
        return email_list
    except Exception as e:
        logging.error(f"Error searching emails: {str(e)}")
        raise Exception(f"Error searching emails: {str(e)}")

async def get_email_content_async(mail: imaplib.IMAP4_SSL, email_id: str) -> dict:
    """Asynchronously get full content of a specific email."""
    loop = asyncio.get_event_loop()
    try:
        logging.debug(f"Fetching email content for ID: {email_id}")
        _, msg_data = await loop.run_in_executor(None, lambda: mail.fetch(email_id, '(RFC822)'))
        logging.debug(f"Successfully fetched email content for ID: {email_id}")
        return format_email_content(msg_data)
    except Exception as e:
        logging.error(f"Error fetching email content: {str(e)}")
        raise Exception(f"Error fetching email content: {str(e)}")

async def count_emails_async(mail: imaplib.IMAP4_SSL, search_criteria: str) -> int:
    """Asynchronously count emails matching the search criteria."""
    loop = asyncio.get_event_loop()
    try:
        _, messages = await loop.run_in_executor(None, lambda: mail.search(None, search_criteria))
        return len(messages[0].split()) if messages[0] else 0
    except Exception as e:
        raise Exception(f"Error counting emails: {str(e)}")

async def send_email_async(
    to_addresses: list[str],
    subject: str,
    content: str,
    cc_addresses: list[str] | None = None
) -> None:
    """Asynchronously send an email."""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG["email"]
        msg['To'] = ', '.join(to_addresses)
        if cc_addresses:
            msg['Cc'] = ', '.join(cc_addresses)
        msg['Subject'] = subject
        msg['Date'] = email.utils.formatdate(localtime=True)
        msg['Message-ID'] = email.utils.make_msgid(domain=EMAIL_CONFIG["email"].split('@')[1])
        
        # Add body
        msg.attach(MIMEText(content, 'plain', 'utf-8'))
        
        # Connect to SMTP server and send email
        def send_sync():
            with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
                server.set_debuglevel(1)  # Enable debug output
                logging.debug(f"Connecting to {EMAIL_CONFIG['smtp_server']}:{EMAIL_CONFIG['smtp_port']}")
                
                # Start TLS
                logging.debug("Starting TLS")
                server.starttls()
                
                # Login
                logging.debug(f"Logging in as {EMAIL_CONFIG['email']}")
                server.login(EMAIL_CONFIG["email"], EMAIL_CONFIG["password"])
                
                # Send email
                all_recipients = to_addresses + (cc_addresses or [])
                logging.debug(f"Sending email to: {all_recipients}")
                result = server.send_message(msg, EMAIL_CONFIG["email"], all_recipients)
                
                if result:
                    # send_message returns a dict of failed recipients
                    raise Exception(f"Failed to send to some recipients: {result}")
                
                logging.debug("Email sent successfully")
        
        # Run the synchronous send function in the executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, send_sync)
        
        # After sending via SMTP, save a copy to the Sent folder via IMAP with timeout
        try:
            logging.debug("Attempting to save copy of email to Sent folder")
            
            # Prepare the message for IMAP append with delivery flags
            email_str = msg.as_string().encode('utf-8')
            
            # Create a task for the IMAP operations with a timeout
            async def save_to_sent_folder():
                try:
                    # Connect to IMAP server
                    mail = imaplib.IMAP4_SSL(EMAIL_CONFIG["imap_server"])
                    mail.login(EMAIL_CONFIG["email"], EMAIL_CONFIG["password"])
                    
                    # Check if this is Infomaniak (based on server name)
                    is_infomaniak = "infomaniak" in EMAIL_CONFIG["imap_server"].lower()
                    logging.debug(f"Server identified as Infomaniak: {is_infomaniak}")
                    
                    # Log all folders for debugging
                    _, folder_list = mail.list()
                    logging.debug("Available folders:")
                    for folder in folder_list:
                        folder_str = folder.decode('utf-8') if isinstance(folder, bytes) else str(folder)
                        logging.debug(f"  - {folder_str}")
                    
                    # Define potential sent folder names based on provider
                    sent_folder_candidates = []
                    
                    if is_infomaniak:
                        # Infomaniak-specific folders - expanded list based on common paths
                        sent_folder_candidates = [
                            'Sent',
                            'Sent Messages',
                            'Sent Items',
                            'INBOX.Sent',
                            'INBOX.Sent Messages',
                            'INBOX.Sent Items',
                            '"Sent Messages"',
                            '"Sent"',
                            '"Sent Items"',
                            'INBOX/"Sent Messages"',
                            'INBOX/"Sent"',
                            'INBOX/"Sent Items"',
                            # Infomaniak format with slashes
                            '/Sent Messages',
                            '/Sent',
                            '/Sent Items',
                        ]
                    else:
                        # General folder names for other providers
                        sent_folder_candidates = [
                            'Sent', 
                            '"Sent Messages"', 
                            'Sent Items', 
                            'SENT',
                            '"Sent Mail"',
                            'Sent Mail',
                            '"Sent Items"',
                            'OUTBOX',
                            'Outbox',
                            'Sent-Mail'
                        ]
                    
                    # Try direct matching with folder names first
                    sent_folder = None
                    for folder_name in sent_folder_candidates:
                        try:
                            logging.debug(f"Trying to select folder: {folder_name}")
                            status, _ = mail.select(folder_name, readonly=True)
                            if status == 'OK':
                                sent_folder = folder_name
                                mail.close()  # Close selected folder
                                logging.debug(f"Successfully matched sent folder: {sent_folder}")
                                break
                        except Exception as e:
                            logging.debug(f"Failed to select folder {folder_name}: {str(e)}")
                    
                    # If we still didn't find the sent folder, try parsing the folder list
                    if not sent_folder:
                        logging.debug("Trying to parse folder list to find sent folder")
                        for folder in folder_list:
                            folder_str = folder.decode('utf-8') if isinstance(folder, bytes) else str(folder)
                            
                            # Look for sent-related keywords in the folder string
                            if any(keyword in folder_str.lower() for keyword in ['sent', 'envoy']):
                                # Extract the folder name - usually in quotes
                                parts = folder_str.split('"')
                                if len(parts) > 2:
                                    sent_folder = parts[1].strip()
                                    logging.debug(f"Found sent folder from parsing: {sent_folder}")
                                    break
                    
                    # Last resort fallback
                    if not sent_folder:
                        if is_infomaniak:
                            # Default for Infomaniak based on common patterns
                            sent_folder = 'Sent' 
                            logging.debug(f"Using Infomaniak default sent folder: {sent_folder}")
                        else:
                            # Default for other providers
                            sent_folder = "Sent"
                            logging.debug(f"Using default sent folder: {sent_folder}")
                    
                    logging.debug(f"Final selected sent folder: {sent_folder}")
                    
                    # Try multiple approaches to save the message
                    success = False
                    errors = []
                    
                    # Try all these variants with proper error handling
                    append_attempts = [
                        # Standard approach
                        lambda: mail.append(sent_folder, '\\Seen', None, email_str),
                        # No flags
                        lambda: mail.append(sent_folder, '', None, email_str),
                        # With quotes if needed
                        lambda: mail.append(f'"{sent_folder}"', '\\Seen', None, email_str) 
                            if not sent_folder.startswith('"') and ' ' in sent_folder else None,
                        # INBOX prefix
                        lambda: mail.append(f'INBOX.{sent_folder}', '\\Seen', None, email_str) 
                            if not sent_folder.startswith('INBOX') else None,
                        # Try with Infomaniak format if applicable
                        lambda: mail.append(f'/INBOX/Sent', '\\Seen', None, email_str) 
                            if is_infomaniak else None,
                        lambda: mail.append(f'/Sent', '\\Seen', None, email_str) 
                            if is_infomaniak else None,
                        lambda: mail.append(f'/INBOX/Sent Messages', '\\Seen', None, email_str) 
                            if is_infomaniak else None,
                        lambda: mail.append(f'/INBOX/"Sent Messages"', '\\Seen', None, email_str) 
                            if is_infomaniak else None,
                    ]
                    
                    for i, attempt_fn in enumerate(append_attempts):
                        try:
                            result = attempt_fn()
                            if result is None:
                                # Skip this attempt as it wasn't applicable
                                continue
                                
                            if result and result[0] == 'OK':
                                logging.debug(f"Successfully saved email to Sent folder (attempt {i+1})")
                                success = True
                                break
                            elif result:
                                errors.append(f"Attempt {i+1} returned: {result}")
                        except Exception as e:
                            errors.append(f"Attempt {i+1} failed: {str(e)}")
                            logging.debug(f"Append attempt {i+1} failed: {str(e)}")
                    
                    if not success:
                        logging.error(f"All attempts to save to Sent folder failed: {', '.join(errors)}")
                        logging.error("The email was sent successfully, but could not be saved to the Sent folder")
                    
                    # Close the connection
                    mail.logout()
                    
                except Exception as e:
                    logging.error(f"Error in save_to_sent_folder task: {str(e)}")
            
            # Run the save operation with a 10-second timeout
            try:
                await asyncio.wait_for(save_to_sent_folder(), timeout=10.0)
            except asyncio.TimeoutError:
                logging.error("Timeout while saving to Sent folder - the email was sent but saving to Sent folder failed")
            
        except Exception as e:
            logging.error(f"Error saving to Sent folder: {str(e)}")
            # Don't raise the exception, as the email was successfully sent
            # This is just a secondary operation
        
        # Return without waiting for the save operation to complete
        return
            
    except Exception as e:
        logging.error(f"Error in send_email_async: {str(e)}")
        raise Exception(f"Failed to send email: {str(e)}")

async def ensure_mailbox_selected(mail: imaplib.IMAP4_SSL, mailbox: str = "inbox") -> None:
    """Ensure a mailbox is selected before performing IMAP operations."""
    loop = asyncio.get_event_loop()
    try:
        logging.debug(f"Selecting mailbox: {mailbox}")
        
        # First check if we need to reestablish connection
        try:
            status = mail.noop()[0]
            if status != 'OK':
                logging.warning("IMAP connection appears broken, reconnecting...")
                mail = imaplib.IMAP4_SSL(EMAIL_CONFIG["imap_server"])
                mail.login(EMAIL_CONFIG["email"], EMAIL_CONFIG["password"])
        except Exception as conn_err:
            logging.warning(f"IMAP connection error: {str(conn_err)}, reconnecting...")
            mail = imaplib.IMAP4_SSL(EMAIL_CONFIG["imap_server"])
            mail.login(EMAIL_CONFIG["email"], EMAIL_CONFIG["password"])
            
        # Now select the mailbox
        status, _ = await loop.run_in_executor(None, lambda: mail.select(mailbox))
        
        if status != 'OK':
            logging.error(f"Failed to select mailbox {mailbox}: {status}")
            # Try to select inbox as fallback
            if mailbox.lower() != 'inbox':
                logging.debug("Attempting to select INBOX as fallback")
                fallback_status, _ = await loop.run_in_executor(None, lambda: mail.select('INBOX'))
                if fallback_status != 'OK':
                    raise Exception(f"Could not select mailbox {mailbox} or INBOX")
                else:
                    logging.debug("Successfully selected INBOX as fallback")
            else:
                raise Exception(f"Could not select mailbox {mailbox}")
        else:
            logging.debug(f"Successfully selected mailbox: {mailbox}")
            
    except Exception as e:
        logging.error(f"Error selecting mailbox {mailbox}: {str(e)}")
        raise Exception(f"Error selecting mailbox: {str(e)}")

async def list_folders_async(mail: imaplib.IMAP4_SSL) -> list[str]:
    """Asynchronously list all available folders/mailboxes."""
    loop = asyncio.get_event_loop()
    try:
        logging.debug("Listing all available folders")
        # Get list of all folders
        _, folder_list = await loop.run_in_executor(None, lambda: mail.list())
        
        # Parse folder names
        folders = []
        for folder in folder_list:
            # Decode if bytes
            if isinstance(folder, bytes):
                folder = folder.decode('utf-8')
            
            # Extract folder name (format: b'(\\HasNoChildren) "/" "folder_name"')
            parts = folder.split(' "', 1)
            if len(parts) > 1:
                folder_name = parts[1].strip('"')
                folders.append(folder_name)
        
        logging.debug(f"Found {len(folders)} folders")
        return folders
    except Exception as e:
        logging.error(f"Error listing folders: {str(e)}")
        raise Exception(f"Error listing folders: {str(e)}")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="list-folders",
            description="List all available email folders/mailboxes in the email account",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="search-emails",
            description="Search emails within a date range and/or with specific keywords",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (optional)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (optional)",
                    },
                    "keyword": {
                        "type": "string",
                        "description": "Keyword to search in email subject and body (optional)",
                    },
                    "folder": {
                        "type": "string",
                        "description": "Folder/mailbox to search in (defaults to 'inbox')",
                    },
                },
            },
        ),
        types.Tool(
            name="get-email-content",
            description="Get the full content of a specific email by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "The ID of the email to retrieve",
                    },
                    "folder": {
                        "type": "string",
                        "description": "Folder/mailbox containing the email (defaults to 'inbox')",
                    },
                },
                "required": ["email_id"],
            },
        ),
        types.Tool(
            name="count-daily-emails",
            description="Count emails received for each day in a date range",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format",
                    },
                    "folder": {
                        "type": "string",
                        "description": "Folder/mailbox to count emails in (defaults to 'inbox')",
                    },
                },
                "required": ["start_date", "end_date"],
            },
        ),
        types.Tool(
            name="send-email",
            description="CONFIRMATION STEP: Actually send the email after user confirms the details. Before calling this, first show the email details to the user for confirmation. Required fields: recipients (to), subject, and content. Optional: CC recipients.",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of recipient email addresses (confirmed)",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Confirmed email subject",
                    },
                    "content": {
                        "type": "string",
                        "description": "Confirmed email content",
                    },
                    "cc": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of CC recipient email addresses (optional, confirmed)",
                    },
                },
                "required": ["to", "subject", "content"],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can search emails and return results.
    """
    if not arguments:
        arguments = {}
    
    try:
        if name == "send-email":
            to_addresses = arguments.get("to", [])
            subject = arguments.get("subject", "")
            content = arguments.get("content", "")
            cc_addresses = arguments.get("cc", [])
            
            if not to_addresses:
                return [types.TextContent(
                    type="text",
                    text="At least one recipient email address is required."
                )]
            
            try:
                logging.info("Attempting to send email")
                logging.info(f"To: {to_addresses}")
                logging.info(f"Subject: {subject}")
                logging.info(f"CC: {cc_addresses}")
                
                async with asyncio.timeout(SEARCH_TIMEOUT):
                    await send_email_async(to_addresses, subject, content, cc_addresses)
                    # Try checking the sent folder to confirm message was saved there
                    try:
                        mail = imaplib.IMAP4_SSL(EMAIL_CONFIG["imap_server"])
                        mail.login(EMAIL_CONFIG["email"], EMAIL_CONFIG["password"])
                        
                        # Try different variations of Sent folder names that might exist
                        sent_folder_options = [
                            'Sent', 
                            'Sent Messages', 
                            'INBOX.Sent',
                            '"Sent Messages"',
                            'Sent Items'
                        ]
                        
                        for folder in sent_folder_options:
                            try:
                                status, _ = mail.select(folder, readonly=True)
                                if status == 'OK':
                                    logging.info(f"Successfully found and selected sent folder: {folder}")
                                    # Check if there are any messages in this folder
                                    _, msg_count = mail.search(None, 'ALL')
                                    if msg_count[0]:
                                        count = len(msg_count[0].split())
                                        logging.info(f"Found {count} messages in sent folder '{folder}'")
                                    else:
                                        logging.info(f"No messages found in sent folder '{folder}'")
                                    mail.close()
                                    break
                            except Exception as e:
                                logging.debug(f"Could not select folder {folder}: {str(e)}")
                        
                        mail.logout()
                    except Exception as check_err:
                        logging.error(f"Error checking sent folder: {str(check_err)}")
                    
                    return [types.TextContent(
                        type="text",
                        text="Email sent successfully! The email was sent to the recipient(s). A copy should appear in your Sent folder, though this may depend on your email provider's configuration. If it doesn't appear in the Sent folder, the email was still delivered to the recipient(s). Check email_client.log for detailed logs."
                    )]
            except asyncio.TimeoutError:
                logging.error("Operation timed out while sending email")
                return [types.TextContent(
                    type="text",
                    text="Operation timed out while sending email."
                )]
            except Exception as e:
                error_msg = str(e)
                logging.error(f"Failed to send email: {error_msg}")
                return [types.TextContent(
                    type="text",
                    text=f"Failed to send email: {error_msg}\n\nPlease check:\n1. Email and password are correct in .env\n2. SMTP settings are correct\n3. Less secure app access is enabled (for Gmail)\n4. Using App Password if 2FA is enabled"
                )]
        
        # Connect to IMAP server using predefined credentials
        mail = imaplib.IMAP4_SSL(EMAIL_CONFIG["imap_server"])
        mail.login(EMAIL_CONFIG["email"], EMAIL_CONFIG["password"])
        
        if name == "list-folders":
            try:
                async with asyncio.timeout(SEARCH_TIMEOUT):
                    folders = await list_folders_async(mail)
                    
                if not folders:
                    return [types.TextContent(
                        type="text",
                        text="No folders found in the email account."
                    )]
                
                # Format the results as a list
                result_text = "Available email folders:\n\n"
                for folder in folders:
                    # Sanitize folder name to handle potential encoding issues
                    try:
                        folder = folder.encode('ascii', errors='replace').decode('ascii')
                    except Exception as e:
                        logging.warning(f"Error sanitizing folder name: {str(e)}")
                        folder = str(folder).replace('\ufeff', '')
                    
                    result_text += f"- {folder}\n"
                
                return [types.TextContent(
                    type="text",
                    text=result_text
                )]
                
            except asyncio.TimeoutError:
                return [types.TextContent(
                    type="text",
                    text="Operation timed out while listing folders."
                )]
                
        elif name == "search-emails":
            # Get folder parameter
            folder = arguments.get("folder", "inbox")
            
            # Select the appropriate mailbox
            await ensure_mailbox_selected(mail, folder)
            
            # Get optional parameters
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            keyword = arguments.get("keyword")
            
            # If no dates provided, default to last 7 days
            if not start_date:
                start_date = datetime.now() - timedelta(days=7)
                start_date = start_date.strftime("%d-%b-%Y")
            else:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d-%b-%Y")
                
            # Always convert end_date to datetime object for consistent handling
            if not end_date:
                end_date_obj = datetime.now()
                end_date = end_date_obj.strftime("%d-%b-%Y")
            else:
                # Convert end_date to datetime object
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                end_date = end_date_obj.strftime("%d-%b-%Y")
            
            # Build search criteria
            if start_date == end_date:
                # If searching for a single day
                search_criteria = f'ON "{start_date}"'
            else:
                # Calculate next day using the already converted end_date_obj
                next_day = (end_date_obj + timedelta(days=1)).strftime("%d-%b-%Y")
                search_criteria = f'SINCE "{start_date}" BEFORE "{next_day}"'
                
            if keyword:
                # Fix: Properly combine keyword search with date criteria
                keyword_criteria = f'(OR SUBJECT "{keyword}" BODY "{keyword}")'
                search_criteria = f'({keyword_criteria} {search_criteria})'
            
            logging.debug(f"Search criteria: {search_criteria}")  # Add debug logging
            
            try:
                async with asyncio.timeout(SEARCH_TIMEOUT):
                    email_list = await search_emails_async(mail, search_criteria)
                    
                if not email_list:
                    return [types.TextContent(
                        type="text",
                        text=f"No emails found in '{folder}' matching the criteria."
                    )]
                
                # Format the results as a table
                result_text = f"Found emails in '{folder}':\n\n"
                result_text += "ID | From | Date | Subject\n"
                result_text += "-" * 80 + "\n"
                
                for email in email_list:
                    # Sanitize the result to ensure no encoding issues
                    for key in ['from', 'subject']:
                        if key in email:
                            email[key] = str(email[key]).replace('\ufeff', '')
                    
                    result_text += f"{email['id']} | {email['from']} | {email['date']} | {email['subject']}\n"
                
                result_text += f"\nUse get-email-content with an email ID and folder='{folder}' to view the full content of a specific email."
                
                # Ensure the result text doesn't have any problematic characters
                result_text = result_text.encode('utf-8', errors='replace').decode('utf-8')
                
                return [types.TextContent(
                    type="text",
                    text=result_text
                )]
                
            except asyncio.TimeoutError:
                return [types.TextContent(
                    type="text",
                    text="Search operation timed out. Please try with a more specific search criteria."
                )]
                
        elif name == "get-email-content":
            email_id = arguments.get("email_id")
            folder = arguments.get("folder", "inbox")
            
            if not email_id:
                return [types.TextContent(
                    type="text",
                    text="Email ID is required."
                )]
            
            try:
                # Select specified mailbox before fetching email content
                await ensure_mailbox_selected(mail, folder)
                
                async with asyncio.timeout(SEARCH_TIMEOUT):
                    email_content = await get_email_content_async(mail, email_id)
                    
                # Sanitize the email content before returning
                for key in ['from', 'to', 'subject', 'content']:
                    if key in email_content:
                        email_content[key] = str(email_content[key]).replace('\ufeff', '')
                
                result_text = (
                    f"From: {email_content['from']}\n"
                    f"To: {email_content['to']}\n"
                    f"Date: {email_content['date']}\n"
                    f"Subject: {email_content['subject']}\n"
                    f"\nContent:\n{email_content['content']}"
                )
                
                # Additional sanitization
                result_text = result_text.encode('utf-8', errors='replace').decode('utf-8')
                
                return [types.TextContent(
                    type="text",
                    text=result_text
                )]
                
            except asyncio.TimeoutError:
                return [types.TextContent(
                    type="text",
                    text="Operation timed out while fetching email content."
                )]
                
        elif name == "count-daily-emails":
            start_date = datetime.strptime(arguments["start_date"], "%Y-%m-%d")
            end_date = datetime.strptime(arguments["end_date"], "%Y-%m-%d")
            folder = arguments.get("folder", "inbox")
            
            # Select specified mailbox before counting emails
            await ensure_mailbox_selected(mail, folder)
            
            result_text = f"Daily email counts in '{folder}':\n\n"
            result_text += "Date | Count\n"
            result_text += "-" * 30 + "\n"
            
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime("%d-%b-%Y")
                search_criteria = f'(ON "{date_str}")'
                
                try:
                    async with asyncio.timeout(SEARCH_TIMEOUT):
                        count = await count_emails_async(mail, search_criteria)
                        result_text += f"{current_date.strftime('%Y-%m-%d')} | {count}\n"
                except asyncio.TimeoutError:
                    result_text += f"{current_date.strftime('%Y-%m-%d')} | Timeout\n"
                
                current_date += timedelta(days=1)
            
            return [types.TextContent(
                type="text",
                text=result_text
            )]
                
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}\n\nIf you see a state error, please try again. If the problem persists, check if:\n1. Your email credentials are correct\n2. Your email provider allows IMAP/SMTP access\n3. The server settings are correct"
        )]
    finally:
        try:
            mail.close()
            mail.logout()
        except:
            pass

async def main():
    # Set console encoding to UTF-8 to handle special characters
    if os.name == 'nt':  # Windows
        try:
            # Try to set console encoding to UTF-8 on Windows
            import sys
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
            # Set console code page to UTF-8
            os.system('chcp 65001 > nul')
            logging.info("Successfully set console encoding to UTF-8")
        except Exception as e:
            logging.error(f"Error setting console encoding: {str(e)}")

    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="email",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())

