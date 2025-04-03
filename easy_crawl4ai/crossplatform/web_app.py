"""
Easy Crawl4AI Web Interface (Cross-Platform) - A user-friendly web interface for the crawl4ai web crawler

This module provides a Flask web application for easy interaction with the crawl4ai
web crawler library. This version is designed to work across Windows, macOS, and Linux.
"""

import os
import sys
import json
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple

try:
    from flask import (
        Flask, render_template, request, redirect, url_for, flash, 
        session, send_from_directory, abort, jsonify
    )
    from werkzeug.utils import secure_filename
except ImportError:
    print("Error: Flask is not installed. Please install it with: pip install flask")
    sys.exit(1)

# Configure error handler - import here so it can be used even without crawl4ai
from error_handler import format_error_html, format_error_message

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the Flask application
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates'))
app.secret_key = os.environ.get("FLASK_SECRET_KEY", str(uuid.uuid4()))

# Configure the database connection
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///easy_crawl4ai.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Import the database and models
try:
    from app import db
    from models import CrawlJob, CrawlResult, BatchJob, BatchJobItem, Setting
    db_available = True
except ImportError:
    logger.warning("Database models not available. Running with limited functionality.")
    db_available = False

# Set constants for file paths - using platform-independent path handling
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS_DIR = BASE_DIR / "results"
DOWNLOADS_DIR = BASE_DIR / "downloads"


def ensure_directory(directory: Path) -> Path:
    """Ensure the directory exists and return the Path object."""
    directory.mkdir(parents=True, exist_ok=True)
    return directory


# Ensure the results and downloads directories exist
ensure_directory(RESULTS_DIR)
ensure_directory(DOWNLOADS_DIR)


@app.route("/")
def home():
    """Home page route"""
    try:
        features_available = check_features()
        return render_template(
            "index.html", 
            features=features_available,
            page_title="Easy Crawl4AI - Web Interface"
        )
    except Exception as e:
        logger.error(f"Error rendering home page: {str(e)}", exc_info=True)
        flash(f"Error: {str(e)}", "danger")
        return render_template("error.html", error=format_error_html(e))


@app.route("/jobs")
def job_list():
    """List all crawl jobs"""
    if not db_available:
        flash("Database functionality is not available.", "warning")
        return redirect(url_for("home"))
    
    try:
        jobs = CrawlJob.query.order_by(CrawlJob.created_at.desc()).all()
        return render_template(
            "jobs.html", 
            jobs=jobs,
            page_title="Crawl Jobs"
        )
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}", exc_info=True)
        flash(f"Error: {str(e)}", "danger")
        return render_template("error.html", error=format_error_html(e))


@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    """View a specific job and its results"""
    if not db_available:
        flash("Database functionality is not available.", "warning")
        return redirect(url_for("home"))
    
    try:
        job = CrawlJob.query.get_or_404(job_id)
        results = CrawlResult.query.filter_by(job_id=job_id).all()
        return render_template(
            "job_detail.html", 
            job=job,
            results=results,
            page_title=f"Job: {job.crawl_type.capitalize()} Crawl"
        )
    except Exception as e:
        logger.error(f"Error viewing job {job_id}: {str(e)}", exc_info=True)
        flash(f"Error: {str(e)}", "danger")
        return render_template("error.html", error=format_error_html(e))


