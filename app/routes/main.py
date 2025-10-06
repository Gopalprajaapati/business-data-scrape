from flask import Blueprint, render_template, request, flash, redirect, url_for
import os
from werkzeug.utils import secure_filename
import pandas as pd
from app.models import Keyword, SearchResult, db
import threading
import time

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    keywords = Keyword.query.order_by(Keyword.id.desc()).limit(5).all()
    return render_template('index.html', keywords=keywords)

@bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('main.index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('main.index'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join('uploads', filename)
        file.save(filepath)
        
        try:
            # Process Excel/CSV file
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
            
            keywords = df.iloc[:, 0].dropna().unique().tolist()
            added = 0
            
            for keyword in keywords:
                if keyword and not Keyword.query.filter_by(keyword=keyword).first():
                    db.session.add(Keyword(keyword=keyword))
                    added += 1
            
            db.session.commit()
            flash(f'{added} new keywords imported successfully!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing file: {str(e)}', 'error')
        
        return redirect(url_for('main.index'))
    
    flash('Invalid file type', 'error')
    return redirect(url_for('main.index'))

@bp.route('/scrape/<int:keyword_id>', methods=['POST'])
def scrape_keyword(keyword_id):
    keyword = Keyword.query.get_or_404(keyword_id)
    
    # Update status
    keyword.status = 'in_progress'
    db.session.commit()
    
    # Start scraping in background thread
    thread = threading.Thread(target=run_scraper, args=(keyword_id,))
    thread.start()
    
    flash(f'Scraping started for "{keyword.keyword}"', 'info')
    return redirect(url_for('main.index'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['xlsx', 'xls', 'csv']

def run_scraper(keyword_id):
    # Simple mock scraper for demo
    with app.app_context():
        keyword = Keyword.query.get(keyword_id)
        
        # Simulate scraping process
        time.sleep(5)
        
        # Add mock results
        results = [
            {'title': f'Test Business 1 for {keyword.keyword}', 'website': 'https://example1.com', 'phone': '+1234567890', 'stars': 4.5, 'reviews': 100},
            {'title': f'Test Business 2 for {keyword.keyword}', 'website': 'https://example2.com', 'phone': '+1234567891', 'stars': 4.2, 'reviews': 50},
        ]
        
        for result_data in results:
            result = SearchResult(
                keyword_id=keyword_id,
                title=result_data['title'],
                website=result_data['website'],
                phone=result_data['phone'],
                stars=result_data['stars'],
                reviews=result_data['reviews']
            )
            db.session.add(result)
        
        # Update keyword status
        keyword.status = 'completed'
        keyword.completed_at = db.func.now()
        db.session.commit()

# Create app instance for background tasks
from app import create_app
app = create_app()
