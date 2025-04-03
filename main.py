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

# Import app and database
from app import app, db
from models import CrawlJob, CrawlResult, Setting

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

@app.route('/jobs')
def job_list():
    """List all crawl jobs"""
    jobs = CrawlJob.query.order_by(CrawlJob.created_at.desc()).all()
    return render_template('jobs.html', jobs=jobs)

@app.route('/job/<int:job_id>')
def job_detail(job_id):
    """View a specific job and its results"""
    job = CrawlJob.query.get_or_404(job_id)
    results = CrawlResult.query.filter_by(job_id=job_id).all()
    return render_template('job_detail.html', job=job, results=results)

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
    
    # Create a new job record
    job = CrawlJob(
        crawl_type=crawl_type,
        url=url if crawl_type != 'multiple' else None,
        urls=urls if crawl_type == 'multiple' else None,
        output_dir=str(output_path),
        format=output_format,
        use_browser=use_browser,
        include_images=include_images,
        include_links=include_links,
        max_depth=max_depth if crawl_type == 'deep' else None,
        max_pages=max_pages if crawl_type == 'deep' else None,
        stay_within_domain=stay_within_domain if crawl_type == 'deep' else None,
        file_types=file_types if crawl_type == 'files' else None,
        max_size=max_size if crawl_type == 'files' else None,
        max_files=max_files if crawl_type == 'files' else None,
        status='running',
        created_at=datetime.utcnow()
    )
    
    # Save the job to the database
    db.session.add(job)
    db.session.commit()
    
    try:
        # Import crawl4ai here to avoid startup errors if not installed
        try:
            import crawl4ai
        except ImportError:
            job.status = 'failed'
            job.error_message = 'crawl4ai library is not installed'
            db.session.commit()
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
            
            # Save result to database
            save_result_to_db(job.id, result, output_file)
            
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
                
                # Save result to database
                save_result_to_db(job.id, result, output_file)
                
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
                
                # Save result to database
                save_result_to_db(job.id, result, output_file)
                
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
                job.status = 'completed'
                job.completed_at = datetime.utcnow()
                job.files_downloaded = 0
                db.session.commit()
                
                flash('No matching files found', 'warning')
                return redirect(url_for('job_detail', job_id=job.id))
            
            # Download files
            for file_url in files:
                file_path = crawler.download_file(file_url, str(output_path))
                if file_path:
                    output_files.append(file_path)
        
        # Update job status
        job.status = 'completed'
        job.completed_at = datetime.utcnow()
        job.pages_crawled = len(results)
        job.files_downloaded = len(output_files) if crawl_type == 'files' else 0
        db.session.commit()
        
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
            output_dir=str(output_path),
            job_id=job.id
        )
        
    except Exception as e:
        logger.error(f"Crawling error: {str(e)}")
        
        # Update job status
        job.status = 'failed'
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.session.commit()
        
        flash(f'Error during crawling: {str(e)}', 'error')
        return redirect(url_for('job_detail', job_id=job.id))

def save_result_to_db(job_id, result, output_file):
    """Save a crawl result to the database"""
    try:
        db_result = CrawlResult(
            job_id=job_id,
            url=result.get('url', ''),
            title=result.get('title', ''),
            output_file=output_file,
            content_length=len(result.get('text', '')),
            word_count=len(result.get('text', '').split()),
            link_count=len(result.get('links', [])),
            image_count=len(result.get('images', [])),
            created_at=datetime.utcnow()
        )
        db.session.add(db_result)
        db.session.commit()
    except Exception as e:
        logger.error(f"Error saving result to database: {str(e)}")

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

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """View and edit application settings"""
    if request.method == 'POST':
        # Update settings
        for key, value in request.form.items():
            if key.startswith('setting_'):
                setting_key = key[8:]  # Remove 'setting_' prefix
                setting = Setting.query.filter_by(key=setting_key).first()
                if setting:
                    setting.value = value
                else:
                    setting = Setting(key=setting_key, value=value)
                    db.session.add(setting)
        
        db.session.commit()
        flash('Settings updated successfully', 'success')
        return redirect(url_for('settings'))
    
    # Get all settings
    all_settings = Setting.query.all()
    return render_template('settings.html', settings=all_settings)

# Initialize default settings if they don't exist
def init_default_settings():
    """Initialize default settings"""
    default_settings = {
        'default_output_dir': './results',
        'default_format': 'markdown',
        'max_concurrent_jobs': '5',
        'enable_browser_crawling': 'true',
        'default_max_depth': '3',
        'default_max_pages': '20',
        'default_file_types': 'pdf,doc,docx,xls,xlsx,ppt,pptx'
    }
    
    for key, value in default_settings.items():
        setting = Setting.query.filter_by(key=key).first()
        if not setting:
            setting = Setting(key=key, value=value)
            db.session.add(setting)
    
    db.session.commit()

# Initialize settings when the app starts
with app.app_context():
    init_default_settings()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)