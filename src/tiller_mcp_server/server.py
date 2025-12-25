"""
Tiller Money MCP Server

Provides Claude Desktop with read-only access to personal finance data
stored in Tiller Money Google Sheets.
"""

import json
import logging
import os
from typing import Optional
from dotenv import load_dotenv

# MCP imports
from mcp.server.fastmcp import FastMCP

# Local imports - handle both direct execution and module import
try:
    from .sheets_client import get_sheets_client, SheetsClientError
    from .tiller_schema import Account, Transaction, Category
except ImportError:
    # Running as script directly, not as module
    import sys
    from pathlib import Path
    # Add src directory to path
    src_path = Path(__file__).parent.parent
    sys.path.insert(0, str(src_path))
    from tiller_mcp_server.sheets_client import get_sheets_client, SheetsClientError
    from tiller_mcp_server.tiller_schema import Account, Transaction, Category

# Load environment variables from .env file (for local testing)
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
try:
    mcp = FastMCP("Tiller MCP Server")
    print("DEBUG: FastMCP server initialized successfully", file=sys.stderr)
except Exception as e:
    print(f"DEBUG ERROR: Failed to initialize FastMCP: {e}", file=sys.stderr)
    raise


@mcp.tool()
def get_accounts(
    account_type: Optional[str] = None
) -> str:
    """
    Get all active financial accounts from Tiller Money.

    This tool retrieves basic account information.
    Hidden/closed accounts are automatically excluded and cannot be accessed.

    Args:
        account_type: Optional filter by account type. Case-insensitive.
                     Examples: "Credit Cards", "Retirement", "Savings"
                     If not specified, returns all active account types.

    Returns:
        JSON string containing array of account objects. Each account includes:
        - display_name: Account name with masked number (e.g., "CREDIT CARD (-XXXX)")
        - account_type: Type/group of account (e.g., "Credit Cards", "Retirement")
        - account_number: Last 4 digits extracted from display_name (e.g., "-XXXX")
        - is_hidden: Always false (hidden accounts are excluded)

    Examples:
        get_accounts()  # Returns all active accounts
        get_accounts(account_type="Credit Cards")  # Returns only credit card accounts
        get_accounts(account_type="retirement")  # Case-insensitive, returns retirement accounts
    """
    try:
        # Get sheets client (singleton)
        logger.info("Fetching accounts from Tiller sheet")
        client = get_sheets_client()

        # Fetch raw account data
        raw_accounts = client.get_accounts_raw()
        logger.info(f"Retrieved {len(raw_accounts)} raw account rows")

        # Parse into Account objects
        accounts = []
        for row in raw_accounts:
            try:
                account = Account.from_sheet_row(row)

                # ALWAYS filter out hidden accounts (user requirement)
                if account.is_hidden:
                    continue

                # Apply optional account_type filter
                if account_type and account.account_type.upper() != account_type.upper():
                    continue

                accounts.append(account)

            except Exception as e:
                logger.warning(f"Failed to parse account row: {e}")
                continue

        logger.info(f"Parsed {len(accounts)} active accounts after filtering")

        # Convert to JSON-serializable format
        account_list = []
        for account in accounts:
            account_dict = {
                "display_name": account.display_name,
                "account_type": account.account_type,
                "account_number": account.account_number,
                "is_hidden": account.is_hidden  # Always false in results
            }
            account_list.append(account_dict)

        # Return formatted JSON
        return json.dumps(account_list, indent=2)

    except SheetsClientError as e:
        logger.error(f"Sheets client error: {e}")
        return json.dumps({
            "error": "Failed to access Tiller spreadsheet",
            "message": str(e),
            "help": "Ensure TILLER_SHEET_ID is set and auth/token.json exists"
        }, indent=2)

    except Exception as e:
        logger.error(f"Unexpected error in get_accounts: {e}", exc_info=True)
        return json.dumps({
            "error": "Unexpected error occurred",
            "message": str(e)
        }, indent=2)


