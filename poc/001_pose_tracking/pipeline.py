"""1つの動画を1つのモデルで解析し、結果ファイルを保存する。"""

import json
import time
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from estimators import ESTIMATORS
from keypoints import (
    CONFIDENCE_THRESHOLD,
    KEYPOINT_NAMES,
    SKELETON_EDGES,
    person_center,
    select_target,
)
from metrics import compute_metrics
from plots import save_confidence_plot, save_speed_plot
from video_io import create_writer, iter_frames, open_video

DATA_DIR = Path(__file__).parent / "data"
MODELS_DIR = DATA_DIR / "models"
RUNS_DIR = DATA_DIR / "runs"
MAX_SIDE = 960

# BGR。左右の入れ替わりを目視で見つけやすいよう、左右で色を分ける。
COLOR_LEFT = (0, 165, 255)
COLOR_RIGHT = (255, 128, 0)
COLOR_CENTER = (0, 220, 0)
COLOR_BONE = (255, 255, 255)
COLOR_WARNING = (0, 0, 255)


def keypoint_color(index: int) -> tuple[int, int, int]:
    """キーポイントの描画色を返す（鼻=緑、左=オレンジ、右=青）。"""
    if index == 0:
        return COLOR_CENTER
    return COLOR_LEFT if KEYPOINT_NAMES[index].startswith("left") else COLOR_RIGHT


def draw_overlay(frame: np.ndarray, person: np.ndarray | None) -> np.ndarray:
    """フレームに骨格を描いた画像を返す。

    Args:
        frame (np.ndarray): BGR 画像。
        person (np.ndarray | None): 形状 (17, 3) の追跡対象。未検出なら None。

    Returns:
        np.ndarray: 描画済みの画像（元の frame は変更しない）。
    """
    canvas = frame.copy()
    if person is None:
        cv2.putText(
            canvas, "NO DETECTION", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLOR_WARNING, 2
        )
        return canvas
    valid = person[:, 2] >= CONFIDENCE_THRESHOLD
    points = person[:, :2].round().astype(int)
    for start, end in SKELETON_EDGES:
        if valid[start] and valid[end]:
            cv2.line(canvas, tuple(points[start]), tuple(points[end]), COLOR_BONE, 2)
    for index in range(len(KEYPOINT_NAMES)):
        if valid[index]:
            cv2.circle(canvas, tuple(points[index]), 4, keypoint_color(index), -1)
    return canvas


def save_keypoints_csv(track: np.ndarray, fps: float, path: Path) -> None:
    """追跡結果を縦持ちの CSV（frame, time_s, keypoint, x, y, confidence）で保存する。

    Args:
        track (np.ndarray): 形状 (T, 17, 3)。
        fps (float): track のフレームレート。
        path (Path): 出力先 CSV。
    """
    frames = track.shape[0]
    count = len(KEYPOINT_NAMES)
    table = pd.DataFrame(
        {
            "frame": np.repeat(np.arange(frames), count),
            "time_s": np.repeat(np.arange(frames) / fps, count).round(3),
            "keypoint": KEYPOINT_NAMES * frames,
            "x": track[:, :, 0].ravel().round(1),
            "y": track[:, :, 1].ravel().round(1),
            "confidence": track[:, :, 2].ravel().round(3),
        }
    )
    table.to_csv(path, index=False)


def run_model(
    video_path: Path,
    model_name: str,
    out_dir: Path,
    target_fps: int,
    on_progress: Callable[[int, int], None],
) -> dict:
    """動画を1つのモデルで解析し、結果ファイルを out_dir に保存する。

    Args:
        video_path (Path): 入力動画。
        model_name (str): ESTIMATORS のキー（"yolo" / "mediapipe"）。
        out_dir (Path): 出力ディレクトリ。
        target_fps (int): 解析するフレームレートの目標。元動画をこの値に近づくよう間引く。
        on_progress (Callable[[int, int], None]): (処理済みフレーム数, 概算の総数) を受け取る。

    Returns:
        dict: compute_metrics の指標。

    Raises:
        ValueError: 動画を開けない、またはフレームを1枚も読めない場合。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    capture, info = open_video(video_path)
    stride = max(1, round(info.fps / target_fps))
    out_fps = info.fps / stride
    total = max(1, info.frame_count // stride)
    estimator = None
    writer = None
    rows: list[np.ndarray] = []
    person_counts: list[int] = []
    previous_center = None
    inference_seconds = 0.0
    try:
        estimator = ESTIMATORS[model_name](MODELS_DIR)
        for index, frame in iter_frames(capture, stride, MAX_SIDE):
            started = time.perf_counter()
            persons = estimator.estimate(frame, int(index * 1000 / info.fps))
            inference_seconds += time.perf_counter() - started
            target = select_target(persons, previous_center)
            if target is not None:
                previous_center = person_center(target)
            rows.append(target if target is not None else np.full((17, 3), np.nan))
            person_counts.append(len(persons))
            if writer is None:
                height, width = frame.shape[:2]
                writer = create_writer(out_dir / "overlay.webm", out_fps, width, height)
            writer.write(draw_overlay(frame, target))
            on_progress(len(rows), total)
    finally:
        capture.release()
        if estimator is not None:
            estimator.close()
        if writer is not None:
            writer.release()
    if not rows:
        raise ValueError("動画からフレームを読み取れませんでした")
    track = np.stack(rows)
    save_keypoints_csv(track, out_fps, out_dir / "keypoints.csv")
    save_confidence_plot(track, out_fps, out_dir / "confidence.png")
    save_speed_plot(track, out_fps, out_dir / "speed.png")
    metrics = compute_metrics(track, out_fps, inference_seconds, person_counts)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
