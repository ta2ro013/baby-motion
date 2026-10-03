# PoC 001: 赤ちゃん動画の姿勢推定トラッキング 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **この計画は PoC である。** `CLAUDE.md` の PoC ルールに従い、TDD と品質チェック（test / lint / format / typecheck）は行わない。各タスクは「書く → 実行して確認 → コミット」で進める。

**Goal:** 赤ちゃんの動画をアップロードすると、2つの姿勢推定モデルでキーポイントを時系列追跡し、骨格オーバーレイ動画・グラフ・指標を並べて見られる HTMX 画面を作り、「実動画で姿勢推定が使い物になるか」を判定する。

**Architecture:** FastAPI + HTMX のローカル Web アプリ。アップロードされた動画をバックグラウンドスレッドで解析し、モデルごとの結果（オーバーレイ動画・CSV・グラフ・指標 JSON）を `data/runs/<run_id>/` に保存、HTMX のポーリングで進捗と結果を表示する。YOLO-pose と MediaPipe の出力は共通スキーマ（COCO 17点）に正規化し、同じ指標・同じ描画で比較する。

**Tech Stack:** Python 3.12 / uv / FastAPI / Jinja2 / HTMX 2 / OpenCV 5 / Ultralytics YOLO26n-pose / MediaPipe 1.0 PoseLandmarker (heavy) / pandas / matplotlib

**Spec:** `docs/plans/20261003-01-basic-policy.md`（「PoC の流れ」: 動画 → フレーム抽出 → 姿勢推定 → キーポイント追跡 → 動きの特徴量 → 可視化）

---

## 目的・背景

`baby-motion` の中核は「赤ちゃんの動画 → 姿勢推定 → モーショントラッキング」である。
しかし一般的な姿勢推定モデルは大人の立位を中心に学習されており、赤ちゃん（頭身が違う・寝ている・寝返りで体が重なる・布団や服で隠れる）で十分に動くかは分からない。

バックエンドや iPhone アプリを作り込む前に、**自分の実動画で姿勢推定がどの程度の信頼性で機能するか**を確認し、次フェーズ（モーション解析）へ進めるか、モデルを変えるべきかを判断する材料を得る。

## 問題・解決方法

### 採用

| 項目 | 採用した方法 | 理由 |
| --- | --- | --- |
| 検証データ | ユーザー自身の実動画（git 管理外） | 実際の撮影条件（角度・服・布団）で評価しないと結論が信頼できない |
| モデル | YOLO26n-pose と MediaPipe PoseLandmarker(heavy) の比較 | 1モデルだけだと「ダメだった」ときに原因（モデル固有か、赤ちゃん動画全般か）を切り分けられない |
| 共通スキーマ | COCO 17点（MediaPipe の33点から対応する17点を抜粋） | 同じ指標・同じ描画コードで公平に比較するため |
| 評価 | 自動指標（検出率・信頼度・途切れ・ジッタ・処理速度）+ オーバーレイ動画の目視 | 正解ラベル作成なしで、定量的な比較基準を残せる |
| 操作形態 | HTMX 画面のみ（アップロード → 進捗 → 結果） | PoC 技術スタックの方針どおり。「動画を受け取る」流れも確認できる |
| 追跡対象の選択 | 最初は平均信頼度が最大の人物、以降は前フレームの中心に最も近い人物 | 親の手や体が映り込んでも対象が飛びにくい。両モデル共通のロジックにできる |
| 出力動画 | VP9 / WebM（OpenCV で直接書き出し） | この環境で動作確認済み。ブラウザでそのまま再生できる |
| PyTorch | CPU 版ホイール（`download.pytorch.org/whl/cpu`） | GPU がなく、CUDA 同梱版は数 GB の無駄なダウンロードになる |

### 棄却

| 棄却した案 | 理由 |
| --- | --- |
| Apple Vision（オンデバイス推論） | Mac / Xcode が必要で現在の WSL2 環境では実行不可。必要なら別 PoC（002）に分ける |
| MoveNet | TensorFlow 依存が増える。まず2モデルで傾向を掴んでから検討する |
| 乳児特化モデル・ファインチューニング | ベースラインの結果を見る前に着手するのは時期尚早 |
| 手動アノテーションによる精度測定（PCK 等） | 作業が重く最初の PoC には過剰。自動指標+目視で不足した場合に検討する |
| CLI バッチ | ユーザー判断により HTMX 画面のみとする |
| H.264 / MP4 での出力 | `opencv-python` に H.264 エンコーダが含まれず、`ffmpeg` も未インストール（確認済み） |
| Ultralytics 内蔵トラッカー（ByteTrack） | MediaPipe 側に同等機能がなく、比較条件が揃わない |

### 留意事項

- **ライセンス:** Ultralytics は AGPL-3.0。PoC での利用は問題ないが、製品に組み込む場合はライセンス（商用ライセンス購入 or 別モデル）の検討が必要。MediaPipe は Apache-2.0。結果の「課題」に必ず記載する。
- **信頼度の意味の違い:** YOLO の keypoint confidence と MediaPipe の `visibility` は定義が異なる。モデル間で信頼度の絶対値を直接比べず、目視と合わせて判断する。

## 完了条件（DoD）