@app.route("/crawl", methods=["POST"])
def run_crawl():
    """Run the crawler with the provided options"""
    if not db_available:
        flash("Database functionality is not available.", "warning")
        return redirect(url_for("home"))
    
    try:
        # Get form data
        crawl_type = request.form.get("crawl_type", "single")
        url = request.form.get("url", "").strip()
        urls_text = request.form.get("urls", "").strip()
        output_dir = request.form.get("output_dir", str(RESULTS_DIR))
        format_type = request.form.get("format", "markdown")
        use_browser = "use_browser" in request.form
        include_images = "include_images" in request.form
        include_links = "include_links" in request.form
        
        # Optional parameters
        max_depth = int(request.form.get("max_depth", 2))
        max_pages = int(request.form.get("max_pages", 20))
        stay_within_domain = "stay_within_domain" in request.form
        file_types = request.form.get("file_types", "pdf,docx,xlsx")
        max_size = int(request.form.get("max_size", 50))
        max_files = int(request.form.get("max_files", 20))
        wait_time = int(request.form.get("wait_time", 0))
        selector = request.form.get("selector", "").strip() or None
        
        # Speed control options
        use_random_delay = "use_random_delay" in request.form
        random_delay_min = int(request.form.get("random_delay_min", 1))
        random_delay_max = int(request.form.get("random_delay_max", 5))
        use_adaptive_delay = "use_adaptive_delay" in request.form
        adaptive_delay_factor = int(request.form.get("adaptive_delay_factor", 2))
        use_scheduled_breaks = "use_scheduled_breaks" in request.form
        requests_before_break = int(request.form.get("requests_before_break", 50))
        break_duration = int(request.form.get("break_duration", 30))
        
        # Basic validation
        if crawl_type in ["single", "deep", "files"] and not url:
            flash("Please enter a URL.", "danger")
            return redirect(url_for("home"))
        
        if crawl_type == "multiple" and not urls_text:
            flash("Please enter at least one URL for multiple crawling.", "danger")
            return redirect(url_for("home"))
        
        # Process URLs for multiple crawl
        urls = []
        if crawl_type == "multiple":
            urls = [line.strip() for line in urls_text.split("\n") if line.strip()]
        
        # Create a new job record
        job = CrawlJob(
            crawl_type=crawl_type,
            url=url if crawl_type != "multiple" else None,
            urls=urls if crawl_type == "multiple" else None,
            output_dir=output_dir,
            format=format_type,
            use_browser=use_browser,
            include_images=include_images,
            include_links=include_links,
            max_depth=max_depth if crawl_type == "deep" else None,
            max_pages=max_pages if crawl_type == "deep" else None,
            stay_within_domain=stay_within_domain if crawl_type == "deep" else None,
            file_types=file_types if crawl_type == "files" else None,
            max_size=max_size if crawl_type == "files" else None,
            max_files=max_files if crawl_type == "files" else None,
            wait_time=wait_time,
            selector=selector,
            use_random_delay=use_random_delay,
            random_delay_min=random_delay_min,
            random_delay_max=random_delay_max,
            use_adaptive_delay=use_adaptive_delay,
            adaptive_delay_factor=adaptive_delay_factor,
            use_scheduled_breaks=use_scheduled_breaks,
            requests_before_break=requests_before_break,
            break_duration=break_duration,
            status="running",
            created_at=datetime.utcnow()
        )
        
        db.session.add(job)
        db.session.commit()
        job_id = job.id
        
        # Ensure the output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Import crawl4ai here to handle import errors gracefully
            import crawl4ai
            from crawl4ai.config import (
                CrawlerRunConfig, DeepCrawlConfig, DownloadConfig, DispatcherConfig
            )
            
            # Create dispatcher config for speed control
            dispatcher_config = DispatcherConfig(
                use_random_delay=use_random_delay,
                random_delay_min_seconds=random_delay_min,
                random_delay_max_seconds=random_delay_max,
                use_adaptive_delay=use_adaptive_delay,
                adaptive_delay_factor=adaptive_delay_factor,
                use_scheduled_breaks=use_scheduled_breaks,
                requests_before_break=requests_before_break,
                break_duration_seconds=break_duration
            )
            
            # Run different types of crawls based on the selected type
            if crawl_type == "single":
                # Single URL crawl
                config = CrawlerRunConfig(
                    url=url,
                    use_browser=use_browser,
                    include_images=include_images,
                    include_links=include_links,
                    wait_time=wait_time,
                    selector=selector
                )
                
                # Import the async loop handling based on platform
                import asyncio
                if sys.platform.startswith('win'):
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                
                result = asyncio.run(crawl4ai.arun(config))
                
                # Save the result
                if result:
                    output_file = save_result(result, output_dir, format_type)
                    save_result_to_db(job_id, result, output_file)
                
                # Update job status
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                job.pages_crawled = 1
                db.session.commit()
                
                flash(f"Successfully crawled URL: {url}", "success")
            
            elif crawl_type == "multiple":
                # Multiple URLs crawl
                configs = [
                    CrawlerRunConfig(
                        url=url,
                        use_browser=use_browser,
                        include_images=include_images,
                        include_links=include_links,
                        wait_time=wait_time,
                        selector=selector
                    ) 
                    for url in urls
                ]
                
                # Import the async loop handling based on platform
                import asyncio
                if sys.platform.startswith('win'):
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                
                results = asyncio.run(
                    crawl4ai.arun_many(configs, dispatcher_config=dispatcher_config)
                )
                
                # Save the results
                successful_count = 0
                for result in results:
                    if result:
                        output_file = save_result(result, output_dir, format_type)
                        save_result_to_db(job_id, result, output_file)
                        successful_count += 1
                
                # Update job status
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                job.pages_crawled = successful_count
                db.session.commit()
                
                flash(f"Successfully crawled {successful_count} out of {len(urls)} URLs", "success")
            
            elif crawl_type == "deep":
                # Deep crawling
                config = DeepCrawlConfig(
                    start_url=url,
                    use_browser=use_browser,
                    include_images=include_images,
                    include_links=include_links,
                    max_depth=max_depth,
                    max_pages=max_pages,
                    stay_within_domain=stay_within_domain
                )
                
                # Import the async loop handling based on platform
                import asyncio
                if sys.platform.startswith('win'):
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                
                results = asyncio.run(
                    crawl4ai.adeep_crawl(config, dispatcher_config=dispatcher_config)
                )
                
                # Save the results
                successful_count = 0
                for result in results:
                    if result:
                        output_file = save_result(result, output_dir, format_type)
                        save_result_to_db(job_id, result, output_file)
                        successful_count += 1
                
                # Update job status
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                job.pages_crawled = successful_count
                db.session.commit()
                
                flash(f"Successfully deep-crawled {successful_count} pages starting from {url}", "success")
            
            elif crawl_type == "files":
                # File downloading
                file_extensions = [ext.strip() for ext in file_types.split(',')]
                config = DownloadConfig(
                    url=url,
                    file_types=file_extensions,
                    max_file_size_mb=max_size,
                    use_browser=use_browser,
                    max_files=max_files
                )
                
                # Import the async loop handling based on platform
                import asyncio
                if sys.platform.startswith('win'):
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                
                downloaded_files = asyncio.run(
                    crawl4ai.adownload_files(config, output_dir, dispatcher_config=dispatcher_config)
                )
                
                # Update job status
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                job.files_downloaded = len(downloaded_files) if downloaded_files else 0
                db.session.commit()
                
                if downloaded_files:
                    flash(f"Successfully downloaded {len(downloaded_files)} files from {url}", "success")
                else:
                    flash(f"No files found to download from {url}", "warning")
            
            else:
                # Unknown crawl type
                job.status = "failed"
                job.error_message = f"Unknown crawl type: {crawl_type}"
                db.session.commit()
                flash(f"Unknown crawl type: {crawl_type}", "danger")
                return redirect(url_for("home"))
            
        except Exception as e:
            logger.error(f"Error running crawl: {str(e)}", exc_info=True)
            
            # Update job status to failed
            job.status = "failed"
            job.error_message = str(e)
            db.session.commit()
            
            # Format an error message
            error_info = format_error_message(e)
            flash(f"Error: {error_info.get('message', str(e))}", "danger")
            return render_template("error.html", error=format_error_html(e))
        
        # Redirect to the job details page
        return redirect(url_for("job_detail", job_id=job_id))
        
    except Exception as e:
        logger.error(f"Error processing crawl request: {str(e)}", exc_info=True)
        flash(f"Error: {str(e)}", "danger")
        return render_template("error.html", error=format_error_html(e))


