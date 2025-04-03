from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
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