---
name: telegram-result-message
description: Use this skill when you need to convert an artifact result.md into Telegram-ready messages, including safe formatting and batched sending support.
---

# Telegram Result Message

Use this skill to turn `artifacts/{issue-comment-id}/result.md` into one or more Telegram-ready text messages.

## Goals

- Read a completed `result.md` artifact.
- Extract the important user-facing outcome.
- Convert Markdown into Telegram-safe plain text or Telegram-safe HTML.
- Preserve supported Markdown-style presentation through Telegram-compatible formatting.
- Convert unsupported Markdown tables into monospaced table blocks that Telegram can display clearly.
- Split long output into ordered batches that can be sent one by one.
- Keep every batch understandable on its own.

## Inputs

Required:

- `result_path`: path to the source result file, usually `artifacts/{issue-comment-id}/result.md`.

Optional:

- `parse_mode`: `plain`, `markdown`, or `html`. Default: `html`.
- `max_chars`: maximum characters per Telegram message. Default: `3500` to leave margin below Telegram's 4096-character limit.
- `owner`, `repo`, `branch`: used to turn artifact paths into raw GitHub URLs.
- `issue_comment_id`: artifact directory id, used in generated file links.

## Recommended workflow

Use the bundled converter for repeatable transformations:

```bash
python .agents/skills/telegram-result-message/scripts/convert_result.py \
  artifacts/{issue-comment-id}/result.md \
  --parse-mode html \
  --max-chars 3500
```

If you want the generated `telegram-message.txt` and `telegram-message.json` to keep Markdown syntax instead of converting Markdown to Telegram HTML, use:

```bash
python .agents/skills/telegram-result-message/scripts/convert_result.py \
  artifacts/{issue-comment-id}/result.md \
  --parse-mode markdown \
  --max-chars 3500
```

When raw artifact URLs are useful, also pass:

```bash
--owner {owner} --repo {repo} --branch {branch} --issue-comment-id {issue-comment-id}
```

If the script cannot cover a special case, follow the conversion rules below manually and still produce the same output files.

## Output

Write converted messages into the same artifact directory as:

- `telegram-message.txt`: all batches separated by `--- message {n}/{total} ---` markers.
- `telegram-message.json`: machine-readable list of messages for senders that support batch loops.

Recommended JSON shape:

```json
{
  "parse_mode": "html",
  "source": "artifacts/{issue-comment-id}/result.md",
  "count": 2,
  "messages": [
    { "index": 1, "total": 2, "text": "..." },
    { "index": 2, "total": 2, "text": "..." }
  ]
}
```

## Conversion Rules

### 1. Prefer concise Telegram copy

Start with a status line when it can be inferred:

- `✅ 任務完成`
- `⚠️ 任務遇到阻塞`
- `❌ 任務未完成`

Then include only the most useful sections:

1. Summary / result
2. Deliverables and artifact paths
3. Important warnings or next steps
4. Links, when available

### 2. Preserve supported Markdown presentation

Use `--parse-mode html` by default so Telegram can render common Markdown semantics safely.
Use `--parse-mode markdown` when the output files should retain Markdown syntax and avoid generated HTML tags.

In `markdown` mode:

- Keep headings, bold markers, inline code markers, fenced code blocks, links, lists, blockquotes, and Markdown tables as Markdown.
- Still split long content into batches and add batch prefixes when needed.
- Set `telegram-message.json.parse_mode` to `markdown` so senders can decide whether to send it as plain text or Markdown-compatible Telegram formatting.

In `html` mode:

- Markdown headings become bold section titles.
- `**bold**` and `__bold__` become Telegram `<b>` formatting.
- Inline code becomes Telegram `<code>` formatting.
- Code blocks become Telegram `<pre>` formatting and must not be escaped into visible `&lt;pre&gt;` text.
- Markdown blockquotes become Telegram `<blockquote>` formatting.
- Markdown links become Telegram clickable `<a href="...">` links.

Telegram does not support full GitHub-flavored Markdown directly, so do not send raw Markdown tables or unsupported HTML tags.

### 3. Markdown tables

Telegram does not support Markdown table rendering. When a table is found, convert it into a monospaced aligned text table and wrap it in `<pre>...</pre>` in `html` mode.

Example source:

```markdown
| 參數 | 必填 | 說明 |
|---|---:|---|
| issue_number | 是 | Issue 編號 |
```

Telegram-friendly output:

```html
<pre>參數         | 必填 | 說明
-------------+------+-----------
issue_number | 是   | Issue 編號</pre>
```

This keeps table-like visual alignment inside Telegram even though Telegram has no native table support.

### 4. Remove Markdown that Telegram does not need

For `plain` mode:

- Remove heading markers (`#`, `##`, etc.) but keep the heading text.
- Convert Markdown links `[text](url)` to `text: url`.
- Convert bold/code markers to normal readable text.
- Keep bullets as `-` or numbered items.
- Keep fenced code block content, but remove the fences when space is limited.

For `html` mode:

- Escape `&`, `<`, and `>` in normal text.
- Use only Telegram-supported tags when needed: `<b>`, `<i>`, `<u>`, `<s>`, `<code>`, `<pre>`, and `<a href="...">`.
- Do not emit unsupported HTML tags.

### 5. File links

When `owner`, `repo`, `branch`, and an artifact path are known, append raw GitHub links using this format:

```text
https://github.com/{owner}/{repo}/blob/{branch}/artifacts/{issue-comment-id}/{filename}?raw=true
```

Do not include `.pi` paths or internal system files in Telegram messages.

### 6. Batch splitting

Telegram messages must stay below `max_chars`.

Splitting order:

1. Split on section boundaries first, such as blank lines before headings.
2. Then split on paragraph boundaries.
3. Then split on bullet boundaries.
4. Only split inside a long line as the last resort.

Every batch must include a prefix when there is more than one batch:

```text
第 {index}/{total} 則
```

Keep the prefix included in the character budget.

### 7. Validation checklist

Before using the generated messages:

- Confirm every message length is less than or equal to `max_chars`.
- Confirm batch order is stable and complete.
- Confirm artifact paths exclude `.pi` and system output unless explicitly requested.
- Confirm `html` mode has escaped special characters and only supported tags.
- Confirm Markdown tables are converted to aligned monospaced blocks instead of raw pipe tables.
- Confirm the output can be sent independently by a Telegram sender loop.

## Sender Loop Usage

A sender can read `telegram-message.json` and send each item in order:

```pseudo
payload = read_json("telegram-message.json")
for message in payload.messages:
    telegram.send_message(text=message.text, parse_mode=payload.parse_mode)
```
