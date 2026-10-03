"""共通キーポイントスキーマ（COCO 17点）と追跡対象の選択。"""

import numpy as np

KEYPOINT_NAMES = [
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]

SKELETON_EDGES = [
    (0, 1), (0, 2), (1, 3), (2, 4),
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16),
]

# MediaPipe の33点のうち、COCO 17点に対応するインデックス（KEYPOINT_NAMES と同じ順）。
MEDIAPIPE_TO_COCO = [0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]

CONFIDENCE_THRESHOLD = 0.5


def person_center(person: np.ndarray) -> np.ndarray:
    """人物の中心座標を返す。

    信頼度がしきい値以上のキーポイントの平均。1点もなければ全点の平均。

    Args:
        person (np.ndarray): 形状 (17, 3) の [x, y, confidence]。

    Returns:
        np.ndarray: 形状 (2,) の [x, y]。
    """
    valid = person[person[:, 2] >= CONFIDENCE_THRESHOLD]
    points = valid if len(valid) else person
    return points[:, :2].mean(axis=0)


def select_target(
    persons: list[np.ndarray], previous_center: np.ndarray | None
) -> np.ndarray | None:
    """検出された人物の中から追跡対象を1人選ぶ。

    前フレームの中心が無ければ平均信頼度が最大の人物、
    あれば前フレームの中心に最も近い人物を選ぶ。

    Args:
        persons (list[np.ndarray]): 各要素が形状 (17, 3) の人物。
        previous_center (np.ndarray | None): 前回選んだ人物の中心。

    Returns:
        np.ndarray | None: 選ばれた人物。persons が空なら None。
    """
    if not persons:
        return None
    if previous_center is None:
        return max(persons, key=lambda person: float(person[:, 2].mean()))
    return min(
        persons,
        key=lambda person: float(np.linalg.norm(person_center(person) - previous_center)),
    )
