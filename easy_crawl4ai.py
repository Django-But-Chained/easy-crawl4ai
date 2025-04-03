#!/usr/bin/env python3
"""
Easy Crawl4AI - A user-friendly CLI wrapper for the crawl4ai web crawler

This script provides a simplified interface to the powerful crawl4ai
web crawler library, making it accessible for users without technical expertise.
"""

# Entry point to run the CLI directly without installing the package
try:
    # First, try to import from the installed package
    from easy_crawl4ai import cli
except ImportError:
    # If not installed as a package, import from the local module
    from easy_crawl4ai.cli import cli

if __name__ == "__main__":
    cli()