#!/usr/bin/env python3
"""
Easy Crawl4AI Web Interface launcher - A user-friendly web interface for the crawl4ai web crawler
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
    print("=" * 80)
    print("Easy Crawl4AI Web Interface - A user-friendly web crawler for non-technical users")
    print("=" * 80)
    print("This tool helps you extract content from websites in a simple, non-technical way.")
    print("It's built on top of the powerful crawl4ai library.")
    print("\nStarting the web interface...")


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import flask
        import flask_sqlalchemy
        import sqlalchemy
    except ImportError:
        print("Required dependencies not installed.")
        print("Please run: pip install flask flask-sqlalchemy sqlalchemy")
        print("Then restart the application.")
        sys.exit(1)
    
    try:
        import crawl4ai
    except ImportError:
        print("Warning: crawl4ai library is not installed.")
        print("The application will start, but crawling functionality will be limited.")
        print("Please install with: pip install crawl4ai")


def main():
    """Main function to run the web interface."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Easy Crawl4AI Web Interface")
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--database', default=None, help='Database URL (e.g., sqlite:///crawl4ai.db)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    # Check dependencies
    check_dependencies()
    
    # Show welcome message
    show_welcome_message()
    
    # Set up database environment variable if provided
    if args.database:
        os.environ['DATABASE_URL'] = args.database
    
    # Import the web app from the local web module
    try:
        from easy_crawl4ai.web import app, init_db
        
        # Initialize the database
        init_db()
        
        # Run the app
        app.run(host=args.host, port=args.port, debug=args.debug)
    except Exception as e:
        logger.error(f"Error starting the web interface: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()