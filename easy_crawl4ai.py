#!/usr/bin/env python3
"""
Easy Crawl4AI - A user-friendly CLI wrapper for the crawl4ai web crawler

This script provides a simplified interface to the powerful crawl4ai
web crawler library, making it accessible for users without technical expertise.
"""

import os
import sys
import time
import click
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    # Import the crawl4ai library
    from crawl4ai import WebCrawler, AsyncWebCrawler
    from crawl4ai.config import CrawlerConfig, BrowserCrawlerConfig
    from crawl4ai.processor import MarkdownProcessor
    from crawl4ai.utils.url import URLPatternFilter
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.table import Table
    from rich.markdown import Markdown
    from rich import print as rprint
except ImportError:
    print("Error: Required libraries not found. Please install with:")
    print("pip install crawl4ai rich click")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Create rich console for pretty output
console = Console()

def show_welcome_message():
    """Display a welcome message with information about the tool."""
    welcome_text = """
    # Easy Crawl4AI

    A user-friendly wrapper for the powerful crawl4ai web crawler.
    
    This tool helps you extract content from websites without any technical knowledge.
    
    ## What can you do?
    
    - Crawl single or multiple web pages
    - Save the content as markdown, text, or HTML
    - Customize how the content is extracted
    - Download files from websites
    
    Use --help with any command to see more options.
    """
    
    console.print(Panel(Markdown(welcome_text), title="Welcome to Easy Crawl4AI", border_style="blue"))

def ensure_directory(directory: str) -> Path:
    """Ensure the directory exists and return the Path object."""
    path = Path(directory)
    if not path.exists():
        path.mkdir(parents=True)
        console.print(f"Created directory: [bold green]{path}[/]")
    return path

def save_result(result: Dict[str, Any], output_dir: str, format_type: str, filename: Optional[str] = None) -> str:
    """Save the crawl result to the specified directory with the given format."""
    output_path = ensure_directory(output_dir)
    
    # Generate a filename if not provided
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        domain = result.get("domain", "website")
        filename = f"{domain}_{timestamp}"
    
    # Save the content based on the format
    if format_type == "markdown":
        file_path = output_path / f"{filename}.md"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(result.get("markdown", ""))
    elif format_type == "html":
        file_path = output_path / f"{filename}.html"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(result.get("html", ""))
    elif format_type == "text":
        file_path = output_path / f"{filename}.txt"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(result.get("text", ""))
    elif format_type == "json":
        import json
        file_path = output_path / f"{filename}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
    else:
        raise ValueError(f"Unsupported format: {format_type}")
    
    return str(file_path)

def display_crawl_summary(result: Dict[str, Any], output_file: str):
    """Display a summary of the crawl result."""
    table = Table(title="Crawl Summary")
    
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("URL", result.get("url", "N/A"))
    table.add_row("Title", result.get("title", "N/A"))
    table.add_row("Content Length", str(len(result.get("text", ""))) + " characters")
    table.add_row("Links Found", str(len(result.get("links", []))))
    table.add_row("Output File", output_file)
    
    console.print(table)

@click.group()
def cli():
    """Easy Crawl4AI - A user-friendly web crawler for non-technical users."""
    pass

