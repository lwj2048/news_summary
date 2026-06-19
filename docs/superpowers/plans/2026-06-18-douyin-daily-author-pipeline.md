# Douyin Daily Author Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 保留现有单视频运行方式，同时新增一个可定时执行的“抓取指定抖音博主当天全部未处理视频并接入现有 workflow”的批处理入口。

**Architecture:** 新增一个负责“博主页抓取与当天过滤”的模块、一个负责“状态读写与去重”的模块，以及一个负责“逐条调用现有单视频流水线”的批处理脚本。GitHub Actions 新增独立定时 workflow，现有手动单视频 workflow 保持可用。

**Tech Stack:** Python 3.11、requests、pytest、GitHub Actions、现有 `run_pipeline.py`

---

## File Structure

- Create: `scripts/douyin_author_feed.py`
  - 负责从博主主页或相关接口解析视频列表，并提供当天过滤函数。
- Create: `scripts/douyin_state.py`
  - 负责读取、初始化、查询、写入 `processed_douyin_videos.json`。
- Create: `scripts/run_daily_author_pipeline.py`
  - 负责批处理编排，逐条调用现有 `scripts/run_pipeline.py`。
- Create: `tests/test_douyin_author_feed.py`
  - 覆盖发布时间解析和当天过滤逻辑。
- Create: `tests/test_douyin_state.py`
  - 覆盖状态文件初始化、去重判断、成功后写入逻辑。
- Create: `tests/test_run_daily_author_pipeline.py`
  - 覆盖批处理编排、失败传播、无新视频返回码。
- Create: `.github/workflows/douyin_daily_author_pipeline.yml`
  - 每日定时和手动触发新批处理脚本。
- Modify: `README.md`
  - 补充新的每日批处理和定时说明。
- Modify: `requirements.txt`
  - 增加 `pytest` 作为测试依赖。
- Create: `data/.gitkeep`
  - 确保状态文件目录被 Git 跟踪。

### Task 1: Author Feed Filtering

**Files:**
- Create: `tests/test_douyin_author_feed.py`
- Create: `scripts/douyin_author_feed.py`

- [ ] **Step 1: Write the failing test**

```python
from datetime import date

from scripts.douyin_author_feed import filter_today_videos, parse_publish_time


def test_parse_publish_time_handles_epoch_milliseconds():
    dt = parse_publish_time(1718674200000)
    assert dt.isoformat() == "2024-06-18T09:30:00+08:00"


def test_filter_today_videos_keeps_only_today_entries():
    videos = [
        {
            "video_id": "100",
            "video_url": "https://www.douyin.com/video/100",
            "published_at_raw": "2026-06-18T09:30:00+08:00",
        },
        {
            "video_id": "101",
            "video_url": "https://www.douyin.com/video/101",
            "published_at_raw": "2026-06-17T23:59:59+08:00",
        },
        {
            "video_id": "102",
            "video_url": "https://www.douyin.com/video/102",
            "published_at_raw": None,
        },
    ]

    filtered = filter_today_videos(videos, today=date(2026, 6, 18))

    assert [item["video_id"] for item in filtered] == ["100"]
    assert filtered[0]["published_at"] == "2026-06-18T09:30:00+08:00"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_douyin_author_feed.py -v`
Expected: `ModuleNotFoundError` 或 `ImportError`，因为 `scripts/douyin_author_feed.py` 尚不存在。

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from datetime import date, datetime
from typing import Iterable
from zoneinfo import ZoneInfo

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def parse_publish_time(raw_value):
    if raw_value is None:
        return None

    if isinstance(raw_value, (int, float)):
        timestamp = raw_value / 1000 if raw_value > 10**11 else raw_value
        return datetime.fromtimestamp(timestamp, tz=SHANGHAI_TZ)

    if isinstance(raw_value, str):
        text = raw_value.strip()
        if not text:
            return None
        if text.isdigit():
            return parse_publish_time(int(text))
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=SHANGHAI_TZ)
        return parsed.astimezone(SHANGHAI_TZ)

    return None


