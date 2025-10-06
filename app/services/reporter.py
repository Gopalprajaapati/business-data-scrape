# app/services/reporter.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
import logging
from datetime import datetime, timedelta
from flask import render_template
import pdfkit
from app.models import SearchResult, Keyword, WebsiteAnalysis

logger = logging.getLogger(__name__)


class BusinessIntelligenceReporter:
    def __init__(self):
        self.sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (12, 8)

    def generate_comprehensive_report(self, keyword_id, report_type='executive'):
        """Generate comprehensive business intelligence report"""
        keyword = Keyword.query.get(keyword_id)
        if not keyword:
            return None

        results = SearchResult.query.filter_by(keyword_id=keyword_id).all()
        analyses = WebsiteAnalysis.query.join(SearchResult).filter(
            SearchResult.keyword_id == keyword_id
        ).all()

        report_data = {
            'executive_summary': self.generate_executive_summary(keyword, results, analyses),
            'market_analysis': self.analyze_market_landscape(results),
            'competitor_benchmarking': self.benchmark_competitors(results, analyses),
            'opportunity_analysis': self.identify_opportunities(results, analyses),
            'recommendations': self.generate_strategic_recommendations(results, analyses),
            'visualizations': self.create_report_visualizations(results, analyses)
        }

        if report_type == 'pdf':
            return self.generate_pdf_report(report_data, keyword)
        elif report_type == 'excel':
            return self.generate_excel_report(report_data, keyword)
        else:
            return report_data

    def generate_executive_summary(self, keyword, results, analyses):
        """Generate executive summary with key insights"""
        total_businesses = len(results)
        businesses_with_websites = len([r for r in results if r.website])
        analyzed_websites = len(analyses)

        # Calculate average metrics
        avg_rating = self.calculate_average_rating(results)
        avg_website_score = self.calculate_average_website_score(analyses)

        # Market segmentation
        market_segments = self.analyze_market_segments(results)

        # Competitive landscape
        competitive_intensity = self.assess_competitive_intensity(results, analyses)

        summary = {
            'keyword': keyword.keyword,
            'total_businesses_analyzed': total_businesses,
            'businesses_with_websites': businesses_with_websites,
            'websites_analyzed': analyzed_websites,
            'market_coverage_percentage': (
                        businesses_with_websites / total_businesses * 100) if total_businesses else 0,
            'average_customer_rating': avg_rating,
            'average_website_quality': avg_website_score,
            'market_segments': market_segments,
            'competitive_intensity': competitive_intensity,
            'key_findings': self.extract_key_findings(results, analyses),
            'market_gaps': self.identify_market_gaps(results)
        }

        return summary

    def analyze_market_landscape(self, results):
        """Deep market landscape analysis"""
        market_data = {
            'size_distribution': self.analyze_business_size_distribution(results),
            'geographic_distribution': self.analyze_geographic_distribution(results),
            'price_range_analysis': self.analyze_price_ranges(results),
            'service_categories': self.categorize_services(results),
            'customer_sentiment': self.analyze_customer_sentiment(results),
            'market_trends': self.identify_market_trends(results)
        }

        return market_data

    def benchmark_competitors(self, results, analyses):
        """Comprehensive competitor benchmarking"""
        competitors_data = []

        for result in results:
            if not result.website:
                continue

            analysis = next((a for a in analyses if a.result_id == result.id), None)
            if not analysis:
                continue

            competitor_profile = {
                'business_name': result.title,
                'website': result.website,
                'overall_score': analysis.score,
                'seo_score': getattr(analysis, 'seo_score', 0),
                'performance_score': getattr(analysis, 'performance_score', 0),
                'security_score': getattr(analysis, 'security_score', 0),
                'credibility_score': getattr(analysis, 'credibility_score', 0),
                'customer_rating': result.stars or 0,
                'review_count': result.reviews or 0,
                'social_media_presence': self.assess_social_media_presence(result),
                'competitive_advantages': self.identify_competitive_advantages(analysis),
                'weaknesses': self.identify_competitor_weaknesses(analysis),
                'threat_level': self.assess_competitive_threat(result, analysis)
            }

            competitors_data.append(competitor_profile)

        # Sort by threat level and score
        competitors_data.sort(key=lambda x: (x['threat_level'], x['overall_score']), reverse=True)

        return {
            'top_competitors': competitors_data[:10],
            'competitive_gaps': self.analyze_competitive_gaps(competitors_data),
            'market_leadership': self.identify_market_leaders(competitors_data)
        }

    def identify_opportunities(self, results, analyses):
        """Identify market opportunities and gaps"""
        opportunities = {
            'underserved_markets': self.find_underserved_markets(results),
            'technology_gaps': self.identify_technology_gaps(analyses),
            'service_gaps': self.identify_service_gaps(results),
            'pricing_opportunities': self.analyze_pricing_opportunities(results),
            'geographic_opportunities': self.identify_geographic_opportunities(results),
            'digital_presence_opportunities': self.analyze_digital_presence_gaps(analyses)
        }

        # Prioritize opportunities
        prioritized_opportunities = self.prioritize_opportunities(opportunities)

        return {
            'opportunities': opportunities,
            'prioritized_list': prioritized_opportunities,
            'implementation_roadmap': self.create_implementation_roadmap(prioritized_opportunities)
        }

    def generate_strategic_recommendations(self, results, analyses):
        """Generate data-driven strategic recommendations"""
        recommendations = {
            'immediate_actions': self.generate_immediate_actions(results, analyses),
            'short_term_strategies': self.generate_short_term_strategies(results, analyses),
            'long_term_initiatives': self.generate_long_term_initiatives(results, analyses),
            'competitive_positioning': self.recommend_competitive_positioning(results, analyses),
            'digital_transformation': self.recommend_digital_transformation(analyses),
            'market_expansion': self.recommend_market_expansion(results)
        }

        return recommendations

    def create_report_visualizations(self, results, analyses):
        """Create comprehensive data visualizations"""
        visualizations = {}

        try:
            # Market share pie chart
            visualizations['market_share'] = self.create_market_share_chart(results)

            # Website quality distribution
            visualizations['quality_distribution'] = self.create_quality_distribution_chart(analyses)

            # Competitive positioning matrix
            visualizations['competitive_matrix'] = self.create_competitive_matrix(results, analyses)

            # Trend analysis
            visualizations['trend_analysis'] = self.create_trend_analysis_chart(results)

            # SWOT analysis visualization
            visualizations['swot_analysis'] = self.create_swot_visualization(results, analyses)

        except Exception as e:
            logger.error(f"Visualization creation failed: {e}")

        return visualizations

    # Advanced analytical methods
    def analyze_business_size_distribution(self, results):
        """Analyze business size distribution using proxy indicators"""
        size_categories = {'small': 0, 'medium': 0, 'large': 0}

        for result in results:
            # Use review count as proxy for business size
            review_count = result.reviews or 0

            if review_count < 50:
                size_categories['small'] += 1
            elif review_count < 200:
                size_categories['medium'] += 1
            else:
                size_categories['large'] += 1

        return size_categories

    def assess_competitive_intensity(self, results, analyses):
        """Assess competitive intensity in the market"""
        intensity_score = 0
        factors = []

        # Factor 1: Number of competitors
        total_competitors = len(results)
        if total_competitors > 50:
            intensity_score += 30
            factors.append("High number of competitors")
        elif total_competitors > 20:
            intensity_score += 20
            factors.append("Moderate number of competitors")
        else:
            intensity_score += 10
            factors.append("Low number of competitors")

        # Factor 2: Quality of competition
        high_quality_competitors = len([a for a in analyses if a.score >= 70])
        if high_quality_competitors > 10:
            intensity_score += 40
            factors.append("Many high-quality competitors")
        elif high_quality_competitors > 5:
            intensity_score += 25
            factors.append("Several high-quality competitors")
        else:
            intensity_score += 15
            factors.append("Few high-quality competitors")

        # Factor 3: Market concentration
        top_5_review_count = sum(sorted([r.reviews or 0 for r in results], reverse=True)[:5])
        total_review_count = sum(r.reviews or 0 for r in results)

        if total_review_count > 0:
            concentration_ratio = top_5_review_count / total_review_count
            if concentration_ratio > 0.7:
                intensity_score += 30
                factors.append("High market concentration")
            elif concentration_ratio > 0.4:
                intensity_score += 20
                factors.append("Moderate market concentration")
            else:
                intensity_score += 10
                factors.append("Fragmented market")

        return {
            'intensity_score': min(100, intensity_score),
            'intensity_level': self.get_intensity_level(intensity_score),
            'factors': factors
        }

    def identify_market_gaps(self, results):
        """Identify gaps in the current market"""
        gaps = []

        # Analyze service categories
        categories = self.categorize_services(results)
        underrepresented = [cat for cat, count in categories.items() if count < len(results) * 0.1]

        if underrepresented:
            gaps.append(f"Underrepresented services: {', '.join(underrepresented)}")

        # Analyze geographic coverage
        geographic_data = self.analyze_geographic_distribution(results)
        if len(geographic_data) < 3:
            gaps.append("Limited geographic coverage in the market")

        # Analyze price points
        price_ranges = self.analyze_price_ranges(results)
        if not price_ranges.get('premium', 0):
            gaps.append("Lack of premium service providers")

        return gaps

    def create_competitive_matrix(self, results, analyses):
        """Create competitive positioning matrix"""
        matrix_data = []

        for result in results:
            analysis = next((a for a in analyses if a.result_id == result.id), None)
            if analysis:
                matrix_data.append({
                    'business': result.title,
                    'market_share': (result.reviews or 0) / max(1, sum(r.reviews or 0 for r in results)),
                    'quality_score': analysis.score,
                    'growth_potential': self.assess_growth_potential(result, analysis)
                })

        return matrix_data

    # Visualization methods
    def create_market_share_chart(self, results):
        """Create market share visualization"""
        try:
            # Group by review count ranges
            review_ranges = {'0-50': 0, '51-200': 0, '201-500': 0, '501+': 0}

            for result in results:
                reviews = result.reviews or 0
                if reviews <= 50:
                    review_ranges['0-50'] += 1
                elif reviews <= 200:
                    review_ranges['51-200'] += 1
                elif reviews <= 500:
                    review_ranges['201-500'] += 1
                else:
                    review_ranges['501+'] += 1

            plt.figure(figsize=(10, 6))
            plt.pie(review_ranges.values(), labels=review_ranges.keys(), autopct='%1.1f%%')
            plt.title('Market Share Distribution by Business Size')

            # Save to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()

            return f"data:image/png;base64,{image_base64}"

        except Exception as e:
            logger.error(f"Market share chart creation failed: {e}")
            return None

    def generate_pdf_report(self, report_data, keyword):
        """Generate comprehensive PDF report"""
        try:
            # Render HTML template
            html_content = render_template(
                'reports/comprehensive_report.html',
                report_data=report_data,
                keyword=keyword,
                generated_date=datetime.now().strftime('%Y-%m-%d %H:%M')
            )

            # Configure PDF options
            options = {
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'no-outline': None
            }

            # Generate PDF
            pdf = pdfkit.from_string(html_content, False, options=options)

            return pdf

        except Exception as e:
            logger.error(f"PDF report generation failed: {e}")
            return None

    def generate_excel_report(self, report_data, keyword):
        """Generate multi-sheet Excel report"""
        try:
            with BytesIO() as output:
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    # Executive Summary sheet
                    summary_df = pd.DataFrame([report_data['executive_summary']])
                    summary_df.to_excel(writer, sheet_name='Executive Summary', index=False)

                    # Competitor Analysis sheet
                    competitors_df = pd.DataFrame(report_data['competitor_benchmarking']['top_competitors'])
                    competitors_df.to_excel(writer, sheet_name='Competitor Analysis', index=False)

                    # Market Analysis sheet
                    market_df = pd.DataFrame([report_data['market_analysis']])
                    market_df.to_excel(writer, sheet_name='Market Analysis', index=False)

                    # Opportunities sheet
                    opportunities_list = []
                    for category, opportunities in report_data['opportunity_analysis']['opportunities'].items():
                        if isinstance(opportunities, list):
                            for opp in opportunities:
                                opportunities_list.append({'category': category, 'opportunity': opp})
                        elif isinstance(opportunities, dict):
                            for key, value in opportunities.items():
                                opportunities_list.append({'category': category, 'opportunity': f"{key}: {value}"})

                    opportunities_df = pd.DataFrame(opportunities_list)
                    opportunities_df.to_excel(writer, sheet_name='Opportunities', index=False)

                return output.getvalue()

        except Exception as e:
            logger.error(f"Excel report generation failed: {e}")
            return None

    # Helper methods
    def calculate_average_rating(self, results):
        """Calculate average customer rating"""
        ratings = [r.stars for r in results if r.stars]
        return sum(ratings) / len(ratings) if ratings else 0

    def calculate_average_website_score(self, analyses):
        """Calculate average website quality score"""
        scores = [a.score for a in analyses if a.score]
        return sum(scores) / len(scores) if scores else 0

    def categorize_services(self, results):
        """Categorize businesses by service type"""
        categories = {}

        for result in results:
            title = result.title.lower()

            # Simple categorization logic (can be enhanced with ML)
            if any(word in title for word in ['restaurant', 'cafe', 'food', 'dining']):
                categories['Food & Dining'] = categories.get('Food & Dining', 0) + 1
            elif any(word in title for word in ['hotel', 'lodging', 'resort', 'inn']):
                categories['Hospitality'] = categories.get('Hospitality', 0) + 1
            elif any(word in title for word in ['shop', 'store', 'retail', 'boutique']):
                categories['Retail'] = categories.get('Retail', 0) + 1
            elif any(word in title for word in ['medical', 'clinic', 'hospital', 'doctor']):
                categories
                Healthcare
                '] = categories.get('
                Healthcare
                ', 0) + 1
            else:
                categories['Other'] = categories.get('Other', 0) + 1

        return categories

    def get_intensity_level(self, score):
        """Get competitive intensity level"""
        if score >= 70:
            return "High"
        elif score >= 40:
            return "Medium"
        else:
            return "Low"