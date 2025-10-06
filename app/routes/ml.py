# app/routes/ml.py
from flask import Blueprint, jsonify, request
from app.ml import BusinessIntelligenceML, PredictiveAnalytics, RecommendationEngine
from app.models import Keyword, SearchResult, WebsiteAnalysis, db
import logging

bp = Blueprint('ml', __name__, url_prefix='/api/v1/ml')

# Initialize ML services
ml_engine = BusinessIntelligenceML()
predictive_analytics = PredictiveAnalytics()
recommendation_engine = RecommendationEngine()


@bp.route('/train/website-quality', methods=['POST'])
def train_website_quality_model():
    """Train website quality prediction model"""
    try:
        # Get training data from database
        training_data = get_website_quality_training_data()

        # Train model
        result = ml_engine.train_website_quality_predictor(training_data)

        # Save model
        ml_engine.save_models()

        return jsonify({
            'success': True,
            'model': 'website_quality_predictor',
            'results': result
        })

    except Exception as e:
        logging.error(f"Website quality model training failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/predict/website-quality', methods=['POST'])
def predict_website_quality():
    """Predict website quality using ML model"""
    try:
        data = request.get_json()
        features = data.get('features', {})

        prediction = ml_engine.predict_website_quality(features)

        return jsonify({
            'success': True,
            'prediction': prediction,
            'features_used': list(features.keys())
        })

    except Exception as e:
        logging.error(f"Website quality prediction failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/analyze/market-trends', methods=['POST'])
def analyze_market_trends():
    """Analyze market trends using predictive analytics"""
    try:
        data = request.get_json()
        keywords = data.get('keywords', [])
        days_back = data.get('days_back', 90)

        trends = predictive_analytics.analyze_market_trends(keywords, days_back)

        return jsonify({
            'success': True,
            'analysis_period_days': days_back,
            'trends_analyzed': len(trends),
            'market_trends': trends
        })

    except Exception as e:
        logging.error(f"Market trend analysis failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/recommend/similar-businesses', methods=['POST'])
def recommend_similar_businesses():
    """Get similar business recommendations"""
    try:
        data = request.get_json()
        business_id = data.get('business_id')
        top_n = data.get('top_n', 5)

        # Get business data for recommendation model
        businesses_data = get_businesses_for_recommendation()
        recommendation_engine.build_recommendation_model(businesses_data)

        similar_businesses = recommendation_engine.get_similar_businesses(business_id, top_n)

        return jsonify({
            'success': True,
            'base_business_id': business_id,
            'similar_businesses_count': len(similar_businesses),
            'similar_businesses': similar_businesses
        })

    except Exception as e:
        logging.error(f"Similar business recommendation failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/recommend/keywords', methods=['POST'])
def recommend_keywords():
    """Get keyword recommendations based on successful patterns"""
    try:
        data = request.get_json()
        successful_keywords = data.get('successful_keywords', [])
        top_n = data.get('top_n', 10)

        recommendations = recommendation_engine.recommend_keywords(successful_keywords, top_n)

        return jsonify({
            'success': True,
            'recommendations_count': len(recommendations),
            'recommendations': recommendations
        })

    except Exception as e:
        logging.error(f"Keyword recommendation failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/optimize/suggestions', methods=['POST'])
def get_optimization_suggestions():
    """Get website optimization suggestions"""
    try:
        data = request.get_json()
        website_analysis = data.get('website_analysis', {})

        suggestions = recommendation_engine.suggest_optimizations(website_analysis)

        return jsonify({
            'success': True,
            'suggestions_count': len(suggestions),
            'optimization_suggestions': suggestions
        })

    except Exception as e:
        logging.error(f"Optimization suggestions failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/clustering/businesses', methods=['POST'])
def cluster_businesses():
    """Cluster businesses based on features"""
    try:
        data = request.get_json()
        businesses_data = data.get('businesses_data', [])
        n_clusters = data.get('n_clusters', 5)

        clustering_result = ml_engine.cluster_businesses(businesses_data, n_clusters)

        return jsonify({
            'success': True,
            'clusters_created': n_clusters,
            'clustering_result': clustering_result
        })

    except Exception as e:
        logging.error(f"Business clustering failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/anomalies/detect', methods=['POST'])
def detect_anomalies():
    """Detect anomalies in business data"""
    try:
        data = request.get_json()
        business_data = data.get('business_data', [])
        method = data.get('method', 'isolation_forest')

        anomalies = ml_engine.detect_anomalies(business_data, method)

        return jsonify({
            'success': True,
            'anomalies_detected': anomalies['total_anomalies'],
            'anomaly_analysis': anomalies
        })

    except Exception as e:
        logging.error(f"Anomaly detection failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Helper functions
def get_website_quality_training_data():
    """Get training data for website quality prediction"""
    # This would query the database for historical website analysis data
    # For now, return mock data structure
    return pd.DataFrame({
        'mobile_friendly': [1, 0, 1, 1, 0],
        'load_time': [2.1, 5.3, 1.8, 3.2, 6.1],
        'professional_look': [1, 0, 1, 1, 0],
        'word_count': [450, 120, 680, 320, 90],
        'image_count': [12, 5, 18, 8, 3],
        'internal_links': [15, 3, 22, 9, 2],
        'external_links': [8, 1, 12, 5, 0],
        'score': [85, 35, 92, 68, 28]
    })


def get_businesses_for_recommendation():
    """Get business data for recommendation engine"""
    # This would query the database for business data
    # For now, return mock data structure
    return [
        {
            'id': 1,
            'title': 'Test Restaurant',
            'stars': 4.5,
            'reviews': 150,
            'has_website': True,
            'has_contact': True,
            'has_social': True,
            'score': 85
        },
        # ... more businesses
    ]