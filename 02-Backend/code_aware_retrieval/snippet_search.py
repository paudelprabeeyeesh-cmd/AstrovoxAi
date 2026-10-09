from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CodeSnippet:
    file_path: str
    start_line: int
    end_line: int
    content: str
    language: Optional[str] = None


class SnippetSearch:
    def __init__(self) -> None:
        self._snippets: List[CodeSnippet] = []

    def index(self, snippets: List[CodeSnippet]) -> None:
        self._snippets.extend(snippets)

    def search(self, query: str, case_sensitive: bool = False) -> List[CodeSnippet]:
        results = []
        for snippet in self._snippets:
            haystack = snippet.content if case_sensitive else snippet.content.lower()
            q = query if case_sensitive else query.lower()
            if q in haystack:
                results.append(snippet)
        return results

    def search_regex(self, pattern: str) -> List[CodeSnippet]:
        import re

        compiled = re.compile(pattern)
        results = []
        for snippet in self._snippets:
            if compiled.search(snippet.content):
                results.append(snippet)
        return results
