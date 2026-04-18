#!/usr/bin/env python3
"""
Authentication setup script for Tiller MCP Server.

This script handles the OAuth2 authentication flow for Google Sheets API access.
Run this once to authenticate and generate the token.json file.

Usage:
    python auth/auth_setup.py
"""

import os
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    # Load .env from project root (parent of auth directory)
    project_root = Path(__file__).parent.parent
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Loaded environment variables from {env_path}")
except ImportError:
    pass  # python-dotenv not installed, will use system environment variables

# Define the scopes for Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(SCRIPT_DIR, 'credentials.json')
TOKEN_PATH = os.path.join(SCRIPT_DIR, 'token.json')


def authenticate_google_sheets():
    """
    Authenticate with Google Sheets API and save credentials.

    Returns:
        Google Sheets API service object
    """
    creds = None

    # Check if we have saved credentials
    if os.path.exists(TOKEN_PATH):
        print(f"Found existing token at {TOKEN_PATH}")
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # If no valid credentials, let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Token expired, refreshing...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Token refresh failed ({e}), deleting token and re-authenticating...")
                os.remove(TOKEN_PATH)
                creds = None
        if not creds:
            if not os.path.exists(CREDENTIALS_PATH):
                print(f"ERROR: credentials.json not found at {CREDENTIALS_PATH}")
                print("\nPlease follow these steps:")
                print("1. Go to https://console.cloud.google.com")
                print("2. Create a project and enable Google Sheets API")
                print("3. Create OAuth 2.0 credentials")
                print("4. Download credentials.json to auth/ directory")
                return None

            print(f"Starting authentication flow using {CREDENTIALS_PATH}")
            print("A browser window will open for authorization...")
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        print(f"Saving credentials to {TOKEN_PATH}")
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
        print("✓ Credentials saved successfully")
    else:
        print("✓ Existing credentials are valid")

    return build('sheets', 'v4', credentials=creds)


def test_connection(service, spreadsheet_id=None):
    """
    Test the connection by fetching spreadsheet metadata.

    Args:
        service: Google Sheets API service object
        spreadsheet_id: Optional spreadsheet ID to test with
    """
    if not spreadsheet_id:
        print("\nNo spreadsheet ID provided. Skipping connection test.")
        print("To test with your Tiller spreadsheet, set TILLER_SHEET_ID environment variable")
        return

    try:
        print(f"\nTesting connection to spreadsheet: {spreadsheet_id}")
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        print(f"✓ Successfully connected to: {spreadsheet['properties']['title']}")
        print(f"\nAvailable sheets:")
        for sheet in spreadsheet['sheets']:
            props = sheet['properties']
            print(f"  - {props['title']} ({props['gridProperties']['rowCount']} rows)")
    except HttpError as error:
        print(f"✗ Error testing connection: {error}")


def main():
    """Main authentication setup flow."""
    print("=" * 60)
    print("Tiller MCP Server - Authentication Setup")
    print("=" * 60)
    print()

    # Authenticate
    service = authenticate_google_sheets()

    if not service:
        print("\n✗ Authentication failed")
        return 1

    print("\n✓ Authentication successful!")

    # Test connection if TILLER_SHEET_ID is set
    spreadsheet_id = os.environ.get('TILLER_SHEET_ID')
    test_connection(service, spreadsheet_id)

    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print("\nYou can now use the Tiller MCP server.")
    print(f"Token saved to: {TOKEN_PATH}")
    print("\nThe token will automatically refresh when needed.")

    return 0


if __name__ == "__main__":
    exit(main())
