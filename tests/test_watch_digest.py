"""Tests for watch service, digest generation, and cron management."""

from pathlib import Path
from unittest.mock import patch

import pytest

from openseed.models.paper import Author, Paper, Tag
from openseed.models.watch import ArxivWatch
from openseed.services.digest import generate_digest, save_digest
from openseed.storage.library import PaperLibrary


@pytest.fixture
def lib(tmp_path: Path) -> PaperLibrary:
    return PaperLibrary(tmp_path / "library")


class TestWatchService:
    def test_run_all_watches_empty(self, lib: PaperLibrary) -> None:
        from openseed.services.watch import run_all_watches

        assert run_all_watches(lib) == {}

    @patch("openseed.services.watch.search_papers")
    def test_run_single_watch(self, mock_search, lib: PaperLibrary) -> None:
        from openseed.services.watch import run_single_watch

        w = ArxivWatch(query="attention", since_year=2024)
        lib.add_watch(w)
        mock_search.return_value = [
            Paper(title="New Paper", arxiv_id="2401.00001", authors=[Author(name="A")]),
        ]
        results = run_single_watch(lib, w)
        assert len(results) == 1
        assert results[0].title == "New Paper"
        updated = lib.list_watches()[0]
        assert updated.last_run is not None

    @patch("openseed.services.watch.search_papers")
    def test_run_single_watch_filters_year(self, mock_search, lib: PaperLibrary) -> None:
        from openseed.services.watch import run_single_watch

        w = ArxivWatch(query="attention", since_year=2024)
        lib.add_watch(w)
        mock_search.return_value = [
            Paper(title="Old", arxiv_id="1901.00001"),
            Paper(title="New", arxiv_id="2401.00001"),
        ]
        results = run_single_watch(lib, w)
        assert len(results) == 1
        assert results[0].title == "New"

    @patch("openseed.services.watch.search_papers")
    def test_run_all_watches(self, mock_search, lib: PaperLibrary) -> None:
        from openseed.services.watch import run_all_watches

        w1 = ArxivWatch(id="w1", query="attention")
        w2 = ArxivWatch(id="w2", query="diffusion")
        lib.add_watch(w1)
        lib.add_watch(w2)
        mock_search.return_value = [Paper(title="P", arxiv_id="2401.00001")]
        results = run_all_watches(lib)
        assert len(results) == 2
        assert "w1" in results
        assert "w2" in results


class TestDigest:
    def test_empty_digest(self) -> None:
        content = generate_digest({}, {})
        assert "No new papers found" in content

    def test_digest_with_papers(self) -> None:
        papers = [Paper(title="Cool Paper", arxiv_id="2401.00001", authors=[Author(name="Smith")])]
        content = generate_digest(
            {"w1": papers},
            {"w1": "attention mechanisms"},
        )
        assert "Cool Paper" in content
        assert "attention mechanisms" in content
        assert "1 papers" in content

    def test_digest_multiple_watches(self) -> None:
        content = generate_digest(
            {
                "w1": [Paper(title="P1", arxiv_id="2401.00001")],
                "w2": [Paper(title="P2", arxiv_id="2401.00002")],
            },
            {"w1": "attention", "w2": "diffusion"},
        )
        assert "2 papers" in content
        assert "attention" in content
        assert "diffusion" in content

    def test_save_digest(self, tmp_path: Path) -> None:
        path = save_digest("# Test Digest\n", tmp_path / "digests")
        assert path.exists()
        assert "digest_" in path.name
        assert path.read_text() == "# Test Digest\n"


class TestCron:
    @patch("openseed.services.cron._read_crontab", return_value="")
    @patch("openseed.services.cron._write_crontab")
    def test_install(self, mock_write, mock_read) -> None:
        from openseed.services.cron import install

        result = install()
        assert "openseed" in result
        assert "watch run" in result
        mock_write.assert_called_once()

    @patch("openseed.services.cron._read_crontab", return_value="# openseed-watch-cron")
    def test_install_already_scheduled(self, mock_read) -> None:
        from openseed.services.cron import install

        assert install() == "already scheduled"

    @patch(
        "openseed.services.cron._read_crontab",
        return_value="other\n0 8 * * * openseed watch run >> log 2>&1 # openseed-watch-cron",
    )
    @patch("openseed.services.cron._write_crontab")
    def test_uninstall(self, mock_write, mock_read) -> None:
        from openseed.services.cron import uninstall

        assert uninstall() is True
        written = mock_write.call_args[0][0]
        assert "openseed-watch-cron" not in written
        assert "other" in written

    @patch("openseed.services.cron._read_crontab", return_value="")
    def test_uninstall_not_scheduled(self, mock_read) -> None:
        from openseed.services.cron import uninstall

        assert uninstall() is False

    @patch("openseed.services.cron.is_scheduled", return_value=True)
    def test_get_status_scheduled(self, mock_sched) -> None:
        from openseed.services.cron import get_status

        status = get_status()
        assert status["scheduled"] is True
        assert "watch.log" in status["log_path"]

    @patch("openseed.services.cron.is_scheduled", return_value=False)
    def test_get_status_not_scheduled(self, mock_sched) -> None:
        from openseed.services.cron import get_status

        status = get_status()
        assert status["scheduled"] is False


class TestSmartQueue:
    def test_smart_queue_prefers_tag_overlap(self, lib: PaperLibrary) -> None:
        read_paper = Paper(
            id="r1",
            title="Read Paper",
            status="read",
            tags=[Tag(name="transformers"), Tag(name="nlp")],
        )
        unread_relevant = Paper(
            id="u1",
            title="Relevant Unread",
            status="unread",
            tags=[Tag(name="transformers")],
        )
        unread_unrelated = Paper(
            id="u2",
            title="Unrelated Unread",
            status="unread",
            tags=[Tag(name="physics")],
        )
        lib.add_paper(read_paper)
        lib.add_paper(unread_relevant)
        lib.add_paper(unread_unrelated)

        from openseed.cli.paper import _smart_queue_score

        recent_tags = {"transformers", "nlp"}
        score_relevant = _smart_queue_score(unread_relevant, recent_tags)
        score_unrelated = _smart_queue_score(unread_unrelated, recent_tags)
        assert score_relevant > score_unrelated