@mcp.tool()
def get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    account: Optional[str] = None,
    category: Optional[str] = None,
    min_amount: Optional[str] = None,
    max_amount: Optional[str] = None,
    description: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0
) -> str:
    """
    Get transactions from Tiller Money with optional filtering.

    Args:
        start_date: Filter by date >= this (MM/DD/YYYY format). Optional.
        end_date: Filter by date <= this (MM/DD/YYYY format). Optional.
        account: Filter by account number (partial match, case-insensitive). Optional.
                 Example: "XXXX" or "-XXXX" to match account ending in XXXX.
        category: Filter by category name (partial match, case-insensitive). Optional.
                  Example: "Groceries" matches "Groceries & Food"
        min_amount: Filter transactions >= this amount (inclusive). Optional.
                    Supports negative values (expenses are negative).
                    Example: "0" for income only, "-100" for expenses >= -$100
        max_amount: Filter transactions <= this amount (inclusive). Optional.
                    Supports negative values (expenses are negative).
                    Example: "-100" for large expenses, "50" for small transactions
        description: Search transaction descriptions (partial match, case-insensitive). Optional.
                     Searches both Description and Full Description fields.
                     Example: "starbucks" finds all Starbucks transactions
        limit: Maximum transactions to return (default 100)
        offset: Skip first N transactions (for pagination, default 0)

    Returns:
        JSON array of transaction objects sorted by date (most recent first).
        Each transaction includes: date, description, category, amount, amount_str,
        account, account_number, institution, month, week, transaction_id,
        check_number, and full_description.

    Examples:
        get_transactions()  # Get 100 most recent transactions
        get_transactions(limit=20)  # Get 20 most recent
        get_transactions(start_date="12/01/2025", end_date="12/20/2025")
        get_transactions(account="XXXX", limit=50)  # All transactions for account -XXXX
        get_transactions(limit=100, offset=100)  # Pagination: next 100

        # Advanced filtering examples
        get_transactions(category="Groceries", min_amount="100")  # Grocery transactions over $100
        get_transactions(
            start_date="12/01/2025",
            end_date="12/31/2025",
            category="Dining",
            min_amount="20",
            max_amount="50"
        )  # Dining expenses between $20-$50 in December
        get_transactions(min_amount="0")  # List all income transactions
        get_transactions(description="starbucks")  # Find all Starbucks purchases
        get_transactions(category="Shopping", max_amount="-200")  # Large shopping expenses
    """
    import re

    try:
        # Validate date format if provided
        date_pattern = re.compile(r'^\d{2}/\d{2}/\d{4}$')
        if start_date and not date_pattern.match(start_date):
            return json.dumps({
                "error": "Invalid date format",
                "message": "start_date must be in MM/DD/YYYY format",
                "provided": start_date
            }, indent=2)

        if end_date and not date_pattern.match(end_date):
            return json.dumps({
                "error": "Invalid date format",
                "message": "end_date must be in MM/DD/YYYY format",
                "provided": end_date
            }, indent=2)

        # Validate date range
        if start_date and end_date and start_date > end_date:
            return json.dumps({
                "error": "Invalid date range",
                "message": "start_date must be <= end_date",
                "start_date": start_date,
                "end_date": end_date
            }, indent=2)

        # Validate and parse amount parameters
        parsed_min_amount = None
        parsed_max_amount = None

        if min_amount is not None:
            try:
                parsed_min_amount = float(min_amount)
            except ValueError:
                return json.dumps({
                    "error": "Invalid min_amount format",
                    "message": f"min_amount must be a valid number, got: {min_amount}",
                    "examples": ["100", "-50.25", "0"]
                }, indent=2)

        if max_amount is not None:
            try:
                parsed_max_amount = float(max_amount)
            except ValueError:
                return json.dumps({
                    "error": "Invalid max_amount format",
                    "message": f"max_amount must be a valid number, got: {max_amount}",
                    "examples": ["500", "-10.00", "0"]
                }, indent=2)

        # Validate amount range
        if parsed_min_amount is not None and parsed_max_amount is not None:
            if parsed_min_amount > parsed_max_amount:
                return json.dumps({
                    "error": "Invalid amount range",
                    "message": f"min_amount ({min_amount}) cannot be greater than max_amount ({max_amount})"
                }, indent=2)

        logger.info(
            f"Fetching transactions with filters: "
            f"start_date={start_date}, end_date={end_date}, "
            f"account={account}, category={category}, "
            f"min_amount={min_amount}, max_amount={max_amount}, "
            f"description={description}, "
            f"limit={limit}, offset={offset}"
        )
        client = get_sheets_client()

        # Fetch all transactions
        raw_transactions = client.get_transactions_raw()
        logger.info(f"Retrieved {len(raw_transactions)} raw transaction rows")

        # Helper function to convert MM/DD/YYYY to YYYYMMDD for comparison
        def date_to_sortable(date_str):
            try:
                parts = date_str.split('/')
                if len(parts) == 3:
                    return f"{parts[2]}{parts[0].zfill(2)}{parts[1].zfill(2)}"
                return date_str
            except:
                return date_str

        # Parse into Transaction objects
        transactions = []
        for row in raw_transactions:
            try:
                transaction = Transaction.from_sheet_row(row)

                # Apply date filters (convert to sortable format for comparison)
                if start_date:
                    if date_to_sortable(transaction.date) < date_to_sortable(start_date):
                        continue
                if end_date:
                    if date_to_sortable(transaction.date) > date_to_sortable(end_date):
                        continue

                # Apply account filter (case-insensitive partial match on account_number)
                if account and account.upper() not in transaction.account_number.upper():
                    continue

                # Filter by category (partial match, case-insensitive)
                if category and category.upper() not in transaction.category.upper():
                    continue

                # Filter by minimum amount (inclusive)
                if parsed_min_amount is not None and transaction.amount < parsed_min_amount:
                    continue

                # Filter by maximum amount (inclusive)
                if parsed_max_amount is not None and transaction.amount > parsed_max_amount:
                    continue

                # Search description (both fields, partial match, case-insensitive)
                if description:
                    desc_upper = description.upper()
                    if desc_upper not in transaction.description.upper() and desc_upper not in transaction.full_description.upper():
                        continue

                transactions.append(transaction)

            except Exception as e:
                logger.warning(f"Failed to parse transaction row: {e}")
                continue

        logger.info(f"Parsed {len(transactions)} transactions after filtering")

        # Sort by date descending (most recent first)
        # Convert MM/DD/YYYY to YYYYMMDD for proper string sorting
        def date_sort_key(t):
            try:
                parts = t.date.split('/')
                if len(parts) == 3:
                    # Convert MM/DD/YYYY to YYYYMMDD with zero-padding
                    month = parts[0].zfill(2)
                    day = parts[1].zfill(2)
                    year = parts[2]
                    return f"{year}{month}{day}"
                return t.date
            except:
                return t.date

        transactions.sort(key=date_sort_key, reverse=True)

        # Apply pagination
        paginated = transactions[offset:offset+limit]
        logger.info(f"Returning {len(paginated)} transactions after pagination")

        # Convert to JSON-serializable format
        transaction_list = []
        for t in paginated:
            transaction_dict = {
                "date": t.date,
                "description": t.description,
                "category": t.category,
                "amount": t.amount,
                "amount_str": t.amount_str,
                "account": t.account,
                "account_number": t.account_number,
                "institution": t.institution,
                "month": t.month,
                "week": t.week,
                "transaction_id": t.transaction_id,
                "check_number": t.check_number,
                "full_description": t.full_description
            }
            transaction_list.append(transaction_dict)

        return json.dumps(transaction_list, indent=2)

    except SheetsClientError as e:
        logger.error(f"Sheets client error: {e}")
        return json.dumps({
            "error": "Failed to access Tiller spreadsheet",
            "message": str(e),
            "help": "Ensure TILLER_SHEET_ID is set and auth/token.json exists"
        }, indent=2)

    except Exception as e:
        logger.error(f"Unexpected error in get_transactions: {e}", exc_info=True)
        return json.dumps({
            "error": "Unexpected error occurred",
            "message": str(e)
        }, indent=2)


