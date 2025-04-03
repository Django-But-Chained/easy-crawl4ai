#!/usr/bin/env python3
"""
Easy Crawl4AI - A user-friendly CLI wrapper for the crawl4ai web crawler

This script provides a simplified interface to the powerful crawl4ai
web crawler library, making it accessible for users without technical expertise.
This version is designed to work across Windows, macOS, and Linux.
"""

import os
import sys
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

try:
    import click
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import print as rprint
except ImportError:
    print("Required dependencies not found. Please install with: pip install click rich")
    sys.exit(1)

# Global console for rich output
console = Console()

def show_welcome_message():
    """Display a welcome message with information about the tool."""
    console.print("\n[bold cyan]Welcome to Easy Crawl4AI![/bold cyan]")
    console.print("A simplified tool for web crawling without technical expertise.\n")


def ensure_directory(directory: str) -> Path:
    """Ensure the directory exists and return the Path object."""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_result(result: Dict[str, Any], output_dir: str, format_type: str, filename: Optional[str] = None) -> str:
    """Save the crawl result to the specified directory with the given format."""
    # Create a valid filename if none is provided
    if not filename:
        safe_url = result.get("url", "unknown").replace("://", "_").replace("/", "_").replace("?", "_")
        safe_url = "".join(c for c in safe_url if c.isalnum() or c in "_-.")[:50]  # Limit length and restrict to safe chars
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_url}_{timestamp}"
    
    # Ensure filename has proper extension
    if not filename.endswith(f".{format_type}"):
        filename = f"{filename}.{format_type}"
    
    # Create the output directory if it doesn't exist
    output_path = ensure_directory(output_dir)
    
    # Full path to the output file
    file_path = os.path.join(output_path, filename)
    
    # Save the result in the specified format
    if format_type == "json":
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    else:
        # For text, markdown, and html formats, get the appropriate content
        if format_type == "markdown":
            content = result.get("markdown", "")
        elif format_type == "html":
            content = result.get("html", "")
        else:  # default to text
            content = result.get("text", "")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return file_path


def display_crawl_summary(result: Dict[str, Any], output_file: str):
    """Display a summary of the crawl result."""
    # Create a table for the summary
    table = Table(title="Crawl Summary", show_header=True, header_style="bold magenta")
    table.add_column("Property", style="cyan")
    table.add_column("Value")
    
    # Add rows to the table
    table.add_row("URL", result.get("url", "Unknown"))
    table.add_row("Title", result.get("title", "Unknown"))
    table.add_row("Content Length", str(len(result.get("text", ""))))
    table.add_row("Word Count", str(len(result.get("text", "").split())))
    table.add_row("Link Count", str(len(result.get("links", []))))
    table.add_row("Image Count", str(len(result.get("images", []))))
    table.add_row("Output File", output_file)
    
    # Print the table
    console.print(table)
    
    # Indicate success
    console.print(f"\n[green]✓[/green] Successfully crawled and saved to: [bold]{output_file}[/bold]\n")


@click.group()
@click.version_option(message="Easy Crawl4AI Version: %(version)s")
def cli():
    """Easy Crawl4AI - A user-friendly web crawler for non-technical users."""
    show_welcome_message()


@cli.command()
@click.argument('url')
@click.option('-o', '--output-dir', default='./results', 
              help='Directory to save results (default: ./results)')
@click.option('-f', '--format', default='markdown', 
              type=click.Choice(['markdown', 'html', 'text', 'json']),
              help='Output format (default: markdown)')
@click.option('-b', '--browser', is_flag=True, 
              help='Use browser-based crawling for JavaScript-heavy sites')
@click.option('--include-images/--no-images', default=True, 
              help='Include images in the output (default: include)')
@click.option('--include-links/--no-links', default=True, 
              help='Include links in the output (default: include)')
@click.option('-n', '--filename', 
              help='Custom filename for the output (without extension)')
@click.option('-w', '--wait', default=0, type=int,
              help='Time to wait in seconds after page load (for dynamic content)')
@click.option('-s', '--selector', 
              help='CSS selector to extract specific content')
@click.option('-r', '--max-retries', default=3, type=int,
              help='Maximum number of retry attempts if the crawl fails')