@cli.command("crawl")
@click.argument("url", required=True)
@click.option(
    "--output-dir", "-o", 
    default="./crawl_results",
    help="Directory where crawl results will be saved."
)
@click.option(
    "--format", "-f",
    type=click.Choice(["markdown", "html", "text", "json"]), 
    default="markdown",
    help="Output format for the crawled content."
)
@click.option(
    "--browser/--no-browser", 
    default=False,
    help="Use browser-based crawling (for JavaScript-heavy websites)."
)
@click.option(
    "--include-images/--no-images", 
    default=True,
    help="Include image descriptions in the output."
)
@click.option(
    "--include-links/--no-links", 
    default=True,
    help="Include links in the output."
)
@click.option(
    "--filename", "-n",
    help="Custom filename for the output (without extension)."
)
@click.option(
    "--wait", "-w",
    type=int, 
    default=0,
    help="Wait time in seconds after page load (for JavaScript rendering)."
)
@click.option(
    "--selector", "-s",
    help="CSS selector to extract specific content (e.g., 'main', '.content')."
)
@click.option(
    "--max-retries", 
    type=int, 
    default=3,
    help="Maximum number of retry attempts for failed requests."
)
def crawl_single(
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
    with console.status("[bold green]Setting up crawler...") as status:
        try:
            # Configure the crawler
            config = BrowserCrawlerConfig() if browser else CrawlerConfig()
            config.include_images = include_images
            config.include_links = include_links
            config.max_retries = max_retries
            
            if selector:
                config.content_selector = selector
            
            # Create the crawler
            crawler = WebCrawler(config=config)
            status.update("[bold green]Crawling website...")
            
            # Perform the crawl
            result = crawler.run(url)
            
            # Wait if specified
            if wait > 0:
                status.update(f"[bold yellow]Waiting {wait} seconds for JavaScript rendering...")
                time.sleep(wait)
            
            # Save the result
            status.update("[bold blue]Saving results...")
            output_file = save_result(result, output_dir, format, filename)
            
        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/]")
            sys.exit(1)
    
    # Display summary
    display_crawl_summary(result, output_file)
    console.print(f"[bold green]Success![/] Content saved to: {output_file}")

@cli.command("crawl-multiple")
@click.argument("urls", nargs=-1, required=True)
@click.option(
    "--output-dir", "-o", 
    default="./crawl_results",
    help="Directory where crawl results will be saved."
)
@click.option(
    "--format", "-f",
    type=click.Choice(["markdown", "html", "text", "json"]), 
    default="markdown",
    help="Output format for the crawled content."
)
@click.option(
    "--browser/--no-browser", 
    default=False,
    help="Use browser-based crawling (for JavaScript-heavy websites)."
)
@click.option(
    "--include-images/--no-images", 
    default=True,
    help="Include image descriptions in the output."
)
@click.option(
    "--include-links/--no-links", 
    default=True,
    help="Include links in the output."
)
@click.option(
    "--wait", "-w",
    type=int, 
    default=0,
    help="Wait time in seconds after page load (for JavaScript rendering)."
)
@click.option(
    "--selector", "-s",
    help="CSS selector to extract specific content (e.g., 'main', '.content')."
)
@click.option(
    "--max-retries", 
    type=int, 
    default=3,
    help="Maximum number of retry attempts for failed requests."
)
@click.option(
    "--concurrent", "-c",
    type=int, 
    default=5,
    help="Number of URLs to crawl concurrently."
)
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
    if not urls:
        console.print("[bold red]Error: No URLs provided[/]")
        return
    
    with console.status("[bold green]Setting up crawler...") as status:
        try:
            # Configure the crawler
            config = BrowserCrawlerConfig() if browser else CrawlerConfig()
            config.include_images = include_images
            config.include_links = include_links
            config.max_retries = max_retries
            
            if selector:
                config.content_selector = selector
            
            # Create the async crawler
            crawler = AsyncWebCrawler(config=config, concurrency=concurrent)
            
            # Prepare for crawling
            total_urls = len(urls)
            status.update(f"[bold green]Crawling {total_urls} websites concurrently...")
            
            # Perform the crawl
            results = crawler.run_many(urls)
            
            # Wait if specified
            if wait > 0:
                status.update(f"[bold yellow]Waiting {wait} seconds for JavaScript rendering...")
                time.sleep(wait)
            
            # Save the results
            status.update("[bold blue]Saving results...")
            output_files = []
            for result in results:
                if result:
                    output_file = save_result(result, output_dir, format)
                    output_files.append((result.get("url", "Unknown URL"), output_file))
            
        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/]")
            sys.exit(1)
    
    # Display summary
    table = Table(title=f"Crawl Results for {len(output_files)} URLs")
    table.add_column("URL", style="cyan")
    table.add_column("Output File", style="green")
    
    for url, output_file in output_files:
        table.add_row(url, output_file)
    
    console.print(table)
    console.print(f"[bold green]Success![/] All content saved to: {output_dir}")