def save_result_to_db(job_id, result, output_file):
    """Save a crawl result to the database"""
    if not db_available:
        return
    
    try:
        # Extract relevant information
        url = result.get("url", "")
        title = result.get("title", "")
        content_length = len(result.get("text", ""))
        word_count = len(result.get("text", "").split())
        link_count = len(result.get("links", []))
        image_count = len(result.get("images", []))
        
        # Create a new result record
        result_record = CrawlResult(
            job_id=job_id,
            url=url,
            title=title,
            output_file=output_file,
            content_length=content_length,
            word_count=word_count,
            link_count=link_count,
            image_count=image_count,
            created_at=datetime.utcnow()
        )
        
        db.session.add(result_record)
        db.session.commit()
        return result_record.id
    except Exception as e:
        logger.error(f"Error saving result to database: {str(e)}", exc_info=True)
        # Continue without database storage if there's an error
        return None


def save_result(result, output_dir, format_type, filename=None):
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
    output_path = ensure_directory(Path(output_dir))
    
    # Full path to the output file
    file_path = output_path / filename
    
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
    
    return str(file_path)


@app.route("/download/<path:filename>")
def download_file(filename):
    """Download a specific file."""
    try:
        # Security check - normalize the path and make sure it's not going above the results directory
        file_path = Path(filename).resolve()
        base_path = Path(RESULTS_DIR).resolve()
        
        # Check if the file is within the results directory or its subdirectories
        if base_path in file_path.parents or file_path == base_path:
            directory = os.path.dirname(filename)
            file_name = os.path.basename(filename)
            return send_from_directory(directory, file_name, as_attachment=True)
        else:
            abort(403)  # Forbidden
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}", exc_info=True)
        flash(f"Error downloading file: {str(e)}", "danger")
        abort(404)


@app.route("/view/<path:filename>")
def view_file(filename):
    """View a specific file."""
    try:
        # Security check - normalize the path and make sure it's not going above the results directory
        file_path = Path(filename).resolve()
        
        if not file_path.exists():
            flash(f"File not found: {filename}", "danger")
            abort(404)
        
        # Determine the file type by extension
        _, ext = os.path.splitext(filename)
        file_type = ext.lower()[1:]  # Remove the leading dot
        
        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Choose the appropriate template based on file type
        if file_type == "md" or file_type == "markdown":
            return render_template("view_markdown.html", content=content, filename=filename, page_title="View Markdown")
        elif file_type == "html" or file_type == "htm":
            return render_template("view_html.html", content=content, filename=filename, page_title="View HTML")
        elif file_type == "json":
            try:
                # Pretty-print JSON
                json_data = json.loads(content)
                formatted_content = json.dumps(json_data, indent=2)
                return render_template("view_json.html", content=formatted_content, filename=filename, page_title="View JSON")
            except json.JSONDecodeError:
                # If JSON parsing fails, display as text
                return render_template("view_text.html", content=content, filename=filename, page_title="View Text")
        else:
            # Default to text view for other files
            return render_template("view_text.html", content=content, filename=filename, page_title="View Text")
    
    except Exception as e:
        logger.error(f"Error viewing file: {str(e)}", exc_info=True)
        flash(f"Error viewing file: {str(e)}", "danger")
        return render_template("error.html", error=format_error_html(e))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    """View and edit application settings"""
    if not db_available:
        flash("Database functionality is not available.", "warning")
        return redirect(url_for("home"))
    
    if request.method == "POST":
        try:
            # Update settings
            for key, value in request.form.items():
                if key.startswith("setting_"):
                    setting_key = key[8:]  # Remove the "setting_" prefix
                    setting = Setting.query.filter_by(key=setting_key).first()
                    if setting:
                        setting.value = value
                        db.session.commit()
            
            flash("Settings updated successfully.", "success")
            return redirect(url_for("settings"))
        
        except Exception as e:
            logger.error(f"Error updating settings: {str(e)}", exc_info=True)
            flash(f"Error updating settings: {str(e)}", "danger")
    
    try:
        # Get all settings
        all_settings = Setting.query.all()
        
        # If no settings exist, initialize defaults
        if not all_settings:
            init_default_settings()
            all_settings = Setting.query.all()
        
        # Group settings by category
        settings_by_category = {}
        for setting in all_settings:
            category = setting.key.split('_')[0] if '_' in setting.key else 'general'
            if category not in settings_by_category:
                settings_by_category[category] = []
            settings_by_category[category].append(setting)
        
        return render_template(
            "settings.html", 
            settings_by_category=settings_by_category,
            page_title="Settings"
        )
    
    except Exception as e:
        logger.error(f"Error loading settings: {str(e)}", exc_info=True)
        flash(f"Error loading settings: {str(e)}", "danger")
        return render_template("error.html", error=format_error_html(e))


