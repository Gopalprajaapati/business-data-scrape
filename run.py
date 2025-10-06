from app import create_app, db
from app.models import Keyword, SearchResult, WebsiteAnalysis

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'Keyword': Keyword,
        'SearchResult': SearchResult,
        'WebsiteAnalysis': WebsiteAnalysis
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
