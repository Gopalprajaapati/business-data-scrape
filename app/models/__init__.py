# app/models/__init__.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index, Text, DateTime, Float, Boolean, Integer, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func
from datetime import datetime
import logging

db = SQLAlchemy()


class BaseModel(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def save(self):
        """Save object to database"""
        try:
            db.session.add(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error saving {self.__class__.__name__}: {e}")
            return False

    def delete(self):
        """Delete object from database"""
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error deleting {self.__class__.__name__}: {e}")
            return False


class Keyword(BaseModel):
    __tablename__ = 'keywords'

    # Columns
    keyword = db.Column(db.String(500), nullable=False, index=True)
    status = db.Column(db.String(50), default='pending', index=True)
    priority = db.Column(db.Integer, default=1)  # 1-5 scale
    completed_at = db.Column(db.DateTime)
    last_scraped = db.Column(db.DateTime)
    total_results = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Float, default=0.0)

    # Relationships
    results = db.relationship('SearchResult', backref='keyword_obj', lazy='dynamic', cascade='all, delete-orphan')
    analyses = db.relationship('WebsiteAnalysis', backref='keyword_analysis', lazy='dynamic')

    # Indexes
    __table_args__ = (
        Index('idx_keyword_status', 'keyword', 'status'),
        Index('idx_keyword_priority', 'priority', 'status'),
        Index('idx_keyword_created', 'created_at'),
    )

    @hybrid_property
    def is_completed(self):
        return self.status == 'completed'

    @hybrid_property
    def days_since_last_scrape(self):
        if self.last_scraped:
            return (datetime.utcnow() - self.last_scraped).days
        return None

    def update_stats(self):
        """Update keyword statistics"""
        self.total_results = self.results.count()

        successful_results = self.results.filter(
            SearchResult.title.isnot(None),
            SearchResult.website.isnot(None)
        ).count()

        if self.total_results > 0:
            self.success_rate = (successful_results / self.total_results) * 100

        self.save()

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'keyword': self.keyword,
            'status': self.status,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_results': self.total_results,
            'success_rate': self.success_rate,
            'days_since_last_scrape': self.days_since_last_scrape
        }


