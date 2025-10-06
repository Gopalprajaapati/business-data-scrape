# tests/test_routes.py
import pytest
import json
from io import BytesIO


class TestKeywordRoutes:
    def test_create_keyword(self, client, session):
        """Test keyword creation via API"""
        response = client.post('/keywords/', json={
            'keyword': 'test restaurants',
            'priority': 2
        })

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['keyword'] == 'test restaurants'
        assert data['status'] == 'pending'

    def test_get_keywords(self, client, session, sample_keyword):
        """Test keywords retrieval via API"""
        response = client.get('/keywords/')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['keywords']) >= 1

    def test_delete_keyword(self, client, session, sample_keyword):
        """Test keyword deletion via API"""
        response = client.delete(f'/keywords/{sample_keyword.id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True


class TestScrapingRoutes:
    @patch('app.services.scraper.AdvancedScraperService.scrape_google_maps_advanced')
    def test_immediate_scraping(self, mock_scrape, client):
        """Test immediate scraping via API"""
        mock_scrape.return_value = [{'title': 'Test Business', 'website': 'https://test.com'}]

        response = client.post('/api/v1/scrape', json={
            'keyword': 'test business',
            'max_results': 10
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['results_count'] == 1


class TestAnalysisRoutes:
    @patch('app.services.analyzer.IntelligentWebsiteAnalyzer.comprehensive_analysis')
    def test_website_analysis(self, mock_analysis, client):
        """Test website analysis via API"""
        mock_analysis.return_value = {
            'score': 85,
            'seo_score': 80,
            'performance_score': 90
        }

        response = client.post('/api/v1/analyze/website', json={
            'url': 'https://example.com',
            'analysis_type': 'comprehensive'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['analysis']['score'] == 85


class TestReportRoutes:
    @patch('app.services.reporter.BusinessIntelligenceReporter.generate_comprehensive_report')
    def test_report_generation(self, mock_report, client, sample_keyword):
        """Test report generation via API"""
        mock_report.return_value = {
            'executive_summary': {'total_businesses': 10},
            'market_analysis': {'segments': {}}
        }

        response = client.post('/api/v1/reports/generate', json={
            'keyword_id': sample_keyword.id,
            'report_type': 'executive',
            'format': 'json'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True


class TestFileUploadRoutes:
    def test_excel_upload(self, client, session):
        """Test Excel file upload"""
        # Create test Excel file
        import pandas as pd
        df = pd.DataFrame({'keywords': ['test1', 'test2', 'test3']})

        excel_file = BytesIO()
        df.to_excel(excel_file, index=False)
        excel_file.seek(0)

        response = client.post('/upload/', data={
            'file': (excel_file, 'test_keywords.xlsx')
        }, content_type='multipart/form-data')

        assert response.status_code in [200, 201]