- ブラウザで動画（`.mp4` / `.mov` / `.m4v` / `.webm`）をアップロードすると、進捗表示のあと、両モデルの骨格オーバーレイ動画・グラフ・指標比較表が表示される
- 人物が映っていない動画、動画でないファイル、対応外の拡張子でもアプリが落ちず、画面に結果またはエラーが表示される
- 実動画 3〜5 本（下記「撮影条件」）で解析を実行し、`poc/001_pose_tracking/README.md` の「結果」に指標と目視所見が記入されている
- README の「結果」に、暫定判定基準に照らした**結論（次フェーズへ進む / モデルを再検討する）**が書かれている
- 実動画・解析結果・モデルファイルが git にコミットされていない

**暫定判定基準**（PoC 開始時点の仮置き。結果を見て妥当性も評価する）

| 指標 | 「使える」とみなす目安 |
| --- | --- |
| 検出率 | 90% 以上 |
| 有効キーポイント率（信頼度 0.5 以上） | 70% 以上 |
| 最長の途切れ | 1.0 秒以下 |
| 目視 | 寝返り中も骨格が大きく破綻しない・左右が入れ替わり続けない・対象が親に移らない |

**撮影条件**（各 10〜30 秒、真上または斜め上から全身が映るもの）

1. 仰向けで手足を動かしている
2. 寝返り（仰向け → うつ伏せ）
3. うつ伏せ
4. 親の手や体が映り込む
5. （任意）暗め・柄物の布団など条件が悪いもの

## 実装方針

### Global Constraints

- 作業ブランチは `poc/pose-tracking`。`main` へ直接コミットしない。
- Python の実行・依存追加はすべて uv 経由（`uv run` / `uv add`）。`python` / `pip` を直接実行しない。
- コマンドはすべて `poc/` ディレクトリで実行する（`poc/pyproject.toml` が PoC 共通のプロジェクト定義）。
- コードは `poc/001_pose_tracking/` 配下のみ。`backend/` `frontend/` には触れない。
- 実動画・解析結果・モデルファイルは `poc/001_pose_tracking/data/` 配下に置き、コミットしない。
- サーバーは `127.0.0.1` のみで待ち受ける。動画を外部サービスへ送信しない。
- 関数・クラスには Google スタイルの docstring を書く。グラフ内の文字は英語（matplotlib に日本語フォントがないため）。
- デザインは簡易でよい。

### 事前に確認済みの事実（2026-10-03、この環境）

| 事実 | 影響 |
| --- | --- |
| 依存は Python 3.12 で解決できる（mediapipe 1.0.1 / ultralytics 8.4.171 / opencv-python 5.0.0 / torch 2.14.1+cpu / numpy 2.5.3） | Task 1 の `pyproject.toml` はそのまま通る |
| MediaPipe は `libGLESv2.so.2` がないと `OSError` で起動しない。この環境には未インストール | Task 1 で `sudo apt install -y libgles2` が必要（**ユーザーが実行**） |
| `yolo26n-pose.pt` は `YOLO("<path>")` で指定パスへ自動ダウンロードされる。出力は `result.keypoints.data` = `(人数, 17, 3)`、0人なら `(0, 17, 3)` | 推定器の実装 |
| MediaPipe の `detect_for_video` は 0人なら `pose_landmarks == []`。landmark は `x, y`（0〜1 正規化）と `visibility` を持つ | 推定器の実装 |
| OpenCV の `VP90` + `.webm` は書き出せる（「tag is not supported」という警告が出るが無害） | 出力動画 |
| 処理時間の目安（CPU）: YOLO 約 20ms/フレーム、MediaPipe heavy 約 50ms/フレーム、VP9 書き出し 約 75ms/フレーム（960x540） | 30秒動画を 15fps で両モデル解析して 2 分前後 |

### ファイル構成

```
poc/
├── pyproject.toml                  # 変更: 依存追加、PyTorch CPU インデックス
└── 001_pose_tracking/
    ├── README.md                   # 検証概要 / 詳細 / 評価方法 / 結果 / 課題
    ├── data/                       # git 管理外（.gitkeep のみコミット）
    │   ├── models/                 #   モデルファイル（自動ダウンロード）
    │   └── runs/<run_id>/          #   input.<ext>, summary.json, <model>/{overlay.webm, keypoints.csv, confidence.png, speed.png, metrics.json}
    ├── keypoints.py                # 共通スキーマ（COCO 17点）と追跡対象の選択
    ├── estimators.py               # YOLO / MediaPipe 推定器（共通インターフェース）
    ├── video_io.py                 # 動画の読み込み・リサイズ・WebM 書き出し
    ├── metrics.py                  # 自動指標の計算（純粋関数）
    ├── plots.py                    # 信頼度・速度グラフの保存
    ├── pipeline.py                 # 1動画 × 1モデルの解析
    ├── jobs.py                     # バックグラウンド実行と結果の読み書き
    ├── app.py                      # FastAPI ルート
    ├── make_smoke_videos.py        # 動作確認用の合成動画を作る
    └── templates/
        ├── base.html
        ├── index.html
        ├── run.html
        ├── _status.html
        └── _result.html
```

### データフロー