def crawl(
    url: str, 
    output_dir: str, 
    format: str, 
    browser: bool, 
    include_images: bool, 
    include_links: bool,
    filename: Optional[str],
    wait: int,
    selector: Optional[str],
    max_retries: int
):
    """
    Crawl a single URL and save the content.
    
    This command downloads the content from a single URL and saves it in the
    specified format. It's perfect for quick retrieval of information from
    a specific web page.
    
    Example:
        easy_crawl4ai crawl https://example.com -o ./my_results -f markdown
    """
    try:
        # Show a progress message
        with console.status(f"[bold green]Crawling {url}...[/bold green]", spinner="dots"):
            try:
                # Import crawl4ai here to allow the CLI to work even if crawl4ai is not installed
                # Users will get a helpful error message when they try to use a command that requires it
                from crawl4ai import arun
                from crawl4ai.config import CrawlerRunConfig
            except ImportError:
                console.print("[bold red]Error:[/bold red] The crawl4ai package is not installed.")
                console.print("Please install it with: [bold]pip install crawl4ai[/bold]")
                return
            
            # Create a configuration for the crawler
            config = CrawlerRunConfig(
                url=url,
                use_browser=browser,
                include_images=include_images,
                include_links=include_links,
                wait_time=wait,
                selector=selector,
                max_retries=max_retries
            )
            
            # Crawl the URL with the async function, but run it synchronously
            import asyncio
            if sys.platform.startswith('win'):
                # Windows-specific event loop policy
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            result = asyncio.run(arun(config))
            
            # Save the result to a file
            output_file = save_result(result, output_dir, format, filename)
            
        # Display a summary of the crawl
        display_crawl_summary(result, output_file)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        
        # Try to provide more helpful context based on the error
        if "Timeout" in str(e):
            console.print("\nThe request timed out. Possible solutions:")
            console.print("• Check your internet connection")
            console.print("• The website might be down or too slow")
            console.print("• Try increasing the timeout with --timeout option")
        elif "SSL" in str(e):
            console.print("\nSSL certificate verification failed. Possible solutions:")
            console.print("• The website might have an invalid certificate")
            console.print("• Try using the --browser option which might handle this better")
        elif "Connection" in str(e):
            console.print("\nConnection error. Possible solutions:")
            console.print("• Check your internet connection")
            console.print("• The website might be blocking automated requests")
            console.print("• Try using the --browser option")
        elif "Permission" in str(e) and sys.platform != 'win32':
            console.print("\nPermission error. Possible solutions:")
            console.print(f"• Check if you have write permission in the directory: {output_dir}")
            console.print(f"• Try running: chmod -R 755 {output_dir}")


@cli.command()
@click.argument('urls', nargs=-1, required=True)
@click.option('-o', '--output-dir', default='./results', 
              help='Directory to save results (default: ./results)')
@click.option('-f', '--format', default='markdown', 
              type=click.Choice(['markdown', 'html', 'text', 'json']),
              help='Output format (default: markdown)')
@click.option('-b', '--browser', is_flag=True, 
              help='Use browser-based crawling for JavaScript-heavy sites')
@click.option('--include-images/--no-images', default=True, 
              help='Include images in the output (default: include)')
@click.option('--include-links/--no-links', default=True, 
              help='Include links in the output (default: include)')
@click.option('-w', '--wait', default=0, type=int,
              help='Time to wait in seconds after page load (for dynamic content)')
@click.option('-s', '--selector', 
              help='CSS selector to extract specific content')
@click.option('-r', '--max-retries', default=3, type=int,
              help='Maximum number of retry attempts if the crawl fails')
@click.option('-c', '--concurrent', default=3, type=int,
              help='Number of URLs to crawl concurrently (default: 3)')
@click.option('--random-delay/--no-random-delay', default=False,
              help='Add random delays between requests to avoid rate limiting')
@click.option('--random-delay-min', default=1, type=int,
              help='Minimum delay in seconds when using random delay (default: 1)')
@click.option('--random-delay-max', default=5, type=int,
              help='Maximum delay in seconds when using random delay (default: 5)')
@click.option('--adaptive-delay/--no-adaptive-delay', default=False,
              help='Automatically adjust delay based on server response time')
@click.option('--adaptive-factor', default=2, type=int,
              help='Multiplication factor for adaptive delay (default: 2)')
@click.option('--scheduled-breaks/--no-scheduled-breaks', default=False,
              help='Take periodic breaks during crawling to avoid overloading servers')
@click.option('--requests-before-break', default=50, type=int,
              help='Number of requests before taking a break (default: 50)')
