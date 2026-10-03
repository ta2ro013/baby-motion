"""追跡結果のグラフを PNG で保存する。"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from keypoints import CONFIDENCE_THRESHOLD, KEYPOINT_NAMES  # noqa: E402
from metrics import body_scale, masked_xy  # noqa: E402

LIMB_NAMES = ["left_wrist", "right_wrist", "left_ankle", "right_ankle"]


def save_confidence_plot(track: np.ndarray, fps: float, path: Path) -> None:
    """フレームごとの平均信頼度と未検出区間のグラフを保存する。

    Args:
        track (np.ndarray): 形状 (T, 17, 3)。
        fps (float): track のフレームレート。
        path (Path): 出力先 PNG。
    """
    times = np.arange(len(track)) / fps
    confidence = track[:, :, 2]
    detected = ~np.isnan(confidence).all(axis=1)
    mean_confidence = np.where(
        detected, np.nansum(confidence, axis=1) / confidence.shape[1], np.nan
    )
    figure, axis = plt.subplots(figsize=(8, 3))
    axis.plot(times, mean_confidence, label="mean keypoint confidence")
    axis.fill_between(
        times, 0, 1, where=~detected, color="red", alpha=0.2, label="no detection"
    )
    axis.axhline(CONFIDENCE_THRESHOLD, color="gray", linestyle="--", linewidth=0.8)
    axis.set_ylim(0, 1)
    axis.set_xlabel("time [s]")
    axis.set_ylabel("confidence")
    axis.legend(loc="lower right")
    figure.tight_layout()
    figure.savefig(path, dpi=100)
    plt.close(figure)


def save_speed_plot(track: np.ndarray, fps: float, path: Path) -> None:
    """手首・足首の速度（体サイズ/秒）のグラフを保存する。

    Args:
        track (np.ndarray): 形状 (T, 17, 3)。
        fps (float): track のフレームレート。
        path (Path): 出力先 PNG。
    """
    xy = masked_xy(track)
    scale = body_scale(xy)
    figure, axis = plt.subplots(figsize=(8, 3))
    if scale is None or len(xy) < 2:
        axis.text(0.5, 0.5, "no valid keypoints", ha="center", va="center")
    else:
        times = np.arange(1, len(xy)) / fps
        speed = np.linalg.norm(np.diff(xy, axis=0), axis=2) * fps / scale
        for name in LIMB_NAMES:
            axis.plot(times, speed[:, KEYPOINT_NAMES.index(name)], label=name, linewidth=0.9)
        axis.legend(loc="upper right", ncol=2)
    axis.set_xlabel("time [s]")
    axis.set_ylabel("speed [body size / s]")
    figure.tight_layout()
    figure.savefig(path, dpi=100)
    plt.close(figure)