```text
[ブラウザ] --POST /jobs (動画)--> app.py --> jobs.start_job (スレッド)
                                              └─ モデルごとに pipeline.run_model
                                                   video_io.iter_frames → estimators.estimate
                                                   → keypoints.select_target → オーバーレイ描画
                                                   → metrics / plots / CSV → data/runs/<run_id>/<model>/
[ブラウザ] --GET /jobs/<id>/status (1秒ごと)--> 進捗 or 結果フラグメント
```

モジュール間で受け渡す型:

- **Person**: `np.ndarray` 形状 `(17, 3)`、各行 `[x_px, y_px, confidence]`
- **track**: `np.ndarray` 形状 `(フレーム数, 17, 3)`。未検出フレームは全要素 `NaN`

### Review Focus

タスクの基本確認だけでは踏まない、実利用で壊れやすい入力。各行の確認手順を担当タスクに入れてある。

1. **iPhone の `.mov`（HEVC / 縦撮り回転メタデータ / HDR）** — 正しい向きで解析され、開けない場合は画面にエラーが出る（Task 5）
2. **人物が1人も映らない動画** — 落ちずに検出率 0・未算出の指標は `-` と表示される（Task 4）
3. **動画でないファイル・対応外の拡張子** — 「解析中」のまま止まらず、エラーが表示される（Task 4）
4. **親など2人目が映り込む動画** — 追跡対象が赤ちゃんから移らない。複数人検出率が指標に出る（Task 5）
5. **長い・高解像度の動画（4K / 60fps / 数分）** — 縮小と間引きで現実的な時間で終わり、進捗が表示され続ける（Task 5）

## 影響箇所

| 影響を受ける機能 | 影響内容 | 確認ポイント |
| --- | --- | --- |
| `poc/pyproject.toml`（PoC 共通） | 依存追加、PyTorch を CPU 版インデックスに固定 | `uv sync` が成功する。今後の PoC も CPU 版 torch になる |
| `.gitignore` | `poc/*/data/*`・`*.task`・`*.webm` を追加 | `git status` に動画・結果・モデルが出ない |
| `backend/` `frontend/` | なし | 変更されていない |

## TODO

### Task 1: 環境準備

**Files:**
- Modify: `poc/pyproject.toml`
- Modify: `.gitignore`
- Create: `poc/001_pose_tracking/data/.gitkeep`
- Create: `poc/uv.lock`（`uv` が生成）

**Interfaces:**
- Produces: `poc/` で `uv run` すると fastapi / mediapipe / ultralytics / cv2 が import できる環境

- [x] **Step 1: ブランチを確認する**

```bash
git branch --show-current
```

Expected: `poc/pose-tracking`（違う場合は `git switch poc/pose-tracking`、無ければ `git switch -c poc/pose-tracking`）

- [ ] **Step 2: システムライブラリを入れる（ユーザーが実行）**

MediaPipe が `libGLESv2.so.2` を必要とする。sudo が必要なので、ユーザーに次の実行を依頼する。

```bash
sudo apt install -y libgles2
```

確認:

```bash
ldconfig -p | grep libGLESv2
```

Expected: `libGLESv2.so.2 ... => /usr/lib/x86_64-linux-gnu/libGLESv2.so.2`

- [x] **Step 3: `poc/pyproject.toml` に PyTorch の CPU インデックスを書く**

ファイル末尾（`[tool.uv]` ブロックの後）に追記する。

```toml
[tool.uv.sources]
torch = { index = "pytorch-cpu" }
torchvision = { index = "pytorch-cpu" }

[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true
```

- [x] **Step 4: 依存を追加する**

```bash
cd poc && uv add fastapi jinja2 mediapipe python-multipart uvicorn torch torchvision
```

Expected: `Resolved ... packages` のあとインストールが完了する。`poc/pyproject.toml` の `dependencies` が次の12個になる（順序・バージョン指定は uv に任せる）:
`fastapi, jinja2, matplotlib, mediapipe, numpy, opencv-python, pandas, python-multipart, torch, torchvision, ultralytics, uvicorn`

- [x] **Step 5: `.gitignore` に追記する**

ファイル末尾に追記する。

```gitignore

# PoC data (videos, run outputs, model files)
poc/*/data/*
!poc/*/data/.gitkeep
*.task
*.webm
```

- [x] **Step 6: データディレクトリを作る**

```bash
mkdir -p poc/001_pose_tracking/data poc/001_pose_tracking/templates && touch poc/001_pose_tracking/data/.gitkeep
```

- [x] **Step 7: import を確認する**

```bash
cd poc && uv run python -c "
import cv2, fastapi, mediapipe, torch, ultralytics
from mediapipe.tasks.python import vision
print(cv2.__version__, mediapipe.__version__, ultralytics.__version__, torch.__version__)
"
```

Expected: 4つのバージョンが表示され、torch は `+cpu` で終わる。エラーなし。

- [x] **Step 8: コミット**

```bash
git add .gitignore poc/pyproject.toml poc/uv.lock poc/001_pose_tracking/data/.gitkeep docs/plans/20261003-02-poc-pose-tracking.md
git commit -m "poc: 姿勢推定トラッキング PoC の環境を準備"
```

---

### Task 2: 共通スキーマと2つの推定器

**Files:**
- Create: `poc/001_pose_tracking/keypoints.py`
- Create: `poc/001_pose_tracking/estimators.py`
- Create: `poc/001_pose_tracking/make_smoke_videos.py`