def init_default_settings():
    """Initialize default settings"""
    if not db_available:
        return
    
    default_settings = [
        # Output settings
        {
            "key": "output_default_directory",
            "value": str(RESULTS_DIR),
            "description": "Default directory for saving crawl results"
        },
        {
            "key": "output_default_format",
            "value": "markdown",
            "description": "Default output format (markdown, html, text, json)"
        },
        
        # Crawl settings
        {
            "key": "crawl_default_max_depth",
            "value": "2",
            "description": "Default maximum depth for deep crawling"
        },
        {
            "key": "crawl_default_max_pages",
            "value": "20",
            "description": "Default maximum pages to crawl during deep crawling"
        },
        {
            "key": "crawl_default_stay_within_domain",
            "value": "true",
            "description": "Default setting for staying within the original domain"
        },
        
        # Files settings
        {
            "key": "files_default_types",
            "value": "pdf,docx,xlsx,pptx,txt",
            "description": "Default file types to download"
        },
        {
            "key": "files_default_max_size",
            "value": "50",
            "description": "Default maximum file size in MB"
        },
        {
            "key": "files_default_max_files",
            "value": "20",
            "description": "Default maximum number of files to download"
        },
        
        # Browser settings
        {
            "key": "browser_default_wait_time",
            "value": "0",
            "description": "Default wait time in seconds after page load"
        },
        
        # Speed control settings
        {
            "key": "speed_use_random_delay",
            "value": "false",
            "description": "Add random delays between requests"
        },
        {
            "key": "speed_random_delay_min",
            "value": "1",
            "description": "Minimum delay in seconds when using random delay"
        },
        {
            "key": "speed_random_delay_max", 
            "value": "5",
            "description": "Maximum delay in seconds when using random delay"
        },
        {
            "key": "speed_use_adaptive_delay",
            "value": "false",
            "description": "Adjust delay based on server response time"
        },
        {
            "key": "speed_adaptive_delay_factor",
            "value": "2",
            "description": "Multiplication factor for adaptive delay"
        },
        {
            "key": "speed_use_scheduled_breaks",
            "value": "false",
            "description": "Take periodic breaks during crawling"
        },
        {
            "key": "speed_requests_before_break",
            "value": "50",
            "description": "Number of requests before taking a break"
        },
        {
            "key": "speed_break_duration",
            "value": "30",
            "description": "Duration of breaks in seconds"
        }
    ]
    
    for setting_data in default_settings:
        setting = Setting.query.filter_by(key=setting_data["key"]).first()
        if not setting:
            setting = Setting(
                key=setting_data["key"],
                value=setting_data["value"],
                description=setting_data["description"]
            )
            db.session.add(setting)
    
    db.session.commit()


@app.route("/install-feature/<feature>", methods=["POST"])
def install_feature(feature):
    """Install optional crawl4ai features"""
    if feature == "browser":
        try:
            # Check if playwright is installed
            try:
                import playwright
                has_playwright = True
            except ImportError:
                has_playwright = False
            
            if not has_playwright:
                # Install playwright
                import subprocess
                
                # Use the appropriate pip command based on platform
                if sys.platform == "win32":
                    pip_cmd = [sys.executable, "-m", "pip", "install", "playwright"]
                    install_cmd = [sys.executable, "-m", "playwright", "install"]
                else:
                    pip_cmd = ["pip", "install", "playwright"]
                    install_cmd = ["playwright", "install"]
                
                # Install playwright package
                subprocess.check_call(pip_cmd)
                
                # Install browser binaries
                subprocess.check_call(install_cmd)
                
                flash("Browser automation (playwright) has been installed successfully.", "success")
            else:
                flash("Browser automation (playwright) is already installed.", "info")
            
        except Exception as e:
            logger.error(f"Error installing browser feature: {str(e)}", exc_info=True)
            flash(f"Error installing browser feature: {str(e)}", "danger")
            return redirect(url_for("home"))
    
    elif feature == "pdf":
        try:
            # Check if PyPDF2 is installed
            try:
                import PyPDF2
                has_pypdf = True
            except ImportError:
                has_pypdf = False
            
            if not has_pypdf:
                # Install PyPDF2
                import subprocess
                
                # Use the appropriate pip command based on platform
                if sys.platform == "win32":
                    pip_cmd = [sys.executable, "-m", "pip", "install", "PyPDF2"]
                else:
                    pip_cmd = ["pip", "install", "PyPDF2"]
                
                # Install PyPDF2 package
                subprocess.check_call(pip_cmd)
                
                flash("PDF processing (PyPDF2) has been installed successfully.", "success")
            else:
                flash("PDF processing (PyPDF2) is already installed.", "info")
            
        except Exception as e:
            logger.error(f"Error installing PDF feature: {str(e)}", exc_info=True)
            flash(f"Error installing PDF feature: {str(e)}", "danger")
            return redirect(url_for("home"))
    
    else:
        flash(f"Unknown feature: {feature}", "danger")
    
    return redirect(url_for("home"))