@cli.command("deep-crawl")
@click.argument("url", required=True)
@click.option(
    "--output-dir", "-o", 
    default="./crawl_results",
    help="Directory where crawl results will be saved."
)
@click.option(
    "--format", "-f",
    type=click.Choice(["markdown", "html", "text", "json"]), 
    default="markdown",
    help="Output format for the crawled content."
)
@click.option(
    "--browser/--no-browser", 
    default=False,
    help="Use browser-based crawling (for JavaScript-heavy websites)."
)
@click.option(
    "--include-images/--no-images", 
    default=True,
    help="Include image descriptions in the output."
)
@click.option(
    "--include-links/--no-links", 
    default=True,
    help="Include links in the output."
)
@click.option(
    "--max-depth", "-d",
    type=int, 
    default=2,
    help="Maximum depth for crawling (1 = only the provided URL)."
)
@click.option(
    "--max-pages", "-p",
    type=int, 
    default=10,
    help="Maximum number of pages to crawl."
)
@click.option(
    "--stay-within-domain/--explore-external",
    default=True,
    help="Whether to stay within the same domain or explore external links."
)
@click.option(
    "--filename-prefix", "-n",
    default="deep_crawl",
    help="Prefix for the output filenames."
)
@click.option(
    "--max-retries", 
    type=int, 
    default=3,
    help="Maximum number of retry attempts for failed requests."
)
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
    with console.status("[bold green]Setting up deep crawler...") as status:
        try:
            from urllib.parse import urlparse
            
            # Parse the domain for filtering
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Configure the crawler
            config = BrowserCrawlerConfig() if browser else CrawlerConfig()
            config.include_images = include_images
            config.include_links = include_links
            config.max_retries = max_retries
            
            # Set up URL pattern filter if staying within domain
            url_filter = None
            if stay_within_domain:
                url_filter = URLPatternFilter(allow_patterns=[f"https?://{domain}.*"])
            
            # Create a processor for the output format
            processor = MarkdownProcessor()
            
            # Prepare for crawling
            status.update(f"[bold green]Starting deep crawl from {url}...")
            
            # Use crawl4ai's deep crawling capabilities
            from crawl4ai.deep import DeepCrawler
            
            # Create the deep crawler
            deep_crawler = DeepCrawler(
                config=config,
                processor=processor,
                max_depth=max_depth,
                max_pages=max_pages,
                url_filter=url_filter
            )
            
            # Perform the deep crawl
            results = deep_crawler.run(url)
            
            # Create progress bar for saving
            status.update("[bold blue]Saving results...")
            
        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/]")
            sys.exit(1)
    
    # Save results with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        task = progress.add_task("[bold green]Saving crawled pages...", total=len(results))
        
        output_files = []
        for i, result in enumerate(results):
            if result:
                try:
                    filename = f"{filename_prefix}_{i+1}"
                    output_file = save_result(result, output_dir, format, filename)
                    output_files.append((result.get("url", "Unknown URL"), output_file))
                except Exception as e:
                    console.print(f"[bold yellow]Warning: Failed to save result for a page: {str(e)}[/]")
            progress.update(task, advance=1)
    
    # Display summary
    table = Table(title=f"Deep Crawl Results ({len(output_files)} pages)")
    table.add_column("URL", style="cyan", no_wrap=False)
    table.add_column("Output File", style="green")
    
    for url, output_file in output_files:
        table.add_row(url, os.path.basename(output_file))
    
    console.print(table)
    console.print(f"[bold green]Success![/] All content saved to: {output_dir}")

