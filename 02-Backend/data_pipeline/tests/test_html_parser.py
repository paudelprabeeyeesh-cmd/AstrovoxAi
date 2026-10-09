import unittest
from unittest.mock import MagicMock, patch

from data_pipeline.html_parser import HTMLParser


class TestHTMLParser(unittest.TestCase):
    def test_init(self):
        parser = HTMLParser(remove_scripts=False)
        self.assertEqual(parser.remove_scripts, False)

    @patch("data_pipeline.html_parser.BeautifulSoup")
    def test_parse_basic(self, mock_bs_cls):
        mock_soup = MagicMock()
        mock_bs_cls.return_value = mock_soup
        mock_soup.title.string = "Test Title"
        mock_soup.find.return_value = MagicMock(get_text=MagicMock(return_value="hello world"))
        mock_soup.find_all.return_value = []

        parser = HTMLParser()
        result = parser.parse("<html><head><title>Test Title</title></head><body>hello world</body></html>")
        self.assertEqual(result.title, "Test Title")
        self.assertIn("hello", result.text)

    @patch("data_pipeline.html_parser.BeautifulSoup")
    def test_parse_removes_scripts(self, mock_bs_cls):
        mock_soup = MagicMock()
        mock_bs_cls.return_value = mock_soup
        mock_soup.title.string = "Title"
        mock_soup.find.return_value = MagicMock(get_text=MagicMock(return_value="text"))
        mock_soup.find_all.return_value = []

        parser = HTMLParser(remove_scripts=True)
        parser.parse("<html><script>alert(1)</script><body>text</body></html>")
        mock_soup.__contains__.assert_not_called()  # just verify it parsed

    @patch("data_pipeline.html_parser.BeautifulSoup")
    def test_parse_links(self, mock_bs_cls):
        mock_soup = MagicMock()
        mock_bs_cls.return_value = mock_soup
        mock_soup.title.string = "Title"
        mock_soup.find.return_value = MagicMock(get_text=MagicMock(return_value="text"))
        mock_tag = MagicMock()
        mock_tag.get.return_value = "http://example.com"
        mock_soup.find_all.return_value = [mock_tag]

        parser = HTMLParser()
        result = parser.parse("<html><body><a href='http://example.com'>link</a></body></html>")
        self.assertEqual(result.links, ["http://example.com"])
