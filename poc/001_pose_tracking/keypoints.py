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
MIN_VALID_KEYPOINTS = 5
MAX_JUMP_BODY_SIZES = 1.0


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


def person_size(person: np.ndarray) -> float:
    """人物の大きさ（有効キーポイントの外接矩形の対角線）を返す。

    Args:
        person (np.ndarray): 形状 (17, 3) の [x, y, confidence]。

    Returns:
        float: ピクセル単位の大きさ。
    """
    valid = person[person[:, 2] >= CONFIDENCE_THRESHOLD]
    points = valid if len(valid) else person
    extent = points[:, :2].max(axis=0) - points[:, :2].min(axis=0)
    return float(np.hypot(extent[0], extent[1]))


def usable_persons(persons: list[np.ndarray]) -> list[np.ndarray]:
    """有効キーポイントが MIN_VALID_KEYPOINTS 点以上ある人物だけを返す。

    布団のしわなど、枠だけ検出されて関節が取れていないものを「検出」に数えないため。

    Args:
        persons (list[np.ndarray]): 各要素が形状 (17, 3) の人物。

    Returns:
        list[np.ndarray]: 使える人物のリスト。
    """
    return [
        person
        for person in persons
        if int((person[:, 2] >= CONFIDENCE_THRESHOLD).sum()) >= MIN_VALID_KEYPOINTS
    ]


class TargetTracker:
    """フレームをまたいで追跡対象を1人選び続ける。

    最初は平均信頼度が最大の人物を選ぶ。以降は前回の中心に最も近い人物を選ぶが、
    前回の体サイズ × MAX_JUMP_BODY_SIZES より遠い場合は別人とみなし未検出にする。
    max_lost_frames を超えて見失った後に見つかった場合は選び直し、reset_count を増やす。

    Attributes:
        reset_count (int): 見失った後に対象を選び直した回数。
    """

    def __init__(self, max_lost_frames: int) -> None:
        """追跡状態を初期化する。

        Args:
            max_lost_frames (int): この数を超えて連続で見失ったら選び直す。
        """
        self.reset_count = 0
        self._max_lost_frames = max_lost_frames
        self._center: np.ndarray | None = None
        self._size = 0.0
        self._lost = 0

    def update(self, persons: list[np.ndarray]) -> np.ndarray | None:
        """1フレーム分の検出結果から追跡対象を選ぶ。

        Args:
            persons (list[np.ndarray]): usable_persons を通した人物のリスト。

        Returns:
            np.ndarray | None: 追跡対象。見つからなければ None。
        """
        if not persons:
            self._lost += 1
            return None
        if self._center is None or self._lost > self._max_lost_frames:
            if self._center is not None:
                self.reset_count += 1
            target = max(persons, key=lambda person: float(person[:, 2].mean()))
        else:
            center = self._center
            target = min(
                persons,
                key=lambda person: float(np.linalg.norm(person_center(person) - center)),
            )
            distance = float(np.linalg.norm(person_center(target) - center))
            if distance > MAX_JUMP_BODY_SIZES * self._size:
                self._lost += 1
                return None
        self._center = person_center(target)
        self._size = person_size(target)
        self._lost = 0
        return target