@mcp.tool()
def get_transaction_details(
    transaction_id: str
) -> str:
    """
    Get full details for a single transaction by ID.

    Args:
        transaction_id: Required 24-character hexadecimal transaction ID

    Returns:
        JSON object with complete transaction details, or error if not found.

    Examples:
        get_transaction_details(transaction_id="123abc456def789012345678")
    """
    import re

    try:
        # Validate transaction_id format
        if not re.match(r'^[a-f0-9]{24}$', transaction_id):
            return json.dumps({
                "error": "Invalid transaction_id format",
                "message": "transaction_id must be a 24-character hexadecimal string",
                "provided": transaction_id,
                "example": "123abc456def789012345678"
            }, indent=2)

        logger.info(f"Fetching transaction details for ID: {transaction_id}")
        client = get_sheets_client()

        # Fetch all transactions
        raw_transactions = client.get_transactions_raw()
        logger.info(f"Retrieved {len(raw_transactions)} raw transaction rows")

        # Search for matching transaction
        for row in raw_transactions:
            try:
                transaction = Transaction.from_sheet_row(row)

                if transaction.transaction_id == transaction_id:
                    # Found it! Return complete details
                    transaction_dict = {
                        "date": transaction.date,
                        "description": transaction.description,
                        "category": transaction.category,
                        "amount": transaction.amount,
                        "amount_str": transaction.amount_str,
                        "account": transaction.account,
                        "account_number": transaction.account_number,
                        "institution": transaction.institution,
                        "month": transaction.month,
                        "week": transaction.week,
                        "transaction_id": transaction.transaction_id,
                        "check_number": transaction.check_number,
                        "full_description": transaction.full_description
                    }
                    logger.info(f"Found transaction: {transaction.description}")
                    return json.dumps(transaction_dict, indent=2)

            except Exception as e:
                logger.warning(f"Failed to parse transaction row: {e}")
                continue

        # Not found
        logger.warning(f"Transaction not found: {transaction_id}")
        return json.dumps({
            "error": "Transaction not found",
            "transaction_id": transaction_id
        }, indent=2)

    except SheetsClientError as e:
        logger.error(f"Sheets client error: {e}")
        return json.dumps({
            "error": "Failed to access Tiller spreadsheet",
            "message": str(e),
            "help": "Ensure TILLER_SHEET_ID is set and auth/token.json exists"
        }, indent=2)

    except Exception as e:
        logger.error(f"Unexpected error in get_transaction_details: {e}", exc_info=True)
        return json.dumps({
            "error": "Unexpected error occurred",
            "message": str(e)
        }, indent=2)


