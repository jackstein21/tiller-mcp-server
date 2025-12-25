# Product Requirements Document

## Tiller MCP Server v1.0

**Document Version:** 1.0  
**Date:** December 25, 2025  
**Status:** Prod

---

## Executive Summary

This PRD outlines the initial development of a Model Context Protocol (MCP) server that provides Claude with direct access to personal financial data stored in Tiller Money Google Sheets. The project takes an iterative, one-tool-at-a-time approach, starting with read-only query capabilities and potentially expanding to data validation and categorization assistance.

### Current State

- Financial data tracked in Google Sheets with Tiller Money integration
- Manual data review and cleanup processes
- Transaction categorization done entirely by hand
- No programmatic query interface

### Target State

- Local stdio MCP server providing Claude access to Tiller data
- Natural language queries for financial analysis
- Read-only access initially (safety-first design)

---

## Goals & Non-Goals

### Goals

1. **Query Access**: Enable natural language queries against Tiller transaction data
2. **Learning Project**: Understand Google Sheets API and MCP protocol through hands-on development
3. **Incremental Development**: Build one tool at a time, testing thoroughly before expanding
4. **Local & Secure**: Keep all data access local via stdio, no cloud deployment required
5. **Data Integrity**: Read-only operations to prevent accidental data corruption

### Non-Goals

1. Real-time data sync (Tiller handles this)
2. Multi-user access (personal use only)
3. Web-based deployment
4. Bulk write operations in initial version
5. Mobile access

---

## Technical Architecture

### Components

**MCP Server**
- Python-based stdio server
- Google Sheets API integration for data access
- Tool definitions following MCP specification

**Authentication**
- OAuth2 credentials for Google Sheets API
- Local credential storage
- No persistent sessions (auth per request if needed)

**Data Access Layer**
- Read operations against Tiller spreadsheet
- Sheet structure mapping (Transactions, Categories, Accounts, Budgets)
- Query result formatting for Claude consumption

### Deployment Model

- Local execution only
- Configured in Claude Desktop config file
- No hosting or cloud infrastructure needed
- Runs on-demand when Claude needs data

---

## Implemented Tool Specifications

### get_accounts()

**Status**: ✅ Implemented and tested

**Purpose**: Retrieve all active financial accounts from Tiller Money with basic account information

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `account_type` | string | No | Optional filter by account type/group. Case-insensitive. Examples: "Credit Cards", "Retirement", "Savings" |

**Returns**: JSON array of account objects, each containing:
- `display_name` (string): Account name with masked number (e.g., "CREDIT CARD (-XXXX)")
- `account_type` (string): Account type/group from Tiller's Group column (e.g., "Credit Cards", "Retirement")
- `account_number` (string): Last 4 digits extracted from display_name (e.g., "-XXXX")
- `is_hidden` (boolean): Always false (hidden accounts are excluded)

**Example Use Cases**:
- "Show me all my accounts"
- "List my credit card accounts"
- "What retirement accounts do I have?"

**Implementation Details**:
- Reads from Accounts sheet columns A-D only (simplified schema)
- ALWAYS excludes hidden accounts (no option to include them)
- Account number extracted from display_name using regex parsing
- Account type comes from Group column (column C)
- Supports case-insensitive filtering by account_type

**Data Source**: `Accounts!A2:D` (4 columns)
- Column A: Display name with masked number
- Column B: Class Override (not used)
- Column C: Group (used as account_type)
- Column D: Hide flag

### get_transactions()

**Status**: ✅ Implemented and tested