class SearchResult(BaseModel):
    __tablename__ = 'search_results'

    # Columns
    keyword_id = db.Column(db.Integer, db.ForeignKey('keywords.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(500))
    link = db.Column(db.Text)
    website = db.Column(db.Text, index=True)
    stars = db.Column(db.Float, index=True)
    reviews = db.Column(db.Integer)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(200))
    address = db.Column(db.Text)

    # Social Media
    facebook = db.Column(db.Text)
    instagram = db.Column(db.Text)
    linkedin = db.Column(db.Text)
    twitter = db.Column(db.Text)
    youtube = db.Column(db.Text)

    # Additional metadata
    category = db.Column(db.String(100), index=True)
    business_hours = db.Column(db.Text)
    price_range = db.Column(db.String(50))

    # Quality flags
    has_website = db.Column(db.Boolean, default=False, index=True)
    has_contact = db.Column(db.Boolean, default=False, index=True)
    has_social = db.Column(db.Boolean, default=False, index=True)

    # Relationships
    analyses = db.relationship('WebsiteAnalysis', backref='result', lazy='dynamic', cascade='all, delete-orphan')

    # Indexes
    __table_args__ = (
        Index('idx_result_keyword', 'keyword_id', 'created_at'),
        Index('idx_result_website', 'website'),
        Index('idx_result_rating', 'stars'),
        Index('idx_result_category', 'category'),
        Index('idx_result_quality', 'has_website', 'has_contact', 'has_social'),
        Index('idx_result_comprehensive', 'keyword_id', 'has_website', 'stars'),
    )

    @hybrid_property
    def quality_score(self):
        """Calculate quality score based on available data"""
        score = 0
        if self.title:
            score += 20
        if self.website:
            score += 30
        if self.phone or self.email:
            score += 20
        if self.stars:
            score += 15
        if self.facebook or self.instagram or self.linkedin:
            score += 15
        return score

    def update_quality_flags(self):
        """Update quality flags based on available data"""
        self.has_website = bool(self.website)
        self.has_contact = bool(self.phone or self.email)
        self.has_social = bool(self.facebook or self.instagram or self.linkedin or self.twitter)
        self.save()

    def to_dict(self, include_analysis=False):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'keyword_id': self.keyword_id,
            'title': self.title,
            'link': self.link,
            'website': self.website,
            'stars': self.stars,
            'reviews': self.reviews,
            'phone': self.phone,
            'email': self.email,
            'address': self.address,
            'social_media': {
                'facebook': self.facebook,
                'instagram': self.instagram,
                'linkedin': self.linkedin,
                'twitter': self.twitter,
                'youtube': self.youtube
            },
            'quality_score': self.quality_score,
            'has_website': self.has_website,
            'has_contact': self.has_contact,
            'has_social': self.has_social,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

        if include_analysis and self.analyses.first():
            data['analysis'] = self.analyses.first().to_dict()

        return data


class WebsiteAnalysis(BaseModel):
    __tablename__ = 'website_analyses'

    # Columns
    result_id = db.Column(db.Integer, db.ForeignKey('search_results.id', ondelete='CASCADE'), nullable=False,
                          index=True)

    # Basic Analysis
    mobile_friendly = db.Column(db.Boolean)
    load_time = db.Column(db.Float)
    professional_look = db.Column(db.Boolean)
    issues = db.Column(db.Text)
    score = db.Column(db.Integer, index=True)

    # Advanced Analysis
    seo_score = db.Column(db.Integer)
    performance_score = db.Column(db.Integer)
    security_score = db.Column(db.Integer)
    credibility_score = db.Column(db.Integer)

    # Technical Details
    technology_stack = db.Column(db.Text)  # JSON string
    server_info = db.Column(db.Text)
    ssl_grade = db.Column(db.String(5))

    # Content Analysis
    word_count = db.Column(db.Integer)
    image_count = db.Column(db.Integer)
    internal_links = db.Column(db.Integer)
    external_links = db.Column(db.Integer)

    # Caching
    is_cached = db.Column(db.Boolean, default=False)
    cache_key = db.Column(db.String(100), index=True)

    # Indexes
    __table_args__ = (
        Index('idx_analysis_score', 'score'),
        Index('idx_analysis_seo', 'seo_score'),
        Index('idx_analysis_performance', 'performance_score'),
        Index('idx_analysis_comprehensive', 'result_id', 'score', 'created_at'),
        Index('idx_analysis_cached', 'is_cached', 'created_at'),
    )

    @hybrid_property
    def overall_grade(self):
        """Convert score to letter grade"""
        if self.score >= 90:
            return 'A+'
        elif self.score >= 80:
            return 'A'
        elif self.score >= 70:
            return 'B'
        elif self.score >= 60:
            return 'C'
        elif self.score >= 50:
            return 'D'
        else:
            return 'F'

    @hybrid_property
    def analysis_age_days(self):
        """Days since analysis was performed"""
        if self.created_at:
            return (datetime.utcnow() - self.created_at).days
        return None

    def get_technology_stack_list(self):
        """Parse technology stack from JSON string"""
        import json
        try:
            if self.technology_stack:
                return json.loads(self.technology_stack)
        except:
            pass
        return []

    def set_technology_stack(self, tech_list):
        """Set technology stack as JSON string"""
        import json
        try:
            self.technology_stack = json.dumps(tech_list)
        except:
            self.technology_stack = '[]'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'result_id': self.result_id,
            'scores': {
                'overall': self.score,
                'seo': self.seo_score,
                'performance': self.performance_score,
                'security': self.security_score,
                'credibility': self.credibility_score
            },
            'metrics': {
                'mobile_friendly': self.mobile_friendly,
                'load_time': self.load_time,
                'professional_look': self.professional_look,
                'word_count': self.word_count,
                'image_count': self.image_count,
                'internal_links': self.internal_links,
                'external_links': self.external_links
            },
            'technical': {
                'technology_stack': self.get_technology_stack_list(),
                'server_info': self.server_info,
                'ssl_grade': self.ssl_grade
            },
            'grade': self.overall_grade,
            'issues': self.issues.split('|') if self.issues else [],
            'is_cached': self.is_cached,
            'analysis_age_days': self.analysis_age_days,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# Database Manager Class
class DatabaseManager:
    def __init__(self, db):
        self.db = db

    def optimize_database(self):
        """Perform database optimization tasks"""
        try:
            # Create missing indexes
            self.create_missing_indexes()

            # Update statistics
            self.update_table_statistics()

            # Clean up old data
            self.cleanup_old_data()

            # Vacuum database (SQLite)
            self.vacuum_database()

            logging.info("Database optimization completed successfully")
            return True

        except Exception as e:
            logging.error(f"Database optimization failed: {e}")
            return False

    def create_missing_indexes(self):
        """Create essential indexes if missing"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_keywords_search ON keywords(keyword, status)",
            "CREATE INDEX IF NOT EXISTS idx_results_comprehensive ON search_results(keyword_id, has_website, stars, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_analyses_performance ON website_analyses(score, seo_score, performance_score)",
        ]

        for index_sql in indexes:
            try:
                self.db.session.execute(index_sql)
            except Exception as e:
                logging.warning(f"Failed to create index: {e}")

    def update_table_statistics(self):
        """Update database statistics for query optimization"""
        try:
            if self.db.engine.url.drivername == 'sqlite':
                self.db.session.execute("ANALYZE")
            elif self.db.engine.url.drivername == 'postgresql':
                self.db.session.execute("ANALYZE")
            # Add other database types as needed
        except Exception as e:
            logging.warning(f"Failed to update statistics: {e}")

    def cleanup_old_data(self, days_old=30):
        """Clean up data older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            # Delete old search results and their analyses
            old_results = SearchResult.query.filter(
                SearchResult.created_at < cutoff_date
            ).all()

            for result in old_results:
                self.db.session.delete(result)

            self.db.session.commit()
            logging.info(f"Cleaned up {len(old_results)} old records")

        except Exception as e:
            self.db.session.rollback()
            logging.error(f"Data cleanup failed: {e}")

    def vacuum_database(self):
        """Vacuum SQLite database to reduce file size"""
        try:
            if self.db.engine.url.drivername == 'sqlite':
                self.db.session.execute("VACUUM")
                logging.info("Database vacuum completed")
        except Exception as e:
            logging.warning(f"Database vacuum failed: {e}")

    def get_database_stats(self):
        """Get database statistics"""
        stats = {}

        try:
            # Table row counts
            stats['keywords_count'] = Keyword.query.count()
            stats['results_count'] = SearchResult.query.count()
            stats['analyses_count'] = WebsiteAnalysis.query.count()

            # Quality metrics
            stats['websites_with_analysis'] = SearchResult.query.filter(
                SearchResult.has_website == True
            ).join(WebsiteAnalysis).count()

            stats['average_website_score'] = self.db.session.query(
                func.avg(WebsiteAnalysis.score)
            ).scalar() or 0

            # Performance metrics
            stats['successful_scrapes'] = Keyword.query.filter_by(status='completed').count()
            stats['pending_scrapes'] = Keyword.query.filter_by(status='pending').count()

        except Exception as e:
            logging.error(f"Failed to get database stats: {e}")

        return stats