@click.option('--break-duration', default=30, type=int,
              help='Duration of breaks in seconds (default: 30)')
def crawl_multiple(
    urls: List[str], 
    output_dir: str, 
    format: str, 
    browser: bool, 
    include_images: bool, 
    include_links: bool,
    wait: int,
    selector: Optional[str],
    max_retries: int,
    concurrent: int,
    random_delay: bool,
    random_delay_min: int,
    random_delay_max: int,
    adaptive_delay: bool,
    adaptive_factor: int,
    scheduled_breaks: bool,
    requests_before_break: int,
    break_duration: int
):
    """
    Crawl multiple URLs and save the content.
    
    This command downloads content from multiple URLs in parallel and saves
    each result separately. It's useful for batch processing of web pages.
    
    Example:
        easy_crawl4ai crawl-multiple https://example.com https://another.com -o ./results
    """
    try:
        # Show progress
        with console.status(f"[bold green]Crawling {len(urls)} URLs...[/bold green]", spinner="dots"):
            try:
                # Import crawl4ai here to allow the CLI to work even if crawl4ai is not installed
                from crawl4ai import arun_many
                from crawl4ai.config import CrawlerRunConfig, DispatcherConfig
            except ImportError:
                console.print("[bold red]Error:[/bold red] The crawl4ai package is not installed.")
                console.print("Please install it with: [bold]pip install crawl4ai[/bold]")
                return
            
            # Create configuration for crawler
            configs = [
                CrawlerRunConfig(
                    url=url,
                    use_browser=browser,
                    include_images=include_images,
                    include_links=include_links,
                    wait_time=wait,
                    selector=selector,
                    max_retries=max_retries
                ) 
                for url in urls
            ]
            
            # Create configuration for dispatcher
            dispatcher_config = DispatcherConfig(
                max_concurrent_tasks=concurrent,
                use_random_delay=random_delay,
                random_delay_min_seconds=random_delay_min,
                random_delay_max_seconds=random_delay_max,
                use_adaptive_delay=adaptive_delay,
                adaptive_delay_factor=adaptive_factor,
                use_scheduled_breaks=scheduled_breaks,
                requests_before_break=requests_before_break,
                break_duration_seconds=break_duration
            )
            
            # Crawl all URLs
            import asyncio
            if sys.platform.startswith('win'):
                # Windows-specific event loop policy
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            results = asyncio.run(arun_many(configs, dispatcher_config=dispatcher_config))
            
            # Save each result
            output_files = []
            for i, result in enumerate(results):
                if result:  # Some results might be None if there was an error
                    output_file = save_result(result, output_dir, format)
                    output_files.append((result.get("url", f"URL {i+1}"), output_file))
        
        # Display summary
        console.print(f"\n[green]✓[/green] Successfully crawled [bold]{len(output_files)}/{len(urls)}[/bold] URLs\n")
        
        # Create a table with results
        table = Table(title="Crawl Results", show_header=True, header_style="bold magenta")
        table.add_column("URL", style="cyan")
        table.add_column("Output File")
        
        for url, file in output_files:
            table.add_row(url, file)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@cli.command()
@click.argument('url')
@click.option('-o', '--output-dir', default='./results', 
              help='Directory to save results (default: ./results)')
@click.option('-f', '--format', default='markdown', 
              type=click.Choice(['markdown', 'html', 'text', 'json']),
              help='Output format (default: markdown)')
@click.option('-b', '--browser', is_flag=True, 
              help='Use browser-based crawling for JavaScript-heavy sites')
@click.option('--include-images/--no-images', default=True, 
              help='Include images in the output (default: include)')
@click.option('--include-links/--no-links', default=True, 
              help='Include links in the output (default: include)')
@click.option('-d', '--max-depth', default=2, type=int,
              help='Maximum link depth to crawl (default: 2)')
@click.option('-p', '--max-pages', default=20, type=int,
              help='Maximum number of pages to crawl (default: 20)')
@click.option('--stay-within-domain/--allow-external-domains', default=True,
              help='Stay within the same domain when crawling (default: stay within domain)')
@click.option('--filename-prefix', default='page', 
              help='Prefix for generated filenames (default: "page")')
@click.option('-r', '--max-retries', default=3, type=int,
              help='Maximum number of retry attempts if the crawl fails')
@click.option('--random-delay/--no-random-delay', default=True,
              help='Add random delays between requests to avoid rate limiting (default: enabled)')
