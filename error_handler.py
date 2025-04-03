"""
Error handling module for Easy Crawl4AI

This module provides user-friendly error messages and helpful suggestions
for common issues encountered when using the application.
"""

import logging
from typing import Dict, Any, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Define error categories
ERROR_CATEGORIES = {
    "connection": "Connection Error",
    "url": "URL Error",
    "browser": "Browser Error",
    "parse": "Parsing Error",
    "file": "File Error",
    "dependency": "Dependency Error",
    "authentication": "Authentication Error",
    "rate_limit": "Rate Limit Error",
    "timeout": "Timeout Error",
    "permission": "Permission Error",
    "database": "Database Error",
    "unknown": "Unknown Error"
}

# Define error messages with helpful suggestions
ERROR_MESSAGES = {
    # Connection errors
    "connection_refused": {
        "category": "connection",
        "message": "The server refused to connect.",
        "suggestion": "Check if the website is online and try again later. If using a proxy, make sure it's working correctly."
    },
    "connection_timeout": {
        "category": "connection",
        "message": "The connection timed out.",
        "suggestion": "The website might be slow or unresponsive. Try again later or increase the timeout value in settings."
    },
    "dns_error": {
        "category": "connection",
        "message": "Could not resolve the domain name.",
        "suggestion": "Check if the URL is correct. The domain might be unavailable or your internet connection might have DNS issues."
    },
    
    # URL errors
    "invalid_url": {
        "category": "url",
        "message": "The URL is invalid.",
        "suggestion": "Make sure the URL starts with 'http://' or 'https://' and contains a valid domain name."
    },
    "url_not_found": {
        "category": "url",
        "message": "The URL was not found (404 error).",
        "suggestion": "The page might have been moved or deleted. Check if the URL is correct."
    },
    
    # Browser errors
    "browser_not_available": {
        "category": "browser",
        "message": "Browser-based crawling is not available.",
        "suggestion": "Install the 'browser' feature from the Settings page or uncheck the 'Use Browser' option."
    },
    "browser_navigation_failed": {
        "category": "browser",
        "message": "Browser navigation failed.",
        "suggestion": "The website might be using complex JavaScript or anti-bot measures. Try again without browser-based crawling."
    },
    
    # Parsing errors
    "content_extraction_failed": {
        "category": "parse",
        "message": "Failed to extract content from the page.",
        "suggestion": "The website structure might be complex or non-standard. Try using browser-based crawling or specify a CSS selector."
    },
    "selector_not_found": {
        "category": "parse",
        "message": "The specified CSS selector was not found on the page.",
        "suggestion": "Check if the selector is correct. The page structure might have changed since you last inspected it."
    },
    
    # File errors
    "file_save_error": {
        "category": "file",
        "message": "Failed to save the result file.",
        "suggestion": "Check if the output directory exists and you have write permissions."
    },
    "file_not_found": {
        "category": "file",
        "message": "The specified file was not found.",
        "suggestion": "Check if the file path is correct and the file exists."
    },
    "file_too_large": {
        "category": "file",
        "message": "The file is too large to download.",
        "suggestion": "Increase the max file size in settings or specify a smaller file."
    },
    
    # Dependency errors
    "dependency_not_installed": {
        "category": "dependency",
        "message": "A required dependency is not installed.",
        "suggestion": "Go to the Settings page and install the required feature or dependency."
    },
    "crawl4ai_not_installed": {
        "category": "dependency",
        "message": "The crawl4ai library is not installed.",
        "suggestion": "Install crawl4ai using 'pip install crawl4ai' or from the Settings page."
    },
    
    # Authentication errors
    "authentication_required": {
        "category": "authentication",
        "message": "The website requires authentication.",
        "suggestion": "Login is required to access this content. Try using browser-based crawling with login support."
    },
    "authentication_failed": {
        "category": "authentication",
        "message": "Authentication failed.",
        "suggestion": "Check if your login credentials are correct and try again."
    },
    
    # Rate limit errors
    "rate_limited": {
        "category": "rate_limit",
        "message": "You've been rate limited by the website.",
        "suggestion": "The website has detected too many requests. Wait a while before trying again or use a proxy."
    },
    
    # Timeout errors
    "page_load_timeout": {
        "category": "timeout",
        "message": "The page took too long to load.",
        "suggestion": "The website might be slow or contain heavy resources. Try increasing the timeout in settings."
    },
    
    # Permission errors
    "robots_txt_disallowed": {
        "category": "permission",
        "message": "Access to this URL is disallowed by robots.txt.",
        "suggestion": "This website doesn't allow crawling of this page. Consider respecting their policy."
    },
    "access_denied": {
        "category": "permission",
        "message": "Access to the website was denied (403 error).",
        "suggestion": "The website is blocking access. It might require authentication or be blocking automated access."
    },
    
    # Database errors
    "database_connection_error": {
        "category": "database",
        "message": "Failed to connect to the database.",
        "suggestion": "Check if the database server is running and the connection settings are correct."
    },
    "database_query_error": {
        "category": "database",
        "message": "A database query failed.",
        "suggestion": "There might be an issue with the database schema or data consistency."
    },
    
    # Unknown/general errors
    "unknown_error": {
        "category": "unknown",
        "message": "An unknown error occurred.",
        "suggestion": "Check the application logs for more details."
    }
}

