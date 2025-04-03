from setuptools import setup, find_packages
import os
import glob

try:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = "Easy Crawl4AI - A user-friendly wrapper for the crawl4ai web crawler"

# Create package data dictionary
package_data = {
    'easy_crawl4ai': [
        'templates/*.html',
        'static/css/*.css',
        'static/js/*.js',
    ]
}

# Collect template files
template_files = []
if os.path.exists("templates"):
    for root, dirs, files in os.walk("templates"):
        for file in files:
            if file.endswith('.html'):
                template_files.append(os.path.join(root, file))

setup(
    name="easy-crawl4ai",
    version="1.0.0",
    author="Easy Crawl4AI Team",
    author_email="info@easycrawl4ai.example.com",
    description="A user-friendly interface for the crawl4ai web crawler",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/easy-crawl4ai",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "crawl4ai>=0.5.0",
        "click>=8.0.0",
        "rich>=10.0.0",
        "flask>=2.0.0",
        "flask-sqlalchemy>=3.0.0",
        "sqlalchemy>=2.0.0",
        "gunicorn>=20.0.0",
        "psycopg2-binary>=2.9.0",
        "email-validator>=1.1.0",
    ],
    extras_require={
        'pdf': ["PyPDF2>=3.0.0"],
        'browser': ["playwright>=1.30.0"],
        'llm': ["openai>=0.27.0", "langchain>=0.0.200"],
        'all': [
            "PyPDF2>=3.0.0",
            "playwright>=1.30.0",
            "openai>=0.27.0",
            "langchain>=0.0.200"
        ],
    },
    entry_points={
        "console_scripts": [
            "easy_crawl4ai=easy_crawl4ai:cli",
            "easy_crawl4ai_web=easy_crawl4ai.web_app:main",
            "easy_crawl4ai_crossplatform=easy_crawl4ai.crossplatform.web_app:main",
            "easy_crawl4ai_crossplatform_cli=easy_crawl4ai.crossplatform.cli:cli",
        ],
    },
    include_package_data=True,
    package_data=package_data,
    data_files=[('templates', template_files)] if template_files else [],
)
