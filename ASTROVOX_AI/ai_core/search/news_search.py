from typing import Optional, Dict, Any, List
import requests
from datetime import datetime, timedelta
from urllib.parse import quote


class NewsSearch:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def search_newsapi(self, query: str, num_results: int = 10, days_back: int = 7) -> List[Dict[str, Any]]:
        if not self.api_key:
            return [{
                'title': f'Mock news: {query}',
                'source': 'Mock News',
                'published_at': datetime.utcnow().isoformat(),
                'url': 'https://example.com/news',
                'description': f'Mock news article about {query}.'
            }]
        from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        url = (
            f"https://newsapi.org/v2/everything?q={quote(query)}"
            f"&from={from_date}&pageSize={num_results}&apiKey={self.api_key}"
        )
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            results = []
            for article in data.get('articles', []):
                results.append({
                    'title': article.get('title'),
                    'source': article.get('source', {}).get('name'),
                    'published_at': article.get('publishedAt'),
                    'url': article.get('url'),
                    'description': article.get('description'),
                    'api_source': 'newsapi'
                })
            return results
        except Exception:
            return []

    def search_google_news_rss(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
        try:
            response = requests.get(url, timeout=10)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            results = []
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for item in root.findall('.//item')[:num_results]:
                title = item.find('title')
                link = item.find('link')
                pub_date = item.find('pubDate')
                results.append({
                    'title': title.text if title is not None else '',
                    'source': 'Google News RSS',
                    'published_at': pub_date.text if pub_date is not None else '',
                    'url': link.text if link is not None else '',
                    'description': '',
                    'api_source': 'google_news_rss'
                })
            return results
        except Exception:
            return []

    def search(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        newsapi = self.search_newsapi(query, num_results)
        rss = self.search_google_news_rss(query, num_results)
        combined = newsapi + rss
        seen = set()
        unique = []
        for item in combined:
            key = item.get('url') or item.get('title', '')
            if key and key not in seen:
                seen.add(key)
                unique.append(item)
        return unique[:num_results]

    def search_with_fallback(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        results = self.search(query, num_results)
        if not results:
            return [{
                'title': 'No news found',
                'source': '',
                'published_at': '',
                'url': '',
                'description': 'Consider refining your news search query.',
                'source': 'fallback'
            }]
        return results
