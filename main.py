#!/usr/bin/env python3
"""
Easy Crawl4AI Web Interface - A user-friendly web interface for the crawl4ai web crawler
"""

import os
import sys
import json
import logging
import importlib.util
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Import error handler
try:
    from error_handler import format_error_message, format_error_html
except ImportError:
    # Define minimal versions if error_handler.py is not available
    def format_error_message(exception, include_exception_details=False):
        return {
            "category": "Error",
            "message": str(exception),
            "suggestion": "Please try again or contact support."
        }
    
    def format_error_html(exception, include_traceback=False):
        return f"""
        <div class="alert alert-danger">
            <h4 class="alert-heading">Error</h4>
            <p><strong>{str(exception)}</strong></p>
            <hr>
            <p class="mb-0">Please try again or contact support.</p>
        </div>
        """

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
        
        # Check for browser support if needed
        if use_browser:
            import importlib.util
            browser_module = importlib.util.find_spec('playwright')
            if not browser_module:
                job.status = 'failed'
                job.error_message = "Browser-based crawling requires the 'playwright' module. Please install it from the Settings page."
                db.session.commit()
                flash("Browser-based crawling requires the 'playwright' module. Please install it from the Settings page.", 'error')
                return redirect(url_for('job_detail', job_id=job.id))
        
        # Check for PDF support if downloading PDF files
        if crawl_type == 'files' and 'pdf' in file_types.lower():
            import importlib.util
            pdf_module = importlib.util.find_spec('PyPDF2')
            if not pdf_module:
                flash("PDF processing is available but requires the 'PyPDF2' module. Files will be downloaded but content extraction may be limited.", 'warning')
        
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
        
        # Format the error message using our error handler
        error_info = format_error_message(e, include_exception_details=True)
        
        # Update job status with detailed error info
        job.status = 'failed'
        job.error_message = json.dumps(error_info)
        job.completed_at = datetime.utcnow()
        db.session.commit()
        
        # Show a helpful flash message
        flash(f'Error: {error_info["message"]}. {error_info["suggestion"]}', 'error')
        
        # Check if this is a common error with a clear solution
        if error_info["type"] in ["browser_not_available", "dependency_not_installed"]:
            return redirect(url_for('settings'))
            
        return render_template('error.html', 
                              error=error_info, 
                              back_url=url_for('home'),
                              retry_url=url_for('job_detail', job_id=job.id))

