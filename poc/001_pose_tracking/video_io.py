"""動画の読み込みと書き出し。"""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

DEFAULT_FPS = 30.0
MAX_REASONABLE_FPS = 240.0


@dataclass
class VideoInfo:
    """動画のメタデータ。

    Attributes:
        fps (float): フレームレート。
        frame_count (int): 総フレーム数（メタデータ由来の概算）。
    """

    fps: float
    frame_count: int


def open_video(path: Path) -> tuple[cv2.VideoCapture, VideoInfo]:
    """動画を開く。

    回転メタデータ（iPhone の縦撮りなど）は OpenCV が自動で適用する。

    Args:
        path (Path): 動画ファイル。

    Returns:
        tuple[cv2.VideoCapture, VideoInfo]: キャプチャとメタデータ。

    Raises:
        ValueError: 動画として開けない場合。
    """
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError("動画を開けませんでした（対応していない形式か、壊れている可能性があります）")
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not 0 < fps <= MAX_REASONABLE_FPS:
        fps = DEFAULT_FPS
    return capture, VideoInfo(fps=fps, frame_count=int(capture.get(cv2.CAP_PROP_FRAME_COUNT)))


def resize_to_max_side(frame: np.ndarray, max_side: int) -> np.ndarray:
    """長辺が max_side 以下、かつ幅・高さが偶数になるよう縮小する。

    Args:
        frame (np.ndarray): BGR 画像。
        max_side (int): 長辺の上限ピクセル数。

    Returns:
        np.ndarray: 縮小後の画像（縮小不要ならそのまま）。
    """
    height, width = frame.shape[:2]
    scale = min(1.0, max_side / max(height, width))
    new_width = max(2, int(width * scale) // 2 * 2)
    new_height = max(2, int(height * scale) // 2 * 2)
    if (new_width, new_height) == (width, height):
        return frame
    return cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)


def iter_frames(
    capture: cv2.VideoCapture, stride: int, max_side: int
) -> Iterator[tuple[int, np.ndarray]]:
    """stride フレームごとに1枚、縮小したフレームを返す。

    Args:
        capture (cv2.VideoCapture): 開いた動画。
        stride (int): 何フレームごとに1枚取り出すか。
        max_side (int): 長辺の上限ピクセル数。

    Yields:
        tuple[int, np.ndarray]: 元動画でのフレーム番号と BGR 画像。
    """
    index = 0
    while capture.grab():
        if index % stride == 0:
            ok, frame = capture.retrieve()
            if not ok:
                break
            yield index, resize_to_max_side(frame, max_side)
        index += 1


def create_writer(path: Path, fps: float, width: int, height: int) -> cv2.VideoWriter:
    """ブラウザで再生できる VP9 / WebM のライターを作る。

    Args:
        path (Path): 出力先（.webm）。
        fps (float): フレームレート。
        width (int): 幅。
        height (int): 高さ。

    Returns:
        cv2.VideoWriter: 開いたライター。

    Raises:
        RuntimeError: ライターを開けない場合。
    """
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"VP90"), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError("オーバーレイ動画の書き出しを開始できませんでした")
    return writer
