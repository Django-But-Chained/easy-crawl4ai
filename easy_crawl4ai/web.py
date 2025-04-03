#!/usr/bin/env python3
"""
Easy Crawl4AI Web Interface - A user-friendly web interface for the crawl4ai web crawler

This script provides a simplified web interface to the powerful crawl4ai
web crawler library, making it accessible for users without technical expertise.
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

try:
    from flask_sqlalchemy import SQLAlchemy
    from sqlalchemy.orm import DeclarativeBase
    from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
except ImportError:
    print("Flask-SQLAlchemy or SQLAlchemy is not installed.")
    print("Please install with: pip install flask-sqlalchemy sqlalchemy")
    print("Then restart the application.")
    sys.exit(1)


# Define the Flask application and database
class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", os.urandom(24).hex())

    # Configure the database - make sure we have DATABASE_URL from environment
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        # If no database URL is provided, use a default SQLite database
        print("WARNING: DATABASE_URL not set. Using SQLite database.")
        database_url = "sqlite:///crawl4ai.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize the app with the database extension
    db.init_app(app)

    return app


# Initialize the Flask application
app = create_app()


# Define models 
class CrawlJob(db.Model):
    """Model for tracking crawl jobs"""
    __tablename__ = 'crawl_jobs'
    
    id = Column(Integer, primary_key=True)
    crawl_type = Column(String(50), nullable=False)  # single, multiple, deep, files
    url = Column(String(2048), nullable=True)         # Main URL for single, deep, files
    urls = Column(JSON, nullable=True)                # List of URLs for multiple crawl
    output_dir = Column(String(255), nullable=False)
    format = Column(String(20), nullable=True)
    use_browser = Column(Boolean, default=False)
    include_images = Column(Boolean, default=True)
    include_links = Column(Boolean, default=True)
    
    # For deep crawl
    max_depth = Column(Integer, nullable=True)
    max_pages = Column(Integer, nullable=True)
    stay_within_domain = Column(Boolean, default=True)
    
    # For file downloads
    file_types = Column(String(255), nullable=True)
    max_size = Column(Integer, nullable=True)
    max_files = Column(Integer, nullable=True)
    
    # Metadata
    status = Column(String(20), default='pending')  # pending, running, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    pages_crawled = Column(Integer, default=0)
    files_downloaded = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<CrawlJob {self.id} - {self.crawl_type} - {self.status}>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'crawl_type': self.crawl_type,
            'url': self.url,
            'urls': self.urls,
            'output_dir': self.output_dir,
            'format': self.format,
            'use_browser': self.use_browser,
            'include_images': self.include_images,
            'include_links': self.include_links,
            'max_depth': self.max_depth,
            'max_pages': self.max_pages,
            'stay_within_domain': self.stay_within_domain,
            'file_types': self.file_types,
            'max_size': self.max_size,
            'max_files': self.max_files,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'pages_crawled': self.pages_crawled,
            'files_downloaded': self.files_downloaded
        }


class CrawlResult(db.Model):
    """Model for storing crawl results"""
    __tablename__ = 'crawl_results'
    
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, nullable=False)
    url = Column(String(2048), nullable=False)
    title = Column(String(512), nullable=True)
    output_file = Column(String(512), nullable=False)
    content_length = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)
    link_count = Column(Integer, nullable=True)
    image_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<CrawlResult {self.id} - {self.url}>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'url': self.url,
            'title': self.title,
            'output_file': self.output_file,
            'content_length': self.content_length,
            'word_count': self.word_count,
            'link_count': self.link_count,
            'image_count': self.image_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Setting(db.Model):
    """Model for application settings"""
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), nullable=False, unique=True)
    value = Column(Text, nullable=True)
    description = Column(String(512), nullable=True)
    
    def __repr__(self):
        return f"<Setting {self.key}>"


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
        'all': ['crawl4ai[all]']
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
        if feature == 'browser':
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
        flash(f'Error installing packages: {e}', 'error')
    
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


def init_db():
    """Initialize the database"""
    with app.app_context():
        db.create_all()
        init_default_settings()


def run_app():
    """Run the Flask application"""
    # Initialize the database
    init_db()
    
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == '__main__':
    run_app()