def check_features():
    """Check which optional features are available"""
    features = {
        "browser_automation": False,
        "pdf_processing": False
    }
    
    # Check for playwright for browser automation
    try:
        import playwright
        features["browser_automation"] = True
    except ImportError:
        pass
    
    # Check for PyPDF2 for PDF processing
    try:
        import PyPDF2
        features["pdf_processing"] = True
    except ImportError:
        pass
    
    return features


@app.route("/error")
def error_page():
    """Display an error page with helpful information"""
    error = request.args.get("error", "An unknown error occurred.")
    return render_template("error.html", error=error)


@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('error.html', error="Page not found (404)"), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('error.html', error=format_error_html(error)), 500


# Batch job routes
@app.route("/batches")
def batch_jobs():
    """List all batch jobs"""
    if not db_available:
        flash("Database functionality is not available.", "warning")
        return redirect(url_for("home"))
    
    try:
        batches = BatchJob.query.order_by(BatchJob.created_at.desc()).all()
        return render_template(
            "batches.html", 
            batches=batches,
            page_title="Batch Jobs"
        )
    except Exception as e:
        logger.error(f"Error listing batch jobs: {str(e)}", exc_info=True)
        flash(f"Error: {str(e)}", "danger")
        return render_template("error.html", error=format_error_html(e))


@app.route("/batches/new")
def new_batch():
    """Form for creating a new batch job"""
    if not db_available:
        flash("Database functionality is not available.", "warning")
        return redirect(url_for("home"))
    
    try:
        # Get default settings
        settings = {s.key: s.value for s in Setting.query.all()}
        
        return render_template(
            "new_batch.html", 
            settings=settings,
            page_title="New Batch Job"
        )
    except Exception as e:
        logger.error(f"Error loading new batch form: {str(e)}", exc_info=True)
        flash(f"Error: {str(e)}", "danger")
        return render_template("error.html", error=format_error_html(e))


@app.route("/batches/create", methods=["POST"])
def create_batch():
    """Create a new batch job"""
    if not db_available:
        flash("Database functionality is not available.", "warning")
        return redirect(url_for("home"))
    
    try:
        # Get form data
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        urls_text = request.form.get("urls", "").strip()
        output_dir = request.form.get("output_dir", str(RESULTS_DIR))
        format_type = request.form.get("format", "markdown")
        use_browser = "use_browser" in request.form
        include_images = "include_images" in request.form
        include_links = "include_links" in request.form
        
        # Concurrency and timeout settings
        concurrent_workers = int(request.form.get("concurrent_workers", 3))
        timeout_per_url = int(request.form.get("timeout_per_url", 60))
        
        # Speed control options
        use_random_delay = "use_random_delay" in request.form
        random_delay_min = int(request.form.get("random_delay_min", 1))
        random_delay_max = int(request.form.get("random_delay_max", 5))
        use_adaptive_delay = "use_adaptive_delay" in request.form
        adaptive_delay_factor = int(request.form.get("adaptive_delay_factor", 2))
        use_scheduled_breaks = "use_scheduled_breaks" in request.form
        requests_before_break = int(request.form.get("requests_before_break", 50))
        break_duration = int(request.form.get("break_duration", 30))
        
        # Basic validation
        if not name:
            flash("Please enter a name for the batch job.", "danger")
            return redirect(url_for("new_batch"))
        
        if not urls_text:
            flash("Please enter at least one URL.", "danger")
            return redirect(url_for("new_batch"))
        
        # Process URLs - handle different input formats and clean them
        urls = []
        for line in urls_text.split("\n"):
            line = line.strip()
            if line:
                # Skip comments and empty lines
                if line.startswith("#") or not line:
                    continue
                # Remove any trailing comments
                if "#" in line:
                    line = line.split("#")[0].strip()
                # Add the URL
                if line:
                    urls.append(line)
        
        if not urls:
            flash("No valid URLs found. Please enter at least one URL.", "danger")
            return redirect(url_for("new_batch"))
        
        # Create a new batch job
        batch = BatchJob(
            name=name,
            description=description,
            output_dir=output_dir,
            format=format_type,
            use_browser=use_browser,
            include_images=include_images,
            include_links=include_links,
            concurrent_workers=concurrent_workers,
            timeout_per_url=timeout_per_url,
            use_random_delay=use_random_delay,
            random_delay_min=random_delay_min,
            random_delay_max=random_delay_max,
            use_adaptive_delay=use_adaptive_delay,
            adaptive_delay_factor=adaptive_delay_factor,
            use_scheduled_breaks=use_scheduled_breaks,
            requests_before_break=requests_before_break,
            break_duration=break_duration,
            status="pending",
            created_at=datetime.utcnow(),
            total_urls=len(urls)
        )
        
        db.session.add(batch)
        db.session.commit()
        
        # Create batch items for each URL
        for i, url in enumerate(urls):
            item = BatchJobItem(
                batch_job_id=batch.id,
                url=url,
                priority=0,  # Default priority
                status="pending",
                created_at=datetime.utcnow()
            )
            db.session.add(item)
        
        db.session.commit()
        
        flash(f"Batch job '{name}' created with {len(urls)} URLs.", "success")
        return redirect(url_for("batch_detail", batch_id=batch.id))
    
    except Exception as e:
        logger.error(f"Error creating batch job: {str(e)}", exc_info=True)
        flash(f"Error: {str(e)}", "danger")
        return render_template("error.html", error=format_error_html(e))


