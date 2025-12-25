"""
Google Sheets API client for Tiller Money data access.

Handles authentication, token refresh, and sheet range queries.
"""

import os
from pathlib import Path
from typing import List, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)


class SheetsClientError(Exception):
    """Custom exception for SheetsClient errors."""
    pass


class SheetsClient:
    """Client for interacting with Tiller Google Sheets."""

    # Define scopes needed for Google Sheets access
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    def __init__(self, spreadsheet_id: str):
        """
        Initialize the SheetsClient.

        Args:
            spreadsheet_id: The Google Sheets spreadsheet ID

        Raises:
            SheetsClientError: If spreadsheet_id is not provided
        """
        if not spreadsheet_id:
            raise SheetsClientError("spreadsheet_id is required")

        self.spreadsheet_id = spreadsheet_id
        self._service = None
        self._credentials = None

    def _get_credentials_path(self) -> Path:
        """
        Get the path to token.json.

        Returns:
            Path to token.json in the auth directory
        """
        # Navigate from src/tiller_mcp_server/ to project root, then to auth/token.json
        project_root = Path(__file__).parent.parent.parent
        return project_root / 'auth' / 'token.json'

    def _get_credentials(self) -> Credentials:
        """
        Load and refresh Google credentials.

        Uses the OAuth2 token created by auth/auth_setup.py.
        Automatically refreshes expired credentials.

        Returns:
            Valid Google credentials

        Raises:
            SheetsClientError: If credentials cannot be loaded or refreshed
        """
        if self._credentials and self._credentials.valid:
            return self._credentials

        token_path = self._get_credentials_path()

        if not token_path.exists():
            raise SheetsClientError(
                f"Token file not found at {token_path}. "
                "Run 'python auth/auth_setup.py' to authenticate."
            )

        try:
            # Load credentials from token.json
            creds = Credentials.from_authorized_user_file(str(token_path), self.SCOPES)

            # Refresh if expired
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    logger.info("Refreshing expired credentials")
                    creds.refresh(Request())

                    # Save refreshed token back to file
                    with open(token_path, 'w') as token:
                        token.write(creds.to_json())
                    logger.info("Saved refreshed credentials")
                else:
                    raise SheetsClientError(
                        "Credentials are invalid and cannot be refreshed. "
                        "Run 'python auth/auth_setup.py' to re-authenticate."
                    )

            self._credentials = creds
            return creds

        except Exception as e:
            raise SheetsClientError(f"Failed to load credentials: {e}")

    def _get_service(self):
        """
        Get or create the Google Sheets API service.

        Returns:
            Google Sheets API service object (Resource)
        """
        if self._service is None:
            creds = self._get_credentials()
            self._service = build('sheets', 'v4', credentials=creds)
        return self._service

    def get_sheet_range(self, range_name: str) -> List[List[str]]:
        """
        Read a range from the spreadsheet.

        Args:
            range_name: A1 notation range (e.g., "Accounts!A1:Q" or "Transactions!A2:P100")

        Returns:
            List of rows, where each row is a list of cell values (strings)

        Raises:
            SheetsClientError: If the API call fails
        """
        try:
            service = self._get_service()
            result = service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])
            logger.debug(f"Retrieved {len(values)} rows from {range_name}")
            return values

        except HttpError as error:
            logger.error(f"Google Sheets API error: {error}")
            raise SheetsClientError(f"Failed to read range {range_name}: {error}")
        except Exception as error:
            logger.error(f"Unexpected error reading sheet: {error}")
            raise SheetsClientError(f"Unexpected error: {error}")

    def get_accounts_raw(self) -> List[List[str]]:
        """
        Get raw account data from the Accounts sheet.

        Returns:
            List of account rows (excluding header row)
        """
        # Fetch from row 2 to end (skip header), columns A-D (4 columns)
        values = self.get_sheet_range('Accounts!A2:D')

        return values if values else []

    def get_transactions_raw(self, limit: Optional[int] = None) -> List[List[str]]:
        """
        Get raw transaction data from the Transactions sheet.

        Args:
            limit: Optional limit on number of rows to fetch

        Returns:
            List of transaction rows (excluding header row)
        """
        if limit:
            # Fetch limited rows: A2:P{limit+1} (+1 for 0-based to 1-based)
            range_name = f'Transactions!A2:P{limit + 1}'
        else:
            # Fetch all rows: A2:P (dynamic, reads until end)
            range_name = 'Transactions!A2:P'

        values = self.get_sheet_range(range_name)
        return values if values else []

    def get_categories_raw(self, include_monthly_budgets: bool = False) -> List[List[str]]:
        """
        Get raw category data from the Categories sheet.

        Args:
            include_monthly_budgets: If True, read columns A-P to include monthly budgets.
                                    If False, read only A-C (default, backward compatible).

        Returns:
            List of category rows (excluding header row)
        """
        if include_monthly_budgets:
            # Read full range with monthly budget columns (A-P)
            values = self.get_sheet_range('Categories!A2:P')
        else:
            # Default: read only category, group, type (A-C)
            values = self.get_sheet_range('Categories!A2:C')

        return values if values else []


# Global singleton instance
_sheets_client_instance: Optional[SheetsClient] = None


def get_sheets_client() -> SheetsClient:
    """
    Get or create the global SheetsClient instance.

    Reads TILLER_SHEET_ID from environment variables.

    Returns:
        Initialized SheetsClient

    Raises:
        SheetsClientError: If TILLER_SHEET_ID not set
    """
    global _sheets_client_instance

    if _sheets_client_instance is None:
        spreadsheet_id = os.environ.get('TILLER_SHEET_ID')
        if not spreadsheet_id:
            raise SheetsClientError(
                "TILLER_SHEET_ID environment variable not set. "
                "Set it in Claude Desktop config or .env file for testing."
            )
        _sheets_client_instance = SheetsClient(spreadsheet_id)

    return _sheets_client_instance
