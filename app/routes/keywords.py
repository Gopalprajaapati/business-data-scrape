from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app.models import Keyword, SearchResult, db

bp = Blueprint('keywords', __name__)

@bp.route('/keywords')
def keywords():
    keywords = Keyword.query.order_by(Keyword.id.desc()).all()
    return render_template('keywords.html', keywords=keywords)

@bp.route('/keywords/<int:keyword_id>')
def keyword_results(keyword_id):
    keyword = Keyword.query.get_or_404(keyword_id)
    results = SearchResult.query.filter_by(keyword_id=keyword_id).all()
    return render_template('results.html', keyword=keyword, results=results)

@bp.route('/api/keywords', methods=['POST'])
def create_keyword():
    data = request.get_json()
    if not data or 'keyword' not in data:
        return jsonify({'error': 'Keyword is required'}), 400
    
    keyword = Keyword(keyword=data['keyword'])
    db.session.add(keyword)
    db.session.commit()
    
    return jsonify({
        'id': keyword.id,
        'keyword': keyword.keyword,
        'status': keyword.status
    }), 201