**Interfaces:**
- Consumes: Task 1 の環境
- Produces:
  - `keypoints.KEYPOINT_NAMES: list[str]`（17個）、`SKELETON_EDGES: list[tuple[int, int]]`、`MEDIAPIPE_TO_COCO: list[int]`、`CONFIDENCE_THRESHOLD: float = 0.5`
  - `keypoints.person_center(person: np.ndarray) -> np.ndarray`（形状 `(2,)`）
  - `keypoints.select_target(persons: list[np.ndarray], previous_center: np.ndarray | None) -> np.ndarray | None`
  - `estimators.ESTIMATORS: dict[str, type]`（キー `"yolo"`, `"mediapipe"`）。各クラスは `__init__(models_dir: Path)`、`estimate(frame_bgr: np.ndarray, timestamp_ms: int) -> list[np.ndarray]`、`close() -> None` を持つ
  - `data/smoke_person.mp4`（人物あり）、`data/smoke_blank.mp4`（人物なし）

- [x] **Step 1: `keypoints.py` を書く**

`poc/001_pose_tracking/keypoints.py`

```python
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
```

- [x] **Step 2: `estimators.py` を書く**

`poc/001_pose_tracking/estimators.py`

```python
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
```

- [x] **Step 3: `make_smoke_videos.py` を書く**

実動画なしでパイプラインを確認するための合成動画（Ultralytics 同梱のサンプル画像を横にスライドしたものと、真っ黒なもの）を作る。

`poc/001_pose_tracking/make_smoke_videos.py`

```python
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
```

- [x] **Step 4: 合成動画を作る**

```bash
cd poc && uv run python 001_pose_tracking/make_smoke_videos.py
```

Expected: `wrote ['smoke_blank.mp4', 'smoke_person.mp4']`

- [x] **Step 5: 両推定器が共通スキーマで返すことを確認する**

```bash
cd poc/001_pose_tracking && uv run python -c "
from pathlib import Path
import cv2
from estimators import ESTIMATORS
from keypoints import select_target
models = Path('data/models'); models.mkdir(parents=True, exist_ok=True)
for video in ['smoke_person.mp4', 'smoke_blank.mp4']:
    ok, frame = cv2.VideoCapture('data/' + video).read()
    for name, cls in ESTIMATORS.items():
        estimator = cls(models)
        persons = estimator.estimate(frame, 0)
        target = select_target(persons, None)
        print(video, name, 'persons', len(persons), 'target', None if target is None else target.shape)
        estimator.close()
"
```

Expected（初回はモデルのダウンロードが走る）:
- `smoke_person.mp4` は両モデルとも `persons` が 1 以上、`target (17, 3)`
- `smoke_blank.mp4` は両モデルとも `persons 0 target None`
- `data/models/` に `yolo26n-pose.pt` と `pose_landmarker_heavy.task` がある

- [x] **Step 6: コミット**

```bash
git add poc/001_pose_tracking/keypoints.py poc/001_pose_tracking/estimators.py poc/001_pose_tracking/make_smoke_videos.py
git status --short   # data/ 配下の動画・モデルが出ていないことを確認
git commit -m "poc: 共通キーポイントスキーマと YOLO / MediaPipe 推定器を追加"
```

---

### Task 3: 解析パイプライン（動画 → オーバーレイ・CSV・指標・グラフ）

**Files:**
- Create: `poc/001_pose_tracking/video_io.py`
- Create: `poc/001_pose_tracking/metrics.py`
- Create: `poc/001_pose_tracking/plots.py`
- Create: `poc/001_pose_tracking/pipeline.py`

**Interfaces:**
- Consumes: `keypoints.KEYPOINT_NAMES / SKELETON_EDGES / CONFIDENCE_THRESHOLD / person_center / select_target`、`estimators.ESTIMATORS`
- Produces:
  - `pipeline.DATA_DIR / MODELS_DIR / RUNS_DIR: Path`
  - `pipeline.run_model(video_path: Path, model_name: str, out_dir: Path, target_fps: int, on_progress: Callable[[int, int], None]) -> dict` — `out_dir` に `overlay.webm` `keypoints.csv` `confidence.png` `speed.png` `metrics.json` を書き、指標 dict を返す。動画を開けない・フレームが0枚のときは `ValueError`
  - 指標 dict のキー: `frames, duration_s, detection_rate, mean_confidence, valid_keypoint_rate, gap_count, longest_gap_s, jitter, multi_person_rate, processing_fps, per_keypoint_valid_rate`（算出不能な値は `None`）

- [x] **Step 1: `video_io.py` を書く**

`poc/001_pose_tracking/video_io.py`

```python
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
```

- [x] **Step 2: `metrics.py` を書く**

`poc/001_pose_tracking/metrics.py`

```python
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
    track: np.ndarray, fps: float, inference_seconds: float, person_counts: list[int]
) -> dict:
    """追跡結果の自動指標を計算する。

    Args:
        track (np.ndarray): 形状 (T, 17, 3)。未検出フレームは NaN。T は1以上。
        fps (float): track のフレームレート（間引き後）。
        inference_seconds (float): 推論にかかった合計秒数。
        person_counts (list[int]): 各フレームで検出された人数。

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
        "multi_person_rate": _ratio(sum(count >= 2 for count in person_counts), frames),
        "processing_fps": (
            round(frames / inference_seconds, 1) if inference_seconds > 0 else None
        ),
        "per_keypoint_valid_rate": {
            name: _ratio(valid[:, index].sum(), frames)
            for index, name in enumerate(KEYPOINT_NAMES)
        },
    }
```