@click.option('--random-delay-min', default=1, type=int,
              help='Minimum delay in seconds when using random delay (default: 1)')
@click.option('--random-delay-max', default=5, type=int,
              help='Maximum delay in seconds when using random delay (default: 5)')
@click.option('--adaptive-delay/--no-adaptive-delay', default=True,
              help='Automatically adjust delay based on server response time (default: enabled)')
@click.option('--adaptive-factor', default=2, type=int,
              help='Multiplication factor for adaptive delay (default: 2)')
@click.option('--scheduled-breaks/--no-scheduled-breaks', default=True,
              help='Take periodic breaks during crawling to avoid overloading servers (default: enabled)')
@click.option('--requests-before-break', default=50, type=int,
              help='Number of requests before taking a break (default: 50)')
@click.option('--break-duration', default=30, type=int,
              help='Duration of breaks in seconds (default: 30)')
def deep_crawl(
    url: str, 
    output_dir: str, 
    format: str, 
    browser: bool, 
    include_images: bool, 
    include_links: bool,
    max_depth: int,
    max_pages: int,
    stay_within_domain: bool,
    filename_prefix: str,
    max_retries: int,
    random_delay: bool,
    random_delay_min: int,
    random_delay_max: int,
    adaptive_delay: bool,
    adaptive_factor: int,
    scheduled_breaks: bool,
    requests_before_break: int,
    break_duration: int
):
    """
    Perform deep crawling starting from a URL.
    
    This command crawls not only the provided URL but also follows links
    to discover and crawl additional pages. It's great for exploring websites
    more thoroughly.
    
    Example:
        easy_crawl4ai deep-crawl https://example.com -d 3 -p 20 -o ./deep_results
    """
    try:
        # Show progress
        with console.status(f"[bold green]Deep crawling from {url}...[/bold green]", spinner="dots"):
            try:
                # Import crawl4ai here to allow the CLI to work even if crawl4ai is not installed
                from crawl4ai import adeep_crawl
                from crawl4ai.config import DeepCrawlConfig, DispatcherConfig
            except ImportError:
                console.print("[bold red]Error:[/bold red] The crawl4ai package is not installed.")
                console.print("Please install it with: [bold]pip install crawl4ai[/bold]")
                return
            
            # Create configuration for deep crawler
            config = DeepCrawlConfig(
                start_url=url,
                use_browser=browser,
                include_images=include_images,
                include_links=include_links,
                max_depth=max_depth,
                max_pages=max_pages,
                stay_within_domain=stay_within_domain,
                max_retries=max_retries
            )
            
            # Create configuration for dispatcher
            dispatcher_config = DispatcherConfig(
                use_random_delay=random_delay,
                random_delay_min_seconds=random_delay_min,
                random_delay_max_seconds=random_delay_max,
                use_adaptive_delay=adaptive_delay,
                adaptive_delay_factor=adaptive_factor,
                use_scheduled_breaks=scheduled_breaks,
                requests_before_break=requests_before_break,
                break_duration_seconds=break_duration
            )
            
            # Perform deep crawl
            import asyncio
            if sys.platform.startswith('win'):
                # Windows-specific event loop policy
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            results = asyncio.run(adeep_crawl(config, dispatcher_config=dispatcher_config))
            
            # Save each result
            output_files = []
            for i, result in enumerate(results):
                if result:  # Some results might be None if there was an error
                    filename = f"{filename_prefix}_{i+1}"
                    output_file = save_result(result, output_dir, format, filename)
                    output_files.append((result.get("url", f"URL {i+1}"), output_file))
        
        # Display summary
        console.print(f"\n[green]✓[/green] Successfully crawled [bold]{len(output_files)}[/bold] pages starting from {url}\n")
        
        # Create a table with results
        table = Table(title="Deep Crawl Results", show_header=True, header_style="bold magenta")
        table.add_column("URL", style="cyan")
        table.add_column("Output File")
        
        for url, file in output_files:
            table.add_row(url, file)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        if "max_depth" in str(e):
            console.print("\nThere was an issue with the crawl depth. Try:")
            console.print("• Setting a smaller max_depth value (1-3 is often reasonable)")
        elif "max_pages" in str(e):
            console.print("\nThere was an issue with the maximum pages. Try:")
            console.print("• Setting a smaller max_pages value to limit the crawl scope")
        

