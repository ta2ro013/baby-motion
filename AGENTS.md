## プロジェクト概要

`baby-motion` は、画像・動画解析を用いて、赤ちゃんの運動発達を記録・可視化する iPhone アプリ。
日常の赤ちゃんの動画を、姿勢推定とモーショントラッキングによって構造化された成長記録に変換する。

詳細は `README.md` を参照。

## ドキュメントマップ

- `docs/design`
    本システムの設計内容を管理するディレクトリ。
    実装計画で実装した内容を`push`, `PR`する前に本ディレクトリに反映する。
    反映する内容がなければスキップ。

- `docs/design/TECH_STACK.md`
    本システムの採用技術と利用方針を記載する。

- `docs/design/ARCHITECTURE.md`
    本システムのアーキテクチャ設計を記載する。

- `docs/plans`
    実装計画を管理するディレクトリ。
    命名規則は `yyyymmdd-nn-<dev-summary>.md`（`<dev-summary>` は英語・ケバブケース）。
    詳細は `.claude/rules/planning.md` を参照。

- `.claude/rules/planning.md`
    実装計画の記載方法を記載する。

- `.claude/rules/developing.md`
    開発方針（TDD、品質チェック、Git 運用）を記載する。

- `.claude/rules/testing.md`
    単体テスト / 結合テスト / E2E テストの切り分けと方針を記載する。

- `.claude/rules/coding-style.md`
    コーディング規約を記載する。

- `.claude/rules/logging.md`
    ログ出力のルール（構造化ログ、秘密情報の出力禁止）を記載する。

- `.claude/rules/frontend-design.md`
    フロントエンド / UI のデザインルールを記載する。


## 開発環境

### Python

Python の実行とパッケージ管理は、すべて uv（`/home/tatsuro/.local/bin/uv`）経由で行う。

- スクリプトの実行: `uv run <コマンド>`（例: `uv run python main.py`）
- 依存の追加: `uv add <パッケージ>`
- **`python` / `pip` を直接実行しない**（環境にデフォルトでインストールされている Python の利用は禁止）。

### Node.js

`node` / `npm` は Volta（`/home/tatsuro/.volta/bin/volta`）で管理されたものを使う。

- Node.js のバージョン固定・変更: `volta pin node@<バージョン>`
- Volta を介さずに Node.js を別途インストールしない。


## 判断に迷った場合

仕様・設計・実装方法について判断に迷う場合は、独断で進めない。

ユーザーに以下を提示して判断を仰ぐ。

1. 何について迷っているか
2. 判断に迷う理由
3. 考えられる候補
4. 各候補のメリット・デメリット
5. 推奨案がある場合は、その理由

例：

```text
認証方式について判断が必要です。

候補A: NextAuth
- メリット: Next.jsとの統合が容易
- デメリット: 現時点では認証自体がMVPに不要

候補B: 認証を実装しない
- メリット: MVPをシンプルに維持できる
- デメリット: ユーザー別データ保存はできない

MVPでは候補Bを推奨します。
どちらで進めるか確認してください。
```

## PoC

- 実現性の確認や精度確認が必要な機能については、Proof of Concept を実施する。
- PoC では、`.claude/rules/developing.md` の TDD と品質チェックは不要。
- `poc`ディレクトリで作業する。ディレクトリ構成は以下。

    ```
    poc
    ├── 001_<機能概要>
    │   ├── README.md # PoCの内容を記載する。検証概要、詳細、評価方法、結果、課題。
    │   ├── data # 検証用データを格納するディレクトリ
    │   └── <コード>
    ├── 002_<機能概要>
    ・・・
    ```

- PoCにおける技術スタックは以下。
    - Python / HTMX
    - **HTMX で検証が難しい場合は、代替方法をユーザーに相談して決める**
    - PoCにおいてデザインが重要でない場合は、簡易なデザインで良い。

- ブランチ名は `poc/xxxxx` とする。