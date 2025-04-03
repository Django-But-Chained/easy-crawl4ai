#!/usr/bin/env python3
"""
Easy Crawl4AI Web - A user-friendly web interface for the crawl4ai web crawler

This script provides a simplified web interface to the powerful crawl4ai
web crawler library, making it accessible for users without technical expertise.
"""

import os
import sys
import logging
from pathlib import Path

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
    print("For more information, see the README.md file.\n")

def check_dependencies():
    """Check if required dependencies are installed."""
    missing_dependencies = []
    
    try:
        import flask
    except ImportError:
        missing_dependencies.append("flask")
    
    try:
        import crawl4ai
    except ImportError:
        missing_dependencies.append("crawl4ai")
    
    try:
        import rich
    except ImportError:
        missing_dependencies.append("rich")
    
    try:
        import click
    except ImportError:
        missing_dependencies.append("click")
    
    if missing_dependencies:
        print(f"Error: Required libraries not found - {', '.join(missing_dependencies)}")
        print("Please install all required dependencies with:")
        print("pip install crawl4ai rich click flask")
        return False
    
    return True

def main():
    """Main function to run the web interface."""
    show_welcome_message()
    
    if not check_dependencies():
        sys.exit(1)
    
    print("Starting the web interface...")
    print("Access it at: http://localhost:5000 or your Replit URL")
    
    try:
        # Import Flask app and run it
        from main import app
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"Error starting web interface: {str(e)}")
        print("Please make sure main.py is configured correctly.")
        sys.exit(1)

if __name__ == "__main__":
    main()