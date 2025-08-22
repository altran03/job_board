"""
Gmail OAuth2 Authentication Module
"""
import os
import json
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Gmail API scopes needed for reading emails
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'  # For marking emails as read
]

# Fix paths for Docker container
CREDENTIALS_FILE = Path('/app/credentials.json')  # In Docker container
TOKEN_FILE = Path('/app/token.json')  # In Docker container


def get_gmail_service() -> Optional[object]:
    """
    Authenticate and return Gmail API service object.
    Returns None if authentication fails.
    """
    creds = None
    
    # Load existing token if available
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    
    # If no valid credentials available, let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                creds = None
        
        if not creds:
            if not CREDENTIALS_FILE.exists():
                print(f"Credentials file not found at {CREDENTIALS_FILE}")
                print("Please download credentials.json from Google Cloud Console")
                print("and place it in the backend/ directory")
                return None
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_FILE), SCOPES
                )
                # Use headless mode for Docker environment
                creds = flow.run_local_server(port=0, open_browser=False)
                
                # Save credentials for next run
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
                    
            except Exception as e:
                print(f"Error during OAuth flow: {e}")
                print("Try running authentication locally instead of in Docker")
                return None
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except HttpError as error:
        print(f"Error building Gmail service: {error}")
        return None


def test_gmail_connection() -> bool:
    """
    Test Gmail API connection by fetching user profile.
    Returns True if successful, False otherwise.
    """
    service = get_gmail_service()
    if not service:
        return False
    
    try:
        profile = service.users().getProfile(userId='me').execute()
        print(f"Connected to Gmail as: {profile['emailAddress']}")
        return True
    except HttpError as error:
        print(f"Error testing Gmail connection: {error}")
        return False


if __name__ == "__main__":
    # Test authentication when run directly
    if test_gmail_connection():
        print("Gmail authentication successful!")
    else:
        print("Gmail authentication failed!")
