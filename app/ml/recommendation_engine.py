# app/ml/recommendation_engine.py
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class RecommendationEngine:
    def __init__(self):
        self.similarity_matrix = None
        self.business_features = None
        self.vectorizer = None

    def build_recommendation_model(self, businesses_data):
        """Build recommendation model based on business features"""
        try:
            # Prepare features for similarity calculation
            feature_vectors = self.prepare_feature_vectors(businesses_data)

            # Calculate similarity matrix
            self.similarity_matrix = cosine_similarity(feature_vectors)
            self.business_features = businesses_data

            logger.info("Recommendation model built successfully")

            return {
                'model_type': 'cosine_similarity',
                'businesses_count': len(businesses_data),
                'features_used': list(feature_vectors.columns) if hasattr(feature_vectors, 'columns') else [],
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to build recommendation model: {e}")
            raise

    def get_similar_businesses(self, business_id, top_n=5):
        """Get similar businesses based on various features"""
        try:
            if self.similarity_matrix is None:
                raise ValueError("Recommendation model not built")

            # Find business index
            business_indices = {b['id']: i for i, b in enumerate(self.business_features)}
            if business_id not in business_indices:
                raise ValueError(f"Business {business_id} not found in model")

            idx = business_indices[business_id]

            # Get similarity scores
            similarity_scores = list(enumerate(self.similarity_matrix[idx]))

            # Sort by similarity (descending) and exclude self
            similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)
            similarity_scores = [score for score in similarity_scores if score[0] != idx]

            # Get top N similar businesses
            similar_businesses = []
            for i, (similar_idx, score) in enumerate(similarity_scores[:top_n]):
                similar_business = self.business_features[similar_idx].copy()
                similar_business['similarity_score'] = float(score)
                similar_business['rank'] = i + 1
                similar_businesses.append(similar_business)

            return similar_businesses

        except Exception as e:
            logger.error(f"Failed to get similar businesses: {e}")
            return []

    def recommend_keywords(self, successful_keywords, top_n=10):
        """Recommend new keywords based on successful patterns"""
        try:
            # Analyze successful keyword patterns
            keyword_patterns = self.analyze_keyword_patterns(successful_keywords)

            # Generate recommendations
            recommendations = []
            for pattern in keyword_patterns[:top_n]:
                recommended_keywords = self.generate_keyword_variations(pattern)
                recommendations.extend(recommended_keywords)

            # Rank recommendations by potential
            ranked_recommendations = self.rank_keyword_recommendations(recommendations)

            return ranked_recommendations[:top_n]

        except Exception as e:
            logger.error(f"Keyword recommendation failed: {e}")
            return []

    def suggest_optimizations(self, website_analysis):
        """Suggest optimizations for website improvement"""
        try:
            optimizations = []

            # Mobile friendliness
            if not website_analysis.get('mobile_friendly', True):
                optimizations.append({
                    'category': 'mobile',
                    'priority': 'high',
                    'suggestion': 'Implement responsive design and viewport meta tag',
                    'impact': 'High impact on user experience and SEO',
                    'estimated_effort': 'Medium'
                })

            # Performance
            load_time = website_analysis.get('load_time', 0)
            if load_time > 3:
                optimizations.append({
                    'category': 'performance',
                    'priority': 'high' if load_time > 5 else 'medium',
                    'suggestion': 'Optimize images and implement caching',
                    'impact': f'Reduce load time from {load_time}s to under 3s',
                    'estimated_effort': 'Medium'
                })

            # SEO
            seo_score = website_analysis.get('seo_score', {}).get('seo_score', 0)
            if seo_score < 70:
                optimizations.append({
                    'category': 'seo',
                    'priority': 'medium',
                    'suggestion': 'Improve meta tags and heading structure',
                    'impact': 'Increase organic search visibility',
                    'estimated_effort': 'Low'
                })

            # Content
            word_count = website_analysis.get('word_count', 0)
            if word_count < 300:
                optimizations.append({
                    'category': 'content',
                    'priority': 'medium',
                    'suggestion': 'Add more descriptive content and service details',
                    'impact': 'Improve user engagement and SEO',
                    'estimated_effort': 'Medium'
                })

            # Sort by priority and impact
            priority_order = {'high': 3, 'medium': 2, 'low': 1}
            optimizations.sort(key=lambda x: priority_order.get(x['priority'], 0), reverse=True)

            return optimizations

        except Exception as e:
            logger.error(f"Optimization suggestion failed: {e}")
            return []

    # Helper methods
    def prepare_feature_vectors(self, businesses_data):
        """Prepare feature vectors for similarity calculation"""
        features = []

        for business in businesses_data:
            feature_vector = [
                business.get('stars', 0) or 0,
                np.log1p(business.get('reviews', 0) or 0),
                1 if business.get('has_website') else 0,
                1 if business.get('has_contact') else 0,
                1 if business.get('has_social') else 0,
                business.get('score', 0) or 0
            ]
            features.append(feature_vector)

        return np.array(features)

    def analyze_keyword_patterns(self, successful_keywords):
        """Analyze patterns in successful keywords"""
        patterns = []

        for keyword in successful_keywords:
            # Extract location patterns
            if ' in ' in keyword.lower():
                parts = keyword.lower().split(' in ')
                service = parts[0].strip()
                location = parts[1].strip()
                patterns.append({
                    'service': service,
                    'location': location,
                    'pattern': 'service_in_location'
                })

            # Extract service type patterns
            service_terms = ['restaurant', 'hotel', 'shop', 'store', 'clinic', 'service']
            for term in service_terms:
                if term in keyword.lower():
                    patterns.append({
                        'service_type': term,
                        'pattern': 'service_type'
                    })

        return patterns

    def generate_keyword_variations(self, pattern):
        """Generate keyword variations based on patterns"""
        variations = []

        if pattern['pattern'] == 'service_in_location':
            # Generate variations with different locations
            locations = ['new york', 'london', 'los angeles', 'chicago', 'miami']
            for location in locations:
                variations.append(f"{pattern['service']} in {location}")

        elif pattern['pattern'] == 'service_type':
            # Generate variations with different service types
            services = ['best', 'top', 'affordable', 'luxury']
            for service in services:
                variations.append(f"{service} {pattern['service_type']}")

        return variations

    def rank_keyword_recommendations(self, recommendations):
        """Rank keyword recommendations by potential"""
        ranked = []

        for keyword in recommendations:
            # Simple ranking based on keyword characteristics
            score = 0

            # Length score (shorter keywords often perform better)
            length_score = max(0, 1 - (len(keyword) / 100))
            score += length_score * 0.3

            # Specificity score (more specific keywords often have better intent)
            word_count = len(keyword.split())
            specificity_score = min(1.0, word_count / 5)
            score += specificity_score * 0.4

            # Location score (keywords with locations often perform well)
            location_score = 0.3 if any(
                loc in keyword.lower() for loc in ['new york', 'london', 'los angeles']) else 0.1
            score += location_score * 0.3

            ranked.append({
                'keyword': keyword,
                'score': score,
                'potential': 'high' if score > 0.7 else 'medium' if score > 0.4 else 'low'
            })

        ranked.sort(key=lambda x: x['score'], reverse=True)
        return ranked