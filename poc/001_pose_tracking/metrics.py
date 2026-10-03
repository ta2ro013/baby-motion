"""追跡結果から自動指標を計算する。"""

import warnings

import numpy as np

from keypoints import CONFIDENCE_THRESHOLD, KEYPOINT_NAMES


def masked_xy(track: np.ndarray) -> np.ndarray:
    """信頼度がしきい値未満の座標を NaN にした xy を返す。

    Args:
        track (np.ndarray): 形状 (T, 17, 3)。未検出フレームは NaN。

    Returns:
        np.ndarray: 形状 (T, 17, 2)。
    """
    valid = np.nan_to_num(track[:, :, 2], nan=0.0) >= CONFIDENCE_THRESHOLD
    return np.where(valid[:, :, None], track[:, :, :2], np.nan)


def body_scale(xy: np.ndarray) -> float | None:
    """体の大きさの代表値（有効キーポイントの外接矩形の対角線の中央値）を返す。

    Args:
        xy (np.ndarray): masked_xy の出力。

    Returns:
        float | None: ピクセル単位の体サイズ。算出できなければ None。
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        extent = np.nanmax(xy, axis=1) - np.nanmin(xy, axis=1)
        scale = float(np.nanmedian(np.hypot(extent[:, 0], extent[:, 1])))
    return scale if np.isfinite(scale) and scale > 0 else None


def _ratio(numerator: float, denominator: float) -> float | None:
    """割合を小数3桁で返す。分母が0なら None。"""
    return round(float(numerator) / float(denominator), 3) if denominator else None


def _gap_lengths(detected: np.ndarray) -> list[int]:
    """未検出が連続した区間の長さ（フレーム数）を列挙する。"""
    gaps: list[int] = []
    run = 0
    for flag in detected:
        if flag:
            if run:
                gaps.append(run)
            run = 0
        else:
            run += 1
    if run:
        gaps.append(run)
    return gaps


def _jitter(xy: np.ndarray) -> float | None:
    """キーポイントのブレを返す。

    位置の2階差分（加速度）の大きさの中央値を体サイズで割った値。
    滑らかな動きでは小さく、フレームごとに点が跳ねると大きくなる。
    """
    scale = body_scale(xy)
    if scale is None or len(xy) < 3:
        return None
    acceleration = np.linalg.norm(xy[2:] - 2 * xy[1:-1] + xy[:-2], axis=2)
    if np.isnan(acceleration).all():
        return None
    return round(float(np.nanmedian(acceleration)) / scale, 4)


def compute_metrics(
    track: np.ndarray,
    fps: float,
    inference_seconds: float,
    person_counts: list[int],
    target_reset_count: int,
) -> dict:
    """追跡結果の自動指標を計算する。

    Args:
        track (np.ndarray): 形状 (T, 17, 3)。未検出フレームは NaN。T は1以上。
        fps (float): track のフレームレート（間引き後）。
        inference_seconds (float): 推論にかかった合計秒数。
        person_counts (list[int]): 各フレームで検出された人数（有効キーポイントが足りる人物のみ）。
        target_reset_count (int): 見失った後に追跡対象を選び直した回数。

    Returns:
        dict: 指標。算出できない値は None。
    """
    frames = int(track.shape[0])
    confidence = track[:, :, 2]
    detected = ~np.isnan(confidence).all(axis=1)
    valid = np.nan_to_num(confidence, nan=0.0) >= CONFIDENCE_THRESHOLD
    gaps = _gap_lengths(detected)
    return {
        "frames": frames,
        "duration_s": round(frames / fps, 2),
        "detection_rate": _ratio(detected.sum(), frames),
        "mean_confidence": (
            round(float(np.nanmean(confidence[detected])), 3) if detected.any() else None
        ),
        "valid_keypoint_rate": _ratio(valid.sum(), valid.size),
        "gap_count": len(gaps),
        "longest_gap_s": round(max(gaps, default=0) / fps, 2),
        "jitter": _jitter(masked_xy(track)),
        "target_reset_count": target_reset_count,
        "multi_person_rate": _ratio(sum(count >= 2 for count in person_counts), frames),
        "processing_fps": (
            round(frames / inference_seconds, 1) if inference_seconds > 0 else None
        ),
        "per_keypoint_valid_rate": {
            name: _ratio(valid[:, index].sum(), frames)
            for index, name in enumerate(KEYPOINT_NAMES)
        },
    }
