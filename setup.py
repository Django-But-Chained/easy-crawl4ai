from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="easy-crawl4ai",
    version="1.0.0",
    author="Easy Crawl4AI Team",
    author_email="info@easycrawl4ai.com",
    description="A user-friendly CLI wrapper for the crawl4ai web crawler",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/easy-crawl4ai",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "crawl4ai>=0.5.0",
        "click>=8.0.0",
        "rich>=12.0.0",
    ],
    entry_points={
        "console_scripts": [
            "easy_crawl4ai=easy_crawl4ai:cli",
        ],
    },
    py_modules=["easy_crawl4ai"],
)