def save_result_to_db(job_id, result, output_file):
    """Save a crawl result to the database"""
    try:
        # Get content analysis settings
        enable_content_analysis = Setting.query.filter_by(key='enable_content_analysis').first()
        content_analysis_level = Setting.query.filter_by(key='content_analysis_default').first()
        
        # If we're performing content analysis, generate insights
        content_insights = None
        if enable_content_analysis and enable_content_analysis.value == 'true':
            try:
                # Import our content analyzer
                from content_analyzer import analyze_content_quality
                
                # Get OpenAI API key from settings
                api_key_setting = Setting.query.filter_by(key='openai_api_key').first()
                api_key = api_key_setting.value if api_key_setting else None
                
                # Set environment variable for API key
                if api_key:
                    os.environ['OPENAI_API_KEY'] = api_key
                
                # Analyze content
                logger.info(f"Performing content analysis for URL: {result.get('url', '')}")
                content_insights = analyze_content_quality(result, api_key)
                logger.info("Content analysis completed successfully")
            except Exception as e:
                logger.error(f"Error during content analysis: {str(e)}")
                content_insights = {
                    "error": True,
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        # Create database record
        db_result = CrawlResult(
            job_id=job_id,
            url=result.get('url', ''),
            title=result.get('title', ''),
            output_file=output_file,
            content_length=len(result.get('text', '')),
            word_count=len(result.get('text', '').split()),
            link_count=len(result.get('links', [])),
            image_count=len(result.get('images', [])),
            content_insights=content_insights,
            created_at=datetime.utcnow()
        )
        db.session.add(db_result)
        db.session.commit()
        
        # Return the result ID for reference
        return db_result.id
    except Exception as e:
        logger.error(f"Error saving result to database: {str(e)}")
        error_info = format_error_message(e)
        flash(f"Error saving results: {error_info['message']}", 'warning')
        return None

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
    try:
        file_path = Path(RESULTS_DIR) / filename
        
        if not file_path.exists():
            error_info = {
                "category": "File Error",
                "message": f"File not found: {filename}",
                "suggestion": "The file may have been deleted or moved. Please check the job details or try crawling the URL again."
            }
            flash(f'File not found: {filename}', 'error')
            return render_template('error.html', error=error_info, back_url=url_for('job_list'))
        
        # Try to read the file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with a different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception:
                error_info = {
                    "category": "File Error",
                    "message": f"Cannot read file: {filename}",
                    "suggestion": "The file encoding is not supported. Try downloading the file instead of viewing it."
                }
                return render_template('error.html', error=error_info, 
                                      back_url=url_for('job_list'),
                                      retry_url=url_for('download_file', filename=filename))
        
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
                error_info = {
                    "category": "Parse Error",
                    "message": "Cannot parse JSON file",
                    "suggestion": "The file doesn't contain valid JSON data. Viewing as plain text instead."
                }
                flash("Cannot parse JSON file. Viewing as plain text instead.", 'warning')
                return render_template('view_text.html', filename=filename, content=content)
        else:
            # Plain text view
            return render_template('view_text.html', filename=filename, content=content)
            
    except Exception as e:
        # Use our error handler for any other exceptions
        error_info = format_error_message(e)
        logger.error(f"Error viewing file {filename}: {str(e)}")
        return render_template('error.html', 
                              error=error_info,
                              back_url=url_for('job_list'),
                              retry_url=url_for('download_file', filename=filename))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """View and edit application settings"""
    if request.method == 'POST':
        # Update settings
        for key, value in request.form.items():
            if key.startswith('setting_'):
                setting_key = key[8:]  # Remove 'setting_' prefix
                
                # Special handling for OpenAI API key
                if setting_key == 'openai_api_key' and value:
                    # Validate the API key (optional)
                    try:
                        # Store the API key in environment variable temporarily
                        os.environ['OPENAI_API_KEY'] = value
                        
                        # Try to import and initialize OpenAI
                        if importlib.util.find_spec('openai'):
                            import openai
                            from openai import OpenAI
                            client = OpenAI(api_key=value)
                            # Make a simple call to validate the key
                            response = client.models.list()
                            flash('OpenAI API key validated successfully', 'success')
                        else:
                            flash('OpenAI package not installed. API key will be saved but not validated.', 'warning')
                    except Exception as e:
                        flash(f'Error validating OpenAI API key: {str(e)}', 'error')
                        logger.error(f"API key validation error: {str(e)}")
                
                # Save the setting
                setting = Setting.query.filter_by(key=setting_key).first()
                if setting:
                    if setting_key == 'openai_api_key' and not value and setting.value:
                        # If clearing the API key, confirm with the user
                        flash('API key has been cleared.', 'info')
                    setting.value = value
                else:
                    setting = Setting(key=setting_key, value=value)
                    db.session.add(setting)
        
        db.session.commit()
        flash('Settings updated successfully', 'success')
        return redirect(url_for('settings'))
    
    # Get all settings
    all_settings = Setting.query.all()
    
    # Import check for content analysis
    content_analysis_available = importlib.util.find_spec('openai') is not None
    
    return render_template('settings.html', 
                          settings=all_settings, 
                          content_analysis_available=content_analysis_available)

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
        'default_file_types': 'pdf,doc,docx,xls,xlsx,ppt,pptx',
        'enable_content_analysis': 'true',
        'openai_api_key': '',  # This will be set through the UI
        'content_analysis_default': 'basic'  # Options: 'none', 'basic', 'full'
    }
    
    # Add optional feature settings
    import importlib.util
    
    # Check if PDF features are installed
    spec = importlib.util.find_spec('PyPDF2')
    default_settings['feature_pdf_installed'] = 'true' if spec else 'false'
    
    # Check if browser features are installed
    spec = importlib.util.find_spec('playwright')
    default_settings['feature_browser_installed'] = 'true' if spec else 'false'
    
    # Check if LLM features are installed
    spec = importlib.util.find_spec('openai')
    llm_part1 = spec is not None
    spec = importlib.util.find_spec('langchain')
    llm_part2 = spec is not None
    default_settings['feature_llm_installed'] = 'true' if (llm_part1 and llm_part2) else 'false'
    
    # Apply settings
    for key, value in default_settings.items():
        setting = Setting.query.filter_by(key=key).first()
        if not setting:
            setting = Setting(key=key, value=value)
            db.session.add(setting)
        elif key.startswith('feature_') and key.endswith('_installed'):
            # Update feature installation status
            setting.value = value
    
    db.session.commit()