@cli.command()
@click.argument('url')
@click.option('-o', '--output-dir', default='./downloads', 
              help='Directory to save downloaded files (default: ./downloads)')
@click.option('-t', '--file-types', default='pdf,docx,xlsx,pptx,txt', 
              help='Comma-separated list of file extensions to download (default: pdf,docx,xlsx,pptx,txt)')
@click.option('-m', '--max-size', default=50, type=int,
              help='Maximum file size in MB to download (default: 50MB)')
@click.option('-b', '--browser', is_flag=True, 
              help='Use browser-based crawling for JavaScript-heavy sites')
@click.option('-f', '--max-files', default=20, type=int,
              help='Maximum number of files to download (default: 20)')
@click.option('--random-delay/--no-random-delay', default=True,
              help='Add random delays between requests to avoid rate limiting (default: enabled)')
@click.option('--random-delay-min', default=1, type=int,
              help='Minimum delay in seconds when using random delay (default: 1)')
@click.option('--random-delay-max', default=5, type=int,
              help='Maximum delay in seconds when using random delay (default: 5)')
@click.option('--adaptive-delay/--no-adaptive-delay', default=True,
              help='Automatically adjust delay based on server response time (default: enabled)')
@click.option('--adaptive-factor', default=2, type=int,
              help='Multiplication factor for adaptive delay (default: 2)')
@click.option('--scheduled-breaks/--no-scheduled-breaks', default=True,
              help='Take periodic breaks during downloading to avoid overloading servers (default: enabled)')
@click.option('--requests-before-break', default=20, type=int,
              help='Number of requests before taking a break (default: 20)')
@click.option('--break-duration', default=30, type=int,
              help='Duration of breaks in seconds (default: 30)')
def download_files(
    url: str,
    output_dir: str,
    file_types: str,
    max_size: int,
    browser: bool,
    max_files: int,
    random_delay: bool,
    random_delay_min: int,
    random_delay_max: int,
    adaptive_delay: bool,
    adaptive_factor: int,
    scheduled_breaks: bool,
    requests_before_break: int,
    break_duration: int
):
    """
    Download files from a website.
    
    This command finds and downloads files (like PDFs, documents, etc.) from
    a website. It's useful for collecting documents or resources from a page.
    
    Example:
        easy_crawl4ai download-files https://example.com -o ./downloads -t pdf,docx
    """
    try:
        # Create the output directory
        ensure_directory(output_dir)
        
        # Show progress
        with console.status(f"[bold green]Finding files to download from {url}...[/bold green]", spinner="dots"):
            try:
                # Import crawl4ai here to allow the CLI to work even if crawl4ai is not installed
                from crawl4ai import adownload_files
                from crawl4ai.config import DownloadConfig, DispatcherConfig
            except ImportError:
                console.print("[bold red]Error:[/bold red] The crawl4ai package is not installed.")
                console.print("Please install it with: [bold]pip install crawl4ai[/bold]")
                return
            
            # Split file types
            file_extensions = [ext.strip() for ext in file_types.split(',')]
            
            # Create configuration for file downloader
            config = DownloadConfig(
                url=url,
                file_types=file_extensions,
                max_file_size_mb=max_size,
                use_browser=browser,
                max_files=max_files
            )
            
            # Create configuration for dispatcher
            dispatcher_config = DispatcherConfig(
                use_random_delay=random_delay,
                random_delay_min_seconds=random_delay_min,
                random_delay_max_seconds=random_delay_max,
                use_adaptive_delay=adaptive_delay,
                adaptive_delay_factor=adaptive_factor,
                use_scheduled_breaks=scheduled_breaks,
                requests_before_break=requests_before_break,
                break_duration_seconds=break_duration
            )
            
            # Perform the file downloads
            import asyncio
            if sys.platform.startswith('win'):
                # Windows-specific event loop policy
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            downloaded_files = asyncio.run(
                adownload_files(config, output_dir, dispatcher_config=dispatcher_config)
            )
        
        # Display summary
        if downloaded_files:
            console.print(f"\n[green]✓[/green] Successfully downloaded [bold]{len(downloaded_files)}[/bold] files from {url}\n")
            
            # Create a table with results
            table = Table(title="Downloaded Files", show_header=True, header_style="bold magenta")
            table.add_column("File Name", style="cyan")
            table.add_column("Size")
            table.add_column("Source URL")
            
            for file_info in downloaded_files:
                file_path = file_info.get("file_path", "Unknown")
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                
                # Format file size
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
                source_url = file_info.get("url", "Unknown")
                table.add_row(file_name, size_str, source_url)
            
            console.print(table)
        else:
            console.print(f"\n[yellow]No files found or downloaded from {url}[/yellow]")
            console.print("Try:")
            console.print("• Checking if the website contains files of the specified types")
            console.print("• Using --browser option if the site uses JavaScript")
            console.print("• Adjusting the --file-types option to include other file extensions")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        if "permission" in str(e).lower():
            console.print("\nPermission error. Try:")
            console.print(f"• Checking if you have write permission in: {output_dir}")
            console.print(f"• Using a different output directory with --output-dir")
        elif "not a directory" in str(e).lower():
            console.print("\nThe specified output path is not a directory. Try:")
            console.print("• Specifying a different path for --output-dir")
            console.print("• Ensuring the parent directory exists")


