# app/ml/model_manager.py
import json
import pandas as pd
from datetime import datetime, timedelta
import logging
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# ML Metrics
ML_PREDICTION_COUNT = Counter('ml_predictions_total', 'Total ML Predictions', ['model_type', 'status'])
ML_PREDICTION_DURATION = Histogram('ml_prediction_duration_seconds', 'ML Prediction Duration')
ML_MODEL_ACCURACY = Gauge('ml_model_accuracy', 'ML Model Accuracy', ['model_type'])
ML_MODEL_DRIFT = Gauge('ml_model_drift', 'ML Model Drift Detection', ['model_type'])


class MLModelManager:
    def __init__(self):
        self.model_versions = {}
        self.performance_history = {}
        self.drift_detectors = {}

    def register_model(self, model_name, model_version, performance_metrics):
        """Register a new model version"""
        model_key = f"{model_name}_{model_version}"

        self.model_versions[model_key] = {
            'model_name': model_name,
            'version': model_version,
            'performance_metrics': performance_metrics,
            'registered_at': datetime.utcnow().isoformat(),
            'status': 'active'
        }

        # Initialize performance history
        if model_name not in self.performance_history:
            self.performance_history[model_name] = []

        self.performance_history[model_name].append({
            'timestamp': datetime.utcnow().isoformat(),
            'version': model_version,
            'metrics': performance_metrics
        })

        logger.info(f"Registered model: {model_key}")

    def monitor_model_performance(self, model_name, actual_values, predictions):
        """Monitor model performance and detect drift"""
        try:
            # Calculate current performance
            from sklearn.metrics import accuracy_score, mean_squared_error

            if model_name.startswith('classifier'):
                current_accuracy = accuracy_score(actual_values, predictions)
                ML_MODEL_ACCURACY.labels(model_type=model_name).set(current_accuracy)
            else:
                current_mse = mean_squared_error(actual_values, predictions)
                ML_MODEL_ACCURACY.labels(model_type=model_name).set(1.0 / (1.0 + current_mse))

            # Check for model drift
            drift_detected = self.check_model_drift(model_name, current_accuracy)

            if drift_detected:
                ML_MODEL_DRIFT.labels(model_type=model_name).set(1)
                logger.warning(f"Model drift detected for {model_name}")

                # Trigger retraining if significant drift
                if self.should_retrain_model(model_name):
                    self.trigger_model_retraining(model_name)
            else:
                ML_MODEL_DRIFT.labels(model_type=model_name).set(0)

            return {
                'model_name': model_name,
                'current_performance': current_accuracy,
                'drift_detected': drift_detected,
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Model performance monitoring failed for {model_name}: {e}")
            return None

    def check_model_drift(self, model_name, current_performance):
        """Check for model performance drift"""
        if model_name not in self.performance_history:
            return False

        # Get historical performance
        history = self.performance_history[model_name]
        if len(history) < 5:  # Need sufficient history
            return False

        # Calculate performance degradation
        recent_performance = [h['metrics'].get('accuracy', 0) for h in history[-5:]]
        avg_recent_performance = sum(recent_performance) / len(recent_performance)

        performance_drop = avg_recent_performance - current_performance

        # Significant drop indicates potential drift
        return performance_drop > 0.1  # 10% performance drop

    def should_retrain_model(self, model_name):
        """Determine if model should be retrained"""
        drift_count = sum(1 for record in self.performance_history.get(model_name, [])
                          if record.get('drift_detected', False))

        # Retrain if drift detected in 3 consecutive checks
        return drift_count >= 3

    def trigger_model_retraining(self, model_name):
        """Trigger model retraining process"""
        try:
            logger.info(f"Triggering retraining for model: {model_name}")

            # This would typically queue a retraining task
            # For now, just log the event
            retraining_event = {
                'model_name': model_name,
                'triggered_at': datetime.utcnow().isoformat(),
                'reason': 'performance_drift',
                'status': 'queued'
            }

            # Store retraining event
            if 'retraining_events' not in self.performance_history:
                self.performance_history['retraining_events'] = []

            self.performance_history['retraining_events'].append(retraining_event)

            return retraining_event

        except Exception as e:
            logger.error(f"Failed to trigger model retraining for {model_name}: {e}")
            return None

    def get_model_statistics(self):
        """Get overall model statistics"""
        stats = {
            'total_models': len(self.model_versions),
            'active_models': sum(1 for m in self.model_versions.values() if m['status'] == 'active'),
            'models_by_type': {},
            'performance_summary': {}
        }

        # Count models by type
        for model_key, model_info in self.model_versions.items():
            model_type = model_info['model_name']
            stats['models_by_type'][model_type] = stats['models_by_type'].get(model_type, 0) + 1

        # Calculate performance summary
        for model_name in self.performance_history:
            if model_name != 'retraining_events':
                performances = [h['metrics'].get('accuracy', 0) for h in self.performance_history[model_name]]
                if performances:
                    stats['performance_summary'][model_name] = {
                        'average_accuracy': sum(performances) / len(performances),
                        'min_accuracy': min(performances),
                        'max_accuracy': max(performances),
                        'data_points': len(performances)
                    }

        return stats

    def export_model_report(self):
        """Export comprehensive model performance report"""
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'model_statistics': self.get_model_statistics(),
            'model_versions': self.model_versions,
            'performance_history': self.performance_history,
            'recommendations': self.generate_recommendations()
        }

        return report

    def generate_recommendations(self):
        """Generate recommendations based on model performance"""
        recommendations = []

        for model_name, history in self.performance_history.items():
            if model_name == 'retraining_events':
                continue

            # Check if model needs retraining
            drift_count = sum(1 for record in history if record.get('drift_detected', False))
            if drift_count >= 2:
                recommendations.append({
                    'model': model_name,
                    'priority': 'high',
                    'action': 'retrain',
                    'reason': f'Model drift detected {drift_count} times',
                    'estimated_impact': 'High - model performance degradation'
                })

            # Check for data quality issues
            recent_performance = [h['metrics'].get('accuracy', 0) for h in history[-3:]]
            if len(recent_performance) == 3 and max(recent_performance) - min(recent_performance) > 0.2:
                recommendations.append({
                    'model': model_name,
                    'priority': 'medium',
                    'action': 'investigate_data_quality',
                    'reason': 'High performance variance in recent evaluations',
                    'estimated_impact': 'Medium - potential data quality issues'
                })

        return recommendations