def filter_today_videos(videos: Iterable[dict], today: date | None = None):
    target_day = today or datetime.now(tz=SHANGHAI_TZ).date()
    filtered = []

    for video in videos:
        published_dt = parse_publish_time(video.get("published_at_raw"))
        if published_dt is None:
            continue
        if published_dt.date() != target_day:
            continue

        enriched = dict(video)
        enriched["published_at"] = published_dt.isoformat()
        filtered.append(enriched)

    return filtered
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_douyin_author_feed.py -v`
Expected: 2 tests `PASSED`。

- [ ] **Step 5: Commit**

```bash
git add tests/test_douyin_author_feed.py scripts/douyin_author_feed.py
git commit -m "test: cover author feed date filtering"
```

### Task 2: Processed State Store

**Files:**
- Create: `tests/test_douyin_state.py`
- Create: `scripts/douyin_state.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.douyin_state import ProcessedVideoStore


def test_store_defaults_to_unprocessed_for_unknown_video(tmp_path: Path):
    store = ProcessedVideoStore(tmp_path / "processed.json")
    assert store.is_processed("author-1", "video-1") is False


def test_store_marks_video_processed_after_recording(tmp_path: Path):
    store = ProcessedVideoStore(tmp_path / "processed.json")

    store.record_processed(
        author_id="author-1",
        video_id="video-1",
        video_url="https://www.douyin.com/video/1",
        published_at="2026-06-18T09:30:00+08:00",
        processed_at="2026-06-18T10:00:00+08:00",
    )

    reloaded = ProcessedVideoStore(tmp_path / "processed.json")
    assert reloaded.is_processed("author-1", "video-1") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_douyin_state.py -v`
Expected: `ModuleNotFoundError`，因为 `scripts/douyin_state.py` 尚不存在。

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

import json
from pathlib import Path


class ProcessedVideoStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = self._load()

    def _load(self):
        if not self.path.exists():
            return {"version": 1, "authors": {}}
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2, sort_keys=True)

    def is_processed(self, author_id: str, video_id: str) -> bool:
        author_bucket = self.data.get("authors", {}).get(author_id, {})
        videos = author_bucket.get("videos", {})
        return video_id in videos

    def record_processed(
        self,
        author_id: str,
        video_id: str,
        video_url: str,
        published_at: str,
        processed_at: str,
    ) -> None:
        authors = self.data.setdefault("authors", {})
        author_bucket = authors.setdefault(author_id, {"videos": {}})
        videos = author_bucket.setdefault("videos", {})
        videos[video_id] = {
            "video_id": video_id,
            "video_url": video_url,
            "published_at": published_at,
            "processed_at": processed_at,
        }
        self._save()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_douyin_state.py -v`
Expected: 2 tests `PASSED`。

- [ ] **Step 5: Commit**

```bash
git add tests/test_douyin_state.py scripts/douyin_state.py
git commit -m "test: add processed video state store"
```

### Task 3: Batch Runner Orchestration

**Files:**
- Create: `tests/test_run_daily_author_pipeline.py`
- Create: `scripts/run_daily_author_pipeline.py`
- Modify: `scripts/douyin_author_feed.py`
- Modify: `scripts/douyin_state.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from scripts.run_daily_author_pipeline import run_daily_pipeline


def test_run_daily_pipeline_processes_only_unprocessed_today_videos(tmp_path: Path):
    calls = []

    def fake_fetcher(_author_url):
        return [
            {
                "video_id": "100",
                "video_url": "https://www.douyin.com/video/100",
                "published_at_raw": "2026-06-18T09:30:00+08:00",
            },
            {
                "video_id": "101",
                "video_url": "https://www.douyin.com/video/101",
                "published_at_raw": "2026-06-18T11:00:00+08:00",
            },
        ]

    def fake_runner(video_url):
        calls.append(video_url)
        return 0

    exit_code = run_daily_pipeline(
        author_url="https://www.douyin.com/user/demo",
        author_id="author-demo",
        state_file=tmp_path / "processed.json",
        today="2026-06-18",
        fetch_videos=fake_fetcher,
        run_single_video=fake_runner,
    )

    assert exit_code == 0
    assert calls == [
        "https://www.douyin.com/video/100",
        "https://www.douyin.com/video/101",
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_run_daily_author_pipeline.py -v`
Expected: `ModuleNotFoundError` 或缺少 `run_daily_pipeline`。

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from scripts.douyin_author_feed import filter_today_videos, get_author_videos
from scripts.douyin_state import ProcessedVideoStore

