from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app import db

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
    content_insights = Column(JSON, nullable=True)  # Store AI-powered insights
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
            'content_insights': self.content_insights,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class BatchJob(db.Model):
    """Model for batch processing of multiple URLs"""
    __tablename__ = 'batch_jobs'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    output_dir = Column(String(255), nullable=False)
    format = Column(String(20), default='markdown')
    use_browser = Column(Boolean, default=False)
    include_images = Column(Boolean, default=True)
    include_links = Column(Boolean, default=True)
    
    # Processing options
    concurrent_workers = Column(Integer, default=3)  # How many URLs to process concurrently
    timeout_per_url = Column(Integer, default=60)    # Timeout in seconds per URL
    
    # Metadata
    status = Column(String(20), default='pending')  # pending, running, completed, failed, paused
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Statistics
    total_urls = Column(Integer, default=0)
    processed_urls = Column(Integer, default=0)
    successful_urls = Column(Integer, default=0)
    failed_urls = Column(Integer, default=0)
    
    # Relationships
    items = relationship("BatchJobItem", back_populates="batch_job", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<BatchJob {self.id} - {self.name} - {self.status}>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'output_dir': self.output_dir,
            'format': self.format,
            'use_browser': self.use_browser,
            'include_images': self.include_images,
            'include_links': self.include_links,
            'concurrent_workers': self.concurrent_workers,
            'timeout_per_url': self.timeout_per_url,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_urls': self.total_urls,
            'processed_urls': self.processed_urls,
            'successful_urls': self.successful_urls,
            'failed_urls': self.failed_urls
        }
    
    def progress_percentage(self):
        """Calculate the progress percentage of the batch job"""
        if self.total_urls <= 0:
            return 0
        return int((self.processed_urls / self.total_urls) * 100)
    
    def remaining_urls(self):
        """Calculate the number of remaining URLs to process"""
        return self.total_urls - self.processed_urls


class BatchJobItem(db.Model):
    """Model for individual URLs within a batch job"""
    __tablename__ = 'batch_job_items'
    
    id = Column(Integer, primary_key=True)
    batch_job_id = Column(Integer, ForeignKey('batch_jobs.id'), nullable=False)
    url = Column(String(2048), nullable=False)
    priority = Column(Integer, default=0)  # Higher number = higher priority
    
    # Processing status
    status = Column(String(20), default='pending')  # pending, processing, completed, failed, skipped
    result_id = Column(Integer, ForeignKey('crawl_results.id'), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    batch_job = relationship("BatchJob", back_populates="items")
    result = relationship("CrawlResult", foreign_keys=[result_id])
    
    def __repr__(self):
        return f"<BatchJobItem {self.id} - {self.url} - {self.status}>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'batch_job_id': self.batch_job_id,
            'url': self.url,
            'priority': self.priority,
            'status': self.status,
            'result_id': self.result_id,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
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