import unittest
from unittest.mock import MagicMock, patch

from data_pipeline.web_crawler import CrawlConfig, DistributedCrawler


class TestCrawler(unittest.TestCase):
    def test_init(self):
        config = CrawlConfig(delay=0.5, timeout=5)
        crawler = DistributedCrawler(config=config)
        self.assertEqual(crawler.config.delay, 0.5)
        self.assertEqual(crawler.config.timeout, 5)

    def test_default_init(self):
        crawler = DistributedCrawler()
        self.assertIsNotNone(crawler.config)

    @patch("data_pipeline.web_crawler.urllib.robotparser.RobotFileParser")
    def test_allowed_by_robots(self, mock_rfp):
        crawler = DistributedCrawler()
        mock_rp = MagicMock()
        mock_rfp.return_value = mock_rp
        mock_rp.can_fetch.return_value = True
        result = crawler._allowed_by_robots("http://example.com/page")
        self.assertTrue(result)

    @patch("data_pipeline.web_crawler.time.time", return_value=100.0)
    def test_respect_politeness(self, mock_time):
        config = CrawlConfig(delay=1.0)
        crawler = DistributedCrawler(config=config)
        crawler._last_request["example.com"] = 99.5
        crawler._respect_politeness("http://example.com/page")
        self.assertEqual(crawler._last_request["example.com"], 100.0)

    @patch("data_pipeline.web_crawler.requests.Session")
    def test_fetch(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.text = "<html>body</html>"
        mock_session.get.return_value = mock_resp

        config = CrawlConfig(delay=0.0)
        crawler = DistributedCrawler(config=config)
        with patch.object(crawler, "_allowed_by_robots", return_value=True):
            result = crawler.fetch("http://example.com/page")
        self.assertEqual(result, "<html>body</html>")

    @patch("data_pipeline.web_crawler.requests.Session")
    def test_fetch_disallowed(self, mock_session_cls):
        config = CrawlConfig(delay=0.0)
        crawler = DistributedCrawler(config=config)
        with patch.object(crawler, "_allowed_by_robots", return_value=False):
            result = crawler.fetch("http://example.com/page")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
