import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from scripts.list_douyin_author_videos import main


class ListDouyinAuthorVideosTests(unittest.TestCase):
    @patch("scripts.list_douyin_author_videos.get_author_video_urls")
    def test_main_prints_video_urls_in_order(self, mock_get_author_video_urls):
        mock_get_author_video_urls.return_value = [
            "https://www.douyin.com/video/3",
            "https://www.douyin.com/video/2",
            "https://www.douyin.com/video/1",
        ]

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["--author-url", "https://www.douyin.com/user/demo"])

        self.assertEqual(0, exit_code)
        self.assertEqual(
            stdout.getvalue().splitlines(),
            [
                "https://www.douyin.com/video/3",
                "https://www.douyin.com/video/2",
                "https://www.douyin.com/video/1",
            ],
        )

    @patch("scripts.list_douyin_author_videos.get_author_video_urls")
    def test_main_accepts_empty_result(self, mock_get_author_video_urls):
        mock_get_author_video_urls.return_value = []

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["--author-url", "https://www.douyin.com/user/demo"])

        self.assertEqual(0, exit_code)
        self.assertEqual("", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