def classify_error(exception: Exception) -> str:
    """
    Classify an exception into a specific error type.
    
    Args:
        exception: The exception that was raised
        
    Returns:
        The error type code
    """
    error_type = "unknown_error"
    error_message = str(exception).lower()
    
    # Connection errors
    if any(term in error_message for term in ["connection refused", "failed to establish", "connectrefused"]):
        error_type = "connection_refused"
    elif any(term in error_message for term in ["timed out", "timeout"]):
        error_type = "connection_timeout"
    elif any(term in error_message for term in ["dns", "name resolution", "name or service not known"]):
        error_type = "dns_error"
    
    # URL errors
    elif any(term in error_message for term in ["invalid url", "invalid scheme", "no scheme"]):
        error_type = "invalid_url"
    elif "404" in error_message or "not found" in error_message:
        error_type = "url_not_found"
    
    # Browser errors
    elif "playwright" in error_message or "browser" in error_message:
        if "not installed" in error_message or "not found" in error_message:
            error_type = "browser_not_available"
        else:
            error_type = "browser_navigation_failed"
    
    # Parsing errors
    elif "selector" in error_message and ("not found" in error_message or "no matches" in error_message):
        error_type = "selector_not_found"
    elif "extract" in error_message or "parse" in error_message:
        error_type = "content_extraction_failed"
    
    # File errors
    elif "permission denied" in error_message and ("write" in error_message or "save" in error_message):
        error_type = "file_save_error"
    elif "no such file" in error_message or "file not found" in error_message:
        error_type = "file_not_found"
    elif "file too large" in error_message or "exceeds maximum" in error_message:
        error_type = "file_too_large"
    
    # Dependency errors
    elif "module" in error_message and "not found" in error_message:
        if "crawl4ai" in error_message:
            error_type = "crawl4ai_not_installed"
        else:
            error_type = "dependency_not_installed"
    
    # Authentication errors
    elif "login" in error_message or "authentication" in error_message:
        if "required" in error_message:
            error_type = "authentication_required"
        else:
            error_type = "authentication_failed"
    
    # Rate limit errors
    elif "rate limit" in error_message or "too many requests" in error_message or "429" in error_message:
        error_type = "rate_limited"
    
    # Timeout errors
    elif "page load" in error_message and "timeout" in error_message:
        error_type = "page_load_timeout"
    
    # Permission errors
    elif "robots.txt" in error_message and "disallowed" in error_message:
        error_type = "robots_txt_disallowed"
    elif "403" in error_message or "forbidden" in error_message:
        error_type = "access_denied"
    
    # Database errors
    elif "database" in error_message and "connection" in error_message:
        error_type = "database_connection_error"
    elif "sql" in error_message or "query" in error_message:
        error_type = "database_query_error"
    
    return error_type

def get_error_info(exception: Exception) -> Tuple[str, Dict[str, Any]]:
    """
    Get user-friendly error information for an exception.
    
    Args:
        exception: The exception that was raised
        
    Returns:
        A tuple containing (error_type, error_info_dict)
    """
    error_type = classify_error(exception)
    error_info = ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown_error"])
    
    # Log the error for debugging
    logger.error(f"Error: {str(exception)}, Classified as: {error_type}")
    
    return error_type, error_info

def format_error_message(exception: Exception, include_exception_details: bool = False) -> Dict[str, Any]:
    """
    Format an exception into a user-friendly error message with suggestions.
    
    Args:
        exception: The exception that was raised
        include_exception_details: Whether to include the original exception details
        
    Returns:
        A dictionary with formatted error information
    """
    error_type, error_info = get_error_info(exception)
    
    formatted_error = {
        "type": error_type,
        "category": ERROR_CATEGORIES.get(error_info["category"], "Error"),
        "message": error_info["message"],
        "suggestion": error_info["suggestion"],
        "resolved": False
    }
    
    if include_exception_details:
        formatted_error["exception"] = {
            "type": type(exception).__name__,
            "message": str(exception)
        }
    
    return formatted_error

def format_error_html(exception: Exception, include_traceback: bool = False) -> str:
    """
    Format an exception into HTML for display in the web interface.
    
    Args:
        exception: The exception that was raised
        include_traceback: Whether to include the traceback
        
    Returns:
        HTML formatted error message
    """
    error_type, error_info = get_error_info(exception)
    category = ERROR_CATEGORIES.get(error_info["category"], "Error")
    
    html = f"""
    <div class="alert alert-danger">
        <h4 class="alert-heading">{category}</h4>
        <p><strong>{error_info["message"]}</strong></p>
        <hr>
        <p class="mb-0"><i class="bi bi-lightbulb"></i> <strong>Suggestion:</strong> {error_info["suggestion"]}</p>
    """
    
    if include_traceback:
        import traceback
        tb = traceback.format_exception(type(exception), exception, exception.__traceback__)
        html += f"""
        <hr>
        <p><strong>Technical Details:</strong></p>
        <pre class="text-muted">{exception.__class__.__name__}: {str(exception)}</pre>
        <details>
            <summary>Show Traceback</summary>
            <pre class="text-muted small">{"".join(tb)}</pre>
        </details>
        """
    
    html += "</div>"
    return html