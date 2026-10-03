---
paths: 
  - "src/**"
---

# Coding Style

## 基本方針

* シンプルで読みやすい実装を優先する
* 過度な抽象化や将来を見越した不要な実装を行わない
* 既存の設計・命名・ディレクトリ構成に合わせる
* 1ファイル1責務とする

## TypeScript

* `any` は原則使用しない
* `unknown` を利用し、必要な型チェックを行う
* ドメインデータには明示的な型を定義する
* 不要な型アサーション（`as`）を避ける
* 型推論で十分な場合は冗長な型定義を行わない

### React / Next.js

* Server Componentを基本とする
* Client Componentは必要な場合のみ `"use client"` を付与する
* ビジネスロジックをReactコンポーネントに直接書きすぎない
* UIコンポーネントは表示とユーザー操作に責務を限定する
* データ取得や変換処理は可能な限りコンポーネントから分離する

### コンポーネント

* 小さく責務の明確なコンポーネントを作成する
* 汎用化の必要性が明確になる前に共通化しない
* Propsは必要最小限にする
* Generative UIで使用するコンポーネントは、構造化データを受け取って描画する

### 命名

* 変数・関数名から役割が分かる名前を使用する
* 不要な略語を避ける
* booleanは `is`、`has`、`can`、`should` など意味が分かる接頭辞を使用する

例：

```ts
const isLoading = true;
const hasEvidence = evidence.length > 0;
```

### フォーマット・Lint

Biomeを使用する。

コード変更後は必要に応じて以下を実行する。

```bash
npm run lint
npm run format:check
npm run typecheck
```

Biomeの警告やTypeScriptエラーを無視して実装を完了しない。


## Python

- 関数の命名は snake_case を使用する
- 関数やクラスには必ず docstring を記載する。Googleスタイルのdocstringとする。

    ```python
    def add(a: int, b: int) -> int:
        """2つの整数を加算する。

        <追加で説明が必要な場合はここに記載する。>

        Args:
            a (int): 加算する最初の整数。
            b (int): 加算する2番目の整数。

        Returns:
            int: 2つの整数の合計。
        """
        return a + b
    ```

### フォーマット・Lint

- 基本的に ruff を使用する。コード変更後は必要に応じて以下を実行する。

  ```bash
  ruff check .
  ```

- 補助として mypy を使用する。コード変更後は必要に応じて以下を実行する。

  ```bash
  mypy .
  ```