DEFAULT_AUTHOR_URL = "https://www.douyin.com/user/MS4wLjABAAAAWGs2N4r_PbCH8uXi07DlK8G5T-dz2EA_bnoWb00V5BaR_-LdVLMDxIfqFbU8qbwX"
DEFAULT_AUTHOR_ID = "MS4wLjABAAAAWGs2N4r_PbCH8uXi07DlK8G5T-dz2EA_bnoWb00V5BaR_-LdVLMDxIfqFbU8qbwX"
DEFAULT_STATE_FILE = Path("data/processed_douyin_videos.json")


def _run_existing_pipeline(video_url: str) -> int:
    result = subprocess.run(
        [sys.executable, "scripts/run_pipeline.py", video_url],
        check=False,
    )
    return result.returncode


def run_daily_pipeline(
    author_url,
    author_id,
    state_file,
    today=None,
    fetch_videos=get_author_videos,
    run_single_video=_run_existing_pipeline,
):
    target_date = date.fromisoformat(today) if isinstance(today, str) else today
    store = ProcessedVideoStore(Path(state_file))
    all_videos = fetch_videos(author_url)
    today_videos = filter_today_videos(all_videos, today=target_date)

    failures = 0

    for video in today_videos:
        if store.is_processed(author_id, video["video_id"]):
            continue

        if run_single_video(video["video_url"]) != 0:
            failures += 1
            continue

        store.record_processed(
            author_id=author_id,
            video_id=video["video_id"],
            video_url=video["video_url"],
            published_at=video["published_at"],
            processed_at=datetime.now().astimezone().isoformat(),
        )

    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description="运行抖音博主每日批处理")
    parser.add_argument("--author-url", default=DEFAULT_AUTHOR_URL)
    parser.add_argument("--author-id", default=DEFAULT_AUTHOR_ID)
    parser.add_argument("--state-file", default=str(DEFAULT_STATE_FILE))
    args = parser.parse_args()

    sys.exit(
        run_daily_pipeline(
            author_url=args.author_url,
            author_id=args.author_id,
            state_file=Path(args.state_file),
        )
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_run_daily_author_pipeline.py -v`
Expected: `PASSED`。

- [ ] **Step 5: Expand test coverage before refactor**

```python
def test_run_daily_pipeline_skips_processed_videos(tmp_path: Path):
    def fake_fetcher(_author_url):
        return [
            {
                "video_id": "100",
                "video_url": "https://www.douyin.com/video/100",
                "published_at_raw": "2026-06-18T09:30:00+08:00",
            }
        ]

    calls = []

    def fake_runner(video_url):
        calls.append(video_url)
        return 0

    run_daily_pipeline(
        author_url="https://www.douyin.com/user/demo",
        author_id="author-demo",
        state_file=tmp_path / "processed.json",
        today="2026-06-18",
        fetch_videos=fake_fetcher,
        run_single_video=fake_runner,
    )
    run_daily_pipeline(
        author_url="https://www.douyin.com/user/demo",
        author_id="author-demo",
        state_file=tmp_path / "processed.json",
        today="2026-06-18",
        fetch_videos=fake_fetcher,
        run_single_video=fake_runner,
    )

    assert calls == ["https://www.douyin.com/video/100"]
```

- [ ] **Step 6: Run tests to verify the new coverage fails for the right reason**

Run: `pytest tests/test_run_daily_author_pipeline.py -v`
Expected: 如果跳过逻辑未生效则失败；否则通过，可直接进入下一步。

- [ ] **Step 7: Refine implementation if needed**

```python
def pending_today_videos(store, author_id, today_videos):
    return [
        video
        for video in today_videos
        if not store.is_processed(author_id, video["video_id"])
    ]
```

将 `run_daily_pipeline()` 内部循环前的待处理筛选提取为辅助函数，保证逻辑清晰，但不改变行为。

- [ ] **Step 8: Run the focused tests**

Run: `pytest tests/test_run_daily_author_pipeline.py -v`
Expected: 全部 `PASSED`。

- [ ] **Step 9: Commit**

```bash
git add tests/test_run_daily_author_pipeline.py scripts/run_daily_author_pipeline.py scripts/douyin_author_feed.py scripts/douyin_state.py
git commit -m "feat: add daily author pipeline runner"
```

### Task 4: Author Feed Fetching Integration

**Files:**
- Modify: `tests/test_douyin_author_feed.py`
- Modify: `scripts/douyin_author_feed.py`

- [ ] **Step 1: Write the failing test**

```python
from scripts.douyin_author_feed import extract_video_entries


def test_extract_video_entries_reads_aweme_list_payload():
    payload = {
        "aweme_list": [
            {
                "aweme_id": "100",
                "desc": "video 100",
                "create_time": 1781746200,
            }
        ]
    }

    videos = extract_video_entries(payload)

    assert videos == [
        {
            "video_id": "100",
            "video_url": "https://www.douyin.com/video/100",
            "title": "video 100",
            "published_at_raw": 1781746200,
        }
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_douyin_author_feed.py -v`
Expected: 缺少 `extract_video_entries`。

- [ ] **Step 3: Write minimal implementation**

```python
import json
import re
from urllib.parse import urlparse

import requests


def extract_author_id(author_url: str) -> str:
    return author_url.rstrip("/").split("/")[-1]


def extract_video_entries(payload: dict):
    videos = []
    for item in payload.get("aweme_list", []):
        video_id = str(item.get("aweme_id") or "").strip()
        if not video_id:
            continue
        videos.append(
            {
                "video_id": video_id,
                "video_url": f"https://www.douyin.com/video/{video_id}",
                "title": item.get("desc", ""),
                "published_at_raw": item.get("create_time"),
            }
        )
    return videos


def get_author_videos(author_url: str, session: requests.Session | None = None):
    http = session or requests.Session()
    response = http.get(author_url, timeout=20)
    response.raise_for_status()

    render_match = re.search(
        r'<script id="RENDER_DATA" type="application/json">(.*?)</script>',
        response.text,
        re.DOTALL,
    )
    if not render_match:
        raise RuntimeError("未找到博主页面视频数据")

    payload = json.loads(render_match.group(1))
    return extract_video_entries(payload if isinstance(payload, dict) else {})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_douyin_author_feed.py -v`
Expected: 新增测试 `PASSED`。

- [ ] **Step 5: Commit**

```bash
git add tests/test_douyin_author_feed.py scripts/douyin_author_feed.py
git commit -m "feat: parse daily author video entries"
```

### Task 5: GitHub Actions Daily Workflow

**Files:**
- Create: `.github/workflows/douyin_daily_author_pipeline.yml`
- Modify: `requirements.txt`
- Create: `data/.gitkeep`

- [ ] **Step 1: Write the failing test surrogate**

因为 GitHub Actions YAML 不适合直接做单元测试，这里使用一次本地语法检查替代红灯步骤。

```bash
python - <<'PY'
from pathlib import Path
import yaml

workflow = Path(".github/workflows/douyin_daily_author_pipeline.yml")
assert workflow.exists(), "workflow file missing"
yaml.safe_load(workflow.read_text(encoding="utf-8"))
PY
```

Expected: 因文件不存在而失败。

- [ ] **Step 2: Write minimal implementation**

```yaml
name: Douyin Daily Author Pipeline

on:
  schedule:
    - cron: "15 1 * * *"
  workflow_dispatch:

permissions:
  contents: write

env:
  PYTHON_VERSION: "3.11"

jobs:
  run_daily_pipeline:
    runs-on: ubuntu-latest

    steps:
      - name: checkout
        uses: actions/checkout@v4

      - name: python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: install system deps
        run: |
          sudo apt update
          sudo apt install -y ffmpeg git

      - name: install python deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install git+https://github.com/openai/whisper.git

      - name: prepare dirs
        run: |
          mkdir -p downloads segments news data

      - name: configure git
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"

      - name: run daily author pipeline
        env:
          QWEN_API_KEY: ${{ secrets.QWEN_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python scripts/run_daily_author_pipeline.py

      - name: push if changed
        run: |
          if [ -n "$(git status --porcelain)" ]; then
            git push origin HEAD:${GITHUB_REF_NAME}
          else
            echo "No changes to push"
          fi
```

同时在 `requirements.txt` 末尾新增：

```text
pytest
```

并创建：

```text
data/.gitkeep
```

- [ ] **Step 3: Run validation**

Run: `python - <<'PY' ... PY`
Expected: YAML 可解析，无异常。

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/douyin_daily_author_pipeline.yml requirements.txt data/.gitkeep
git commit -m "ci: add daily author workflow"
```

### Task 6: README and Final Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write the failing documentation check**

Run: `rg -n "run_daily_author_pipeline|每日批处理|processed_douyin_videos" README.md`
Expected: 搜不到新增说明。

- [ ] **Step 2: Update README**

在 `README.md` 增加以下内容：

```markdown
### 5. 每日批处理指定博主

```bash
python scripts/run_daily_author_pipeline.py
```

说明：

- 默认抓取固定抖音博主主页
- 只处理当天新发布且未处理的视频
- 使用 `data/processed_douyin_videos.json` 按 `video_id` 去重
- 单条视频仍然走现有 `scripts/run_pipeline.py`

### 6. GitHub Actions 定时任务

- 新增 `.github/workflows/douyin_daily_author_pipeline.yml`
- 支持每天定时执行
- 支持在 Actions 页面手动触发
```

- [ ] **Step 3: Run documentation check**

Run: `rg -n "run_daily_author_pipeline|每日批处理|processed_douyin_videos" README.md`
Expected: 至少命中 3 处新增内容。

- [ ] **Step 4: Run full test suite**

Run: `pytest tests -v`
Expected: 全部 `PASSED`。

- [ ] **Step 5: Run targeted script smoke test**

Run: `python scripts/run_daily_author_pipeline.py --help`
Expected: 打印命令行帮助并返回 0。

- [ ] **Step 6: Check git diff**

Run: `git status --short`
Expected: 只包含本次新增和修改文件。

- [ ] **Step 7: Commit**

```bash
git add README.md
git commit -m "docs: document daily author pipeline"
```

## Self-Review

- Spec coverage:
  - 新增每日批处理入口：Task 3
  - 抓取当天视频：Task 1、Task 4
  - 按 `video_id` 去重：Task 2、Task 3
  - 保留现有单视频方式：Task 3 通过调用现有 `run_pipeline.py`
  - GitHub Actions 定时任务：Task 5
  - README 更新：Task 6
- Placeholder scan:
  - 计划中没有 `TBD`、`TODO`、`implement later` 等占位词。
- Type consistency:
  - `video_id`、`video_url`、`published_at_raw`、`published_at`、`author_id` 在各任务中保持一致。