# Add route for installing features
@app.route('/install-feature/<feature>')
def install_feature(feature):
    """Install optional crawl4ai features"""
    import subprocess
    import sys

    # Define valid features and associated packages
    feature_packages = {
        'pdf': ['PyPDF2'],
        'browser': ['playwright'],
        'llm': ['openai', 'langchain'],
        'all': ['PyPDF2', 'playwright', 'openai', 'langchain']
    }
    
    if feature not in feature_packages:
        flash(f'Invalid feature: {feature}', 'error')
        return redirect(url_for('settings'))
    
    packages = feature_packages[feature]
    try:
        # Install packages using pip
        for package in packages:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Installed {package}: {result.stdout}")
        
        # For browser feature, we need to install playwright browsers
        if feature == 'browser' or feature == 'all':
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'playwright', 'install'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                logger.info(f"Installed playwright browsers: {result.stdout}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Error installing playwright browsers: {e}")
                flash(f'Error installing playwright browsers: {e}', 'error')
        
        # Record installation in settings
        feature_setting_key = f"feature_{feature}_installed"
        setting = Setting.query.filter_by(key=feature_setting_key).first()
        if not setting:
            setting = Setting(key=feature_setting_key, value='true')
            db.session.add(setting)
        else:
            setting.value = 'true'
        db.session.commit()
        
        flash(f'Successfully installed {feature} feature!', 'success')
    except subprocess.CalledProcessError as e:
        logger.error(f"Error installing packages: {e}")
        
        # Format a helpful error message
        error_info = {
            "category": "Dependency Error",
            "message": f"Failed to install {feature} feature.",
            "suggestion": "Check your internet connection and try again. If the problem persists, you may need to manually install the packages or contact support."
        }
        
        # If we have stderr output, include it for more detail
        if e.stderr:
            error_info["exception"] = {
                "type": "Installation Error",
                "message": e.stderr
            }
            
        # Save the error in a session variable to display on the error page
        flash(f'Error installing {feature} feature. Please check your internet connection and try again.', 'error')
        
        # Log detailed error
        logger.error(f"Package installation error: {e.stderr if e.stderr else str(e)}")
    
    return redirect(url_for('settings'))

# Add route for status check of optional features
@app.route('/check-features')
def check_features():
    """Check which optional features are available"""
    import importlib.util
    
    features = {
        'pdf': {'module': 'PyPDF2', 'installed': False},
        'browser': {'module': 'playwright', 'installed': False},
        'llm': {'module': 'openai', 'installed': False}
    }
    
    # Check which modules are installed
    for feature, info in features.items():
        spec = importlib.util.find_spec(info['module'])
        features[feature]['installed'] = spec is not None
    
    return jsonify(features)

