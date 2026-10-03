"""動作確認用の合成動画を data/ に作る。"""

from pathlib import Path

import cv2
import numpy as np
from ultralytics.utils import ASSETS

DATA_DIR = Path(__file__).parent / "data"


def write_video(path: Path, frames: list[np.ndarray], fps: float) -> None:
    """フレーム列を mp4 として書き出す。

    Args:
        path (Path): 出力先。
        frames (list[np.ndarray]): 同じサイズの BGR 画像。
        fps (float): フレームレート。
    """
    height, width = frames[0].shape[:2]
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    for frame in frames:
        writer.write(frame)
    writer.release()


def main() -> None:
    """人物ありと人物なしの動画を作る。"""
    image = cv2.imread(str(ASSETS / "bus.jpg"))
    person_frames = [image[:, x : x + 640].copy() for x in range(0, 170, 2)]
    write_video(DATA_DIR / "smoke_person.mp4", person_frames, 30.0)
    blank_frames = [np.zeros((480, 640, 3), np.uint8) for _ in range(60)]
    write_video(DATA_DIR / "smoke_blank.mp4", blank_frames, 30.0)
    print("wrote", sorted(p.name for p in DATA_DIR.glob("smoke_*.mp4")))


if __name__ == "__main__":
    main()
