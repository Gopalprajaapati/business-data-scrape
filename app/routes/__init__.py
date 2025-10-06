from .main import bp as main_bp

# Only import what exists
try:
    from .keywords import bp as keywords_bp
except ImportError:
    keywords_bp = None

try:
    from .scraping import bp as scraping_bp
except ImportError:
    scraping_bp = None

try:
    from .analysis import bp as analysis_bp
except ImportError:
    analysis_bp = None

try:
    from .api import bp as api_bp
except ImportError:
    api_bp = None

# Only register blueprints that exist
__all__ = ['main_bp']
