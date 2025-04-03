#!/usr/bin/env python3
"""
Easy Crawl4AI - A user-friendly CLI wrapper for the crawl4ai web crawler

This script provides a simplified interface to the powerful crawl4ai
web crawler library, making it accessible for users without technical expertise.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    import click
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
except ImportError:
    print("Required dependencies not installed. Please run: pip install click rich")
    print("Then restart the application.")
    sys.exit(1)

# Create a rich console for formatted output
console = Console()


def show_welcome_message():
    """Display a welcome message with information about the tool."""
    console.print(
        Panel(
            "[bold blue]Easy Crawl4AI[/bold blue] - A user-friendly web crawler for non-technical users\n\n"
            "This tool helps you extract content from websites in a simple, non-technical way.\n"
            "It's built on top of the powerful crawl4ai library.",
            title="Welcome",
            border_style="blue",
            expand=False,
        )
    )


def ensure_directory(directory: str) -> Path:
    """Ensure the directory exists and return the Path object."""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_result(result: Dict[str, Any], output_dir: str, format_type: str, filename: Optional[str] = None) -> str:
    """Save the crawl result to the specified directory with the given format."""
    # Ensure directory exists
    output_dir = ensure_directory(output_dir)
    
    # Generate filename if not provided
    if not filename:
        url = result.get('url', '')
        if url:
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace('.', '_')
            filename = f"{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            filename = f"crawl_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Add appropriate extension based on format
    if format_type == 'markdown' or format_type == 'md':
        filename = f"{filename}.md"
        content = result.get('markdown', '')
    elif format_type == 'html':
        filename = f"{filename}.html"
        content = result.get('html', '')
    elif format_type == 'text' or format_type == 'txt':
        filename = f"{filename}.txt"
        content = result.get('text', '')
    elif format_type == 'json':
        filename = f"{filename}.json"
        content = json.dumps(result, indent=2)
    else:
        # Default to markdown
        filename = f"{filename}.md"
        content = result.get('markdown', '')
    
    # Write content to file
    file_path = output_dir / filename
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return str(file_path)


def display_crawl_summary(result: Dict[str, Any], output_file: str):
    """Display a summary of the crawl result."""
    # Create a summary table
    table = Table(box=box.SIMPLE, show_header=False, border_style="blue")
    table.add_column("Property", style="cyan")
    table.add_column("Value")
    
    # Add basic information
    table.add_row("URL", result.get('url', 'N/A'))
    table.add_row("Title", result.get('title', 'N/A'))
    table.add_row("Content Length", str(len(result.get('text', ''))))
    table.add_row("Word Count", str(len(result.get('text', '').split())))
    table.add_row("Links Found", str(len(result.get('links', []))))
    table.add_row("Images Found", str(len(result.get('images', []))))
    table.add_row("Output File", output_file)
    
    # Display the table
    console.print(Panel(table, title="Crawl Summary", border_style="green"))


@click.group()
def cli():
    """Easy Crawl4AI - A user-friendly web crawler for non-technical users."""
    show_welcome_message()


@cli.command()
@click.argument('url')
@click.option('-o', '--output-dir', default='./results', help='Directory to save results')
@click.option('-f', '--format', default='markdown', type=click.Choice(['markdown', 'html', 'text', 'json']), help='Output format')
@click.option('-b', '--browser', is_flag=True, help='Use browser-based crawling (requires playwright)')
@click.option('-i', '--include-images', is_flag=True, default=True, help='Include images in output')
@click.option('-l', '--include-links', is_flag=True, default=True, help='Include links in output')
@click.option('--filename', help='Custom filename for the output file (without extension)')
@click.option('--wait', default=0, help='Time to wait for JavaScript rendering in seconds (with browser mode)')
@click.option('--selector', help='CSS selector to extract specific content')
@click.option('--max-retries', default=3, help='Maximum number of retry attempts')
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
        # Import crawl4ai here to avoid startup errors if not installed
        try:
            import crawl4ai
        except ImportError:
            console.print(
                "[bold red]Error:[/bold red] crawl4ai library is not installed.",
                "Please install it with: [bold]pip install crawl4ai[/bold]"
            )
            sys.exit(1)
        
        # Check for browser support if needed
        if browser:
            import importlib.util
            browser_module = importlib.util.find_spec('playwright')
            if not browser_module:
                console.print(
                    "[bold yellow]Warning:[/bold yellow] Browser-based crawling requires the 'playwright' module.",
                    "Install it with: [bold]pip install playwright[/bold] and [bold]playwright install[/bold]"
                )
                sys.exit(1)
        
        with console.status("[bold green]Crawling the URL...[/bold green]"):
            # Set up crawler with options
            crawler = crawl4ai.Crawler(
                use_browser=browser,
                include_images=include_images,
                include_links=include_links,
                wait_time=wait,
                selector=selector,
                max_retries=max_retries
            )
            
            # Crawl the URL
            result = crawler.crawl_url(url)
            
            # Save the result
            output_file = save_result(result, output_dir, format, filename)
        
        # Display crawl summary
        display_crawl_summary(result, output_file)
        
        console.print(f"[bold green]Success![/bold green] Result saved to: {output_file}")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument('urls', nargs=-1, required=True)
@click.option('-o', '--output-dir', default='./results', help='Directory to save results')
@click.option('-f', '--format', default='markdown', type=click.Choice(['markdown', 'html', 'text', 'json']), help='Output format')
@click.option('-b', '--browser', is_flag=True, help='Use browser-based crawling (requires playwright)')
@click.option('-i', '--include-images', is_flag=True, default=True, help='Include images in output')
@click.option('-l', '--include-links', is_flag=True, default=True, help='Include links in output')
@click.option('--wait', default=0, help='Time to wait for JavaScript rendering in seconds (with browser mode)')
@click.option('--selector', help='CSS selector to extract specific content')
@click.option('--max-retries', default=3, help='Maximum number of retry attempts')
@click.option('--concurrent', default=5, help='Number of concurrent requests')
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
    concurrent: int
):
    """
    Crawl multiple URLs and save the content.
    
    This command downloads content from multiple URLs in parallel and saves
    each result separately. It's useful for batch processing of web pages.
    
    Example:
        easy_crawl4ai crawl-multiple https://example.com https://another.com -o ./results
    """
    try:
        # Import crawl4ai here to avoid startup errors if not installed
        try:
            import crawl4ai
        except ImportError:
            console.print(
                "[bold red]Error:[/bold red] crawl4ai library is not installed.",
                "Please install it with: [bold]pip install crawl4ai[/bold]"
            )
            sys.exit(1)
        
        # Check for browser support if needed
        if browser:
            import importlib.util
            browser_module = importlib.util.find_spec('playwright')
            if not browser_module:
                console.print(
                    "[bold yellow]Warning:[/bold yellow] Browser-based crawling requires the 'playwright' module.",
                    "Install it with: [bold]pip install playwright[/bold] and [bold]playwright install[/bold]"
                )
                sys.exit(1)
        
        with console.status(f"[bold green]Crawling {len(urls)} URLs...[/bold green]"):
            # Set up crawler with options
            crawler = crawl4ai.Crawler(
                use_browser=browser,
                include_images=include_images,
                include_links=include_links,
                wait_time=wait,
                selector=selector,
                max_retries=max_retries
            )
            
            # Crawl the URLs
            results = crawler.crawl_urls(urls, max_concurrent=concurrent)
            
            # Save the results
            output_files = []
            for result in results:
                output_file = save_result(result, output_dir, format)
                output_files.append(output_file)
        
        # Display summary
        console.print(f"[bold green]Success![/bold green] Crawled {len(results)} URLs.")
        console.print(f"Results saved to: {output_dir}")
        
        # Display table of results
        table = Table(title="Crawl Results", box=box.SIMPLE)
        table.add_column("URL", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("File", style="blue")
        
        for result, output_file in zip(results, output_files):
            url = result.get('url', 'N/A')
            title = result.get('title', 'No title')
            table.add_row(url, title, os.path.basename(output_file))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument('url')
@click.option('-o', '--output-dir', default='./deep_results', help='Directory to save results')
@click.option('-f', '--format', default='markdown', type=click.Choice(['markdown', 'html', 'text', 'json']), help='Output format')
@click.option('-b', '--browser', is_flag=True, help='Use browser-based crawling (requires playwright)')
@click.option('-i', '--include-images', is_flag=True, default=True, help='Include images in output')
@click.option('-l', '--include-links', is_flag=True, default=True, help='Include links in output')
@click.option('-d', '--max-depth', default=2, help='Maximum crawl depth')
@click.option('-p', '--max-pages', default=10, help='Maximum pages to crawl')
@click.option('-s', '--stay-within-domain', is_flag=True, default=True, help='Stay within the original domain')
@click.option('--filename-prefix', default='page', help='Prefix for output filenames')
@click.option('--max-retries', default=3, help='Maximum number of retry attempts')
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
    max_retries: int
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
        # Import crawl4ai here to avoid startup errors if not installed
        try:
            import crawl4ai
        except ImportError:
            console.print(
                "[bold red]Error:[/bold red] crawl4ai library is not installed.",
                "Please install it with: [bold]pip install crawl4ai[/bold]"
            )
            sys.exit(1)
        
        # Check for browser support if needed
        if browser:
            import importlib.util
            browser_module = importlib.util.find_spec('playwright')
            if not browser_module:
                console.print(
                    "[bold yellow]Warning:[/bold yellow] Browser-based crawling requires the 'playwright' module.",
                    "Install it with: [bold]pip install playwright[/bold] and [bold]playwright install[/bold]"
                )
                sys.exit(1)
        
        with console.status(f"[bold green]Deep crawling from {url}...[/bold green]"):
            # Set up crawler with options
            crawler = crawl4ai.Crawler(
                use_browser=browser,
                include_images=include_images,
                include_links=include_links,
                stay_within_domain=stay_within_domain,
                max_retries=max_retries
            )
            
            # Perform deep crawl
            results = crawler.deep_crawl(
                start_url=url,
                max_depth=max_depth,
                max_pages=max_pages
            )
            
            # Save the results
            output_files = []
            for i, result in enumerate(results):
                filename = f"{filename_prefix}_{i+1}"
                output_file = save_result(result, output_dir, format, filename)
                output_files.append(output_file)
        
        # Display summary
        console.print(f"[bold green]Success![/bold green] Crawled {len(results)} pages.")
        console.print(f"Results saved to: {output_dir}")
        
        # Display table of results
        table = Table(title="Deep Crawl Results", box=box.SIMPLE)
        table.add_column("Page", style="cyan")
        table.add_column("URL", style="blue")
        table.add_column("Title", style="green")
        
        for i, (result, output_file) in enumerate(zip(results, output_files)):
            url = result.get('url', 'N/A')
            title = result.get('title', 'No title')
            table.add_row(str(i+1), url, title)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument('url')
@click.option('-o', '--output-dir', default='./downloads', help='Directory to save files')
@click.option('-t', '--file-types', default='pdf,doc,docx,xls,xlsx,ppt,pptx', help='Comma-separated list of file extensions to download')
@click.option('-m', '--max-size', default=100, help='Maximum file size in MB')
@click.option('-b', '--browser', is_flag=True, help='Use browser-based crawling (requires playwright)')
@click.option('-f', '--max-files', default=10, help='Maximum number of files to download')
def download_files(
    url: str,
    output_dir: str,
    file_types: str,
    max_size: int,
    browser: bool,
    max_files: int
):
    """
    Download files from a website.
    
    This command finds and downloads files (like PDFs, documents, etc.) from
    a website. It's useful for collecting documents or resources from a page.
    
    Example:
        easy_crawl4ai download-files https://example.com -o ./downloads -t pdf,docx
    """
    try:
        # Import crawl4ai here to avoid startup errors if not installed
        try:
            import crawl4ai
        except ImportError:
            console.print(
                "[bold red]Error:[/bold red] crawl4ai library is not installed.",
                "Please install it with: [bold]pip install crawl4ai[/bold]"
            )
            sys.exit(1)
        
        # Check for browser support if needed
        if browser:
            import importlib.util
            browser_module = importlib.util.find_spec('playwright')
            if not browser_module:
                console.print(
                    "[bold yellow]Warning:[/bold yellow] Browser-based crawling requires the 'playwright' module.",
                    "Install it with: [bold]pip install playwright[/bold] and [bold]playwright install[/bold]"
                )
                sys.exit(1)
        
        # Check for PDF support if downloading PDF files
        if 'pdf' in file_types.lower():
            import importlib.util
            pdf_module = importlib.util.find_spec('PyPDF2')
            if not pdf_module:
                console.print(
                    "[bold yellow]Warning:[/bold yellow] PDF processing requires the 'PyPDF2' module.",
                    "Files will be downloaded but content extraction may be limited.",
                    "Install it with: [bold]pip install PyPDF2[/bold]"
                )
        
        file_ext_list = [ext.strip() for ext in file_types.split(',')]
        
        with console.status(f"[bold green]Searching for files at {url}...[/bold green]"):
            # Set up crawler with options
            crawler = crawl4ai.Crawler(use_browser=browser)
            
            # Find files
            files = crawler.find_files(
                url=url,
                file_types=file_ext_list,
                max_size_mb=max_size,
                max_files=max_files
            )
            
            if not files:
                console.print("[yellow]No matching files found.[/yellow]")
                sys.exit(0)
            
            # Ensure output directory exists
            output_path = ensure_directory(output_dir)
            
            # Download files
            downloaded_files = []
            with console.status(f"[bold green]Downloading {len(files)} files...[/bold green]"):
                for file_url in files:
                    file_path = crawler.download_file(file_url, str(output_path))
                    if file_path:
                        downloaded_files.append(file_path)
        
        # Display summary
        console.print(f"[bold green]Success![/bold green] Downloaded {len(downloaded_files)} files.")
        console.print(f"Files saved to: {output_dir}")
        
        # Display table of downloaded files
        table = Table(title="Downloaded Files", box=box.SIMPLE)
        table.add_column("Filename", style="green")
        table.add_column("Source", style="blue")
        
        for file_path in downloaded_files:
            filename = os.path.basename(file_path)
            source = file_path.replace(str(output_path), '').strip('/')
            table.add_row(filename, source)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@cli.command()
def info():
    """
    Show information about crawl4ai and this wrapper.
    
    This command displays version information, features, and helpful tips
    about using the Easy Crawl4AI tool.
    """
    try:
        import crawl4ai
        crawl4ai_version = getattr(crawl4ai, "__version__", "unknown")
    except ImportError:
        crawl4ai_version = "not installed"
    
    from easy_crawl4ai import __version__ as tool_version
    
    # Create a panel with version information
    version_panel = Panel(
        f"Easy Crawl4AI version: [bold]{tool_version}[/bold]\n"
        f"crawl4ai version: [bold]{crawl4ai_version}[/bold]\n\n"
        "This tool is a user-friendly wrapper around the crawl4ai library,\n"
        "making it accessible for users without technical expertise.",
        title="Version Information",
        border_style="blue",
    )
    
    # Create a panel with feature information
    feature_panel = Panel(
        "[bold]Key Features:[/bold]\n\n"
        "• Single URL crawling - Extract content from a specific web page\n"
        "• Multiple URL crawling - Process multiple pages in parallel\n"
        "• Deep crawling - Follow links to explore websites thoroughly\n"
        "• File downloading - Find and download documents from websites\n"
        "• Multiple output formats - Save as Markdown, HTML, Text, or JSON\n"
        "• Browser-based crawling - Render JavaScript-heavy sites accurately",
        title="Features",
        border_style="cyan",
    )
    
    # Create a panel with optional dependencies
    dependencies_panel = Panel(
        "[bold]Optional Dependencies:[/bold]\n\n"
        "• [cyan]playwright[/cyan] - Required for browser-based crawling\n"
        "  [dim]pip install playwright && playwright install[/dim]\n\n"
        "• [cyan]PyPDF2[/cyan] - Enhanced PDF processing capabilities\n"
        "  [dim]pip install PyPDF2[/dim]\n\n"
        "• [cyan]openai + langchain[/cyan] - LLM integration for content processing\n"
        "  [dim]pip install openai langchain[/dim]\n\n"
        "• Install all at once: [dim]pip install \"crawl4ai[all]\"[/dim]",
        title="Optional Dependencies",
        border_style="green",
    )
    
    # Create a panel with usage tips
    tips_panel = Panel(
        "[bold]Usage Tips:[/bold]\n\n"
        "• Use [cyan]--browser[/cyan] for JavaScript-heavy sites (requires playwright)\n"
        "• Use [cyan]--format[/cyan] to specify the output format (markdown, html, text, json)\n"
        "• For deep crawling, use [cyan]-d/--max-depth[/cyan] to control how many links to follow\n"
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