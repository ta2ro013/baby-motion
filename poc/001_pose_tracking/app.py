"""PoC 001: 姿勢推定トラッキングの HTMX 画面。"""

import re
import shutil
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from estimators import ESTIMATORS
from jobs import JOBS, Job, list_summaries, load_summary, start_job
from pipeline import RUNS_DIR

ALLOWED_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}
RUN_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
METRIC_LABELS = [
    ("frames", "解析フレーム数"),
    ("duration_s", "長さ [秒]"),
    ("detection_rate", "検出率"),
    ("mean_confidence", "平均信頼度"),
    ("valid_keypoint_rate", "有効キーポイント率（信頼度 0.5 以上）"),
    ("gap_count", "途切れ回数"),
    ("longest_gap_s", "最長の途切れ [秒]"),
    ("jitter", "ジッタ（体サイズ比、小さいほど滑らか）"),
    ("multi_person_rate", "複数人が検出されたフレームの割合"),
    ("processing_fps", "推論速度 [フレーム/秒]"),
]

RUNS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()
app.mount("/runs-data", StaticFiles(directory=RUNS_DIR), name="runs-data")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.globals["METRIC_LABELS"] = METRIC_LABELS


def error_fragment(request: Request, message: str) -> HTMLResponse:
    """エラーメッセージのフラグメントを返す。"""
    return templates.TemplateResponse(
        request, "_status.html", {"run_id": "", "job": Job(status="error", error=message)}
    )


@app.get("/")
def index(request: Request) -> HTMLResponse:
    """アップロードフォームと過去の結果一覧を表示する。"""
    return templates.TemplateResponse(
        request, "index.html", {"runs": list_summaries(), "models": list(ESTIMATORS)}
    )


@app.post("/jobs")
def create_job(
    request: Request,
    video: UploadFile,
    target_fps: Annotated[int, Form()] = 15,
    models: Annotated[list[str], Form()] = [],
) -> HTMLResponse:
    """動画を保存して解析ジョブを開始し、進捗フラグメントを返す。"""
    suffix = Path(video.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        allowed = " / ".join(sorted(ALLOWED_SUFFIXES))
        return error_fragment(request, f"対応していない拡張子です（対応: {allowed}）")
    selected = [model for model in models if model in ESTIMATORS]
    if not selected:
        return error_fragment(request, "モデルを1つ以上選択してください")
    run_id = uuid.uuid4().hex
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True)
    video_path = run_dir / f"input{suffix}"
    with video_path.open("wb") as destination:
        shutil.copyfileobj(video.file, destination)
    start_job(
        run_id, video_path, video.filename or "(無題)", selected, min(max(target_fps, 1), 60)
    )
    return templates.TemplateResponse(
        request, "_status.html", {"run_id": run_id, "job": JOBS[run_id]}
    )


@app.get("/jobs/{run_id}/status")
def job_status(request: Request, run_id: str) -> HTMLResponse:
    """進捗フラグメントを返す。完了していれば結果フラグメントを返す。"""
    job = JOBS.get(run_id)
    if job is None:
        raise HTTPException(status_code=404)
    if job.status == "done":
        return templates.TemplateResponse(
            request, "_result.html", {"summary": load_summary(run_id)}
        )
    return templates.TemplateResponse(request, "_status.html", {"run_id": run_id, "job": job})


@app.get("/runs/{run_id}")
def show_run(request: Request, run_id: str) -> HTMLResponse:
    """保存済みの結果を1ページで表示する。"""
    summary = load_summary(run_id) if RUN_ID_PATTERN.match(run_id) else None
    if summary is None:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(request, "run.html", {"summary": summary})
