# Telegram Result Message

將小龍蝦產出的 `result.md` 轉成 Telegram 可直接發送的訊息，並支援超長內容分批傳送。

## 適合情境

- 需要把 `artifacts/{issue-comment-id}/result.md` 轉成 Telegram 通知。
- 需要把過長結果拆成多則 Telegram 訊息。
- 需要讓每一則分批訊息都保有順序與可讀性。

## 主要能力

- 讀取 `result.md` 並整理重點。
- 產生 Telegram 友善的純文字、Markdown 或 HTML 訊息。
- 預設使用 Telegram HTML，支援 Markdown 常用呈現效果，例如標題粗體、粗體、斜體、引用、行內程式碼、程式碼區塊與連結。
- 若需要保留原始 Markdown 語法，可使用 `--parse-mode markdown`，產生的檔案不會被轉成 HTML 標籤。
- 將 Telegram 不支援的 Markdown 表格轉成等寬字體表格式內容。
- 移除不適合 Telegram 的 Markdown 標記。
- 依 Telegram 長度限制分批。
- 輸出 `telegram-message.txt` 與 `telegram-message.json`，方便人工檢視或程式批次發送。

## 建議輸出

```text
artifacts/{issue-comment-id}/telegram-message.txt
artifacts/{issue-comment-id}/telegram-message.json
```

## 建議使用漂亮格式

若希望 Telegram 呈現 Markdown 風格，請使用預設的 HTML 模式：

```bash
python .agents/skills/telegram-result-message/scripts/convert_result.py \
  artifacts/{issue-comment-id}/result.md \
  --parse-mode html \
  --max-chars 3500
```

Markdown 程式碼區塊與表格會自動轉成 Telegram 支援的 `<pre>` 等寬文字區塊，不會顯示成一般文字的 `&lt;pre&gt;` 標籤，讓 Telegram 呈現接近程式碼與表格的對齊效果。

## 保留 Markdown 格式

若希望切割後的 `telegram-message.txt` 與 `telegram-message.json` 保留 Markdown 寫法，而不是轉成 HTML，請使用：

```bash
python .agents/skills/telegram-result-message/scripts/convert_result.py \
  artifacts/{issue-comment-id}/result.md \
  --parse-mode markdown \
  --max-chars 3500
```

這個模式會保留標題、粗體、行內程式碼、程式碼區塊、連結、清單與表格的 Markdown 原文，只做空白整理與分批切割。

## 分批傳送格式

當訊息超過限制時，每則訊息前面會加上：

```text
第 1/3 則
```

讓 Telegram 接收者知道目前閱讀順序。