- [x] **Step 3: `plots.py` を書く**

`poc/001_pose_tracking/plots.py`

```python
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
```

- [x] **Step 4: `pipeline.py` を書く**

`poc/001_pose_tracking/pipeline.py`

```python
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
```

- [x] **Step 5: 人物あり・なしの合成動画で確認する**

```bash
cd poc/001_pose_tracking && uv run python -c "
import json
from pathlib import Path
from pipeline import RUNS_DIR, run_model
for video in ['smoke_person', 'smoke_blank']:
    for model in ['yolo', 'mediapipe']:
        out = RUNS_DIR / '_smoke' / video / model
        metrics = run_model(Path('data') / (video + '.mp4'), model, out, 15, lambda done, total: None)
        metrics.pop('per_keypoint_valid_rate')
        print(video, model, json.dumps(metrics))
        print('  files:', sorted(p.name for p in out.iterdir()))
"
```

Expected:
- 4通りすべてエラーなく完了し、`files:` が `['confidence.png', 'keypoints.csv', 'metrics.json', 'overlay.webm', 'speed.png']`
- `smoke_person`: `frames` が 43 前後、`detection_rate` が 0.9 以上、`mean_confidence` と `jitter` が数値
- `smoke_blank`: `detection_rate` が `0.0`、`mean_confidence` と `jitter` が `null`、`gap_count` が `1`
- `OpenCV: FFMPEG: tag ... 'VP90' is not supported` の警告は無害なので無視してよい

- [x] **Step 6: コミット**

```bash
git add poc/001_pose_tracking/video_io.py poc/001_pose_tracking/metrics.py poc/001_pose_tracking/plots.py poc/001_pose_tracking/pipeline.py
git commit -m "poc: 動画からオーバーレイ・指標・グラフを出力する解析パイプラインを追加"
```

---

### Task 4: HTMX 画面（アップロード → 進捗 → 結果）

**Files:**
- Create: `poc/001_pose_tracking/jobs.py`
- Create: `poc/001_pose_tracking/app.py`
- Create: `poc/001_pose_tracking/templates/base.html`
- Create: `poc/001_pose_tracking/templates/index.html`
- Create: `poc/001_pose_tracking/templates/run.html`
- Create: `poc/001_pose_tracking/templates/_status.html`
- Create: `poc/001_pose_tracking/templates/_result.html`

**Interfaces:**
- Consumes: `pipeline.run_model / RUNS_DIR`、`estimators.ESTIMATORS`
- Produces:
  - `jobs.Job`（`status: "running" | "done" | "error"`, `progress: str`, `error: str`）、`jobs.JOBS: dict[str, Job]`
  - `jobs.start_job(run_id: str, video_path: Path, original_name: str, models: list[str], target_fps: int) -> None`
  - `jobs.load_summary(run_id: str) -> dict | None`、`jobs.list_summaries() -> list[dict]`
  - `summary.json`: `{"run_id", "video", "created_at", "target_fps", "models": {<model>: <指標 dict>}}`
  - ルート: `GET /`、`POST /jobs`、`GET /jobs/{run_id}/status`、`GET /runs/{run_id}`、静的配信 `/runs-data/`

- [x] **Step 1: `jobs.py` を書く**

`poc/001_pose_tracking/jobs.py`

```python
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
```

- [x] **Step 2: `app.py` を書く**

`poc/001_pose_tracking/app.py`

```python
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
```

- [x] **Step 3: テンプレートを書く**

`poc/001_pose_tracking/templates/base.html`

```html
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PoC 001: 姿勢推定トラッキング</title>
  <script src="https://unpkg.com/htmx.org@2.0.4"></script>
  <style>
    body { font-family: sans-serif; max-width: 1200px; margin: 0 auto; padding: 16px; }
    table { border-collapse: collapse; margin: 8px 0; }
    th, td { border: 1px solid #ccc; padding: 4px 10px; text-align: left; }
    form > * { margin: 6px 0; }
    .models { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; }
    .models video, .models img { width: 100%; }
    .error { color: #b00020; font-weight: bold; }
    .legend span { margin-right: 12px; }
  </style>
</head>
<body>
  <h1><a href="/">PoC 001: 姿勢推定トラッキング</a></h1>
  {% block content %}{% endblock %}
</body>
</html>
```

`poc/001_pose_tracking/templates/index.html`

```html
{% extends "base.html" %}
{% block content %}
<form hx-post="/jobs" hx-encoding="multipart/form-data" hx-target="#job" hx-swap="outerHTML"
      hx-disabled-elt="find button">
  <div>
    <label>動画（mp4 / mov / m4v / webm）
      <input type="file" name="video" accept="video/*,.mov,.m4v" required>
    </label>
  </div>
  <div>
    <label>解析フレームレートの目標
      <select name="target_fps">
        <option value="10">10 fps</option>
        <option value="15" selected>15 fps</option>
        <option value="30">30 fps</option>
      </select>
    </label>
  </div>
  <div>
    モデル:
    {% for model in models %}
    <label><input type="checkbox" name="models" value="{{ model }}" checked> {{ model }}</label>
    {% endfor %}
  </div>
  <button type="submit">解析する</button>
</form>

<div id="job"></div>

<h2>過去の結果</h2>
{% if runs %}
<table>
  <tr><th>日時</th><th>動画</th><th>モデル</th></tr>
  {% for run in runs %}
  <tr>
    <td>{{ run.created_at }}</td>
    <td><a href="/runs/{{ run.run_id }}">{{ run.video }}</a></td>
    <td>{{ run.models | join(", ") }}</td>
  </tr>
  {% endfor %}
</table>
{% else %}
<p>まだ結果はありません。</p>
{% endif %}
{% endblock %}
```

