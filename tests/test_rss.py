"""Tests for RSS feed discovery."""

from openseed.services.rss import fetch_feed

_ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>ArXiv cs.CL</title>
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <title>A Novel Approach to NLP</title>
    <summary>We propose a new method.</summary>
    <author><name>Alice Smith</name></author>
    <author><name>Bob Jones</name></author>
    <link href="http://arxiv.org/abs/2401.00001v1" rel="alternate"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2401.00002v1</id>
    <title>Better Language Models</title>
    <summary>Improved pre-training.</summary>
    <author><name>Carol Lee</name></author>
    <link href="http://arxiv.org/abs/2401.00002v1" rel="alternate"/>
  </entry>
</feed>"""

_RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>ML Papers</title>
    <item>
      <title>Deep Learning Survey</title>
      <link>http://arxiv.org/abs/2301.12345</link>
      <description>A comprehensive survey.</description>
    </item>
  </channel>
</rss>"""


class TestAtomParsing:
    def test_parse_atom_feed(self) -> None:
        from unittest.mock import MagicMock, patch

        mock_resp = MagicMock()
        mock_resp.text = _ATOM_FEED
        mock_resp.raise_for_status = MagicMock()

        with patch("openseed.services.rss.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.get.return_value = mock_resp

            papers = fetch_feed("http://example.com/feed.xml")

        assert len(papers) == 2
        assert papers[0].title == "A Novel Approach to NLP"
        assert papers[0].arxiv_id == "2401.00001"
        assert len(papers[0].authors) == 2
        assert papers[0].authors[0].name == "Alice Smith"

    def test_parse_rss_feed(self) -> None:
        from unittest.mock import MagicMock, patch

        mock_resp = MagicMock()
        mock_resp.text = _RSS_FEED
        mock_resp.raise_for_status = MagicMock()

        with patch("openseed.services.rss.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.get.return_value = mock_resp

            papers = fetch_feed("http://example.com/rss.xml")

        assert len(papers) == 1
        assert papers[0].title == "Deep Learning Survey"
        assert papers[0].arxiv_id == "2301.12345"

    def test_fetch_feed_network_error(self) -> None:
        from unittest.mock import MagicMock, patch

        import httpx

        with patch("openseed.services.rss.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.get.side_effect = httpx.TimeoutException("timeout")

            papers = fetch_feed("http://example.com/feed.xml")

        assert papers == []

    def test_max_items(self) -> None:
        from unittest.mock import MagicMock, patch

        mock_resp = MagicMock()
        mock_resp.text = _ATOM_FEED
        mock_resp.raise_for_status = MagicMock()

        with patch("openseed.services.rss.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.get.return_value = mock_resp

            papers = fetch_feed("http://example.com/feed.xml", max_items=1)

        assert len(papers) == 1
