# tests/test_models.py
import pytest
from datetime import datetime, timedelta
from app.models import Keyword, SearchResult, WebsiteAnalysis, DatabaseManager


class TestKeywordModel:
    def test_create_keyword(self, session):
        """Test keyword creation"""
        keyword = Keyword(keyword="test business")
        session.add(keyword)
        session.commit()

        assert keyword.id is not None
        assert keyword.status == 'pending'
        assert keyword.created_at is not None

    def test_keyword_stats_update(self, session, sample_keyword, sample_search_result):
        """Test keyword statistics update"""
        sample_keyword.update_stats()

        assert sample_keyword.total_results == 1
        assert sample_keyword.success_rate == 100.0

    def test_keyword_to_dict(self, sample_keyword):
        """Test keyword serialization"""
        data = sample_keyword.to_dict()

        assert 'id' in data
        assert 'keyword' in data
        assert 'status' in data
        assert 'created_at' in data


class TestSearchResultModel:
    def test_create_search_result(self, session, sample_keyword):
        """Test search result creation"""
        result = SearchResult(
            keyword_id=sample_keyword.id,
            title="Test Business",
            website="https://test.com"
        )
        session.add(result)
        session.commit()

        assert result.id is not None
        assert result.quality_score > 0
        assert result.has_website == True

    def test_quality_score_calculation(self, sample_search_result):
        """Test quality score calculation"""
        score = sample_search_result.quality_score
        assert 0 <= score <= 100

        # Test with more data
        sample_search_result.email = "test@test.com"
        sample_search_result.update_quality_flags()

        new_score = sample_search_result.quality_score
        assert new_score > score

    def test_search_result_to_dict(self, sample_search_result):
        """Test search result serialization"""
        data = sample_search_result.to_dict()

        assert 'id' in data
        assert 'title' in data
        assert 'website' in data
        assert 'quality_score' in data


class TestWebsiteAnalysisModel:
    def test_create_analysis(self, session, sample_search_result):
        """Test website analysis creation"""
        analysis = WebsiteAnalysis(
            result_id=sample_search_result.id,
            score=75,
            mobile_friendly=True,
            load_time=3.0
        )
        session.add(analysis)
        session.commit()

        assert analysis.id is not None
        assert analysis.overall_grade == 'C'

    def test_technology_stack_handling(self, sample_website_analysis):
        """Test technology stack JSON handling"""
        tech_list = ['WordPress', 'React', 'Google Analytics']
        sample_website_analysis.set_technology_stack(tech_list)

        retrieved_list = sample_website_analysis.get_technology_stack_list()
        assert retrieved_list == tech_list

    def test_analysis_to_dict(self, sample_website_analysis):
        """Test analysis serialization"""
        data = sample_website_analysis.to_dict()

        assert 'scores' in data
        assert 'metrics' in data
        assert 'technical' in data
        assert 'grade' in data


class TestDatabaseManager:
    def test_database_stats(self, session, sample_keyword, sample_search_result, sample_website_analysis):
        """Test database statistics collection"""
        db_manager = DatabaseManager(session)
        stats = db_manager.get_database_stats()

        assert stats['keywords_count'] >= 1
        assert stats['results_count'] >= 1
        assert stats['analyses_count'] >= 1