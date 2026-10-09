import re
from dataclasses import dataclass

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


@dataclass
class ParsedArticle:
    title: str
    text: str
    links: list[str]


_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


class HTMLParser:
    def __init__(self, remove_scripts: bool = True) -> None:
        self.remove_scripts = remove_scripts

    def parse(self, html: str) -> ParsedArticle:
        soup = BeautifulSoup(html, "html.parser")
        if self.remove_scripts:
            for tag in soup(["script", "style"]):
                tag.decompose()
        for tag_name in ["nav", "footer", "header", "aside", "form"]:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        title = ""
        if soup.title and soup.title.string:
            title = _clean(soup.title.string)
        body = soup.find("body") or soup
        text = _clean(body.get_text(separator=" "))
        links = [a.get("href", "") for a in soup.find_all("a", href=True)]
        return ParsedArticle(title=title, text=text, links=links)
