from app import db
from datetime import datetime

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, error
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    results = db.relationship('SearchResult', backref='keyword', lazy='dynamic')

class SearchResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword_id = db.Column(db.Integer, db.ForeignKey('keyword.id'), nullable=False)
    title = db.Column(db.String(500))
    website = db.Column(db.String(500))
    phone = db.Column(db.String(50))
    stars = db.Column(db.Float)
    reviews = db.Column(db.Integer)
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)

class WebsiteAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.Integer, db.ForeignKey('search_result.id'), nullable=False)
    score = db.Column(db.Integer)
    mobile_friendly = db.Column(db.Boolean)
    load_time = db.Column(db.Float)
    professional_look = db.Column(db.Boolean)
    issues = db.Column(db.Text)
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    result = db.relationship('SearchResult', backref='analysis')
