# app/ml/predictive_analytics.py
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from datetime import datetime, timedelta
import logging
from app.models import SearchResult, Keyword, WebsiteAnalysis

logger = logging.getLogger(__name__)


class PredictiveAnalytics:
    def __init__(self):
        self.trend_models = {}

    def analyze_market_trends(self, keyword_data, days_back=90):
        """Analyze market trends for specific keywords"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)

            trends_analysis = {}

            for keyword in keyword_data:
                # Get historical data for this keyword
                historical_data = self.get_historical_keyword_data(keyword, start_date, end_date)

                if len(historical_data) < 7:  # Need at least 7 data points
                    continue

                # Analyze trends
                trend = self.calculate_trend(historical_data)
                seasonality = self.analyze_seasonality(historical_data)
                growth_rate = self.calculate_growth_rate(historical_data)

                trends_analysis[keyword] = {
                    'trend': trend,
                    'seasonality': seasonality,
                    'growth_rate': growth_rate,
                    'data_points': len(historical_data),
                    'confidence': self.calculate_confidence(historical_data)
                }

            return trends_analysis

        except Exception as e:
            logger.error(f"Market trend analysis failed: {e}")
            raise

    def predict_keyword_performance(self, keyword, historical_data, forecast_days=30):
        """Predict future performance for a keyword"""
        try:
            if len(historical_data) < 14:  # Need at least 2 weeks of data
                return None

            # Prepare time series data
            dates = [d['date'] for d in historical_data]
            values = [d['value'] for d in historical_data]

            # Create features for prediction
            X = np.arange(len(dates)).reshape(-1, 1)
            y = np.array(values)

            # Train linear regression model
            model = LinearRegression()
            model.fit(X, y)

            # Make predictions
            future_dates = np.arange(len(dates), len(dates) + forecast_days).reshape(-1, 1)
            predictions = model.predict(future_dates)

            # Calculate prediction intervals
            residuals = y - model.predict(X)
            std_residuals = np.std(residuals)
            prediction_intervals = {
                'lower': predictions - 1.96 * std_residuals,
                'upper': predictions + 1.96 * std_residuals
            }

            forecast = {
                'keyword': keyword,
                'forecast_days': forecast_days,
                'predictions': predictions.tolist(),
                'prediction_intervals': prediction_intervals,
                'model_accuracy': r2_score(y, model.predict(X)),
                'trend_slope': float(model.coef_[0]),
                'last_updated': datetime.utcnow().isoformat()
            }

            return forecast

        except Exception as e:
            logger.error(f"Keyword performance prediction failed: {e}")
            return None

    def identify_emerging_markets(self, keyword_data, min_growth_rate=0.1):
        """Identify emerging markets based on growth patterns"""
        try:
            emerging_markets = []

            for keyword, data in keyword_data.items():
                if data['growth_rate'] >= min_growth_rate and data['confidence'] > 0.7:
                    market_potential = self.assess_market_potential(keyword, data)

                    emerging_markets.append({
                        'keyword': keyword,
                        'growth_rate': data['growth_rate'],
                        'market_potential': market_potential,
                        'competition_level': self.assess_competition(keyword),
                        'recommendation_score': self.calculate_recommendation_score(data, market_potential)
                    })

            # Sort by recommendation score
            emerging_markets.sort(key=lambda x: x['recommendation_score'], reverse=True)

            return emerging_markets[:10]  # Return top 10

        except Exception as e:
            logger.error(f"Emerging markets identification failed: {e}")
            raise

    def optimize_scraping_schedule(self, historical_performance):
        """Optimize scraping schedule based on historical performance"""
        try:
            # Analyze performance patterns
            performance_by_hour = self.analyze_performance_by_hour(historical_performance)
            performance_by_day = self.analyze_performance_by_day(historical_performance)

            # Find optimal times
            optimal_hours = self.find_optimal_hours(performance_by_hour)
            optimal_days = self.find_optimal_days(performance_by_day)

            # Generate schedule recommendations
            schedule = {
                'optimal_hours': optimal_hours,
                'optimal_days': optimal_days,
                'high_priority_windows': self.identify_high_priority_windows(performance_by_hour, performance_by_day),
                'low_priority_windows': self.identify_low_priority_windows(performance_by_hour, performance_by_day),
                'estimated_efficiency_gain': self.calculate_efficiency_gain(performance_by_hour, performance_by_day)
            }

            return schedule

        except Exception as e:
            logger.error(f"Scraping schedule optimization failed: {e}")
            raise

    # Helper methods
    def get_historical_keyword_data(self, keyword, start_date, end_date):
        """Get historical data for a keyword"""
        # This would query the database for historical keyword performance
        # For now, return mock data structure
        return [
            {'date': datetime.utcnow() - timedelta(days=i), 'value': np.random.normal(100, 20)}
            for i in range(90, 0, -1)
        ]

    def calculate_trend(self, data):
        """Calculate trend from time series data"""
        if len(data) < 2:
            return 0

        dates = [d['date'] for d in data]
        values = [d['value'] for d in data]

        # Convert dates to numerical values
        date_nums = [(d - min(dates)).days for d in dates]

        # Calculate linear trend
        trend_coef = np.polyfit(date_nums, values, 1)[0]
        return float(trend_coef)

    def analyze_seasonality(self, data):
        """Analyze seasonal patterns in data"""
        if len(data) < 30:
            return {'detected': False, 'strength': 0}

        # Simple seasonality analysis (weekly patterns)
        day_of_week_avg = {}
        for entry in data:
            day = entry['date'].weekday()
            day_of_week_avg[day] = day_of_week_avg.get(day, []) + [entry['value']]

        # Calculate variation by day of week
        if day_of_week_avg:
            day_means = [np.mean(day_of_week_avg[day]) for day in range(7) if day in day_of_week_avg]
            variation = np.std(day_means) / np.mean(day_means) if np.mean(day_means) > 0 else 0

            return {
                'detected': variation > 0.1,
                'strength': float(variation),
                'peak_days': self.identify_peak_days(day_of_week_avg)
            }

        return {'detected': False, 'strength': 0}

    def calculate_growth_rate(self, data):
        """Calculate growth rate from time series data"""
        if len(data) < 7:
            return 0

        # Use first and last week for growth calculation
        first_week_avg = np.mean([d['value'] for d in data[:7]])
        last_week_avg = np.mean([d['value'] for d in data[-7:]])

        if first_week_avg > 0:
            return (last_week_avg - first_week_avg) / first_week_avg
        return 0

    def calculate_confidence(self, data):
        """Calculate confidence score for predictions"""
        if len(data) < 7:
            return 0

        # Factors affecting confidence:
        # 1. Data quantity
        quantity_score = min(1.0, len(data) / 30)

        # 2. Data consistency (lower variance = higher confidence)
        values = [d['value'] for d in data]
        if np.mean(values) > 0:
            consistency_score = 1.0 - (np.std(values) / np.mean(values))
        else:
            consistency_score = 0.5

        # 3. Trend strength
        trend_strength = abs(self.calculate_trend(data)) / 10  # Normalize

        return float((quantity_score + consistency_score + min(1.0, trend_strength)) / 3)