**Purpose**: Query transactions with filtering, sorting, and pagination

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_date` | string | No | Filter by date >= this (MM/DD/YYYY format). Example: "12/01/2025" |
| `end_date` | string | No | Filter by date <= this (MM/DD/YYYY format). Example: "12/31/2025" |
| `account` | string | No | Filter by account number (partial match, case-insensitive). Example: "XXXX" |
| `limit` | integer | No | Maximum transactions to return (default: 100, max: 1000) |
| `offset` | integer | No | Skip first N transactions for pagination (default: 0) |

**Returns**: JSON array of transaction objects sorted by date (most recent first), each containing:
- `date` (string): Transaction date in MM/DD/YYYY format
- `description` (string): Transaction description
- `category` (string): Category name
- `amount` (float): Transaction amount as number (negative for expenses, positive for income)
- `amount_str` (string): Original formatted currency string (e.g., "-$1,255.99")
- `account` (string): Account display name (e.g., "CREDIT CARD (-XXXX)")
- `account_number` (string): Last 4 digits of account number (e.g., "-XXXX")
- `institution` (string): Financial institution name
- `month` (string): Month grouping in MM/DD/YY format
- `week` (string): Week grouping in MM/DD/YY format
- `transaction_id` (string): 24-character hexadecimal transaction ID
- `check_number` (string): Check number if applicable (usually empty)
- `full_description` (string): Full/uppercase original description

**Example Use Cases**:
- "Show me my last 20 transactions"
- "What did I spend in December 2025?"
- "Show transactions for my credit card ending in 0738"
- "Get the next page of results"

**Implementation Details**:
- Chronological sorting with proper date parsing (MM/DD/YYYY format)
- Account number matching is case-insensitive and supports partial matches
- Date range validation with helpful error messages
- Pagination via offset/limit for large result sets
- Currency parsing from formatted strings to float values
- Security: Excludes account_id, date_added, and categorized_date fields

**Data Source**: `Transactions!A2:P` (16 columns, excludes sensitive fields)

### get_transaction_details()

**Status**: ✅ Implemented and tested

**Purpose**: Get complete details for a single transaction by ID

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `transaction_id` | string | Yes | 24-character hexadecimal transaction ID |

**Returns**: JSON object with complete transaction details (same fields as get_transactions)

**Example Use Cases**:
- "Show me details for transaction 123abc456def789012345678"
- "Look up this specific transaction"

**Implementation Details**:
- Validates transaction_id format (24-character hex)
- Returns helpful error if transaction not found
- Same field exposure as get_transactions

**Data Source**: `Transactions!A2:P` (single row lookup by transaction_id)

---

## Planned Tool Specifications (Phase 4+)

### get_transactions() - Enhanced (Phase 4)

**Status**: ✅ Implemented and tested

**New Parameters Added**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category` | string | No | Filter by category name (partial match, case-insensitive). Example: "Groceries" |
| `min_amount` | string | No | Filter transactions with amount >= this value. Example: "50.00" or "-100.00" |
| `max_amount` | string | No | Filter transactions with amount <= this value. Example: "500.00" or "-10.00" |
| `description` | string | No | Search for text in description fields (partial match, case-insensitive). Example: "coffee" |

**Use Cases Enabled**:
- "Show all grocery transactions over $100"
- "Find dining expenses between $20 and $50 in December"
- "List all income transactions" (min_amount="0")
- "Show expenses under $10" (max_amount="-10.00")
- "Find all Starbucks transactions" (description="starbucks")

**Implementation Notes**:
- Amount filters work with negative values (expenses are negative)
- Category filter searches the Category column (column D)
- Description filter searches both Description (column C) and Full Description (column N)
- All text filters are case-insensitive with partial matching
- Multiple filters combine with AND logic

### get_categories()

**Status**: ✅ Implemented and tested

