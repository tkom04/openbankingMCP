"""
HMRC categorization utilities for Open Banking MCP.

Provides consistent category mapping and normalization for HMRC reporting.
"""

# Category mapping for consistent HMRC reporting
CATEGORY_MAP = {
    "Salary": "Income",
    "Shopping": "General expenses",
    "Groceries": "General expenses",
    "Food": "General expenses",
    "Meals": "Office Costs",
    "Travel": "Travel",
    "Transport": "Travel",
    "Utilities": "Utilities",
    "Bank Fees": "Bank charges",
    "Bank charges": "Bank charges",
    "Interest": "Bank Interest",
    "Bank Interest": "Bank Interest",
    "Income": "Income",
    "Office Costs": "Office Costs",
    "General expenses": "General expenses",
    "Uncategorized": "General expenses",
    "cash": "General expenses",  # ✅ normalize lowercase cash
    "Cash": "General expenses",
}


def normalize_category(category: str) -> str:
    """
    Normalize a category to a standard HMRC category.

    Args:
        category: The input category string

    Returns:
        Normalized category string
    """
    if not category:
        return "General expenses"

    # Clean the input
    clean_category = category.strip()

    # Check both raw and title-cased versions
    if clean_category in CATEGORY_MAP:
        return CATEGORY_MAP[clean_category]

    title_cased = clean_category.title()
    if title_cased in CATEGORY_MAP:
        return CATEGORY_MAP[title_cased]

    # If no mapping found, return the original category (title-cased for consistency)
    return title_cased


def get_valid_hmrc_categories() -> list:
    """
    Get list of valid HMRC categories.

    Returns:
        List of valid HMRC category strings
    """
    return list(set(CATEGORY_MAP.values()))


def validate_hmrc_category(category: str) -> bool:
    """
    Validate if a category is a valid HMRC category.

    Args:
        category: The category to validate

    Returns:
        True if valid, False otherwise
    """
    valid_categories = get_valid_hmrc_categories()
    return normalize_category(category) in valid_categories
