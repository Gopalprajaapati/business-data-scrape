# tests/conftest.py
import pytest
import tempfile
import os
from app import create_app, db as _db
from app.models import Keyword, SearchResult, WebsiteAnalysis
from config import TestingConfig


@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    app = create_app(TestingConfig)

    with app.app_context():
        yield app


@pytest.fixture(scope='session')
def db(app):
    """Create database for testing"""
    _db.create_all()
    yield _db
    _db.drop_all()


@pytest.fixture(scope='function')
def session(db):
    """Create database session for each test"""
    connection = db.engine.connect()
    transaction = connection.begin()

    session = db.create_scoped_session(options={'bind': connection})
    db.session = session

    yield session

    transaction.rollback()
    connection.close()
    session.remove()


@pytest.fixture
def client(app, session):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def sample_keyword(session):
    """Create sample keyword for testing"""
    keyword = Keyword(keyword="test restaurants in new york", status="pending")
    session.add(keyword)
    session.commit()
    return keyword


@pytest.fixture
def sample_search_result(session, sample_keyword):
    """Create sample search result for testing"""
    result = SearchResult(
        keyword_id=sample_keyword.id,
        title="Test Restaurant",
        website="https://testrestaurant.com",
        stars=4.5,
        reviews=100,
        phone="+1234567890"
    )
    session.add(result)
    session.commit()
    return result


@pytest.fixture
def sample_website_analysis(session, sample_search_result):
    """Create sample website analysis for testing"""
    analysis = WebsiteAnalysis(
        result_id=sample_search_result.id,
        mobile_friendly=True,
        load_time=2.5,
        professional_look=True,
        score=85,
        seo_score=80,
        performance_score=90,
        security_score=85,
        credibility_score=80
    )
    session.add(analysis)
    session.commit()
    return analysis