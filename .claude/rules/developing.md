# 開発ルール

## 基本方針

本プロジェクトでは、TDD（テスト駆動開発）を基本とする。
必ず以下の順序で進める。

```text
RED
↓
GREEN
↓
REFACTOR
```

テスト方針は `.claude/rules/testing.md` を参照

`poc` ディレクトリ配下の PoC は、TDD および後述の品質チェックの対象外とする。

### RED

機能追加・修正を行う前に、まず失敗するテストを書く。

テストが意図した理由で失敗することを確認してから実装へ進む。

### GREEN

テストを通すために必要な最小限の実装を行う。

この段階では過度な抽象化や最適化を行わない。

### REFACTOR

すべてのテストが成功した状態を維持しながら、必要に応じてコードを整理する。


## 品質チェック

コミット前に、以下を必ず実行する。

```bash
npm run test          # ユニット + 結合テスト（Vitest）
npm run test:e2e      # E2Eテスト（Playwright）
npm run lint
npm run format:check
npm run typecheck
```

すべて成功した状態でのみコミット可能とする。

テスト種別ごとの責務と配置は `.claude/rules/testing.md` に従う。
ドキュメント内では上記の `npm run` スクリプト名を正とし、
`npx vitest` / `npx playwright` を直接案内しない。

以下は禁止する。

* 失敗しているテストを残したままコミットする
* Lintエラーを無視する
* Formatエラーを無視する
* TypeScriptエラーを無視する
* テストを削除・無効化して問題を回避する

### コーディング規約

`.claude/rules/coding-style.md`を準拠すること


## Git 

### ブランチ戦略

**GitHub Flow** を採用する。

- `main` は常にデプロイ可能な状態を保つ。
- 作業は `main` から feature ブランチを切って行う。
- 変更はプルリクエスト（PR）経由で `main` にマージする。


### ブランチ命名規則

`<type>/<short-description>` の形式で命名する。

- `<type>`: 変更の種類（下表）
- `<short-description>`: 変更内容を英語・ケバブケースで簡潔に

| type | 用途 |
| --- | --- |
| feat | 新機能の追加 |
| fix | バグ修正 |
| refactor | 挙動を変えないリファクタリング |
| docs | ドキュメントのみの変更 |
| test | テストの追加・修正 |
| chore | ビルド・依存・設定など雑多な変更 |
| poc | Proof of Concept（概念実証） |

例:

- `feat/add-rag-reranker`
- `fix/token-limit-overflow`
- `refactor/split-retriever-module`

### main ブランチの扱い

- `main` への**直接コミット・直接 push は禁止**。
- 必ず feature ブランチを切って作業し、`main` への反映はプルリクエスト経由で行う。
- GitHub 側の保護設定は行わず、運用ルールとして守る。

### コミット前の品質チェック

コミット前に必ず以下の品質チェックを実施し、**すべて PASS すること**。
1つでも失敗した場合はコミットしない。

- テスト実行
- E2E テスト実行
- リンター / フォーマッター

### コミット単位

- **一言で説明可能な範囲**にまとめる。
- 複数の変更が混ざる場合は、コミットを分割する。

### プルリクエスト

- `main` へのマージはプルリクエスト経由で行う。
- 必ず対応する実装計画のファイル名を記載すること。
