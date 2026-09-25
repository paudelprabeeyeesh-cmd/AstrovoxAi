from typing import Optional, Dict, Any, List
import requests
from urllib.parse import quote


class ImageSearch:
    def __init__(self, api_key: Optional[str] = None, search_engine_id: Optional[str] = None):
        self.api_key = api_key
        self.search_engine_id = search_engine_id

    def search(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        if not self.api_key or not self.search_engine_id:
            return [{
                'title': f'Mock image for {query}',
                'link': 'https://example.com/image.jpg',
                'thumbnail': 'https://example.com/thumb.jpg',
                'context': f'Mock image result for: {query}'
            }]
        url = (
            f"https://www.googleapis.com/customsearch/v1"
            f"?key={self.api_key}&cx={self.search_engine_id}"
            f"&q={quote(query)}&searchType=image&num={num_results}"
        )
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            results = []
            for item in data.get('items', []):
                results.append({
                    'title': item.get('title'),
                    'link': item.get('link'),
                    'thumbnail': item.get('image', {}).get('thumbnailLink'),
                    'context': item.get('image', {}).get('contextLink'),
                    'source': 'google_images'
                })
            return results
        except Exception:
            return []

    def search_with_fallback(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        results = self.search(query, num_results)
        if not results:
            return [{
                'title': 'No images found',
                'link': '',
                'thumbnail': '',
                'context': 'Consider refining your image search query.'
            }]
        return results