@mcp.tool()
def get_categories(
    category_type: Optional[str] = None,
    group: Optional[str] = None,
    include_monthly_budgets: bool = False
) -> str:
    """
    Get all categories from Tiller Money with optional filtering and budget data.

    This tool retrieves category definitions and optionally includes monthly budget
    amounts for each category. Use this with get_transactions() to perform budget
    vs. actual analysis.

    Args:
        category_type: Optional filter by category type. Case-insensitive.
                      Valid values: "Expense", "Income", "Transfer"
                      If not specified, returns all category types.
        group: Optional filter by category group (partial match, case-insensitive).
               Examples: "Living", "Fun", "Primary Income", "Expense"
               If not specified, returns all groups.
        include_monthly_budgets: If True, include monthly budget amounts for each category.
                                Default: False (backward compatible).

    Returns:
        JSON string containing array of category objects. Each category includes:
        - category: Category name (unique identifier)
        - group: Category group/classification
        - type: Category type (Expense/Income/Transfer)
        - monthly_budgets: (if include_monthly_budgets=True) Dictionary with months as keys:
          - Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec
          - Each value contains: {"amount": float, "amount_str": string}

    Examples:
        get_categories()  # Returns all categories (basic info only)
        get_categories(category_type="Expense")  # Returns only expense categories
        get_categories(include_monthly_budgets=True)  # All categories with budget data
        get_categories(category_type="Expense", include_monthly_budgets=True)  # Expense categories with budgets

    Budget Analysis Workflow:
        1. Call get_categories(include_monthly_budgets=True) to get budgeted amounts
        2. Call get_transactions(start_date="01/01/2025", end_date="01/31/2025", category="Groceries")
        3. Sum transaction amounts to get actual spending
        4. Compare budget vs. actual for the category
    """
    try:
        logger.info(
            f"Fetching categories with filters: "
            f"category_type={category_type}, group={group}, include_monthly_budgets={include_monthly_budgets}"
        )
        client = get_sheets_client()

        # Fetch raw category data (with or without monthly budgets)
        raw_categories = client.get_categories_raw(include_monthly_budgets=include_monthly_budgets)
        logger.info(f"Retrieved {len(raw_categories)} raw category rows")

        # Parse into Category objects
        categories = []
        for row in raw_categories:
            try:
                category = Category.from_sheet_row(row, include_monthly_budgets=include_monthly_budgets)

                # Apply category_type filter (case-insensitive exact match)
                if category_type and category.type.upper() != category_type.upper():
                    continue

                # Apply group filter (case-insensitive partial match)
                if group and group.upper() not in category.group.upper():
                    continue

                categories.append(category)

            except Exception as e:
                logger.warning(f"Failed to parse category row: {e}")
                continue

        logger.info(f"Parsed {len(categories)} categories after filtering")

        # Convert to JSON-serializable format
        category_list = []
        for cat in categories:
            category_dict = {
                "category": cat.category,
                "group": cat.group,
                "type": cat.type
            }
            if include_monthly_budgets and cat.monthly_budgets:
                category_dict["monthly_budgets"] = cat.monthly_budgets
            category_list.append(category_dict)

        return json.dumps(category_list, indent=2)

    except SheetsClientError as e:
        logger.error(f"Sheets client error: {e}")
        return json.dumps({
            "error": "Failed to access Tiller spreadsheet",
            "message": str(e),
            "help": "Ensure TILLER_SHEET_ID is set and auth/token.json exists"
        }, indent=2)

    except Exception as e:
        logger.error(f"Unexpected error in get_categories: {e}", exc_info=True)
        return json.dumps({
            "error": "Unexpected error occurred",
            "message": str(e)
        }, indent=2)


def main():
    """Main entry point for the server."""
    logger.info("Starting Tiller Money MCP Server...")

    # Verify environment is configured
    if not os.environ.get('TILLER_SHEET_ID'):
        logger.warning("TILLER_SHEET_ID environment variable not set")
        logger.warning("Server will fail when tools are called without this variable")

    try:
        mcp.run()
    except Exception as e:
        logger.error(f"Failed to run server: {str(e)}")
        raise


# Export for mcp run
app = mcp

if __name__ == "__main__":
    main()