@cli.command()
def info():
    """
    Show information about crawl4ai and this wrapper.
    
    This command displays version information, features, and helpful tips
    about using the Easy Crawl4AI tool.
    """
    try:
        import crawl4ai
        crawl4ai_version = crawl4ai.__version__
        crawler_available = True
    except ImportError:
        crawl4ai_version = "Not installed"
        crawler_available = False
    
    from easy_crawl4ai.crossplatform import __version__ as easy_crawl4ai_version
    
    # Create a panel for version information
    version_panel = Panel(
        f"Easy Crawl4AI (Cross-Platform): [bold cyan]{easy_crawl4ai_version}[/bold cyan]\n"
        f"crawl4ai: [bold {'green' if crawler_available else 'red'}]{crawl4ai_version}[/bold]\n"
        f"Platform: [bold]{sys.platform}[/bold]\n"
        f"Python: [bold]{sys.version.split()[0]}[/bold]",
        title="Version Information",
        border_style="blue",
    )
    
    # Create a panel for features
    feature_panel = Panel(
        "[bold]Features:[/bold]\n\n"
        "• Single URL crawling with customizable output\n"
        "• Multiple URL batch processing\n"
        "• Deep crawling with link following\n"
        "• File downloading from websites\n"
        "• Browser-based crawling for JavaScript-heavy sites\n"
        "• Markdown, HTML, Text, and JSON output formats\n"
        "• Cross-platform support for Windows, macOS, and Linux\n"
        "• Speed control with adaptive delays and scheduled breaks",
        title="Features",
        border_style="green",
    )
    
    # Create a panel for optional dependencies
    dependencies_panel = Panel(
        "[bold]Optional Dependencies:[/bold]\n\n"
        "• [cyan]playwright[/cyan]: Required for browser-based crawling\n"
        "  Install with: [yellow]pip install playwright && playwright install[/yellow]\n"
        "• [cyan]pypdf2[/cyan]: Enables PDF content extraction\n"
        "  Install with: [yellow]pip install pypdf2[/yellow]",
        title="Optional Dependencies",
        border_style="green",
    )
    
    # Create a panel with usage tips
    tips_panel = Panel(
        "[bold]Usage Tips:[/bold]\n\n"
        "• Use [cyan]--browser[/cyan] for JavaScript-heavy sites (requires playwright)\n"
        "• Use [cyan]--format[/cyan] to specify the output format (markdown, html, text, json)\n"
        "• For deep crawling, use [cyan]-d/--max-depth[/cyan] to control how many links to follow\n"
        "• Use [cyan]--random-delay[/cyan] to add random delays between requests\n"
        "• Use [cyan]--adaptive-delay[/cyan] to automatically adjust delay based on response time\n"
        "• Use [cyan]--scheduled-breaks[/cyan] to pause periodically during large crawls\n"
        "• On Windows, run [cyan]asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())[/cyan] \n"
        "  before running async functions if you experience 'RuntimeError: Event loop is closed'\n"
        "• Use [cyan]--help[/cyan] with any command to see all available options\n\n"
        "[bold]For a web interface:[/bold] Run [cyan]easy_crawl4ai_web[/cyan] from command line",
        title="Usage Tips",
        border_style="yellow",
    )
    
    # Print all panels
    console.print(version_panel)
    console.print(feature_panel)
    console.print(dependencies_panel)
    console.print(tips_panel)


if __name__ == "__main__":
    cli()