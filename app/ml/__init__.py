# app/ml/__init__.py
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class BusinessIntelligenceML:
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.vectorizers = {}
        self.model_path = 'ml_models/'

    def train_website_quality_predictor(self, training_data):
        """Train ML model to predict website quality scores"""
        try:
            # Prepare features
            features = [
                'mobile_friendly', 'load_time', 'professional_look',
                'word_count', 'image_count', 'internal_links', 'external_links'
            ]

            X = training_data[features].fillna(0)
            y = training_data['score']

            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # Train model
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            model.fit(X_scaled, y)

            # Save model and scaler
            self.models['website_quality'] = model
            self.scalers['website_quality'] = scaler

            # Calculate feature importance
            feature_importance = dict(zip(features, model.feature_importances_))

            logger.info("Website quality predictor trained successfully")

            return {
                'model': 'website_quality_predictor',
                'accuracy': model.score(X_scaled, y),
                'feature_importance': feature_importance,
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to train website quality predictor: {e}")
            raise

    def predict_website_quality(self, features):
        """Predict website quality score using ML model"""
        try:
            if 'website_quality' not in self.models:
                raise ValueError("Website quality model not trained")

            model = self.models['website_quality']
            scaler = self.scalers['website_quality']

            # Prepare and scale features
            feature_vector = np.array([features.get(f, 0) for f in [
                'mobile_friendly', 'load_time', 'professional_look',
                'word_count', 'image_count', 'internal_links', 'external_links'
            ]]).reshape(1, -1)

            scaled_features = scaler.transform(feature_vector)
            prediction = model.predict(scaled_features)[0]

            return max(0, min(100, prediction))

        except Exception as e:
            logger.error(f"Website quality prediction failed: {e}")
            return None

    def train_business_category_classifier(self, training_data):
        """Train ML model to classify business categories"""
        try:
            # Prepare text data
            business_names = training_data['title'].fillna('')
            categories = training_data['category']

            # Create TF-IDF features
            vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            X = vectorizer.fit_transform(business_names)

            # Train classifier
            model = RandomForestClassifier(
                n_estimators=50,
                random_state=42
            )
            model.fit(X, categories)

            # Save model and vectorizer
            self.models['business_category'] = model
            self.vectorizers['business_category'] = vectorizer

            logger.info("Business category classifier trained successfully")

            return {
                'model': 'business_category_classifier',
                'accuracy': model.score(X, categories),
                'categories': list(model.classes_),
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to train business category classifier: {e}")
            raise

    def predict_business_category(self, business_name):
        """Predict business category using ML"""
        try:
            if 'business_category' not in self.models:
                raise ValueError("Business category model not trained")

            model = self.models['business_category']
            vectorizer = self.vectorizers['business_category']

            # Transform business name
            features = vectorizer.transform([business_name])
            prediction = model.predict(features)[0]
            probability = np.max(model.predict_proba(features))

            return {
                'category': prediction,
                'confidence': float(probability),
                'business_name': business_name
            }

        except Exception as e:
            logger.error(f"Business category prediction failed: {e}")
            return {'category': 'Unknown', 'confidence': 0.0}

    def cluster_businesses(self, businesses_data, n_clusters=5):
        """Cluster businesses based on various features"""
        try:
            # Prepare features for clustering
            features = [
                'stars', 'reviews', 'has_website', 'has_contact', 'has_social'
            ]

            X = businesses_data[features].fillna(0)

            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # Perform clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            clusters = kmeans.fit_predict(X_scaled)

            # Analyze clusters
            businesses_data['cluster'] = clusters
            cluster_analysis = businesses_data.groupby('cluster').agg({
                'stars': 'mean',
                'reviews': 'mean',
                'has_website': 'mean',
                'has_contact': 'mean',
                'has_social': 'mean'
            }).round(3)

            logger.info(f"Business clustering completed: {n_clusters} clusters")

            return {
                'clusters': clusters.tolist(),
                'cluster_centers': kmeans.cluster_centers_.tolist(),
                'cluster_analysis': cluster_analysis.to_dict(),
                'businesses_per_cluster': np.bincount(clusters).tolist()
            }

        except Exception as e:
            logger.error(f"Business clustering failed: {e}")
            raise

    def detect_anomalies(self, data, method='isolation_forest'):
        """Detect anomalies in business data"""
        try:
            from sklearn.ensemble import IsolationForest

            # Prepare features
            features = ['stars', 'reviews', 'load_time', 'score']
            X = data[features].fillna(0)

            if method == 'isolation_forest':
                model = IsolationForest(contamination=0.1, random_state=42)
                anomalies = model.fit_predict(X)

                # Convert to boolean (1 = normal, -1 = anomaly)
                is_anomaly = (anomalies == -1)

                anomaly_analysis = {
                    'total_anomalies': sum(is_anomaly),
                    'anomaly_percentage': (sum(is_anomaly) / len(data)) * 100,
                    'anomaly_indices': np.where(is_anomaly)[0].tolist(),
                    'method': 'isolation_forest'
                }

                return anomaly_analysis

            else:
                raise ValueError(f"Unsupported anomaly detection method: {method}")

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            raise

    def save_models(self):
        """Save trained models to disk"""
        try:
            import os
            os.makedirs(self.model_path, exist_ok=True)

            for model_name, model in self.models.items():
                joblib.dump(model, f"{self.model_path}/{model_name}.pkl")

            for scaler_name, scaler in self.scalers.items():
                joblib.dump(scaler, f"{self.model_path}/{scaler_name}_scaler.pkl")

            for vec_name, vectorizer in self.vectorizers.items():
                joblib.dump(vectorizer, f"{self.model_path}/{vec_name}_vectorizer.pkl")

            logger.info("ML models saved successfully")

        except Exception as e:
            logger.error(f"Failed to save ML models: {e}")

    def load_models(self):
        """Load trained models from disk"""
        try:
            import os
            if not os.path.exists(self.model_path):
                logger.warning("Model directory does not exist")
                return False

            for file in os.listdir(self.model_path):
                if file.endswith('.pkl'):
                    model_name = file.replace('.pkl', '')

                    if 'scaler' in file:
                        self.scalers[model_name.replace('_scaler', '')] = joblib.load(f"{self.model_path}/{file}")
                    elif 'vectorizer' in file:
                        self.vectorizers[model_name.replace('_vectorizer', '')] = joblib.load(
                            f"{self.model_path}/{file}")
                    else:
                        self.models[model_name] = joblib.load(f"{self.model_path}/{file}")

            logger.info("ML models loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load ML models: {e}")
            return False