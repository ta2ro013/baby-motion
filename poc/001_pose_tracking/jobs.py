"""解析ジョブのバックグラウンド実行と、結果サマリーの読み書き。"""

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pipeline import RUNS_DIR, run_model

logger = logging.getLogger("pose-tracking")


@dataclass
class Job:
    """実行中ジョブの状態。

    Attributes:
        status (str): "running" / "done" / "error"。
        progress (str): 画面に出す進捗メッセージ。
        error (str): 失敗時のメッセージ。
    """

    status: str = "running"
    progress: str = "準備中"
    error: str = ""


JOBS: dict[str, Job] = {}


def start_job(
    run_id: str, video_path: Path, original_name: str, models: list[str], target_fps: int
) -> None:
    """解析ジョブを別スレッドで開始する。

    Args:
        run_id (str): 実行 ID。結果は RUNS_DIR / run_id に保存される。
        video_path (Path): 保存済みの入力動画。
        original_name (str): アップロード時のファイル名（表示用）。
        models (list[str]): 実行するモデル名。
        target_fps (int): 解析するフレームレートの目標。
    """
    JOBS[run_id] = Job()
    threading.Thread(
        target=_run, args=(run_id, video_path, original_name, models, target_fps), daemon=True
    ).start()


def _run(
    run_id: str, video_path: Path, original_name: str, models: list[str], target_fps: int
) -> None:
    """モデルを順に実行し、summary.json を書く。失敗はジョブ状態に記録する。"""
    job = JOBS[run_id]
    run_dir = RUNS_DIR / run_id
    try:
        results = {}
        for model in models:

            def on_progress(done: int, total: int, model: str = model) -> None:
                job.progress = f"{model}: {done} / 約{total} フレーム"

            job.progress = f"{model}: モデルを読み込み中"
            results[model] = run_model(video_path, model, run_dir / model, target_fps, on_progress)
        summary = {
            "run_id": run_id,
            "video": original_name,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "target_fps": target_fps,
            "models": results,
        }
        (run_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        job.status = "done"
    except Exception as error:  # noqa: BLE001 スレッド内の失敗を画面に出すため
        logger.exception("pose-tracking.run run_id=%s", run_id)
        job.error = str(error) or type(error).__name__
        job.status = "error"


def load_summary(run_id: str) -> dict | None:
    """保存済みの結果サマリーを読む。

    Args:
        run_id (str): 実行 ID。

    Returns:
        dict | None: summary.json の内容。無ければ None。
    """
    path = RUNS_DIR / run_id / "summary.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_summaries() -> list[dict]:
    """保存済みの結果サマリーを新しい順に返す。

    Returns:
        list[dict]: summary.json の内容のリスト。
    """
    summaries = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in RUNS_DIR.glob("*/summary.json")
    ]
    return sorted(summaries, key=lambda summary: summary["created_at"], reverse=True)
