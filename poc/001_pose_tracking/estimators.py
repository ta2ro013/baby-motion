"""姿勢推定器。出力を共通スキーマ（COCO 17点、ピクセル座標）に揃える。"""

import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision
from ultralytics import YOLO

from keypoints import MEDIAPIPE_TO_COCO

YOLO_WEIGHTS = "yolo26n-pose.pt"
MEDIAPIPE_MODEL = "pose_landmarker_heavy.task"
MEDIAPIPE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task"
)


class YoloPoseEstimator:
    """Ultralytics YOLO-pose による推定器。"""

    def __init__(self, models_dir: Path) -> None:
        """モデルを読み込む。無ければ models_dir に自動ダウンロードされる。

        Args:
            models_dir (Path): モデルファイルの保存先。
        """
        self._model = YOLO(str(models_dir / YOLO_WEIGHTS))

    def estimate(self, frame_bgr: np.ndarray, timestamp_ms: int) -> list[np.ndarray]:
        """1フレームの姿勢を推定する。

        Args:
            frame_bgr (np.ndarray): BGR 画像。
            timestamp_ms (int): フレームの時刻（未使用。インターフェースを揃えるため）。

        Returns:
            list[np.ndarray]: 検出された人物ごとの形状 (17, 3) の [x, y, confidence]。
        """
        result = self._model.predict(frame_bgr, verbose=False, device="cpu")[0]
        return list(result.keypoints.data.cpu().numpy().astype(float))

    def close(self) -> None:
        """リソースを解放する（YOLO は不要）。"""


class MediaPipePoseEstimator:
    """MediaPipe PoseLandmarker による推定器。"""

    def __init__(self, models_dir: Path) -> None:
        """モデルを読み込む。無ければ models_dir にダウンロードする。

        Args:
            models_dir (Path): モデルファイルの保存先。
        """
        model_path = models_dir / MEDIAPIPE_MODEL
        if not model_path.exists():
            urllib.request.urlretrieve(MEDIAPIPE_MODEL_URL, model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=2,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(options)

    def estimate(self, frame_bgr: np.ndarray, timestamp_ms: int) -> list[np.ndarray]:
        """1フレームの姿勢を推定する。

        Args:
            frame_bgr (np.ndarray): BGR 画像。
            timestamp_ms (int): フレームの時刻。呼び出しごとに増加している必要がある。

        Returns:
            list[np.ndarray]: 検出された人物ごとの形状 (17, 3) の [x, y, confidence]。
                confidence には MediaPipe の visibility を入れる。
        """
        height, width = frame_bgr.shape[:2]
        rgb = np.ascontiguousarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        return [
            np.array(
                [
                    [landmarks[i].x * width, landmarks[i].y * height, landmarks[i].visibility]
                    for i in MEDIAPIPE_TO_COCO
                ],
                dtype=float,
            )
            for landmarks in result.pose_landmarks
        ]

    def close(self) -> None:
        """ランドマーカーを閉じる。"""
        self._landmarker.close()


ESTIMATORS = {"yolo": YoloPoseEstimator, "mediapipe": MediaPipePoseEstimator}
