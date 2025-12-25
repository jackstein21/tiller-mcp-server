# Tiller Money MCP Server

A Model Context Protocol (MCP) server for Tiller Money's Google Sheets-based personal finance tracking. Enables natural language queries against your financial data through Claude Desktop with direct read-only access via the Google Sheets API and OAuth2 authentication.

## Quick Start

### 1. Installation

1. **Clone this repository**:
   ```bash
   git clone https://github.com/jackstein21/tiller-mcp-server.git
   cd tiller_mcp
   ```

2. **Set up Python environment**:
   ```bash
   # Using conda (recommended)
   conda create -n tiller_mcp python=3.12
   conda activate tiller_mcp

   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Set up Google Cloud Project**:

   Before authenticating, you need to create a Google Cloud Project and enable the Google Sheets API:

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project (or select an existing one)
   - Enable the Google Sheets API for your project
   - Create OAuth 2.0 credentials (Desktop app type)
   - Download the credentials JSON file
   - Save it as `auth/credentials.json` in this project

4. **Authenticate with Google Sheets**:
   ```bash
   # Run the authentication setup script
   python auth/auth_setup.py
   ```

   Follow the prompts:
   - Your browser will open for Google OAuth consent
   - Grant access to Google Sheets
   - Authentication token will be saved to `auth/token.json`

5. **Configure Claude Desktop**:
   Add this to your Claude Desktop configuration file:

   **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

   **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

   ```json
   {
     "mcpServers": {
       "Tiller Money": {
         "command": "/opt/anaconda3/envs/tiller_mcp/bin/python",
         "args": [
           "/path/to/your/tiller_mcp/src/tiller_mcp_server/server.py"
         ],
         "env": {
           "TILLER_SHEET_ID": "your_tiller_spreadsheet_id_here"
         }
       }
     }
   }
   ```

   **Important**:
   - Replace `/path/to/your/tiller_mcp` with your actual project path
   - Replace `your_tiller_spreadsheet_id_here` with your Tiller spreadsheet ID
   - If not using conda, update the `command` path to your Python interpreter

6. **Get your Tiller Spreadsheet ID**:
   - Open your Tiller spreadsheet in Google Sheets
   - Copy the ID from the URL: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit`

7. **Restart Claude Desktop**

---

## Features

### Account Management
- View all active financial accounts
- Filter by account type (Credit Cards, Retirement, Savings, etc.)

### Transaction Queries
- Search and filter transactions with powerful query options
- Date range filtering (start/end date)
- Account filtering (partial matching by account number)
- Category filtering (partial matching, case-insensitive)
- Amount filtering (min/max amounts for expenses or income)
- Description search across transaction text
- Pagination for large result sets
- Chronological sorting (most recent first)
- Detailed transaction lookup by ID

### Category Management
- View all category definitions from Tiller
- Filter by category type (Expense, Income, Transfer)
- Filter by category group (Living, Fun, etc.)
- Optional monthly budget allocation data per category

### Budget Analysis
- Access monthly budget allocations from Categories sheet
- Compare budgeted vs. actual spending
- Analyze any month or date range
- Natural language budget queries

---

## Available Tools

### Accounts

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_accounts` | Get all active financial accounts | `account_type` (optional) - Filter by account type/group |

### Transactions

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_transactions` | Query transactions with filtering & pagination | `start_date`, `end_date`, `account`, `category`, `min_amount`, `max_amount`, `description`, `limit`, `offset` (all optional) |
| `get_transaction_details` | Get complete details for a single transaction | `transaction_id` (required) - 24-character hex ID |