@app.route("/batches/<int:batch_id>")
def batch_detail(batch_id):
    """View details of a specific batch job"""
    if not db_available:
        flash("Database functionality is not available.", "warning")
        return redirect(url_for("home"))
    
    try:
        batch = BatchJob.query.get_or_404(batch_id)
        items = BatchJobItem.query.filter_by(batch_job_id=batch_id).order_by(BatchJobItem.created_at).all()
        
        return render_template(
            "batch_detail.html", 
            batch=batch,
            items=items,
            page_title=f"Batch: {batch.name}"
        )
    except Exception as e:
        logger.error(f"Error viewing batch job {batch_id}: {str(e)}", exc_info=True)
        flash(f"Error: {str(e)}", "danger")
        return render_template("error.html", error=format_error_html(e))


@app.route("/batches/<int:batch_id>/start", methods=["POST"])
def start_batch(batch_id):
    """Start processing a batch job"""
    if not db_available:
        flash("Database functionality is not available.", "warning")
        return redirect(url_for("home"))
    
    try:
        batch = BatchJob.query.get_or_404(batch_id)
        
        # Only start if the batch is in pending or paused status
        if batch.status not in ["pending", "paused"]:
            flash(f"Cannot start batch job in '{batch.status}' status.", "warning")
            return redirect(url_for("batch_detail", batch_id=batch_id))
        
        # Update status
        batch.status = "running"
        batch.started_at = datetime.utcnow() if not batch.started_at else batch.started_at
        db.session.commit()
        
        # Start processing in a background thread
        import threading
        thread = threading.Thread(target=process_batch_job, args=(batch_id,))
        thread.daemon = True
        thread.start()
        
        flash(f"Batch job '{batch.name}' started.", "success")
        return redirect(url_for("batch_detail", batch_id=batch_id))
    
    except Exception as e:
        logger.error(f"Error starting batch job {batch_id}: {str(e)}", exc_info=True)
        flash(f"Error: {str(e)}", "danger")
        return render_template("error.html", error=format_error_html(e))


@app.route("/batches/<int:batch_id>/pause", methods=["POST"])
def pause_batch(batch_id):
    """Pause a running batch job"""
    if not db_available:
        flash("Database functionality is not available.", "warning")
        return redirect(url_for("home"))
    
    try:
        batch = BatchJob.query.get_or_404(batch_id)
        
        # Only pause if the batch is running
        if batch.status != "running":
            flash(f"Cannot pause batch job in '{batch.status}' status.", "warning")
            return redirect(url_for("batch_detail", batch_id=batch_id))
        
        # Update status
        batch.status = "paused"
        db.session.commit()
        
        flash(f"Batch job '{batch.name}' paused.", "success")
        return redirect(url_for("batch_detail", batch_id=batch_id))
    
    except Exception as e:
        logger.error(f"Error pausing batch job {batch_id}: {str(e)}", exc_info=True)
        flash(f"Error: {str(e)}", "danger")
        return render_template("error.html", error=format_error_html(e))


@app.route("/batches/<int:batch_id>/delete", methods=["POST"])
def delete_batch(batch_id):
    """Delete a batch job and its items"""
    if not db_available:
        flash("Database functionality is not available.", "warning")
        return redirect(url_for("home"))
    
    try:
        batch = BatchJob.query.get_or_404(batch_id)
        
        # Delete all items first (this should cascade, but we'll be explicit)
        BatchJobItem.query.filter_by(batch_job_id=batch_id).delete()
        
        # Delete the batch job
        db.session.delete(batch)
        db.session.commit()
        
        flash(f"Batch job '{batch.name}' deleted.", "success")
        return redirect(url_for("batch_jobs"))
    
    except Exception as e:
        logger.error(f"Error deleting batch job {batch_id}: {str(e)}", exc_info=True)
        flash(f"Error: {str(e)}", "danger")
        return render_template("error.html", error=format_error_html(e))