`poc/001_pose_tracking/templates/run.html`

```html
{% extends "base.html" %}
{% block content %}
{% include "_result.html" %}
{% endblock %}
```

`poc/001_pose_tracking/templates/_status.html`

```html
{% if job.status == "error" %}
<div id="job" class="error">エラー: {{ job.error }}</div>
{% else %}
<div id="job" hx-get="/jobs/{{ run_id }}/status" hx-trigger="every 1s" hx-swap="outerHTML">
  解析中… {{ job.progress }}
</div>
{% endif %}
```

`poc/001_pose_tracking/templates/_result.html`

```html
<div id="job">
  <h2>結果: {{ summary.video }}</h2>
  <p>
    {{ summary.created_at }} / 解析フレームレートの目標 {{ summary.target_fps }} fps /
    <a href="/runs/{{ summary.run_id }}">この結果の固定 URL</a>
  </p>
  <table>
    <tr>
      <th>指標</th>
      {% for name in summary.models %}<th>{{ name }}</th>{% endfor %}
    </tr>
    {% for key, label in METRIC_LABELS %}
    <tr>
      <td>{{ label }}</td>
      {% for name, metrics in summary.models.items() %}
      <td>{{ metrics[key] if metrics[key] is not none else "-" }}</td>
      {% endfor %}
    </tr>
    {% endfor %}
  </table>
  <p class="legend">
    <span style="color: #00dc00">● 鼻</span>
    <span style="color: #ffa500">● 左</span>
    <span style="color: #0080ff">● 右</span>
    （信頼度 0.5 未満の点は描画しない）
  </p>
  <div class="models">
    {% for name, metrics in summary.models.items() %}
    {% set base = "/runs-data/" ~ summary.run_id ~ "/" ~ name %}
    <section>
      <h3>{{ name }}</h3>
      <video src="{{ base }}/overlay.webm" controls loop muted playsinline></video>
      <img src="{{ base }}/confidence.png" alt="{{ name }} の信頼度の推移">
      <img src="{{ base }}/speed.png" alt="{{ name }} の手首・足首の速度">
      <details>
        <summary>キーポイント別の有効率</summary>
        <table>
          {% for keypoint, rate in metrics.per_keypoint_valid_rate.items() %}
          <tr><td>{{ keypoint }}</td><td>{{ rate }}</td></tr>
          {% endfor %}
        </table>
      </details>
      <p><a href="{{ base }}/keypoints.csv">keypoints.csv</a></p>
    </section>
    {% endfor %}
  </div>
</div>
```

- [x] **Step 4: サーバーを起動する**

```bash
cd poc && uv run uvicorn app:app --app-dir 001_pose_tracking --host 127.0.0.1 --port 8000
```

Expected: `Uvicorn running on http://127.0.0.1:8000`（以降の確認は別ターミナル、またはバックグラウンド起動で行う）

- [x] **Step 5: 正常系を確認する（人物あり動画・両モデル）**

```bash
cd poc/001_pose_tracking
curl -s -F video=@data/smoke_person.mp4 -F target_fps=15 -F models=yolo -F models=mediapipe http://127.0.0.1:8000/jobs
```

Expected: `<div id="job" hx-get="/jobs/<32桁の16進>/status" hx-trigger="every 1s" ...>解析中…` が返る。

返ってきた run_id で、完了するまで状態を取得する。

```bash
RUN_ID=<上で返った32桁>
until curl -s http://127.0.0.1:8000/jobs/$RUN_ID/status | grep -q "結果:"; do sleep 2; done
curl -s http://127.0.0.1:8000/jobs/$RUN_ID/status | grep -c -E "overlay.webm|confidence.png|speed.png"
curl -s -o /dev/null -w "%{http_code} %{content_type}\n" http://127.0.0.1:8000/runs-data/$RUN_ID/yolo/overlay.webm
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/runs/$RUN_ID
```

Expected: `6`（2モデル × 3ファイル）、`200 video/webm`、`200`

- [x] **Step 6: 人物なし動画で落ちないことを確認する（Review Focus 2）**

```bash
curl -s -F video=@data/smoke_blank.mp4 -F models=yolo -F models=mediapipe http://127.0.0.1:8000/jobs
RUN_ID=<返った32桁>
until curl -s http://127.0.0.1:8000/jobs/$RUN_ID/status | grep -q "結果:"; do sleep 2; done
curl -s http://127.0.0.1:8000/jobs/$RUN_ID/status | grep -A6 "平均信頼度"
```

Expected: 「平均信頼度」の行に `<td>-</td>` が2つ（両モデル分）出る。サーバーのログに例外が出ていない。

