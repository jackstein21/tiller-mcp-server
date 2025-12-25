"""
Pydantic models and parsing utilities for Tiller Money sheet data.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class AccountColumns:
    """Column indices for the Accounts sheet (0-based indexing)."""
    DISPLAY_NAME = 0       # "CREDIT CARD (-1234)"
    CLASS_OVERRIDE = 1     # Not used
    GROUP = 2              # "Credit Cards", "Retirement" - USE AS TYPE
    HIDE = 3               # Flag for hidden accounts


class TransactionColumns:
    """Column indices for the Transactions sheet (0-based indexing)."""
    EMPTY = 0
    DATE = 1              # MM/DD/YYYY
    DESCRIPTION = 2
    CATEGORY = 3
    AMOUNT = 4            # Currency string
    ACCOUNT = 5           # Display name
    ACCOUNT_NUMBER = 6    # Masked xxxx####
    INSTITUTION = 7
    MONTH = 8             # MM/DD/YY
    WEEK = 9              # MM/DD/YY
    TRANSACTION_ID = 10   # 24-char hex
    ACCOUNT_ID = 11       # 24-char hex
    CHECK_NUMBER = 12
    FULL_DESCRIPTION = 13
    DATE_ADDED = 14       # MM/DD/YY
    CATEGORIZED_DATE = 15


class CategoryColumns:
    """Column indices for the Categories sheet (0-based indexing)."""
    CATEGORY = 0  # Category name (primary key)
    GROUP = 1     # Category group/classification
    TYPE = 2      # Type: Expense/Income/Transfer


class Account(BaseModel):
    """Represents a Tiller Money account (simplified)."""

    display_name: str = Field(..., description="Account name with masked number")
    account_type: str = Field(..., description="Account type from Group column")
    account_number: str = Field(..., description="Last 4 digits extracted from display_name")
    is_hidden: bool = Field(default=False, description="Whether account is hidden")

    @classmethod
    def from_sheet_row(cls, row: List[str]) -> "Account":
        """
        Parse a row from simplified Accounts sheet (4 columns).

        Accounts sheet columns (4 total, 0-indexed):
        0: Account (display name with masked number like "CREDIT CARD (-XXXX)")
        1: Class Override (not used)
        2: Group (e.g., "Credit Cards", "Retirement" - used as account_type)
        3: Hide (flag for hidden accounts)

        Args:
            row: List of cell values from the sheet

        Returns:
            Account object with parsed data
        """
        def safe_get(idx: int, default: str = '') -> str:
            """Safely get value from row by index."""
            return row[idx] if idx < len(row) else default

        display_name = safe_get(AccountColumns.DISPLAY_NAME)

        # Extract last 4 digits from display_name like "Credit Card (-1233) - xxxx1234 (A1B2)"
        # We want the "1234" from "xxxx1234"
        account_number = ""
        if ' - xxxx' in display_name:
            # Find the masked number: "xxxx1234"
            parts = display_name.split(' - xxxx')
            if len(parts) > 1:
                # Get the part after "xxxx" and extract the 4 digits
                # "1234 (A1B2)" -> "1234"
                masked_part = parts[1].split()[0] if parts[1] else ""
                if len(masked_part) >= 4:
                    account_number = masked_part[:4]

        return cls(
            display_name=display_name,
            account_type=safe_get(AccountColumns.GROUP),  # Use Group as type
            account_number=account_number,
            is_hidden=safe_get(AccountColumns.HIDE).strip() != ''
        )


class Transaction(BaseModel):
    """Represents a Tiller Money transaction."""

    date: str = Field(..., description="Transaction date (MM/DD/YYYY)")
    description: str = Field(..., description="Transaction description")
    category: str = Field(..., description="Transaction category")
    amount: float = Field(..., description="Transaction amount (negative for expenses)")
    amount_str: str = Field(..., description="Original amount string with currency formatting")
    account: str = Field(..., description="Account display name")
    account_number: str = Field(..., description="Masked account number for linking")
    institution: str = Field(..., description="Financial institution")
    month: str = Field(default="", description="Month grouping (MM/DD/YY)")
    week: str = Field(default="", description="Week grouping (MM/DD/YY)")
    transaction_id: str = Field(..., description="Unique transaction ID")
    check_number: str = Field(default="", description="Check number if applicable")
    full_description: str = Field(default="", description="Full uppercase description")
    

    @classmethod
    def from_sheet_row(cls, row: List[str]) -> "Transaction":
        """
        Parse a row from Transactions sheet (16 columns).

        Args:
            row: List of cell values from the sheet

        Returns:
            Transaction object with parsed data
        """
        def safe_get(idx: int, default: str = '') -> str:
            """Safely get value from row by index."""
            return row[idx] if idx < len(row) else default

        # Parse amount string to float
        amount_str = safe_get(TransactionColumns.AMOUNT)
        amount = 0.0
        if amount_str:
            try:
                # Remove $ and commas: "-$1,255.19" -> -1255.19
                amount = float(amount_str.replace('$', '').replace(',', ''))
            except ValueError:
                amount = 0.0

        # Extract last 4 digits from account_number field "xxxx1234" -> "1234"
        raw_account_number = safe_get(TransactionColumns.ACCOUNT_NUMBER)
        account_number = ""
        if raw_account_number and len(raw_account_number) >= 4:
            # Take last 4 characters from "xxxx1234"
            account_number = raw_account_number[-4:]

        return cls(
            date=safe_get(TransactionColumns.DATE),
            description=safe_get(TransactionColumns.DESCRIPTION),
            category=safe_get(TransactionColumns.CATEGORY),
            amount=amount,
            amount_str=amount_str,
            account=safe_get(TransactionColumns.ACCOUNT),
            account_number=account_number,
            institution=safe_get(TransactionColumns.INSTITUTION),
            month=safe_get(TransactionColumns.MONTH),
            week=safe_get(TransactionColumns.WEEK),
            transaction_id=safe_get(TransactionColumns.TRANSACTION_ID),
            check_number=safe_get(TransactionColumns.CHECK_NUMBER),
            full_description=safe_get(TransactionColumns.FULL_DESCRIPTION)
        )


class Category(BaseModel):
    """Represents a Tiller Money category."""

    category: str = Field(..., description="Category name")
    group: str = Field(..., description="Category group/classification")
    type: str = Field(..., description="Category type (Expense/Income/Transfer)")
    monthly_budgets: Optional[dict] = Field(default=None, description="Monthly budget amounts by month name")

    @classmethod
    def from_sheet_row(cls, row: List[str], include_monthly_budgets: bool = False) -> "Category":
        """
        Parse a row from Categories sheet.

        Categories sheet columns:
        0: Category (category name, primary key)
        1: Group (e.g., "Expense", "Fun", "Living")
        2: Type (e.g., "Expense", "Income", "Transfer")
        3: Hide From Reports (skip this)
        4-15: Monthly budgets (Jan-Dec 2025) - only read if include_monthly_budgets=True

        Args:
            row: List of cell values from the sheet
            include_monthly_budgets: If True, parse columns E-P (indices 4-15) as monthly budgets

        Returns:
            Category object with parsed data
        """
        def safe_get(idx: int, default: str = '') -> str:
            """Safely get value from row by index."""
            return row[idx] if idx < len(row) else default

        def parse_currency(value: str) -> float:
            """Parse currency string to float."""
            if not value or value.strip() == '':
                return 0.0
            try:
                return float(value.replace('$', '').replace(',', ''))
            except ValueError:
                return 0.0

        # Parse base fields (columns A-C)
        category_dict = {
            "category": safe_get(CategoryColumns.CATEGORY),
            "group": safe_get(CategoryColumns.GROUP),
            "type": safe_get(CategoryColumns.TYPE)
        }

        # Optionally parse monthly budgets (columns E-P, skip D)
        if include_monthly_budgets:
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            budgets = {}
            for i, month in enumerate(month_names):
                # Column D is index 3 (Hide), so monthly data starts at index 4
                budget_str = safe_get(4 + i)  # E=4, F=5, ..., P=15
                budgets[month] = {
                    "amount": parse_currency(budget_str),
                    "amount_str": budget_str
                }
            category_dict["monthly_budgets"] = budgets

        return cls(**category_dict)
