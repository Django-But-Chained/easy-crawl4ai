#!/usr/bin/env python3
"""
Easy Crawl4AI Cross-Platform Web Interface - A user-friendly web interface for the crawl4ai web crawler

This script launches the web interface for Easy Crawl4AI, designed to work across Windows, macOS, and Linux.
"""

import os
import sys
import platform
import webbrowser
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
except ImportError:
    # Fallback if rich is not installed
    class Console:
        def print(self, text, **kwargs):
            print(text)
    
    def Panel(text, **kwargs):
        return text

# Create console for pretty output
console = Console()

def show_welcome_message():
    """Display a welcome message with information about the tool."""
    platform_name = platform.system()
    
    console.print("\n[bold cyan]Welcome to Easy Crawl4AI Web Interface (Cross-Platform)![/bold cyan]")
    console.print(f"Running on {platform_name} ({platform.version()})")
    console.print("A simplified tool for web crawling without technical expertise.\n")
    
    # Display platform-specific tips
    if platform_name == "Windows":
        console.print("[yellow]Windows Tips:[/yellow]")
        console.print("• If browser doesn't open automatically, visit: http://localhost:5000")
        console.print("• To stop the server, press CTRL+C in this window")
        console.print("• For browser-based crawling, install browsers with: playwright install")
    elif platform_name == "Darwin":  # macOS
        console.print("[yellow]macOS Tips:[/yellow]")
        console.print("• If browser doesn't open automatically, visit: http://localhost:5000")
        console.print("• To stop the server, press CTRL+C in this window")
        console.print("• For browser-based crawling, you may need to grant permissions")
    else:  # Linux and others
        console.print("[yellow]Linux Tips:[/yellow]")
        console.print("• If browser doesn't open automatically, visit: http://localhost:5000")
        console.print("• To stop the server, press CTRL+C in this window")
        console.print("• For browser-based crawling on headless servers, use --browser")


def check_dependencies():
    """Check if required dependencies are installed."""
    missing_deps = []
    
    try:
        import flask
    except ImportError:
        missing_deps.append("flask")
    
    try:
        import crawl4ai
    except ImportError:
        missing_deps.append("crawl4ai")
    
    try:
        import rich
    except ImportError:
        missing_deps.append("rich")
    
    try:
        import click
    except ImportError:
        missing_deps.append("click")
    
    if missing_deps:
        console.print("[bold red]Missing required dependencies:[/bold red]")
        for dep in missing_deps:
            console.print(f"- {dep}")
        
        # Provide installation instructions
        console.print("\nPlease install the missing dependencies with:")
        pip_cmd = "pip" if sys.platform != "win32" else "pip"
        console.print(f"[bold]{pip_cmd} install {' '.join(missing_deps)}[/bold]")
        
        if "crawl4ai" in missing_deps:
            console.print("\n[yellow]Note:[/yellow] crawl4ai is required for the core functionality.")
            console.print("To install it, run: [bold]pip install crawl4ai[/bold]")
        
        return False
    
    return True


def main():
    """Main function to run the web interface."""
    show_welcome_message()
    
    if not check_dependencies():
        console.print("\n[bold red]Cannot start the web interface due to missing dependencies.[/bold red]")
        return
    
    try:
        from easy_crawl4ai.crossplatform.web_app import app
        import threading
        import time
        
        # Get the host and port
        host = "0.0.0.0"  # Listen on all interfaces
        port = 5000
        
        # Create a function to open the browser after a short delay
        def open_browser():
            time.sleep(1.5)  # Wait for the server to start
            webbrowser.open(f"http://localhost:{port}")
        
        # Start a thread to open the browser
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        # Start the Flask application
        console.print(f"\n[green]Starting the web server on http://localhost:{port}[/green]")
        console.print("[yellow]Press CTRL+C to stop the server[/yellow]\n")
        
        app.run(host=host, port=port, debug=False)
    
    except Exception as e:
        console.print(f"[bold red]Error starting the web interface:[/bold red] {str(e)}")
        
        # Try to provide more helpful context based on the error
        if "Address already in use" in str(e):
            console.print("\nThe port 5000 is already in use. Possible solutions:")
            console.print("• Close other applications that might be using this port")
            console.print("• Wait a few moments and try again")
            console.print("• Modify the code to use a different port")
        elif "Permission" in str(e):
            console.print("\nPermission error. Possible solutions:")
            console.print("• On Linux/macOS, try running with sudo")
            console.print("• On Windows, try running as Administrator")
            console.print("• Check file and directory permissions")
        elif "ModuleNotFoundError" in str(e) or "ImportError" in str(e):
            console.print("\nMissing module. Possible solutions:")
            console.print("• Ensure all dependencies are installed: pip install -e .")
            console.print("• Try installing the specific missing module")


if __name__ == "__main__":
    main()