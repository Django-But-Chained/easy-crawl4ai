import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
import subprocess
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "easy_crawl4ai_secret")

@app.route('/')
def home():
    """Home page route"""
    return render_template('index.html')

@app.route('/run_crawl', methods=['POST'])
def run_crawl():
    """Run the crawler with the provided options"""
    try:
        # Get form data
        command_type = request.form.get('command_type', 'crawl')
        url = request.form.get('url', '')
        output_dir = request.form.get('output_dir', './crawl_results')
        format_type = request.form.get('format', 'markdown')
        use_browser = 'browser' in request.form
        include_images = 'include_images' in request.form
        include_links = 'include_links' in request.form
        
        # Build the command
        cmd = ['python', 'easy_crawl4ai.py', command_type, url, 
               '--output-dir', output_dir, 
               '--format', format_type]
        
        if use_browser:
            cmd.append('--browser')
        else:
            cmd.append('--no-browser')
            
        if include_images:
            cmd.append('--include-images')
        else:
            cmd.append('--no-images')
            
        if include_links:
            cmd.append('--include-links')
        else:
            cmd.append('--no-links')
        
        # Additional parameters based on command type
        if command_type == 'deep-crawl':
            max_depth = request.form.get('max_depth', '2')
            max_pages = request.form.get('max_pages', '10')
            stay_within_domain = 'stay_within_domain' in request.form
            
            cmd.extend(['--max-depth', max_depth, '--max-pages', max_pages])
            
            if stay_within_domain:
                cmd.append('--stay-within-domain')
            else:
                cmd.append('--explore-external')
        
        # Run the command
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': 'Crawl completed successfully',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Crawl failed',
                'error': result.stderr
            })
    
    except Exception as e:
        logger.error(f"Error running crawl: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred',
            'error': str(e)
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)