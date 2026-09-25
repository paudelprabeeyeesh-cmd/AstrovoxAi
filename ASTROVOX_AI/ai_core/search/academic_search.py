from typing import Optional, Dict, Any, List
import requests
from urllib.parse import quote


class AcademicSearch:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def search_semantic_scholar(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={quote(query)}&fields=title,authors,year,citationCount,url&limit={num_results}"
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            results = []
            for paper in data.get('data', []):
                results.append({'title': paper.get('title'), 'year': paper.get('year'), 'citations': paper.get('citationCount'), 'url': paper.get('url'), 'source': 'semantic_scholar'})
            return results
        except Exception:
            return []

    def search_arxiv(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        url = f"http://export.arxiv.org/api/query?search_query=all:{quote(query)}&start=0&max_results={num_results}"
        try:
            response = requests.get(url, timeout=10)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            results = []
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns)
                link = entry.find('atom:id', ns)
                results.append({'title': title.text if title is not None else '', 'link': link.text if link is not None else '', 'source': 'arxiv'})
            return results
        except Exception:
            return []

    def search(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        semantic = self.search_semantic_scholar(query, num_results)
        arxiv = self.search_arxiv(query, num_results)
        return sorted(semantic + arxiv, key=lambda x: x.get('year', 0), reverse=True)[:num_results]
