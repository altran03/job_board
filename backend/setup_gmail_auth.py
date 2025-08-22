#!/usr/bin/env python3
"""
Standalone Gmail OAuth2 Authentication Setup
Run this locally (not in Docker) to set up Gmail authentication.
"""
import os
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

# Local paths (not Docker paths)
CREDENTIALS_FILE = Path('credentials.json')
TOKEN_FILE = Path('token.json')


def setup_gmail_auth():
    """Set up Gmail OAuth2 authentication locally."""
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
                return False
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_FILE), SCOPES
                )
                print("Opening browser for OAuth authentication...")
                creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
                print(f"Token saved to {TOKEN_FILE}")
                    
            except Exception as e:
                print(f"Error during OAuth flow: {e}")
                return False
    
    # Test the connection
    try:
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        print(f"✅ Successfully authenticated with Gmail as: {profile['emailAddress']}")
        return True
    except HttpError as error:
        print(f"❌ Error testing Gmail connection: {error}")
        return False


if __name__ == "__main__":
    print("Setting up Gmail OAuth2 authentication...")
    if setup_gmail_auth():
        print("🎉 Gmail authentication setup complete!")
        print("You can now run the Docker containers and use Gmail features.")
    else:
        print("❌ Gmail authentication setup failed!")