**Purpose**: Retrieve all category definitions from Tiller Money

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category_type` | string | No | Filter by category type. Valid values: "Expense", "Income", "Transfer" (case-insensitive) |
| `group` | string | No | Filter by category group (partial match, case-insensitive). Examples: "Living", "Fun", "Primary Income" |

**Returns**: JSON array of category objects, each containing:
- `category` (string): Category name
- `group` (string): Category group/classification (e.g., "Expense", "Fun", "Living", "Primary Income")
- `type` (string): Category type (e.g., "Expense", "Income", "Transfer")

**Example Use Cases**:
- "Show me all categories"
- "List all expense categories"
- "What categories are in the Living group?"
- "Show me my income categories"
- "Show expense categories in the Fun group"

**Implementation Details**:
- Reads from Categories sheet columns A-C only
- Category names are unique identifiers
- Type filter: Exact match, case-insensitive
- Group filter: Partial match, case-insensitive
- Group provides finer classification within types
- Comprehensive error handling with helpful messages

**Data Source**: `Categories!A2:C` (3 columns)
- Column A: Category name (primary key)
- Column B: Group classification
- Column C: Type (Expense/Income/Transfer)

### Budget Data Access

**Status**: ✅ Implemented and tested

**Approach**: Budget data is accessed through the Categories sheet monthly columns (E-P) rather than parsing the complex Monthly Budget sheet. The `get_categories()` tool was enhanced with an optional `include_monthly_budgets` parameter.

**Implementation**:
- Enhanced `get_categories()` with `include_monthly_budgets: bool = False` parameter
- When `True`, reads columns A-P from Categories sheet (includes 12 monthly budget columns)
- Returns monthly budgets as dictionary: `{"Jan": {"amount": 600.0, "amount_str": "$600.00"}, ...}`
- Backward compatible - existing calls work unchanged

**Budget Analysis Workflow**:
1. Call `get_categories(include_monthly_budgets=True)` to get budgeted amounts per category
2. Call `get_transactions(start_date="01/01/2025", end_date="01/31/2025", category="Groceries")` to get actuals
3. Claude sums transaction amounts and compares to budget

**Benefits**:
- Leverages existing tools - no new budget-specific tools needed
- Works with any user configuration - no fragile hierarchy detection
- More flexible - can analyze any month or date range
- Simpler codebase - composition of existing tools is more powerful than specialized budget tools

---

## Safety & Error Handling

### Read-Only Safety

- Initial version: absolutely no write operations
- All tools return data, never modify sheets

### Data Validation

- Validate sheet IDs exist before queries
- Verify column structure matches expectations
- Handle missing or malformed data gracefully
- Return clear error messages to Claude

### Rate Limiting

- Google Sheets API: 300 requests/min (project), 60 requests/min (user)
- For personal use, rate limits should never be hit
- Implement basic error handling for quota errors anyway

### Error Scenarios

- Authentication failures
- Sheet not found or access denied
- Malformed query parameters
- Empty result sets
- API quota exceeded (unlikely but handled)

---

## Implementation Phases

### Phase 0: Foundation (Complete)

**Goal**: Set up authentication infrastructure
- [x] Create PRD document
- [x] Create CLAUDE.md guidance document
- [x] Set up Google Cloud project
- [x] Enable Sheets API
- [x] Generate OAuth credentials → `auth/credentials.json`
- [x] Create exploration notebook → `tests/google_sheets_exploration.ipynb`
- [x] Create auth script → `auth/auth_setup.py`
- [x] Complete authentication flow → `auth/token.json`

### Phase 1: Tiller Sheet Structure Discovery (Complete)

**Goal**: Explore and document Tiller sheet structure

**Notebook Location**: `tests/google_sheets_exploration.ipynb`

Tasks completed:
- [x] Create `auth/auth_setup.py` for authentication
- [x] Use auth script to connect to Tiller spreadsheet
- [x] List all sheets in Tiller workbook (10 sheets discovered)
- [x] Document column structure for each sheet:
  - [x] Transactions sheet columns (16 columns)
  - [x] Categories sheet columns (16 columns with embedded budgets)
  - [x] Accounts sheet columns (17 columns)
  - [x] Balance History columns (15 columns)
  - [x] Monthly Budget structure (complex layout, use Categories instead)
- [x] Identify data types (dates, currencies, categories)
- [x] Test basic range queries in notebook
- [x] Document Tiller-specific conventions
- [x] Document findings in CLAUDE.md

### Phase 2: First Tool Implementation (Complete)

**Goal**: Build and test simplest useful tool

**Completed Tasks**:
- [x] Implement basic MCP server structure using FastMCP
- [x] Create `sheets_client.py` with Google Sheets API wrapper
- [x] Create `tiller_schema.py` with simplified Account model (4 fields)
- [x] Implement `get_accounts()` tool
- [x] Test in Claude Desktop
- [x] Simplify schema to 4 columns (A-D) per user requirements
- [x] Document usage patterns in README.md

**Key Decisions**:
- Used FastMCP framework for tool definitions
- Simplified Account schema to 4 fields only (display_name, account_type, account_number, is_hidden)
- Read only 4 columns from Accounts sheet (A-D)
- Account number extracted from display_name via parsing
- Hidden accounts ALWAYS excluded (no option to include them)
- Uses conda Python environment for deployment

### Phase 3: Transaction Tools (Complete)

**Goal**: Implement core transaction querying capabilities

**Completed Tasks**:
- [x] Implement `get_transactions()` tool with filtering and pagination
- [x] Add date range filtering (start_date, end_date)
- [x] Add account filtering with partial matching
- [x] Implement chronological sorting (most recent first)
- [x] Add pagination support (limit, offset)
- [x] Implement `get_transaction_details()` for single transaction lookup
- [x] Test in Claude Desktop with various query patterns
- [x] Document usage in README.md

**Key Features Delivered**:
- Date range queries with MM/DD/YYYY format
- Account number partial matching (case-insensitive)
- Configurable result limits (default 100)
- Offset-based pagination for large datasets
- Transaction ID validation and lookup
- Comprehensive error handling and validation

### Phase 4: Advanced Transaction Search (Completed)

**Goal**: Enhance transaction search with category and amount filtering, enable category-based analysis

**Completed Tasks**:
- [x] Add `category` parameter to `get_transactions()` for category filtering
  - Partial category name matching
  - Case-insensitive search
- [x] Add amount filtering parameters:
  - `min_amount`: Filter transactions >= amount (e.g., "50.00")
  - `max_amount`: Filter transactions <= amount (e.g., "500.00")
  - Support both positive and negative amounts
- [x] Add `description` parameter for text search in transaction descriptions
  - Search both Description and Full Description fields
  - Partial matching, case-insensitive
- [x] Test category analysis use cases:
  - "Show all grocery transactions over $100"
  - "Find dining expenses between $20 and $50 in December"
  - "List all income transactions"
- [x] Document category analysis patterns in README.md

**Implementation Results**:
- Amount comparisons work correctly with negative expenses
- Category filtering handles case variations
- Multiple filters combine with AND logic
- All filters validated with comprehensive error messages

### Phase 4: Category Management (Complete)

**Goal**: Enable discovery and exploration of Tiller categories

**Completed Tasks**:
- [x] Implement `get_categories()` tool for category queries
  - Add `category_type` parameter (Expense, Income, Transfer)
  - Add `group` parameter for filtering by category group
  - Read from Categories sheet columns A-C
- [x] Create Category Pydantic model in tiller_schema.py
- [x] Add CategoryColumns class for column mapping
- [x] Test category discovery use cases
- [x] Update documentation in PRD.md and CLAUDE.md

**Implementation Results**:
- Category type filtering works with case-insensitive exact match
- Group filtering supports partial matching (case-insensitive)
- Both filters combine with AND logic
- Comprehensive error handling and logging
- Follows established patterns from get_accounts and get_transactions

### Phase 5: Budget Data Access (Complete)

**Goal**: Enable budget vs. actual analysis through existing tools

**Completed Tasks**:
- [x] Explored Monthly Budget sheet - determined it was too complex and user-configurable
- [x] Chose simpler approach: Categories sheet monthly columns (E-P)
- [x] Extended Category model with optional `monthly_budgets` field
- [x] Updated `get_categories_raw()` to support `include_monthly_budgets` parameter
- [x] Enhanced `get_categories()` tool with budget data option
- [x] Tested budget data retrieval with user's actual data
- [x] Documented budget analysis workflow in CLAUDE.md and PRD.md

**Implementation Approach**:
- Budget data accessed through Categories sheet columns E-P (Jan-Dec)
- `get_categories(include_monthly_budgets=True)` returns monthly budgets per category
- Claude combines budget data with `get_transactions()` results for analysis
- No specialized budget tools needed - composition is more powerful

**Benefits**:
- Works with any user configuration (no hardcoded assumptions)
- Leverages existing transaction filtering capabilities
- Can analyze any month or date range
- Simpler codebase with fewer edge cases
- Backward compatible - existing code unchanged

### Phase 6: Future Enhancements (Backlog)

**Potential Features**:
- Advanced analytics and trend analysis
- Balance history queries
- AutoCat rule management (read-only)
- Export and reporting capabilities

---

## Testing Strategy

### Jupyter Notebook Testing

- Test all Google Sheets API calls independently
- Verify data parsing and formatting
- Check edge cases (empty results, large ranges)
- Document any API quirks or limitations

### MCP Server Testing

- Use MCP Inspector for tool validation
- Test each tool individually in Claude Desktop
- Test multi-tool workflows
- Verify error messages are helpful

### Data Integrity Testing

- Confirm read-only nature (no accidental writes)
- Verify calculations match manual Excel analysis
- Test with various date ranges and filters
- Validate category aggregations

---

## Success Metrics

### Development Metrics

- Time to first working tool
- API calls per query (efficiency)
- Error rate < 5% for valid queries

### User Value Metrics

- Reduced time for common financial queries
- Ability to answer questions not easily done in Excel
- Natural language interface vs manual filtering

### Quality Metrics

- Accurate data retrieval (100% match with Excel)
- Clear error messages when issues occur
- Fast response times (< 2 seconds for typical queries)

---

## Dependencies

### External Services

- Google Cloud Platform (free tier)
- Google Sheets API (free, with quotas)
- Tiller Money (existing subscription)

### Python Libraries

- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2`
- `google-api-python-client`
- `mcp` (Model Context Protocol SDK)