@cli.command("download-files")
@click.argument("url", required=True)
@click.option(
    "--output-dir", "-o", 
    default="./downloads",
    help="Directory where files will be downloaded."
)
@click.option(
    "--file-types", "-t",
    default="pdf,doc,docx,xls,xlsx,ppt,pptx,csv,zip",
    help="Comma-separated list of file extensions to download."
)
@click.option(
    "--max-size", "-s",
    type=int, 
    default=100,
    help="Maximum file size in MB."
)
@click.option(
    "--browser/--no-browser", 
    default=False,
    help="Use browser-based crawling (for JavaScript-heavy websites)."
)
@click.option(
    "--max-files", "-m",
    type=int, 
    default=10,
    help="Maximum number of files to download."
)
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
    with console.status("[bold green]Setting up file downloader...") as status:
        try:
            # Configure the crawler
            config = BrowserCrawlerConfig() if browser else CrawlerConfig()
            
            # Set up file extensions to look for
            extensions = [ext.strip() for ext in file_types.split(",")]
            
            # Create the crawler
            crawler = WebCrawler(config=config)
            
            # Crawl to get links
            status.update(f"[bold green]Scanning {url} for files...")
            result = crawler.run(url)
            
            # Extract links that match file extensions
            links = result.get("links", [])
            file_links = []
            
            for link in links:
                link_url = link.get("url", "")
                if any(link_url.lower().endswith(f".{ext.lower()}") for ext in extensions):
                    file_links.append(link_url)
            
            # Limit number of files
            file_links = file_links[:max_files]
            
            status.update(f"[bold blue]Found {len(file_links)} files to download...")
            
        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/]")
            sys.exit(1)
    
    # Download files with progress bar
    output_path = ensure_directory(output_dir)
    
    if not file_links:
        console.print("[bold yellow]No matching files found to download.[/]")
        return
    
    from crawl4ai.asset import AssetDownloader
    downloader = AssetDownloader(
        max_size_mb=max_size,
        dest_dir=str(output_path)
    )
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        download_task = progress.add_task("[bold green]Downloading files...", total=len(file_links))
        
        downloaded = []
        skipped = []
        
        for file_url in file_links:
            try:
                # Update progress description
                filename = os.path.basename(file_url)
                progress.update(download_task, description=f"[bold blue]Downloading {filename}...")
                
                # Download the file
                success = downloader.download(file_url)
                
                if success:
                    downloaded.append((file_url, os.path.join(output_dir, os.path.basename(file_url))))
                else:
                    skipped.append((file_url, "Size limit exceeded or download failed"))
                    
            except Exception as e:
                skipped.append((file_url, str(e)))
                
            progress.update(download_task, advance=1)
    
    # Display summary
    if downloaded:
        table = Table(title=f"Downloaded Files ({len(downloaded)})")
        table.add_column("File", style="cyan")
        table.add_column("Saved To", style="green")
        
        for url, path in downloaded:
            table.add_row(os.path.basename(url), path)
        
        console.print(table)
    
    if skipped:
        table = Table(title=f"Skipped Files ({len(skipped)})")
        table.add_column("File", style="yellow")
        table.add_column("Reason", style="red")
        
        for url, reason in skipped:
            table.add_row(os.path.basename(url), reason)
        
        console.print(table)
    
    console.print(f"[bold green]Download Complete![/] {len(downloaded)} files saved to: {output_dir}")

@cli.command("info")
def show_info():
    """
    Show information about crawl4ai and this wrapper.
    
    This command displays version information, features, and helpful tips
    about using the Easy Crawl4AI tool.
    """
    # Get crawl4ai version
    try:
        import crawl4ai
        version = getattr(crawl4ai, "__version__", "Unknown")
    except (ImportError, AttributeError):
        version = "Not installed"
    
    info_text = f"""
    # Easy Crawl4AI Information
    
    ## Version Information
    - crawl4ai version: {version}
    - Easy Crawl4AI version: 1.0.0
    
    ## Available Commands
    - `crawl`: Crawl a single URL
    - `crawl-multiple`: Crawl multiple URLs in parallel
    - `deep-crawl`: Follow links and crawl pages recursively
    - `download-files`: Download files from a website
    - `info`: Show this information
    
    ## Getting Help
    Use `--help` with any command to see detailed options.
    
    Example: `easy_crawl4ai crawl --help`
    
    ## Common Options
    - `--output-dir`, `-o`: Where to save results
    - `--format`, `-f`: Output format (markdown, html, text, json)
    - `--browser/--no-browser`: Use browser-based crawler for JavaScript sites
    
    ## Tips for Non-Technical Users
    - Start with the `crawl` command for a single page
    - Use `deep-crawl` to explore a website more thoroughly
    - The `download-files` command is great for getting documents
    - Markdown format (default) is usually the best option
    - Use the browser mode (`--browser`) for modern, JavaScript-heavy websites
    """
    
    console.print(Panel(Markdown(info_text), title="Easy Crawl4AI Information", border_style="green"))

if __name__ == "__main__":
    show_welcome_message()
    cli()