@app.route("/items/<int:item_id>/retry", methods=["POST"])
def retry_item(item_id):
    """Retry a failed batch job item"""
    if not db_available:
        flash("Database functionality is not available.", "warning")
        return redirect(url_for("home"))
    
    try:
        item = BatchJobItem.query.get_or_404(item_id)
        
        # Only retry if the item failed
        if item.status != "failed":
            flash(f"Cannot retry item in '{item.status}' status.", "warning")
            return redirect(url_for("batch_detail", batch_id=item.batch_job_id))
        
        # Reset the item status
        item.status = "pending"
        item.error_message = None
        item.started_at = None
        item.completed_at = None
        db.session.commit()
        
        # Update batch statistics
        batch = BatchJob.query.get(item.batch_job_id)
        batch.failed_urls -= 1
        db.session.commit()
        
        flash(f"Item for URL '{item.url}' has been reset and will be retried.", "success")
        return redirect(url_for("batch_detail", batch_id=item.batch_job_id))
    
    except Exception as e:
        logger.error(f"Error retrying batch item {item_id}: {str(e)}", exc_info=True)
        flash(f"Error: {str(e)}", "danger")
        return render_template("error.html", error=format_error_html(e))


@app.route("/batches/<int:batch_id>/retry-failed", methods=["POST"])
def retry_failed_urls(batch_id):
    """Retry all failed URLs in a batch job"""
    if not db_available:
        flash("Database functionality is not available.", "warning")
        return redirect(url_for("home"))
    
    try:
        batch = BatchJob.query.get_or_404(batch_id)
        
        # Find all failed items
        failed_items = BatchJobItem.query.filter_by(batch_job_id=batch_id, status="failed").all()
        
        if not failed_items:
            flash("No failed items to retry.", "info")
            return redirect(url_for("batch_detail", batch_id=batch_id))
        
        # Reset all failed items
        for item in failed_items:
            item.status = "pending"
            item.error_message = None
            item.started_at = None
            item.completed_at = None
        
        # Update batch statistics
        batch.failed_urls = 0
        
        # If the batch was completed, set it back to paused so it can be restarted
        if batch.status == "completed":
            batch.status = "paused"
        
        db.session.commit()
        
        flash(f"Reset {len(failed_items)} failed items for retry.", "success")
        return redirect(url_for("batch_detail", batch_id=batch_id))
    
    except Exception as e:
        logger.error(f"Error retrying failed URLs for batch {batch_id}: {str(e)}", exc_info=True)
        flash(f"Error: {str(e)}", "danger")
        return render_template("error.html", error=format_error_html(e))


