#!/usr/bin/env python3
"""
Easy Crawl4AI - A user-friendly CLI wrapper for the crawl4ai web crawler

This script provides a simplified interface to the powerful crawl4ai
web crawler library, making it accessible for users without technical expertise.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# Check if required libraries are installed
try:
    import click
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    import crawl4ai
except ImportError:
    print("Error: Required libraries not found. Please install with:")
    print("pip install crawl4ai rich click")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Create rich console for formatted output
console = Console()

def show_welcome_message():
    """Display a welcome message with information about the tool."""
    console.print(Panel.fit(
        "[bold blue]Easy Crawl4AI[/bold blue] - A user-friendly web crawler\n\n"
        "This tool helps you extract content from websites without any technical knowledge.\n"
        "[green]✓[/green] Crawl single or multiple web pages\n"
        "[green]✓[/green] Save the content as markdown, text, or HTML\n"
        "[green]✓[/green] Customize how the content is extracted\n"
        "[green]✓[/green] Download files from websites",
        title="Welcome",
        border_style="blue"
    ))

def ensure_directory(directory: str) -> Path:
    """Ensure the directory exists and return the Path object."""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path

def save_result(result: Dict[str, Any], output_dir: str, format_type: str, filename: Optional[str] = None) -> str:
    """Save the crawl result to the specified directory with the given format."""
    # Create output directory if it doesn't exist
    dir_path = ensure_directory(output_dir)
    
    # Generate filename if not provided
    if not filename:
        url = result.get('url', 'unknown')
        # Create a safe filename from the URL
        import re
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('.', '_')
        path = parsed_url.path.replace('/', '_')
        if not path:
            path = '_index'
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', f"{domain}{path}")
        filename = f"{safe_name[:50]}"
    
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
        import json
        content = json.dumps(result, indent=2)
    else:
        # Default to markdown
        filename = f"{filename}.md"
        content = result.get('markdown', '')
    
    # Write content to file
    file_path = dir_path / filename
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return str(file_path)

def display_crawl_summary(result: Dict[str, Any], output_file: str):
    """Display a summary of the crawl result."""
    url = result.get('url', 'Unknown URL')
    title = result.get('title', 'No title')
    word_count = len(result.get('text', '').split())
    link_count = len(result.get('links', []))
    image_count = len(result.get('images', []))
    
    console.print(Panel.fit(
        f"[bold green]Successfully crawled:[/bold green] [link={url}]{url}[/link]\n\n"
        f"[bold]Title:[/bold] {title}\n"
        f"[bold]Word count:[/bold] {word_count}\n"
        f"[bold]Links found:[/bold] {link_count}\n"
        f"[bold]Images found:[/bold] {image_count}\n\n"
        f"[bold]Saved to:[/bold] [blue]{output_file}[/blue]",
        title="Crawl Summary",
        border_style="green"
    ))

@click.group()
def cli():
    """Easy Crawl4AI - A user-friendly web crawler for non-technical users."""
    show_welcome_message()

@cli.command()
@click.argument('url')
@click.option('--output-dir', '-o', default='./results', help='Directory to save results')
@click.option('--format', '-f', default='markdown', type=click.Choice(['markdown', 'md', 'html', 'text', 'txt', 'json']), help='Output format')
@click.option('--browser/--no-browser', default=False, help='Use browser-based crawling for JavaScript-heavy sites')
@click.option('--include-images/--no-images', default=True, help='Include image descriptions in the output')
@click.option('--include-links/--no-links', default=True, help='Include hyperlinks in the output')
@click.option('--filename', help='Custom filename for the output (without extension)')
@click.option('--wait', default=0, help='Wait time in seconds for dynamic content to load')
@click.option('--selector', help='CSS selector to extract specific content from the page')
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
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Crawling... [bold green]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(url, total=None)
        
        try:
            crawler = crawl4ai.Crawler(
                use_browser=browser,
                include_images=include_images,
                include_links=include_links,
                wait_time=wait,
                selector=selector,
                max_retries=max_retries
            )
            
            result = crawler.crawl_url(url)
            progress.update(task, completed=True)
            
            output_file = save_result(result, output_dir, format, filename)
            display_crawl_summary(result, output_file)
            
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            sys.exit(1)

@cli.command()
@click.argument('urls', nargs=-1, required=True)
@click.option('--output-dir', '-o', default='./results', help='Directory to save results')
@click.option('--format', '-f', default='markdown', type=click.Choice(['markdown', 'md', 'html', 'text', 'txt', 'json']), help='Output format')
@click.option('--browser/--no-browser', default=False, help='Use browser-based crawling for JavaScript-heavy sites')
@click.option('--include-images/--no-images', default=True, help='Include image descriptions in the output')
@click.option('--include-links/--no-links', default=True, help='Include hyperlinks in the output')
@click.option('--wait', default=0, help='Wait time in seconds for dynamic content to load')
@click.option('--selector', help='CSS selector to extract specific content from the page')
@click.option('--max-retries', default=3, help='Maximum number of retry attempts')
@click.option('--concurrent', '-c', default=5, help='Number of URLs to crawl concurrently')
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
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Crawling multiple URLs... [progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("Processing", total=len(urls))
        
        try:
            crawler = crawl4ai.Crawler(
                use_browser=browser,
                include_images=include_images,
                include_links=include_links,
                wait_time=wait,
                selector=selector,
                max_retries=max_retries,
                concurrent_requests=concurrent
            )
            
            results = crawler.crawl_urls(list(urls))
            
            for i, result in enumerate(results):
                output_file = save_result(result, output_dir, format)
                progress.update(task, advance=1)
            
            console.print(f"[bold green]Successfully crawled {len(results)} URLs[/bold green]")
            console.print(f"Results saved to: [blue]{output_dir}[/blue]")
            
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            sys.exit(1)

@cli.command()
@click.argument('url')
@click.option('--output-dir', '-o', default='./deep_results', help='Directory to save results')
@click.option('--format', '-f', default='markdown', type=click.Choice(['markdown', 'md', 'html', 'text', 'txt', 'json']), help='Output format')
@click.option('--browser/--no-browser', default=False, help='Use browser-based crawling for JavaScript-heavy sites')
@click.option('--include-images/--no-images', default=True, help='Include image descriptions in the output')
@click.option('--include-links/--no-links', default=True, help='Include hyperlinks in the output')
@click.option('--max-depth', '-d', default=2, help='Maximum depth for crawling')
@click.option('--max-pages', '-p', default=10, help='Maximum number of pages to crawl')
@click.option('--stay-within-domain/--explore-external', default=True, help='Restrict crawling to the same domain')
@click.option('--filename-prefix', default='page_', help='Prefix for generated filenames')
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
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Deep crawling... [progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("Processing", total=max_pages)
        
        try:
            crawler = crawl4ai.Crawler(
                use_browser=browser,
                include_images=include_images,
                include_links=include_links,
                stay_within_domain=stay_within_domain,
                max_retries=max_retries
            )
            
            results = crawler.deep_crawl(
                start_url=url,
                max_depth=max_depth,
                max_pages=max_pages
            )
            
            for i, result in enumerate(results):
                output_file = save_result(
                    result, 
                    output_dir, 
                    format, 
                    f"{filename_prefix}{i+1}"
                )
                progress.update(task, advance=1)
            
            console.print(f"[bold green]Successfully crawled {len(results)} pages[/bold green]")
            console.print(f"Results saved to: [blue]{output_dir}[/blue]")
            
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            sys.exit(1)

@cli.command()
@click.argument('url')
@click.option('--output-dir', '-o', default='./downloads', help='Directory to save downloaded files')
@click.option('--file-types', '-t', default='pdf,doc,docx,xls,xlsx,ppt,pptx', help='Comma-separated list of file extensions to download')
@click.option('--max-size', '-s', default=100, help='Maximum file size in MB')
@click.option('--browser/--no-browser', default=False, help='Use browser-based crawling for JavaScript-heavy sites')
@click.option('--max-files', '-m', default=10, help='Maximum number of files to download')
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
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Searching for files... [bold green]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(url, total=None)
        
        try:
            file_ext_list = [ext.strip() for ext in file_types.split(',')]
            
            crawler = crawl4ai.Crawler(use_browser=browser)
            
            files = crawler.find_files(
                url=url,
                file_types=file_ext_list,
                max_size_mb=max_size,
                max_files=max_files
            )
            
            progress.update(task, completed=True)
            
            if not files:
                console.print("[yellow]No matching files found[/yellow]")
                return
            
            # Create output directory
            ensure_directory(output_dir)
            
            # Download files
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]Downloading files... [progress.percentage]{task.percentage:>3.0f}%"),
                console=console
            ) as download_progress:
                download_task = download_progress.add_task("Downloading", total=len(files))
                
                for file_url in files:
                    crawler.download_file(file_url, output_dir)
                    download_progress.update(download_task, advance=1)
            
            console.print(f"[bold green]Successfully downloaded {len(files)} files[/bold green]")
            console.print(f"Files saved to: [blue]{output_dir}[/blue]")
            
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
        version = crawl4ai.__version__
    except:
        version = "Unknown"
    
    console.print(Panel.fit(
        f"[bold blue]Easy Crawl4AI[/bold blue] - A user-friendly wrapper for crawl4ai\n\n"
        f"[bold]crawl4ai version:[/bold] {version}\n\n"
        "[bold]Available commands:[/bold]\n"
        "  [green]crawl[/green] - Download content from a single URL\n"
        "  [green]crawl-multiple[/green] - Download content from multiple URLs\n"
        "  [green]deep-crawl[/green] - Follow links and crawl multiple pages\n"
        "  [green]download-files[/green] - Download files from a website\n"
        "  [green]info[/green] - Show this information\n\n"
        "[bold]Examples:[/bold]\n"
        "  easy_crawl4ai crawl https://example.com -o ./results\n"
        "  easy_crawl4ai deep-crawl https://example.com -d 2 -p 5\n"
        "  easy_crawl4ai download-files https://example.com -t pdf,docx\n\n"
        "[bold]For more information:[/bold]\n"
        "  Use --help with any command to see detailed options\n"
        "  Example: easy_crawl4ai crawl --help",
        title="About Easy Crawl4AI",
        border_style="blue"
    ))
    
    # Display compatibility information for common websites
    console.print(Panel.fit(
        "[bold]Compatibility Tips:[/bold]\n\n"
        "[green]Good compatibility:[/green]\n"
        "  - Wikipedia, news sites, blogs, documentation sites\n"
        "  - Most static content websites\n\n"
        "[yellow]May require browser mode:[/yellow]\n"
        "  - Social media platforms (Twitter, LinkedIn)\n"
        "  - Dynamic websites with JavaScript content\n"
        "  - Use the --browser flag for these sites\n\n"
        "[red]Limited compatibility:[/red]\n"
        "  - Sites with strict anti-scraping measures\n"
        "  - Sites requiring login (would need additional configuration)",
        title="Website Compatibility",
        border_style="yellow"
    ))
    
    # Display the web interface information if available
    try:
        import flask
        console.print(Panel.fit(
            "[bold]Web Interface Available[/bold]\n\n"
            "For an easier graphical interface, you can use:\n"
            "  [green]python easy_crawl4ai_web.py[/green]\n\n"
            "Then open your web browser and visit:\n"
            "  [blue]http://localhost:5000[/blue]",
            title="Web Interface",
            border_style="green"
        ))
    except ImportError:
        pass

if __name__ == "__main__":
    try:
        cli()
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)