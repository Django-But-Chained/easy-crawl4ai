#!/usr/bin/env python3
"""
Easy Crawl4AI Web - A user-friendly web interface for the crawl4ai web crawler

This script provides a simplified web interface to the powerful crawl4ai
web crawler library, making it accessible for users without technical expertise.
"""

import os
import sys
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def show_welcome_message():
    """Display a welcome message with information about the tool."""
    print("\n=== Easy Crawl4AI Web Interface ===\n")
    print("A user-friendly wrapper for the powerful crawl4ai web crawler.")
    print("This tool helps you extract content from websites without any technical knowledge.\n")
    print("Features:")
    print("- Crawl single or multiple web pages")
    print("- Save the content as markdown, text, or HTML")
    print("- Customize how the content is extracted")
    print("- Download files from websites\n")
    print("To use the web interface, open your browser and visit: http://localhost:5000")
    print("Or access it via your Replit URL\n")


def check_dependencies():
    """Check if required dependencies are installed."""
    missing_dependencies = []
    
    try:
        import flask
    except ImportError:
        missing_dependencies.append("flask")
    
    try:
        import flask_sqlalchemy
    except ImportError:
        missing_dependencies.append("flask-sqlalchemy")
    
    try:
        import sqlalchemy
    except ImportError:
        missing_dependencies.append("sqlalchemy")
    
    try:
        import crawl4ai
    except ImportError:
        print("Warning: crawl4ai library is not installed. The application will start, but crawling functionality will be limited.")
        print("Please install with: pip install crawl4ai")
    
    if missing_dependencies:
        print(f"Error: Required libraries not found - {', '.join(missing_dependencies)}")
        print("Please install the required dependencies with:")
        print(f"pip install {' '.join(missing_dependencies)}")
        return False
    
    return True


def main():
    """Main function to run the web interface."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Easy Crawl4AI Web Interface")
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--database', default=None, help='Database URL (e.g., sqlite:///crawl4ai.db)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    # Show welcome message
    show_welcome_message()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Set up database environment variable if provided
    if args.database:
        os.environ['DATABASE_URL'] = args.database
    
    print("Starting the web interface...")
    print(f"Access it at: http://{args.host}:{args.port} or your Replit URL")
    
    # Import the web app
    try:
        # First try to import from the package
        try:
            from easy_crawl4ai.web import app
        except ImportError:
            # If that fails, try to import from the current directory
            from main import app
        
        # Run the app
        app.run(host=args.host, port=args.port, debug=args.debug)
    except Exception as e:
        logger.error(f"Error starting the web interface: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()