@app.route("/batches/<int:batch_id>/export", methods=["GET"])
def export_batch_results(batch_id):
    """Export all results from a batch job"""
    if not db_available:
        flash("Database functionality is not available.", "warning")
        return redirect(url_for("home"))
    
    try:
        batch = BatchJob.query.get_or_404(batch_id)
        
        # Get all successfully completed items with results
        items = BatchJobItem.query.filter_by(batch_job_id=batch_id, status="completed").all()
        
        # Filter items with results
        items_with_results = [item for item in items if item.result_id is not None]
        
        if not items_with_results:
            flash("No results available for export.", "warning")
            return redirect(url_for("batch_detail", batch_id=batch_id))
        
        # Create an export data structure
        export_data = {
            "batch_job": {
                "id": batch.id,
                "name": batch.name,
                "description": batch.description,
                "created_at": batch.created_at.isoformat() if batch.created_at else None,
                "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
                "status": batch.status,
                "total_urls": batch.total_urls,
                "successful_urls": batch.successful_urls
            },
            "results": []
        }
        
        # Add result data
        for item in items_with_results:
            result = CrawlResult.query.get(item.result_id)
            if result:
                # Try to read the output file
                content = ""
                try:
                    with open(result.output_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    logger.warning(f"Could not read output file for result {result.id}: {str(e)}")
                
                export_data["results"].append({
                    "url": item.url,
                    "title": result.title,
                    "content": content,
                    "word_count": result.word_count,
                    "link_count": result.link_count,
                    "image_count": result.image_count,
                    "created_at": result.created_at.isoformat() if result.created_at else None
                })
        
        # Convert to JSON and return as a downloadable file
        response = jsonify(export_data)
        response.headers.set("Content-Disposition", f"attachment; filename=batch_{batch_id}_export.json")
        return response
    
    except Exception as e:
        logger.error(f"Error exporting batch results for {batch_id}: {str(e)}", exc_info=True)
        flash(f"Error: {str(e)}", "danger")
        return render_template("error.html", error=format_error_html(e))


def process_batch_job(batch_id):
    """
    Process a batch job in the background.
    
    This function is called in a separate thread to process URLs in a batch job.
    It selects pending items, crawls them, and updates the database with results.
    """
    if not db_available:
        logger.error("Database functionality is not available for batch processing.")
        return
    
    try:
        # Import required modules
        try:
            import crawl4ai
            from crawl4ai.config import CrawlerRunConfig, DispatcherConfig
        except ImportError:
            logger.error("crawl4ai module not available for batch processing.")
            # Update batch status to failed
            with app.app_context():
                batch = BatchJob.query.get(batch_id)
                if batch:
                    batch.status = "failed"
                    batch.error_message = "crawl4ai module not available"
                    db.session.commit()
            return
        
        # Get batch job configuration
        with app.app_context():
            batch = BatchJob.query.get(batch_id)
            if not batch:
                logger.error(f"Batch job {batch_id} not found.")
                return
            
            # Check if the job is still supposed to be running
            if batch.status != "running":
                logger.info(f"Batch job {batch_id} is not in running status. Current status: {batch.status}")
                return
            
            # Create the output directory
            output_dir = Path(batch.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create dispatcher config for speed control
            dispatcher_config = DispatcherConfig(
                max_concurrent_tasks=batch.concurrent_workers,
                use_random_delay=batch.use_random_delay,
                random_delay_min_seconds=batch.random_delay_min,
                random_delay_max_seconds=batch.random_delay_max,
                use_adaptive_delay=batch.use_adaptive_delay,
                adaptive_delay_factor=batch.adaptive_delay_factor,
                use_scheduled_breaks=batch.use_scheduled_breaks,
                requests_before_break=batch.requests_before_break,
                break_duration_seconds=batch.break_duration
            )
        
        # Process items until all are done or the job is paused/stopped
        while True:
            with app.app_context():
                # Check if the job should still be running
                batch = BatchJob.query.get(batch_id)
                if not batch or batch.status != "running":
                    logger.info(f"Batch job {batch_id} is no longer running. Current status: {batch.status if batch else 'Not found'}")
                    break
                
                # Get a batch of pending items based on the concurrent_workers setting
                items = BatchJobItem.query.filter_by(
                    batch_job_id=batch_id, status="pending"
                ).order_by(
                    BatchJobItem.priority.desc(), BatchJobItem.created_at
                ).limit(batch.concurrent_workers).all()
                
                if not items:
                    # No more pending items, check if we're done
                    pending_count = BatchJobItem.query.filter_by(batch_job_id=batch_id, status="pending").count()
                    processing_count = BatchJobItem.query.filter_by(batch_job_id=batch_id, status="processing").count()
                    
                    if pending_count == 0 and processing_count == 0:
                        # All items are done, update batch status
                        batch.status = "completed"
                        batch.completed_at = datetime.utcnow()
                        db.session.commit()
                        logger.info(f"Batch job {batch_id} completed.")
                        break
                    
                    # If there are still items processing, wait and check again
                    if processing_count > 0:
                        logger.info(f"Waiting for {processing_count} processing items to complete.")
                        db.session.commit()
                        time.sleep(5)  # Wait 5 seconds before checking again
                        continue
                
                # Update items to processing status
                for item in items:
                    item.status = "processing"
                    item.started_at = datetime.utcnow()
                
                db.session.commit()
            
            # Process each item
            for item in items:
                # Check again if the job should still be running
                with app.app_context():
                    batch = BatchJob.query.get(batch_id)
                    if not batch or batch.status != "running":
                        logger.info(f"Batch job {batch_id} is no longer running during item processing.")
                        break
                
                # Process the item
                result = None
                error_message = None
                
                try:
                    # Create configuration for the crawler
                    config = CrawlerRunConfig(
                        url=item.url,
                        use_browser=batch.use_browser,
                        include_images=batch.include_images,
                        include_links=batch.include_links,
                        timeout=batch.timeout_per_url
                    )
                    
                    # Import the async loop handling based on platform
                    import asyncio
                    if sys.platform.startswith('win'):
                        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                    
                    # Use a new event loop for each crawl
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Run the crawler
                    result = loop.run_until_complete(crawl4ai.arun(config))
                    loop.close()
                    
                except Exception as e:
                    logger.error(f"Error processing item URL {item.url}: {str(e)}", exc_info=True)
                    error_message = str(e)
                
                # Update the item with the result
                with app.app_context():
                    item = BatchJobItem.query.get(item.id)
                    
                    if result:
                        # Save the result
                        output_file = save_result(result, batch.output_dir, batch.format)
                        result_id = save_result_to_db(batch.id, result, output_file)
                        
                        # Update the item
                        item.status = "completed"
                        item.result_id = result_id
                        
                        # Update batch statistics
                        batch.processed_urls += 1
                        batch.successful_urls += 1
                        
                    else:
                        # Update the item with error
                        item.status = "failed"
                        item.error_message = error_message
                        
                        # Update batch statistics
                        batch.processed_urls += 1
                        batch.failed_urls += 1
                    
                    item.completed_at = datetime.utcnow()
                    db.session.commit()
            
            # Sleep a bit to prevent overloading the database with constant queries
            time.sleep(1)
    
    except Exception as e:
        logger.error(f"Error in batch job processor for batch {batch_id}: {str(e)}", exc_info=True)
        # Update batch status to failed
        with app.app_context():
            batch = BatchJob.query.get(batch_id)
            if batch:
                batch.status = "failed"
                batch.error_message = str(e)
                db.session.commit()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)