# Add a general error route
@app.route('/error')
def error_page():
    """Display an error page with helpful information"""
    error_type = request.args.get('type', 'unknown_error')
    back_url = request.args.get('back_url', url_for('home'))
    retry_url = request.args.get('retry_url')
    
    # Get error information from our predefined error types
    from error_handler import ERROR_MESSAGES
    error_info = ERROR_MESSAGES.get(error_type, ERROR_MESSAGES['unknown_error'])
    
    # Check for custom message
    custom_message = request.args.get('message')
    if custom_message:
        error_info = error_info.copy()
        error_info['message'] = custom_message
    
    # Check for custom suggestion
    custom_suggestion = request.args.get('suggestion')
    if custom_suggestion:
        error_info = error_info.copy()
        error_info['suggestion'] = custom_suggestion
    
    return render_template('error.html', 
                          error=error_info,
                          back_url=back_url,
                          retry_url=retry_url)

# Set up error handlers for common HTTP errors
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    error_info = {
        "category": "Page Not Found",
        "message": "The page you requested could not be found.",
        "suggestion": "Check the URL and try again, or go back to the home page."
    }
    return render_template('error.html', error=error_info, back_url=url_for('home')), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()  # Roll back any failed database transactions
    
    error_info = {
        "category": "Server Error",
        "message": "An unexpected error occurred on the server.",
        "suggestion": "Please try again later. If the problem persists, contact the administrator."
    }
    
    if app.debug:
        # In debug mode, add the actual error
        error_info["exception"] = {
            "type": type(error).__name__,
            "message": str(error)
        }
    
    return render_template('error.html', error=error_info, back_url=url_for('home')), 500

# Batch Processing Routes
@app.route('/batches')
def batch_jobs():
    """List all batch jobs"""
    # Get active (pending, running, paused) and completed (completed, failed) batch jobs
    from models import BatchJob
    
    active_batches = BatchJob.query.filter(
        BatchJob.status.in_(['pending', 'running', 'paused'])
    ).order_by(BatchJob.created_at.desc()).all()
    
    completed_batches = BatchJob.query.filter(
        BatchJob.status.in_(['completed', 'failed'])
    ).order_by(BatchJob.completed_at.desc()).all()
    
    return render_template('batches.html', 
                          active_batches=active_batches,
                          completed_batches=completed_batches)

@app.route('/new-batch')
def new_batch():
    """Form for creating a new batch job"""
    return render_template('new_batch.html', now=datetime.utcnow())

