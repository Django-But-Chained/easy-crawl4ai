# Easy Crawl4AI

A user-friendly wrapper for the [crawl4ai](https://github.com/unclecode/crawl4ai) web crawler that simplifies usage for non-technical users.

## Features

- Simple, intuitive web interface and command-line interface
- Clear explanations of each option
- Customizable output location for crawled data
- Progress indicators and detailed summaries
- Built on top of the powerful crawl4ai library

## Installation

First, make sure you have Python 3.8 or higher installed. Then install Easy Crawl4AI with all its dependencies:

```bash
# Install required dependencies
pip install crawl4ai rich click flask

# If installing from this repo
pip install .
```

## Usage

### Web Interface (Recommended for Non-Technical Users)

The web interface provides a user-friendly way to configure and run the crawler:

```bash
# Start the web interface
python easy_crawl4ai_web.py

# Or if installed via pip
easy_crawl4ai_web
```

Then open your browser and navigate to: http://localhost:5000

### Command Line Interface

For more advanced users or for scripting purposes, you can use the command-line interface:

```bash
# Get help information
python easy_crawl4ai.py info

# Basic usage: Crawl a single URL
python easy_crawl4ai.py crawl https://example.com -o ./results -f markdown

# Deep crawling: Follow links within a website
python easy_crawl4ai.py deep-crawl https://example.com -d 3 -p 20 -o ./deep_results

# Multiple URLs: Crawl several pages in parallel
python easy_crawl4ai.py crawl-multiple https://example.com https://another.com -o ./results

# Download files: Get PDFs, documents, etc.
python easy_crawl4ai.py download-files https://example.com -o ./downloads -t pdf,docx
```

## Command Options

### Common Options (Available for All Commands)

- `--output-dir`, `-o`: Directory where results will be saved
- `--format`, `-f`: Output format (markdown, html, text, json)
- `--browser/--no-browser`: Use browser-based crawling for JavaScript-heavy sites
- `--include-images/--no-images`: Include image descriptions in the output
- `--include-links/--no-links`: Include hyperlinks in the output

### Command-Specific Options

#### Deep Crawl

- `--max-depth`, `-d`: Maximum depth for crawling (default: 2)
- `--max-pages`, `-p`: Maximum number of pages to crawl (default: 10)
- `--stay-within-domain/--explore-external`: Restrict crawling to the same domain

#### Multiple URLs

- `--concurrent`, `-c`: Number of URLs to crawl concurrently (default: 5)

#### Download Files

- `--file-types`, `-t`: Comma-separated list of file extensions to download
- `--max-size`, `-s`: Maximum file size in MB (default: 100)
- `--max-files`, `-m`: Maximum number of files to download (default: 10)

## Output Formats

- **Markdown**: Human-readable text with formatting (default)
- **HTML**: Original HTML content
- **Text**: Plain text without formatting
- **JSON**: Structured data format for processing

## Example Usage Scenarios

### Scenario 1: Research a Topic

```bash
# Crawl a Wikipedia article and its linked pages
python easy_crawl4ai.py deep-crawl https://en.wikipedia.org/wiki/Artificial_intelligence -d 2 -p 5 -o ./ai_research --stay-within-domain
```

### Scenario 2: Download Course Materials

```bash
# Download all PDFs from a course website
python easy_crawl4ai.py download-files https://university.edu/course101 -o ./course_materials -t pdf,ppt,docx
```

### Scenario 3: Monitor Multiple News Sites

```bash
# Crawl the front pages of several news websites
python easy_crawl4ai.py crawl-multiple https://news.bbc.co.uk https://cnn.com https://reuters.com -o ./news_updates
```

## License

This project is licensed under the Apache 2.0 License - see the LICENSE file for details.

## Acknowledgments

- [crawl4ai](https://github.com/unclecode/crawl4ai) - The powerful web crawler library this tool is based on
- [Click](https://click.palletsprojects.com/) - For the command-line interface
- [Rich](https://rich.readthedocs.io/en/latest/) - For beautiful console output
- [Flask](https://flask.palletsprojects.com/) - For the web interface