- [x] **Step 7: 不正な入力でエラーが表示されることを確認する（Review Focus 3）**

```bash
echo "not a video" > /tmp/fake.txt && cp /tmp/fake.txt /tmp/fake.mp4
curl -s -F video=@/tmp/fake.txt -F models=yolo http://127.0.0.1:8000/jobs
curl -s -F video=@data/smoke_person.mp4 http://127.0.0.1:8000/jobs
curl -s -F video=@/tmp/fake.mp4 -F models=yolo http://127.0.0.1:8000/jobs
RUN_ID=<3つ目で返った32桁>
sleep 3 && curl -s http://127.0.0.1:8000/jobs/$RUN_ID/status
```

Expected（いずれも `hx-trigger` を含まない = ポーリングが止まる）:
1. `<div id="job" class="error">エラー: 対応していない拡張子です…`
2. `<div id="job" class="error">エラー: モデルを1つ以上選択してください`
3. 最後の status が `<div id="job" class="error">エラー: 動画を開けませんでした…`

- [ ] **Step 8: ブラウザで目視確認する**

`http://127.0.0.1:8000/` を Chrome か Edge で開き、`data/smoke_person.mp4` をアップロードする。

Expected:
- 「解析中… yolo: N / 約43 フレーム」のように進捗が更新される
- 完了すると指標比較表と、モデルごとのオーバーレイ動画（骨格が人物に重なって再生される）・グラフ2枚が表示される
- トップに戻ると「過去の結果」に行が増えており、リンクから同じ結果を開ける

- [x] **Step 9: コミット**

```bash
git add poc/001_pose_tracking/jobs.py poc/001_pose_tracking/app.py poc/001_pose_tracking/templates
git status --short   # data/ 配下が出ていないことを確認
git commit -m "poc: 動画アップロードから結果表示までの HTMX 画面を追加"
```

---

### Task 5: README と実動画での評価

**Files:**
- Create: `poc/001_pose_tracking/README.md`

**Interfaces:**
- Consumes: Task 4 の画面、`data/runs/<run_id>/summary.json`
- Produces: PoC の結論（次フェーズへ進む / モデルを再検討する）

- [x] **Step 1: README を書く（結果・課題は評価後に埋める）**

`poc/001_pose_tracking/README.md`

````markdown
# PoC 001: 赤ちゃん動画の姿勢推定トラッキング

実装計画: `docs/plans/20261003-02-poc-pose-tracking.md`

## 検証概要

赤ちゃんの実動画に対して、既存の姿勢推定モデル（YOLO26n-pose / MediaPipe PoseLandmarker heavy）が
モーショントラッキングに使える信頼性で動くかを検証する。

## 詳細

- 動画をブラウザからアップロードすると、各モデルでキーポイント（COCO 17点）を時系列に追跡し、
  骨格オーバーレイ動画・グラフ・指標を並べて表示する。
- 解析は長辺 960px に縮小し、指定したフレームレート（既定 15fps）に間引いて行う。
- 複数人が映る場合、最初のフレームで平均信頼度が最も高い人物を選び、以降は前フレームの中心に最も近い人物を追う。
- 動画・解析結果・モデルファイルは `data/` に保存され、git には含めない。外部への送信は行わない。

### 実行方法

```bash
sudo apt install -y libgles2   # 初回のみ（MediaPipe が必要とする）
cd poc
uv sync
uv run uvicorn app:app --app-dir 001_pose_tracking --host 127.0.0.1 --port 8000
```

`http://127.0.0.1:8000/` を Chrome / Edge で開く。

実動画なしで動作確認する場合:

```bash
cd poc && uv run python 001_pose_tracking/make_smoke_videos.py
```

## 評価方法

### 自動指標

| 指標 | 意味 |
| --- | --- |
| 検出率 | 追跡対象が検出されたフレームの割合 |
| 平均信頼度 | 検出フレームでのキーポイント信頼度の平均（モデル間で定義が違うため絶対値の比較は参考） |
| 有効キーポイント率 | 全フレーム × 17点のうち、信頼度 0.5 以上だった割合 |
| 途切れ回数 / 最長の途切れ | 未検出が連続した区間の数と、最長の長さ |
| ジッタ | 位置の2階差分の中央値 ÷ 体サイズ。小さいほど滑らか |
| 複数人が検出されたフレームの割合 | 親などの映り込みの目安 |
| 推論速度 | 推論のみの処理フレーム数/秒（CPU） |

### 目視チェック

オーバーレイ動画を見て、動画ごと・モデルごとに確認する。

- [ ] 骨格が赤ちゃんの体に重なっているか（特に手首・足首）
- [ ] 寝返りの途中（横向き・うつ伏せ）で骨格が破綻しないか
- [ ] 左（オレンジ）と右（青）が入れ替わらないか
- [ ] 追跡対象が親や物に移らないか
- [ ] 点が細かく震えていないか

### 暫定判定基準

| 指標 | 「使える」とみなす目安 |
| --- | --- |
| 検出率 | 90% 以上 |
| 有効キーポイント率 | 70% 以上 |
| 最長の途切れ | 1.0 秒以下 |
| 目視 | 上のチェックがおおむね満たされる |

## 結果

（評価後に記入する）

## 課題

（評価後に記入する）
````

- [x] **Step 2: コミット**