@app.route('/create-batch', methods=['POST'])
def create_batch():
    """Create a new batch job"""
    from models import BatchJob, BatchJobItem
    
    # Get form data
    name = request.form.get('name', '')
    description = request.form.get('description', '')
    urls_text = request.form.get('urls', '')
    output_dir = request.form.get('output_dir', f'./results/batch_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    output_format = request.form.get('format', 'markdown')
    use_browser = request.form.get('use_browser') == 'on'
    include_images = request.form.get('include_images') == 'on'
    include_links = request.form.get('include_links') == 'on'
    concurrent_workers = int(request.form.get('concurrent_workers', 3))
    timeout_per_url = int(request.form.get('timeout_per_url', 60))
    schedule_type = request.form.get('schedule_type', 'now')
    validate_urls = request.form.get('validate_urls') == 'on'
    
    # Validate input
    if not name:
        flash('Please enter a name for the batch job', 'error')
        return redirect(url_for('new_batch'))
    
    # Process URLs (split by newline and remove empty lines)
    url_list = [url.strip() for url in urls_text.split('\n') if url.strip()]
    
    if not url_list:
        flash('Please enter at least one URL', 'error')
        return redirect(url_for('new_batch'))
    
    # Validate URLs if requested
    valid_urls = []
    invalid_urls = []
    
    if validate_urls:
        for url in url_list:
            # Basic URL validation
            try:
                parsed = urlparse(url)
                if not parsed.scheme or not parsed.netloc:
                    invalid_urls.append(url)
                else:
                    valid_urls.append(url)
            except Exception:
                invalid_urls.append(url)
    else:
        valid_urls = url_list
    
    if invalid_urls:
        flash(f'Found {len(invalid_urls)} invalid URLs. Please check your input.', 'warning')
        if not valid_urls:
            return redirect(url_for('new_batch'))
    
    # Create output directory
    output_path = Path(output_dir)
    ensure_directory(output_path)
    
    # Create a new batch job
    batch = BatchJob(
        name=name,
        description=description,
        output_dir=str(output_path),
        format=output_format,
        use_browser=use_browser,
        include_images=include_images,
        include_links=include_links,
        concurrent_workers=concurrent_workers,
        timeout_per_url=timeout_per_url,
        status='pending' if schedule_type == 'now' else 'paused',
        total_urls=len(valid_urls),
        created_at=datetime.utcnow()
    )
    
    db.session.add(batch)
    db.session.commit()
    
    # Add each URL as a batch item
    for url in valid_urls:
        item = BatchJobItem(
            batch_job_id=batch.id,
            url=url,
            status='pending',
            created_at=datetime.utcnow()
        )
        db.session.add(item)
    
    db.session.commit()
    
    # Flash success message
    flash(f'Batch job "{name}" created with {len(valid_urls)} URLs', 'success')
    
    # Start the batch job if scheduled to run immediately
    if schedule_type == 'now':
        return redirect(url_for('start_batch', batch_id=batch.id))
    else:
        return redirect(url_for('batch_detail', batch_id=batch.id))

@app.route('/batch/<int:batch_id>')
def batch_detail(batch_id):
    """View details of a specific batch job"""
    from models import BatchJob, BatchJobItem
    
    # Get the batch job
    batch = BatchJob.query.get_or_404(batch_id)
    
    # Get all items
    batch_items = BatchJobItem.query.filter_by(batch_job_id=batch_id).all()
    
    # Filter items by status for tabs
    pending_items = [item for item in batch_items if item.status == 'pending']
    processing_items = [item for item in batch_items if item.status == 'processing']
    completed_items = [item for item in batch_items if item.status == 'completed']
    failed_items = [item for item in batch_items if item.status == 'failed']
    
    return render_template(
        'batch_detail.html',
        batch=batch,
        batch_items=batch_items,
        pending_items=pending_items,
        processing_items=processing_items,
        completed_items=completed_items,
        failed_items=failed_items
    )

@app.route('/start-batch/<int:batch_id>')
def start_batch(batch_id):
    """Start processing a batch job"""
    from models import BatchJob
    
    # Get the batch job
    batch = BatchJob.query.get_or_404(batch_id)
    
    # Check if it can be started
    if batch.status not in ['pending', 'paused']:
        flash(f'Cannot start batch job in {batch.status} status', 'error')
        return redirect(url_for('batch_detail', batch_id=batch_id))
    
    # Update the status
    batch.status = 'running'
    batch.started_at = datetime.utcnow() if not batch.started_at else batch.started_at
    db.session.commit()
    
    # Start batch processing in background process
    flash('Batch job started. Processing URLs in background.', 'success')
    
    # Start processing in a background thread
    import threading
    thread = threading.Thread(target=process_batch_job, args=(batch_id,))
    thread.daemon = True
    thread.start()
    
    return redirect(url_for('batch_detail', batch_id=batch_id))

@app.route('/pause-batch/<int:batch_id>')
def pause_batch(batch_id):
    """Pause a running batch job"""
    from models import BatchJob
    
    # Get the batch job
    batch = BatchJob.query.get_or_404(batch_id)
    
    # Check if it can be paused
    if batch.status != 'running':
        flash(f'Cannot pause batch job in {batch.status} status', 'error')
        return redirect(url_for('batch_detail', batch_id=batch_id))
    
    # Update the status
    batch.status = 'paused'
    db.session.commit()
    
    flash('Batch job paused. Currently processing URLs will complete before pausing.', 'info')
    return redirect(url_for('batch_detail', batch_id=batch_id))

@app.route('/delete-batch/<int:batch_id>')
def delete_batch(batch_id):
    """Delete a batch job and its items"""
    from models import BatchJob, BatchJobItem
    
    # Get the batch job
    batch = BatchJob.query.get_or_404(batch_id)
    
    # Check if it's currently running
    if batch.status == 'running':
        flash('Cannot delete a running batch job. Please pause it first.', 'error')
        return redirect(url_for('batch_detail', batch_id=batch_id))
    
    # Delete the batch job (cascade will delete items)
    db.session.delete(batch)
    db.session.commit()
    
    flash(f'Batch job "{batch.name}" deleted', 'success')
    return redirect(url_for('batch_jobs'))

@app.route('/retry-item/<int:item_id>')
def retry_item(item_id):
    """Retry a failed batch job item"""
    from models import BatchJobItem
    
    # Get the item
    item = BatchJobItem.query.get_or_404(item_id)
    
    # Check if it's failed
    if item.status != 'failed':
        flash('Can only retry failed items', 'error')
        return redirect(url_for('batch_detail', batch_id=item.batch_job_id))
    
    # Reset the item
    item.status = 'pending'
    item.error_message = None
    item.started_at = None
    item.completed_at = None
    db.session.commit()
    
    # Update batch statistics
    batch = item.batch_job
    batch.failed_urls -= 1
    batch.processed_urls -= 1
    
    # If the batch is completed or failed, set it back to pending
    if batch.status in ['completed', 'failed']:
        batch.status = 'pending'
    
    db.session.commit()
    
    flash(f'Item for URL {item.url} has been reset and will be retried', 'success')
    return redirect(url_for('batch_detail', batch_id=item.batch_job_id))

@app.route('/retry-failed-urls/<int:batch_id>')
def retry_failed_urls(batch_id):
    """Retry all failed URLs in a batch job"""
    from models import BatchJob, BatchJobItem
    
    # Get the batch job
    batch = BatchJob.query.get_or_404(batch_id)
    
    # Get all failed items
    failed_items = BatchJobItem.query.filter_by(batch_job_id=batch_id, status='failed').all()
    
    if not failed_items:
        flash('No failed items to retry', 'info')
        return redirect(url_for('batch_detail', batch_id=batch_id))
    
    # Reset failed items
    for item in failed_items:
        item.status = 'pending'
        item.error_message = None
        item.started_at = None
        item.completed_at = None
    
    # Update batch statistics and status
    batch.failed_urls = 0
    batch.processed_urls -= len(failed_items)
    
    # If the batch is completed or failed, set it back to pending
    if batch.status in ['completed', 'failed']:
        batch.status = 'pending'
    
    db.session.commit()
    
    flash(f'Reset {len(failed_items)} failed items for retry', 'success')
    return redirect(url_for('batch_detail', batch_id=batch_id))

@app.route('/export-batch-results/<int:batch_id>')
def export_batch_results(batch_id):
    """Export all results from a batch job"""
    from models import BatchJob, BatchJobItem, CrawlResult
    
    # Get the batch job
    batch = BatchJob.query.get_or_404(batch_id)
    
    # Check if it has completed items
    completed_items = BatchJobItem.query.filter_by(batch_job_id=batch_id, status='completed').all()
    
    if not completed_items:
        flash('No completed items to export', 'warning')
        return redirect(url_for('batch_detail', batch_id=batch_id))
    
    # For now, redirect to the batch detail page
    # In a real implementation, you would generate a zip file of all results
    flash('Export functionality will be implemented in a future update', 'info')
    return redirect(url_for('batch_detail', batch_id=batch_id))

def process_batch_job(batch_id):
    """
    Process a batch job in the background.
    
    This function is called in a separate thread to process URLs in a batch job.
    It selects pending items, crawls them, and updates the database with results.
    """
    from models import BatchJob, BatchJobItem, CrawlResult
    
    # Create a new app context for this thread
    with app.app_context():
        try:
            # Get the batch job
            batch = BatchJob.query.get(batch_id)
            if not batch:
                logger.error(f"Batch job {batch_id} not found")
                return
            
            # Check if it's already running
            if batch.status != 'running':
                logger.info(f"Batch job {batch_id} is not in running state")
                return
            
            logger.info(f"Starting batch job {batch_id} processing")
            
            # Import crawl4ai here to avoid startup errors if not installed
            try:
                import crawl4ai
            except ImportError:
                logger.error("crawl4ai library is not installed")
                batch.status = 'failed'
                batch.error_message = 'crawl4ai library is not installed'
                db.session.commit()
                return
            
            # Set up crawler with batch options
            crawler = crawl4ai.Crawler(
                use_browser=batch.use_browser,
                include_images=batch.include_images,
                include_links=batch.include_links,
                timeout=batch.timeout_per_url
            )
            
            # Process items in batches based on concurrent_workers
            concurrent_limit = batch.concurrent_workers
            
            # Keep track of active workers and processed URLs
            active_workers = 0
            total_processed = 0
            
            # Continue until all items are processed or batch status is changed
            while batch.status == 'running' and total_processed < batch.total_urls:
                # Check if batch has been updated by another process
                db.session.refresh(batch)
                
                # If batch status has changed, stop processing
                if batch.status != 'running':
                    logger.info(f"Batch job {batch_id} status changed to {batch.status}, stopping")
                    break
                
                # Find pending items to process
                pending_items = BatchJobItem.query.filter_by(
                    batch_job_id=batch_id, 
                    status='pending'
                ).limit(concurrent_limit - active_workers).all()
                
                if not pending_items:
                    # No more pending items, check if there are any processing items
                    processing_items = BatchJobItem.query.filter_by(
                        batch_job_id=batch_id, 
                        status='processing'
                    ).count()
                    
                    if processing_items == 0:
                        # No more items to process, mark batch as completed
                        batch.status = 'completed'
                        batch.completed_at = datetime.utcnow()
                        db.session.commit()
                        logger.info(f"Batch job {batch_id} completed")
                        break
                    
                    # Wait for processing items to complete
                    logger.info(f"Waiting for {processing_items} items to complete")
                    import time
                    time.sleep(5)
                    continue
                
                # Process each pending item
                for item in pending_items:
                    # Update item status
                    item.status = 'processing'
                    item.started_at = datetime.utcnow()
                    db.session.commit()
                    
                    try:
                        logger.info(f"Processing item {item.id}: {item.url}")
                        
                        # Crawl URL
                        result = crawler.crawl_url(item.url)
                        
                        # Generate filename from URL
                        parsed_url = urlparse(item.url)
                        domain = parsed_url.netloc.replace('.', '_')
                        filename = f"{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        
                        # Save result
                        output_file = save_result(result, batch.output_dir, batch.format, filename)
                        
                        # Create result in database
                        db_result = CrawlResult(
                            job_id=batch_id,  # Use batch_id as job_id for now
                            url=item.url,
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
                        
                        # Update item status
                        item.status = 'completed'
                        item.result_id = db_result.id
                        item.completed_at = datetime.utcnow()
                        
                        # Update batch statistics
                        batch.processed_urls += 1
                        batch.successful_urls += 1
                        
                        logger.info(f"Successfully processed {item.url}")
                        
                    except Exception as e:
                        logger.error(f"Error processing {item.url}: {str(e)}")
                        
                        # Format error message
                        error_info = format_error_message(e, include_exception_details=True)
                        
                        # Update item status
                        item.status = 'failed'
                        item.error_message = json.dumps(error_info)
                        item.completed_at = datetime.utcnow()
                        
                        # Update batch statistics
                        batch.processed_urls += 1
                        batch.failed_urls += 1
                    
                    # Commit changes
                    db.session.commit()
                    total_processed += 1
                
                # Check if we should continue
                if batch.processed_urls >= batch.total_urls:
                    # All items processed, mark batch as completed
                    batch.status = 'completed'
                    batch.completed_at = datetime.utcnow()
                    db.session.commit()
                    logger.info(f"Batch job {batch_id} completed, processed {batch.processed_urls} URLs")
                    break
            
            # Final check for completion
            db.session.refresh(batch)
            if batch.processed_urls >= batch.total_urls and batch.status == 'running':
                batch.status = 'completed'
                batch.completed_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"Batch job {batch_id} completed, processed {batch.processed_urls} URLs")
                
        except Exception as e:
            logger.error(f"Error processing batch job {batch_id}: {str(e)}")
            
            # Try to update batch status if possible
            try:
                if batch:
                    batch.status = 'failed'
                    batch.error_message = str(e)
                    db.session.commit()
            except Exception as inner_e:
                logger.error(f"Error updating batch status: {str(inner_e)}")

# Content Analysis Routes
@app.route('/analyses')
def analysis_list():
    """List all content analyses"""
    # Query the database for content analysis records
    analyses = CrawlResult.query.filter(CrawlResult.content_insights != None).order_by(CrawlResult.created_at.desc()).all()
    
    return render_template('analyses.html', analyses=analyses)

@app.route('/analyze/<int:result_id>', methods=['GET', 'POST'])
def analyze_content(result_id):
    """Analyze content of a crawl result"""
    result = CrawlResult.query.get_or_404(result_id)
    
    # Check if analysis already exists
    has_analysis = result.content_insights is not None
    
    if request.method == 'POST':
        # Get the API key from the form or settings
        api_key = request.form.get('api_key', '')
        analysis_level = request.form.get('analysis_level', 'basic')
        
        # If not provided in form, try to get from settings
        if not api_key:
            api_setting = Setting.query.filter_by(key='openai_api_key').first()
            if api_setting and api_setting.value:
                api_key = api_setting.value
        
        try:
            # Import the content analyzer
            from content_analyzer import analyze_content_quality
            
            # Create content data dictionary
            content_data = {
                'text': '',  # We'll need to read the file
                'title': result.title,
                'format': Path(result.output_file).suffix.lstrip('.'),
                'url': result.url
            }
            
            # Read the content from the file
            try:
                with open(result.output_file, 'r', encoding='utf-8') as f:
                    content_data['text'] = f.read()
            except Exception as e:
                flash(f"Error reading content file: {str(e)}", 'danger')
                return redirect(url_for('job_detail', job_id=result.job_id))
            
            # Perform the analysis
            analysis_results = analyze_content_quality(content_data, api_key)
            
            # If level is basic, remove AI analysis to save tokens
            if analysis_level == 'basic' and 'ai_analysis' in analysis_results:
                del analysis_results['ai_analysis']
            
            # Store the analysis in the database
            result.content_insights = analysis_results
            db.session.commit()
            
            flash("Content analysis completed successfully!", 'success')
            return redirect(url_for('view_analysis', result_id=result.id))
            
        except ImportError:
            flash("Content analyzer module not found. Please check your installation.", 'danger')
            return redirect(url_for('job_detail', job_id=result.job_id))
        except Exception as e:
            flash(f"Error analyzing content: {str(e)}", 'danger')
            return redirect(url_for('job_detail', job_id=result.job_id))
    
    # GET request - show the form
    return render_template('analyze_form.html', result=result, has_analysis=has_analysis)

@app.route('/view-analysis/<int:result_id>')
def view_analysis(result_id):
    """View content analysis results"""
    result = CrawlResult.query.get_or_404(result_id)
    
    # Check if analysis exists
    if not result.content_insights:
        flash("No content analysis available for this result.", 'warning')
        return redirect(url_for('job_detail', job_id=result.job_id))
    
    return render_template('view_analysis.html', result=result)

# Initialize settings when the app starts
with app.app_context():
    init_default_settings()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)