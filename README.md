# Easy Crawl4AI

A user-friendly wrapper for the crawl4ai web crawler, designed to make web scraping accessible to users without technical expertise.

## Features

### Command-Line Interface
- **Single URL crawling**: Extract content from a specific webpage
- **Multiple URL crawling**: Process a list of URLs in parallel 
- **Deep crawling**: Follow links from a starting URL to discover and crawl additional pages
- **File downloading**: Find and download specific file types (PDF, DOC, etc.) from websites
- **Speed control**: Adaptive delays, random delays, and scheduled breaks to respect websites

### Web Interface
- **Job-based crawling**: Submit crawling tasks through a browser and view results
- **Batch processing**: Process multiple URLs in a single batch job with configurable settings
- **Job history**: Track the status and results of all crawling jobs
- **Settings management**: Configure default settings and install optional features

### Output Formats
- Multiple output formats supported: Markdown, HTML, plain text, and JSON
- Ability to view or download results directly from the web interface

### Platform Support
- **Linux version**: Optimized for Linux environments (default version)
- **Cross-platform version**: Compatible with Windows, macOS, and Linux

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/easy-crawl4ai.git
   cd easy-crawl4ai
   ```

2. Install dependencies:
   ```
   pip install -e .
   ```

### Linux Version (Default)

3. Run the web interface:
   ```
   python easy_crawl4ai_web.py
   ```

4. Or use the command-line interface:
   ```
   python easy_crawl4ai.py --help
   ```

### Cross-Platform Version (Windows, macOS, Linux)

3. Run the cross-platform web interface:
   ```
   python easy_crawl4ai_crossplatform.py
   ```

4. Or use the cross-platform command-line interface:
   ```
   python -m easy_crawl4ai.crossplatform.cli --help
   ```

## Requirements

- Python 3.8+
- crawl4ai
- Flask
- SQLAlchemy
- Playwright (optional, for browser-based crawling)
- PyPDF2 (optional, for PDF processing)

## Usage

### Linux Version

#### Command Line

```bash
# Crawl a single URL
python easy_crawl4ai.py crawl https://example.com -o ./results -f markdown

# Crawl multiple URLs
python easy_crawl4ai.py crawl-multiple https://example.com https://another.com -o ./results

# Deep crawl a website
python easy_crawl4ai.py deep-crawl https://example.com -d 3 -p 20 -o ./deep_results

# Download files from a website
python easy_crawl4ai.py download-files https://example.com -o ./downloads -t pdf,docx
```

#### Web Interface

1. Start the web server:
   ```bash
   python easy_crawl4ai_web.py
   ```

2. Open your browser and navigate to `http://localhost:5000`

3. Use the web interface to submit and manage crawling jobs

### Cross-Platform Version

#### Command Line

```bash
# On Windows
python -m easy_crawl4ai.crossplatform.cli crawl https://example.com -o ./results -f markdown

# On macOS
python -m easy_crawl4ai.crossplatform.cli crawl-multiple https://example.com https://another.com -o ./results

# On any platform
python -m easy_crawl4ai.crossplatform.cli deep-crawl https://example.com -d 3 -p 20 -o ./deep_results
python -m easy_crawl4ai.crossplatform.cli download-files https://example.com -o ./downloads -t pdf,docx
```

#### Web Interface

1. Start the cross-platform web server:
   ```bash
   python easy_crawl4ai_crossplatform.py
   ```

2. Your browser should open automatically to `http://localhost:5000`

3. Use the web interface to submit and manage crawling jobs

## License

MIT License