### Categories & Budgets

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_categories` | Get all category definitions with optional monthly budgets | `category_type` (optional) - Filter by type (Expense/Income/Transfer)<br>`group` (optional) - Filter by group (partial match)<br>`include_monthly_budgets` (optional, default: false) - Include monthly budget data |

---

## Usage Examples

### Account Queries
Ask Claude natural language questions like:
- "Show me all my financial accounts"
- "Show me my credit card accounts"
- "List all my retirement accounts"

### Transaction Queries
Query transactions using natural language:
- "Show me my 20 most recent transactions"
- "Show me all transactions in December 2025"
- "Get transactions between 12/01/2025 and 12/20/2025"
- "Show me transactions for account ending in 1234"
- "Show me all grocery transactions"
- "Find all dining expenses in December 2025"
- "Show me all expenses over $100"
- "List all income transactions"
- "Find transactions between $20 and $50"
- "Show me all Starbucks transactions"
- "Find all coffee shop purchases"

### Combined Filters
Combine multiple criteria in one query:
- "Show me December 2025 transactions for account 1234"
- "Find dining expenses between $20 and $50 in December 2025"
- "Show all grocery transactions over $100"

### Category Queries
Explore your category structure:
- "Show me all my categories"
- "List all expense categories"
- "What categories are in the Living group?"
- "Show expense categories in the Fun group"

### Budget Analysis
Analyze budgets vs. actual spending:
- "Show me my budget for December 2025"
- "Get all expense categories with their monthly budgets"
- "How much did I spend on groceries in January vs. my budget?"
- "Which categories am I over budget in for this month?"
- "Show me my total budgeted vs. actual spending for December"

---

## Data Structures

### Account Object

Each account object contains:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `display_name` | string | Account name with masked number | "CREDIT CARD (-XXXX)" |
| `account_type` | string | Account type/group from Tiller | "Credit Cards", "Retirement", "Savings" |
| `account_number` | string | Last 4 digits | "-XXXX" |
| `is_hidden` | boolean | Always false (hidden accounts excluded) | false |

### Transaction Object

Each transaction object contains:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `date` | string | Transaction date | "12/19/2025" |
| `description` | string | Merchant/description | "Coffee Shop Downtown" |
| `category` | string | Transaction category | "Restaurants" |
| `amount` | float | Amount (negative for expenses) | -15.75 |
| `amount_str` | string | Formatted amount string | "-$15.75" |
| `account` | string | Account display name | "CREDIT CARD (-XXXX)" |
| `account_number` | string | Last 4 digits of account | "XXXX" |
| `institution` | string | Financial institution | "Chase" |
| `month` | string | Month grouping | "12/01/25" |
| `week` | string | Week grouping | "12/15/25" |
| `transaction_id` | string | Unique 24-char hex ID | "123abc456def789012345678" |
| `check_number` | string | Check number if applicable | "" |
| `full_description` | string | Full uppercase description | "COFFEE SHOP DOWNTOWN" |

### Category Object

Each category object contains:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `category` | string | Category name (unique identifier) | "Groceries", "Dining Out", "Salary" |
| `group` | string | Category group/classification | "Living", "Fun", "Primary Income" |
| `type` | string | Category type | "Expense", "Income", "Transfer" |
| `monthly_budgets` | object (optional) | Monthly budget amounts | `{"Jan": {"amount": 600.0, "amount_str": "$600.00"}, ...}` |

**Monthly Budgets Structure** (when `include_monthly_budgets=True`):
- Contains 12 months: Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec
- Each month has:
  - `amount` (float): Parsed budget amount (e.g., 600.0)
  - `amount_str` (string): Original currency string (e.g., "$600.00")

---

## Data Privacy & Security

### Read-Only Access
- **v1.0 is completely read-only** - No write operations to your spreadsheet
- Safe to use without risk of data corruption
- Future write operations will require explicit user consent

### Local Execution
- MCP server runs locally on your machine via stdio
- No cloud deployment or data transmission to third parties
- Data never leaves your local environment

### Authentication Security
- OAuth2 credentials stored in `auth/credentials.json` (gitignored)
- Access token stored in `auth/token.json` (gitignored)
- Tokens automatically refresh when expired
- Full Google OAuth security model

### Hidden Accounts
- Hidden accounts are **always excluded** from results
- No option to include hidden accounts (by design)
- Ensures sensitive accounts remain private

---

## Tiller Sheet Integration

The MCP server reads from standard Tiller Money spreadsheet tabs:

### Accounts Sheet
Uses columns A-D for efficiency:
- **Column A**: Display name with masked number
- **Column B**: Class Override (not currently used)
- **Column C**: Group (account type)
- **Column D**: Hide flag

### Transactions Sheet
Uses columns A-P for complete transaction data including date, description, category, amount, account, institution, and metadata.

### Categories Sheet
Uses columns A-C for category definitions, with optional columns D-P for monthly budget allocations (12 months).

---

## Technical Details

### Project Structure
```
tiller_mcp/
├── auth/
│   ├── credentials.json        # OAuth credentials (gitignored)
│   ├── token.json             # OAuth token (gitignored)
│   └── auth_setup.py          # Authentication setup script
├── src/tiller_mcp_server/
│   ├── __init__.py            # Package initialization
│   ├── server.py              # Main MCP server (FastMCP)
│   ├── sheets_client.py       # Google Sheets API wrapper
│   └── tiller_schema.py       # Pydantic models
├── config.json                # Example Claude Desktop config
├── requirements.txt           # Python dependencies
├── PRD.md                     # Product Requirements Document
└── README.md                  # This documentation
```

### Architecture

Three-layer pattern for clean separation of concerns:

1. **Data Models** ([tiller_schema.py](src/tiller_mcp_server/tiller_schema.py))
   - Pydantic models for type-safe data handling
   - Account, Transaction, and Category models
   - Currency parsing, date handling, and account number extraction
   - Optional monthly budget data support

2. **API Client** ([sheets_client.py](src/tiller_mcp_server/sheets_client.py))
   - Google Sheets API authentication and connection
   - Automatic token refresh handling
   - Efficient sheet range queries with singleton pattern

3. **MCP Tools** ([server.py](src/tiller_mcp_server/server.py))
   - FastMCP framework with `@mcp.tool()` decorators
   - Read-only operations with comprehensive validation
   - JSON response formatting with helpful error messages

---

## Troubleshooting

### Authentication Issues

**Error**: "TILLER_SHEET_ID environment variable not set"
- **Solution**: Add `TILLER_SHEET_ID` to Claude Desktop config under `env` section

**Error**: "Token file not found"
- **Solution**: Run `python auth/auth_setup.py` to create authentication token

**Error**: "Credentials are invalid and cannot be refreshed"
- **Solution**: Re-run authentication: `python auth/auth_setup.py`

### Server Connection Issues

**Error**: "Server transport closed unexpectedly" in Claude Desktop
- **Solution**: Check that the Python path in config is correct
- **Solution**: Verify all dependencies are installed: `pip install -r requirements.txt`
- **Solution**: Test server manually: `python src/tiller_mcp_server/server.py`

### Data Issues

**Error**: "Failed to parse account row"
- **Solution**: Check that your Tiller Accounts sheet has the expected column structure
- **Solution**: Verify columns A-D contain: Display Name, Class Override, Group, Hide

### Common Error Messages

| Error | Solution |
|-------|----------|
| "No valid session found" | Run `python auth/auth_setup.py` |
| "Spreadsheet not found" | Verify `TILLER_SHEET_ID` in config |
| "Permission denied" | Re-run auth setup to grant Sheets access |
| "Invalid credentials" | Check `auth/credentials.json` exists |

---

## Development

### Testing
```bash
# Test server manually
python src/tiller_mcp_server/server.py

