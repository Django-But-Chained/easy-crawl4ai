#!/usr/bin/env python3
"""
Easy Crawl4AI Web Interface - A user-friendly web interface for the crawl4ai web crawler
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

try:
    from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
except ImportError:
    print("Flask is not installed. Please install with: pip install flask")
    print("Then restart the application.")
    sys.exit(1)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", os.urandom(24).hex())

# Default directories
RESULTS_DIR = Path('./results')
DOWNLOADS_DIR = Path('./downloads')

def ensure_directory(directory: Path) -> Path:
    """Ensure the directory exists and return the Path object."""
    directory.mkdir(parents=True, exist_ok=True)
    return directory

# Ensure directories exist
ensure_directory(RESULTS_DIR)
ensure_directory(DOWNLOADS_DIR)

@app.route('/')
def home():
    """Home page route"""
    return render_template('index.html')

@app.route('/crawl', methods=['POST'])
def run_crawl():
    """Run the crawler with the provided options"""
    # Get form data
    crawl_type = request.form.get('crawl_type', 'single')
    url = request.form.get('url', '')
    urls = request.form.get('urls', '').split('\n') if request.form.get('urls') else []
    output_format = request.form.get('format', 'markdown')
    use_browser = request.form.get('use_browser') == 'on'
    include_images = request.form.get('include_images') == 'on'
    include_links = request.form.get('include_links') == 'on'
    output_dir = request.form.get('output_dir', str(RESULTS_DIR))
    
    # Validate input
    if crawl_type == 'single' and not url:
        flash('Please enter a URL', 'error')
        return redirect(url_for('home'))
    
    if crawl_type == 'multiple' and not urls:
        flash('Please enter at least one URL', 'error')
        return redirect(url_for('home'))
    
    # Clean up URLs (remove empty lines)
    if crawl_type == 'multiple':
        urls = [u.strip() for u in urls if u.strip()]
    
    # Additional options for deep crawl
    max_depth = int(request.form.get('max_depth', 2))
    max_pages = int(request.form.get('max_pages', 10))
    stay_within_domain = request.form.get('stay_within_domain') == 'on'
    
    # Additional options for file download
    file_types = request.form.get('file_types', 'pdf,doc,docx,xls,xlsx,ppt,pptx')
    max_size = int(request.form.get('max_size', 100))
    max_files = int(request.form.get('max_files', 10))
    
    # Create output directory
    output_path = Path(output_dir)
    ensure_directory(output_path)
    
    try:
        # Import crawl4ai here to avoid startup errors if not installed
        try:
            import crawl4ai
        except ImportError:
            flash('crawl4ai library is not installed. Please install with: pip install crawl4ai', 'error')
            return redirect(url_for('home'))
        
        # Set up crawler with common options
        crawler = crawl4ai.Crawler(
            use_browser=use_browser,
            include_images=include_images,
            include_links=include_links,
            stay_within_domain=(stay_within_domain if crawl_type == 'deep' else True)
        )
        
        results = []
        output_files = []
        
        # Execute based on crawl type
        if crawl_type == 'single':
            # Single URL crawl
            result = crawler.crawl_url(url)
            results = [result]
            
            # Generate filename from URL
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace('.', '_')
            filename = f"{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Save result
            output_file = save_result(result, output_path, output_format, filename)
            output_files = [output_file]
            
        elif crawl_type == 'multiple':
            # Multiple URLs crawl
            results = crawler.crawl_urls(urls)
            
            # Save each result
            for i, result in enumerate(results):
                url = result.get('url', f'unknown_{i}')
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.replace('.', '_')
                filename = f"{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                output_file = save_result(result, output_path, output_format, filename)
                output_files.append(output_file)
                
        elif crawl_type == 'deep':
            # Deep crawl
            results = crawler.deep_crawl(
                start_url=url,
                max_depth=max_depth,
                max_pages=max_pages
            )
            
            # Save each result
            for i, result in enumerate(results):
                filename = f"page_{i+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                output_file = save_result(result, output_path, output_format, filename)
                output_files.append(output_file)
                
        elif crawl_type == 'files':
            # File download
            file_ext_list = [ext.strip() for ext in file_types.split(',')]
            files = crawler.find_files(
                url=url,
                file_types=file_ext_list,
                max_size_mb=max_size,
                max_files=max_files
            )
            
            if not files:
                flash('No matching files found', 'warning')
                return redirect(url_for('home'))
            
            # Download files
            for file_url in files:
                file_path = crawler.download_file(file_url, str(output_path))
                if file_path:
                    output_files.append(file_path)
        
        # Flash success message
        if crawl_type == 'files':
            flash(f'Successfully downloaded {len(output_files)} files', 'success')
        else:
            flash(f'Successfully crawled {len(results)} pages', 'success')
        
        # Return results list page
        return render_template(
            'results.html',
            crawl_type=crawl_type,
            results=results,
            output_files=output_files,
            output_dir=str(output_path)
        )
        
    except Exception as e:
        logger.error(f"Crawling error: {str(e)}")
        flash(f'Error during crawling: {str(e)}', 'error')
        return redirect(url_for('home'))

def save_result(result, output_dir, format_type, filename):
    """Save the crawl result to the specified directory with the given format."""
    # Ensure directory exists
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
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

@app.route('/download/<path:filename>')
def download_file(filename):
    """Download a specific file."""
    return send_from_directory(RESULTS_DIR, filename, as_attachment=True)

@app.route('/view/<path:filename>')
def view_file(filename):
    """View a specific file."""
    file_path = Path(RESULTS_DIR) / filename
    
    if not file_path.exists():
        flash(f'File not found: {filename}', 'error')
        return redirect(url_for('home'))
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Determine file type
    if filename.endswith('.md'):
        # This template would include a Markdown renderer
        return render_template('view_markdown.html', filename=filename, content=content)
    elif filename.endswith('.html'):
        # This displays the HTML in an iframe or directly
        return render_template('view_html.html', filename=filename, content=content)
    elif filename.endswith('.json'):
        # Pretty-print JSON
        try:
            pretty_json = json.dumps(json.loads(content), indent=4)
            return render_template('view_json.html', filename=filename, content=pretty_json)
        except json.JSONDecodeError:
            return render_template('view_text.html', filename=filename, content=content)
    else:
        # Plain text view
        return render_template('view_text.html', filename=filename, content=content)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)