### Development Tools

- Jupyter notebook for API exploration
- Claude Desktop for MCP testing
- Python 3.10+

---

## Project Structure

Current directory layout:

```
tiller_mcp/
├── auth/
│   ├── credentials.json        # OAuth client credentials (gitignored)
│   ├── token.json             # OAuth token (gitignored, created on auth)
│   └── auth_setup.py          # Interactive OAuth setup script
├── src/tiller_mcp_server/      # To be created
│   ├── __init__.py
│   ├── server.py              # Main MCP server with tools
│   ├── sheets_client.py       # Google Sheets API wrapper
│   └── tiller_schema.py       # Pydantic models for Tiller data
├── requirements.txt           # Pip requirements
├── .gitignore                 # Excludes credentials and tokens
├── PRD.md                     # This document
├── CLAUDE.md                  # Claude Code guidance document (gitignored)
└── README.md                  # User-facing documentation
```

**Current State**: Phase 5 complete.

---

## Future Considerations

### Potential Features

- **Data Validation**: Automated cleanup suggestions
- **Reconciliation**: Match transactions to budget categories
- **Trend Analysis**: Advanced analytics and forecasting
- **Export**: Generate reports or visualizations

### Integration Ideas

- Connect to other financial data sources
- Automated monthly spending reports
- Budget recommendations based on patterns
- Anomaly detection for unusual transactions

---

## Appendix A: Google Sheets API Costs

**Free Tier Quotas**:
- 300 requests per minute per project
- 60 requests per minute per user
- No billing required for personal use
- No cost for API access

**Expected Usage**:
- Typical query: 1-3 API calls
- Daily usage: < 50 API calls
- Well within free tier limits

---

## Appendix B: Tool Development Template

```python
# Template for each new tool implementation

async def tool_name(param_a: str, param_b: Optional[str] = None) -> dict:
    """
    Purpose: Brief description
    
    Args:
        param_a: Description
        param_b: Description (optional)
    
    Returns:
        Dictionary with query results
    
    Raises:
        SheetsAPIError: When API call fails
        ValidationError: When parameters are invalid
    """
    # 1. Validate parameters
    # 2. Build Sheets API query
    # 3. Execute query
    # 4. Parse and format results
    # 5. Return structured data
    pass
```

