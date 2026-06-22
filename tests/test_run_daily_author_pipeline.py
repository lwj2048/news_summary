import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.douyin_state import ProcessedVideoStore
from scripts.run_daily_author_pipeline import _published_at_to_timestamp, run_daily_pipeline


class RunDailyAuthorPipelineTests(unittest.TestCase):
    def test_published_at_to_timestamp_uses_shanghai_time(self) -> None:
        self.assertEqual("20250618-0930", _published_at_to_timestamp("2025-06-18T09:30:00+08:00"))

    def test_only_processes_unprocessed_videos_published_today(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "processed.json"
            processed_runs: list[str] = []

            def fake_fetch(_author_url: str) -> list[dict[str, str]]:
                return [
                    {
                        "video_id": "today-new",
                        "video_url": "https://example.com/today-new",
                        "published_at_raw": 1750204800000,
                    },
                    {
                        "video_id": "yesterday",
                        "video_url": "https://example.com/yesterday",
                        "published_at_raw": 1750118400000,
                    },
                ]

            def fake_run(video_url: str) -> int:
                processed_runs.append(video_url)
                return 0

            exit_code = run_daily_pipeline(
                author_url="https://example.com/author",
                author_id="author-1",
                state_file=state_file,
                target_day=date(2025, 6, 18),
                fetch_author_videos=fake_fetch,
                run_single_video=fake_run,
            )

            self.assertEqual(0, exit_code)
            self.assertEqual(["https://example.com/today-new"], processed_runs)

            store = ProcessedVideoStore(state_file)
            self.assertTrue(store.is_processed("author-1", "today-new"))
            self.assertFalse(store.is_processed("author-1", "yesterday"))

    def test_skips_processed_videos_and_returns_non_zero_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "processed.json"
            processed_runs: list[str] = []

            def fake_fetch(_author_url: str) -> list[dict[str, str]]:
                return [
                    {
                        "video_id": "already-done",
                        "video_url": "https://example.com/already-done",
                        "published_at_raw": 1750204800000,
                    },
                    {
                        "video_id": "today-fail",
                        "video_url": "https://example.com/today-fail",
                        "published_at_raw": 1750208400000,
                    },
                ]

            def fake_run(video_url: str) -> int:
                processed_runs.append(video_url)
                return 1

            store = ProcessedVideoStore(state_file)
            store.record_processed(
                author_id="author-1",
                video_id="already-done",
                video_url="https://example.com/already-done",
                published_at="2025-06-18T08:00:00+08:00",
                processed_at="2025-06-18T09:00:00+08:00",
            )

            exit_code = run_daily_pipeline(
                author_url="https://example.com/author",
                author_id="author-1",
                state_file=state_file,
                target_day=date(2025, 6, 18),
                fetch_author_videos=fake_fetch,
                run_single_video=fake_run,
            )

            self.assertEqual(1, exit_code)
            self.assertEqual(["https://example.com/today-fail"], processed_runs)

            reloaded_store = ProcessedVideoStore(state_file)
            self.assertTrue(reloaded_store.is_processed("author-1", "already-done"))
            self.assertFalse(reloaded_store.is_processed("author-1", "today-fail"))

    def test_continues_processing_when_one_video_has_invalid_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "processed.json"
            processed_runs: list[str] = []

            def fake_fetch(_author_url: str) -> list[dict[str, object]]:
                return [
                    {
                        "video_id": "bad-video",
                        "video_url": "",
                        "published_at": "2025-06-18T08:00:00+08:00",
                    },
                    {
                        "video_id": "good-video",
                        "video_url": "https://example.com/good-video",
                        "published_at": "2025-06-18T09:00:00+08:00",
                    },
                ]

            def fake_run(video_url: str) -> int:
                processed_runs.append(video_url)
                return 0

            exit_code = run_daily_pipeline(
                author_url="https://example.com/author",
                author_id="author-1",
                state_file=state_file,
                target_day=date(2025, 6, 18),
                fetch_author_videos=fake_fetch,
                run_single_video=fake_run,
            )

            self.assertEqual(1, exit_code)
            self.assertEqual(["https://example.com/good-video"], processed_runs)

            store = ProcessedVideoStore(state_file)
            self.assertFalse(store.is_processed("author-1", "bad-video"))
            self.assertTrue(store.is_processed("author-1", "good-video"))

    def test_filters_out_non_target_day_videos_when_published_at_is_already_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "processed.json"
            processed_runs: list[str] = []

            def fake_fetch(_author_url: str) -> list[dict[str, object]]:
                return [
                    {
                        "video_id": "yesterday-video",
                        "video_url": "https://example.com/yesterday-video",
                        "published_at": "2025-06-17T23:30:00+08:00",
                    },
                    {
                        "video_id": "today-video",
                        "video_url": "https://example.com/today-video",
                        "published_at": "2025-06-18T09:00:00+08:00",
                    },
                ]

            def fake_run(video_url: str) -> int:
                processed_runs.append(video_url)
                return 0

            exit_code = run_daily_pipeline(
                author_url="https://example.com/author",
                author_id="author-1",
                state_file=state_file,
                target_day=date(2025, 6, 18),
                fetch_author_videos=fake_fetch,
                run_single_video=fake_run,
            )

            self.assertEqual(0, exit_code)
            self.assertEqual(["https://example.com/today-video"], processed_runs)

            store = ProcessedVideoStore(state_file)
            self.assertFalse(store.is_processed("author-1", "yesterday-video"))
            self.assertTrue(store.is_processed("author-1", "today-video"))

    def test_marks_invalid_published_at_string_as_failure_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "processed.json"
            processed_runs: list[str] = []

            def fake_fetch(_author_url: str) -> list[dict[str, object]]:
                return [
                    {
                        "video_id": "bad-published-at",
                        "video_url": "https://example.com/bad-published-at",
                        "published_at": "not-a-valid-iso-time",
                    },
                    {
                        "video_id": "good-video",
                        "video_url": "https://example.com/good-video",
                        "published_at": "2025-06-18T09:00:00+08:00",
                    },
                ]

            def fake_run(video_url: str) -> int:
                processed_runs.append(video_url)
                return 0

            exit_code = run_daily_pipeline(
                author_url="https://example.com/author",
                author_id="author-1",
                state_file=state_file,
                target_day=date(2025, 6, 18),
                fetch_author_videos=fake_fetch,
                run_single_video=fake_run,
            )

            self.assertEqual(1, exit_code)
            self.assertEqual(["https://example.com/good-video"], processed_runs)

            store = ProcessedVideoStore(state_file)
            self.assertFalse(store.is_processed("author-1", "bad-published-at"))
            self.assertTrue(store.is_processed("author-1", "good-video"))

    def test_passes_published_at_into_single_video_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "processed.json"
            processed_runs: list[tuple[str, str]] = []

            def fake_fetch(_author_url: str) -> list[dict[str, object]]:
                return [
                    {
                        "video_id": "today-video",
                        "video_url": "https://example.com/today-video",
                        "published_at": "2025-06-18T09:00:00+08:00",
                    }
                ]

            def fake_run(video_url: str, published_at: str) -> int:
                processed_runs.append((video_url, published_at))
                return 0

            exit_code = run_daily_pipeline(
                author_url="https://example.com/author",
                author_id="author-1",
                state_file=state_file,
                target_day=date(2025, 6, 18),
                fetch_author_videos=fake_fetch,
                run_single_video=fake_run,
            )

            self.assertEqual(0, exit_code)
            self.assertEqual(
                [("https://example.com/today-video", "2025-06-18T09:00:00+08:00")],
                processed_runs,
            )

    def test_all_history_mode_processes_non_target_day_videos(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "processed.json"
            processed_runs: list[str] = []

            def fake_fetch(_author_url: str) -> list[dict[str, object]]:
                return [
                    {
                        "video_id": "old-video",
                        "video_url": "https://example.com/old-video",
                        "published_at_raw": 1750118400000,
                    },
                    {
                        "video_id": "today-video",
                        "video_url": "https://example.com/today-video",
                        "published_at_raw": 1750204800000,
                    },
                ]

            def fake_run(video_url: str) -> int:
                processed_runs.append(video_url)
                return 0

            exit_code = run_daily_pipeline(
                author_url="https://example.com/author",
                author_id="author-1",
                state_file=state_file,
                target_day=date(2025, 6, 18),
                process_all_history=True,
                fetch_author_videos=fake_fetch,
                run_single_video=fake_run,
            )

            self.assertEqual(0, exit_code)
            self.assertEqual(
                ["https://example.com/old-video", "https://example.com/today-video"],
                processed_runs,
            )


if __name__ == "__main__":
    unittest.main()
