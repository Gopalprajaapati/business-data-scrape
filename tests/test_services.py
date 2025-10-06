# tests/test_services.py
import pytest
from unittest.mock import Mock, patch
from app.services.scraper import AdvancedScraperService
from app.services.analyzer import IntelligentWebsiteAnalyzer
from app.services.reporter import BusinessIntelligenceReporter


class TestScraperService:
    @patch('app.services.scraper.webdriver.Chrome')
    def test_scraper_initialization(self, mock_chrome):
        """Test scraper service initialization"""
        scraper = AdvancedScraperService(use_proxies=False, headless=True)

        assert scraper.use_proxies == False
        assert scraper.headless == True
        assert isinstance(scraper.user_agents, list)

    @patch('app.services.scraper.webdriver.Chrome')
    def test_stealth_driver_creation(self, mock_chrome):
        """Test stealth driver creation"""
        scraper = AdvancedScraperService()
        driver = scraper.create_stealth_driver()

        assert mock_chrome.called
        # Verify anti-detection options were set

    def test_contact_info_extraction(self):
        """Test contact information extraction"""
        scraper = AdvancedScraperService()

        # Mock element with contact info
        mock_element = Mock()
        mock_element.text = "Contact us at +1-234-567-8900 or visit 123 Main St, New York, NY 10001"

        contact_data = scraper.extract_contact_info(mock_element)

        assert 'phone' in contact_data
        assert 'address' in contact_data


class TestAnalyzerService:
    def test_analyzer_initialization(self):
        """Test analyzer service initialization"""
        analyzer = IntelligentWebsiteAnalyzer()

        assert hasattr(analyzer, 'analysis_cache')
        assert analyzer.cache_timeout == 3600

    @patch('app.services.analyzer.requests.get')
    def test_basic_analysis(self, mock_get):
        """Test basic website analysis"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><head><title>Test</title></head><body>Content</body></html>'
        mock_response.url = 'https://example.com'
        mock_response.history = []
        mock_get.return_value = mock_response

        analyzer = IntelligentWebsiteAnalyzer()
        analysis = analyzer.basic_website_analysis('https://example.com')

        assert 'load_time' in analysis
        assert 'status_code' in analysis
        assert 'mobile_friendly' in analysis

    def test_score_calculation(self):
        """Test overall score calculation"""
        analyzer = IntelligentWebsiteAnalyzer()

        test_data = {
            'seo_score': 80,
            'security_score': 90,
            'performance_score': 70,
            'credibility_score': 85,
            'basic_score': 75
        }

        score = analyzer.calculate_overall_score(test_data)

        assert 0 <= score <= 100
        assert isinstance(score, int)


class TestReporterService:
    def test_reporter_initialization(self):
        """Test reporter service initialization"""
        reporter = BusinessIntelligenceReporter()

        assert reporter is not None

    def test_executive_summary_generation(self, session, sample_keyword, sample_search_result, sample_website_analysis):
        """Test executive summary generation"""
        reporter = BusinessIntelligenceReporter()

        results = [sample_search_result]
        analyses = [sample_website_analysis]

        summary = reporter.generate_executive_summary(sample_keyword, results, analyses)

        assert 'total_businesses_analyzed' in summary
        assert 'average_website_quality' in summary
        assert 'market_segments' in summary

    def test_competitive_intensity_assessment(self, session, sample_search_result, sample_website_analysis):
        """Test competitive intensity assessment"""
        reporter = BusinessIntelligenceReporter()

        results = [sample_search_result] * 10  # 10 competitors
        analyses = [sample_website_analysis] * 10

        intensity = reporter.assess_competitive_intensity(results, analyses)

        assert 'intensity_score' in intensity
        assert 'intensity_level' in intensity
        assert 'factors' in intensity