```bash
git add poc/001_pose_tracking/README.md
git commit -m "poc: 姿勢推定トラッキング PoC の README を追加"
```

- [ ] **Step 3: 実動画を解析する（ユーザーが実施）**

ユーザーに依頼する: 「完了条件」の撮影条件に沿った実動画 3〜5 本を、ブラウザ（`http://127.0.0.1:8000/`）から1本ずつアップロードし、両モデルで解析する。iPhone で撮った `.mov` をそのまま使う。

各動画で次を確認し、気づいた点をメモしてもらう。

- **Review Focus 1:** iPhone の `.mov` が開け、オーバーレイ動画の向き（縦横）が正しい。開けない場合は画面に「動画を開けませんでした」と出るので、その動画のコーデック情報と合わせて課題に記録する。
- **Review Focus 4:** 親が映り込む動画で、骨格が赤ちゃんに付いたままか。「複数人が検出されたフレームの割合」が 0 より大きいか。
- **Review Focus 5:** 一番長い・高解像度の動画でも進捗が更新され続け、完了するか。所要時間を記録する。
- README の「目視チェック」5項目。

- [ ] **Step 4: 結果を集計する**

```bash
cd poc/001_pose_tracking && uv run python -c "
import json
from pathlib import Path
keys = ['detection_rate', 'valid_keypoint_rate', 'longest_gap_s', 'jitter', 'multi_person_rate', 'processing_fps']
print('| 動画 | モデル | ' + ' | '.join(keys) + ' |')
print('|' + ' --- |' * (len(keys) + 2))
for path in sorted(Path('data/runs').glob('*/summary.json')):
    summary = json.loads(path.read_text(encoding='utf-8'))
    for model, metrics in summary['models'].items():
        print('| ' + ' | '.join([summary['video'], model] + [str(metrics[k]) for k in keys]) + ' |')
"
```

Expected: 動画 × モデルごとに1行の Markdown 表が出力される。

- [ ] **Step 5: README の「結果」「課題」を記入する**

「結果」に書くこと:

1. Step 4 の表（動画のファイル名は「仰向け」「寝返り」など内容を表す名前に置き換える。個人が特定できる情報は書かない）
2. 動画 × モデルごとの目視所見（目視チェック5項目の結果）
3. 暫定判定基準に対する合否
4. **結論**: 次のいずれかを明記する
   - 次フェーズ（モーション解析）へ進む。採用するモデルはどちらか、その理由
   - 条件付きで進む（例: 撮影条件を限定する）
   - モデルを再検討する（乳児特化モデル・ファインチューニング・Apple Vision などを次の PoC で検証）

「課題」に書くこと:

- うまくいかなかった場面（寝返り中、隠れ、親の映り込みなど）と、考えられる原因
- 暫定判定基準そのものが妥当だったか
- Ultralytics のライセンス（AGPL-3.0）— 製品に組み込む場合は検討が必要
- 信頼度の定義がモデル間で異なるため、絶対値を直接比較できないこと
- 正解ラベルによる精度測定は未実施であること
- 最終ターゲットは iPhone であり、サーバー推論 / オンデバイス推論の方針は未決であること

- [ ] **Step 6: コミット**

```bash
git add poc/001_pose_tracking/README.md
git status --short   # 動画・解析結果が含まれていないことを確認
git commit -m "poc: 姿勢推定トラッキング PoC の評価結果を記録"
```

- [ ] **Step 7: 設計ドキュメントへの反映を判断する**

結論でモデルが決まった場合のみ、`docs/design/TECH_STACK.md` に「動画解析: 採用モデルと理由、PoC 001 への参照」を追記してコミットする。決まらなかった場合はスキップする。

---

## レビュー後の変更（2026-10-03）

全体レビューの指摘を受けて、上記 Task 2〜4 のコードから次の点を変更した。実際のコードは `poc/001_pose_tracking/` を正とする。

| 変更 | 理由 |
| --- | --- |
| `keypoints.select_target` を `keypoints.TargetTracker` に置き換えた。前回の体サイズより遠い候補は別人とみなして未検出にし、1秒を超えて見失った後だけ選び直す | 赤ちゃんを1フレーム見失っただけで親に乗り移り、検出率などが親の値になるのを防ぐ |
| 指標に「追跡対象の選び直し回数」を追加し、追跡対象以外の人物を灰色の点で描画する | 対象が入れ替わった可能性を表と動画の両方で気づけるようにする |
| 有効キーポイントが5点未満の検出を「未検出」として扱う（`keypoints.usable_persons`） | 枠だけ検出されて関節が取れていないフレームを検出率に数えないため。モデル間の検出しきい値の差の影響も減らす |
| README に HDR 動画の色の確認、両モデルが同じ人物を追っているかの確認、ジッタと時刻の注意を追記 | iPhone の HDR 動画はトーンマッピングされない可能性があり、モデルではなくデコードが原因で「使えない」と誤判定しうる |
| `.gitignore` に大文字拡張子（`*.MOV` など）を追加 | iPhone のファイル名は `IMG_xxxx.MOV` で、既存の小文字パターンでは無視されない |

未対応（検証未了・ユーザー操作待ち）:

- Task 1 Step 2: `sudo apt install -y libgles2`
- Task 4 Step 8: ブラウザでの目視確認
- Task 5 Step 3 以降: 実動画での評価と README への結果記入
