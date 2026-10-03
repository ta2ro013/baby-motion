---
paths:
  - "src/**"
---

# 構造化ログ・要約・秘密情報禁止

## TypeScript

### ルール

1. 業務コードで `console.log`、`console.error` を直接使用しない
   ログは `src/lib/logging/` の共通関数を経由する。
   直接出力すると、`requestId` の付与や秘密情報のマスク処理を迂回するため。

2. ログ対象は、外部I/O・副作用・失敗する可能性がある処理を中心とする
   例：

   * DBアクセス
   * 外部API呼び出し
   * LLM呼び出し
   * 通知送信
   * ファイル操作

   純粋関数や単純なデータ変換処理では、原則としてログを出力しない。

3. エラーは記録した後、原則として再スローする
   エラーを握りつぶして正常系として扱うことは禁止する。

4. ログには処理の要約のみを記録する
   リクエスト・レスポンス・オブジェクト全体をそのまま出力しない。

5. `info` ログは必要なものに限定する
   以下を主な対象とする。

   * 外部API・LLM・DBアクセスの完了
   * 1秒を超える処理
   * ユーザー操作上重要なイベント
   * バッチや分析処理など、開始・終了を追跡する価値がある処理

   単純な正常終了をすべてログに出力しない。

6. ログは構造化データとして出力する
   自由形式の長文メッセージに必要情報を埋め込まない。

---

## ログ名

ログ名は、処理が属する機能と処理内容が分かる形式にする。

```text
<feature>.<action>
```

`feature` には、原則として `src/features/` 配下の機能名を使用する。

例：

```text
theme-analysis.analyze
market-data.fetch
companies.load-financials
supply-chain.build
```

特定のfeatureに属さない共通基盤や外部サービス処理では、その責務が分かる名前を使用する。

例：

```text
web-search.fetch
ai.generate
logging.serialize-error
```

文章形式の名前は使用しない。

```ts
// Good
log.info("theme-analysis.analyze", { requestId, ms });

// Avoid
log.info("Theme analysis was successfully completed");
```

---

### 共通ログ項目

ログには、必要に応じて以下の項目を付与する。

| キー          | 利用条件          | 内容                |
| ----------- | ------------- | ----------------- |
| `requestId` | リクエストに紐づく処理   | 一連の処理を追跡するための相関ID |
| `userId`    | 関連ユーザーが存在する場合 | ユーザーを識別するID       |
| `err`       | エラー時          | 整形済みのエラー情報        |
| `ms`        | 処理時間を記録する場合   | 所要時間（ミリ秒）         |

ログ名は `log.info()` / `log.error()` の第1引数として指定するため、ログオブジェクト内に `name` を重複して持たせない。

---

### requestId

HTTPリクエストなど、一連の処理に紐づくログでは `requestId` を付与する。

同じ処理の途中で新しい `requestId` を生成せず、入口で生成された値を引き回す。

```ts
log.info("theme-analysis.analyze", {
  requestId,
  ms,
});
```

---

### userId

関連するユーザーが存在する場合のみ記録する。

```ts
log.info("companies.add-watchlist", {
  requestId,
  userId,
});
```

メールアドレス、氏名などの個人情報を識別子の代わりに利用しない。

---

### エラー

エラーは共通関数で以下の形式に整形して記録する。

```ts
type SerializedError = {
  name: string;
  message: string;
  stack?: string;
};
```

例：

```ts
try {
  await fetchMarketData();
} catch (error) {
  log.error("market-data.fetch", {
    requestId,
    err: serializeError(error),
  });

  throw error;
}
```

以下は禁止する。

```ts
// NG: エラーオブジェクトをそのまま出力
console.error(error);

// NG: エラーを握りつぶす
try {
  await fetchMarketData();
} catch (error) {
  log.error("market-data.fetch", {
    err: serializeError(error),
  });
}
```

---

### 処理時間

外部I/Oや重い処理では、必要に応じて `ms` を記録する。

主な対象：

* 外部API
* LLM
* DBアクセス
* 1秒を超える処理
* パフォーマンス監視対象の処理

```ts
const startedAt = performance.now();

await analyzeTheme();

log.info("theme-analysis.analyze", {
  requestId,
  ms: Math.round(performance.now() - startedAt),
});
```

単純な純粋関数では処理時間を記録しない。

---

### ログに記録するデータ

ログには、問題調査に必要な最小限の情報だけを記録する。

#### Good

```ts
log.info("market-data.fetch", {
  requestId,
  ticker: "6268",
  ms: 420,
});
```

#### Avoid

```ts
log.info("market-data.fetch", {
  requestId,
  response: marketDataResponse,
});
```

オブジェクト全体ではなく、ID・件数・ステータスなどに要約する。

例：

```ts
log.info("web-search.fetch", {
  requestId,
  queryLength: query.length,
  resultCount: results.length,
  ms,
});
```

---

### 秘密情報・個人情報の出力禁止

以下はどのログレベルでも出力しない。

* APIキー
* Access Token
* Refresh Token
* Session Token
* Cookie
* Authorization Header
* パスワード
* パスワード再設定リンク
* Secret
* `.env` の内容
* 外部APIの認証情報
* 生の個人情報
* リクエスト・レスポンス全体

例：

```ts
// NG
console.log("reset link generated", email, link);
```

```ts
// OK
log.info("auth.send-reset-link", {
  requestId,
  emailDomain: email.split("@")[1],
});
```

秘密情報が含まれる可能性のあるオブジェクトを、そのままログ関数へ渡してはならない。

---

### ログレベル

#### `info`

正常系のうち、運用上追跡する価値のあるイベントに利用する。

#### `warn`

処理は継続できるが、想定外または注意が必要な状態に利用する。

#### `error`

処理が失敗した場合に利用する。

エラーは原則として記録後に再スローし、呼び出し元に伝播させる。

#### `debug`

開発・調査用途に限定する。

本番で大量に出力される実装にしない。

---

### 例

```ts
const startedAt = performance.now();

try {
  const result = await analyzeTheme(theme);

  log.info("theme-analysis.analyze", {
    requestId,
    resultCount: result.companies.length,
    ms: Math.round(performance.now() - startedAt),
  });

  return result;
} catch (error) {
  log.error("theme-analysis.analyze", {
    requestId,
    err: serializeError(error),
    ms: Math.round(performance.now() - startedAt),
  });

  throw error;
}
```