# Server logs to stderr (visible in Claude Desktop logs)
```

### Contributing New Tools

1. **Design**: Specify tool requirements in [PRD.md](PRD.md)
2. **Data Model**: Add Pydantic model to [tiller_schema.py](src/tiller_mcp_server/tiller_schema.py)
3. **API Client**: Add sheet query method to [sheets_client.py](src/tiller_mcp_server/sheets_client.py)
4. **MCP Tool**: Add tool definition to [server.py](src/tiller_mcp_server/server.py)
5. **Test**: Validate in Claude Desktop

---

## Google Sheets API Quotas

**Free Tier**:
- 300 requests per minute (project)
- 60 requests per minute (user)
- No billing required for personal use

**Expected Usage**:
- Typical query: 1-3 API calls
- Daily usage: < 100 API calls
- Well within free tier limits

---

## Design Principles

- **Read-only**: No write operations to prevent data corruption
- **Local execution**: Runs locally via stdio, no cloud deployment
- **No caching**: Fresh data on every query (within generous API quotas)
- **Privacy-first**: Hidden accounts always excluded
- **Iterative development**: One tool at a time, thoroughly tested

---

## Roadmap

### Completed Features
- Google Sheets API authentication and integration
- Tiller sheet structure discovery and documentation
- Account management tools
- Transaction query tools with comprehensive filtering
- Category management with budget data access
- Budget vs. actual analysis capabilities

### Future Enhancements
- Balance history queries and trend analysis
- Category summary and aggregation tools
- Advanced analytics (spending patterns, trends, forecasting)
- AutoCat rule management (read-only)
- Export and reporting capabilities

---

## Support

For issues, follow these troubleshooting steps:
1. Check authentication: `python auth/auth_setup.py`
2. Verify configuration: Ensure `TILLER_SHEET_ID` is set in Claude Desktop config
3. Test server manually: `python src/tiller_mcp_server/server.py`
4. Review logs: Claude Desktop logs show server stderr output
5. Report issues on GitHub with error details and logs

---

## License

MIT License

---

## Acknowledgments

### Inspiration

Inspired by the [MonarchMoney Python library](https://github.com/hammem/monarchmoney) by [@hammem](https://github.com/hammem) - A fantastic unofficial API for Monarch Money with full MFA support.

Further inspired by [@drbarq](https://github.com/drbarq)'s excellent upgrade: [monarch-mcp-server-god-mode](https://github.com/drbarq/monarch-mcp-server-god-mode)

### Built With

- [Google Sheets API](https://developers.google.com/sheets/api) - Data access
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [Tiller Money](https://www.tillerhq.com/) - Personal finance tracking platform
