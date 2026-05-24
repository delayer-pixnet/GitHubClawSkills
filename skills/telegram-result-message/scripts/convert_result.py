#!/usr/bin/env python3
"""Convert an artifact result.md into Telegram-ready batched messages."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Iterable, List, Optional

SUPPORTED_PARSE_MODES = {"plain", "html", "markdown"}


def is_markdown_table_block(lines: list[str]) -> bool:
    if len(lines) < 2:
        return False
    if not ("|" in lines[0] and "|" in lines[1]):
        return False
    separator = lines[1].strip()
    return bool(re.match(r"^\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?$", separator))


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def render_markdown_table_block(lines: list[str]) -> str:
    rows = [split_table_row(line) for index, line in enumerate(lines) if index != 1]
    if not rows:
        return ""
    column_count = max(len(row) for row in rows)
    normalized = [row + [""] * (column_count - len(row)) for row in rows]
    widths = [max(len(row[col]) for row in normalized) for col in range(column_count)]

    rendered: list[str] = []
    for row_index, row in enumerate(normalized):
        rendered.append(" | ".join(row[col].ljust(widths[col]) for col in range(column_count)).rstrip())
        if row_index == 0:
            rendered.append("-+-".join("-" * widths[col] for col in range(column_count)))
    return "\n".join(rendered)


def convert_markdown_tables(text: str, *, html_mode: bool = False) -> str:
    lines = text.splitlines()
    output: list[str] = []
    index = 0
    while index < len(lines):
        if index + 1 < len(lines) and is_markdown_table_block(lines[index:index + 2]):
            table_lines = [lines[index], lines[index + 1]]
            index += 2
            while index < len(lines) and "|" in lines[index].strip() and lines[index].strip():
                table_lines.append(lines[index])
                index += 1
            rendered = render_markdown_table_block(table_lines)
            if html_mode:
                output.append(f"<pre>{html.escape(rendered)}</pre>")
            else:
                output.append(rendered)
            continue
        output.append(lines[index])
        index += 1
    return "\n".join(output)


def markdown_to_plain(text: str) -> str:
    text = convert_markdown_tables(text)
    text = re.sub(r"```(?:\w+)?\n([\s\S]*?)```", lambda m: m.group(1).strip(), text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1: \2", text)
    text = re.sub(r"^(#{1,6})\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"(?<!\*)\*\*([^*]+)\*\*(?!\*)", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    return normalize_blank_lines(text.strip())


def markdown_to_markdown(text: str) -> str:
    """Convert Markdown into Telegram legacy Markdown safely.

    Telegram 的 legacy Markdown 可以呈現粗體、斜體、行內程式碼、程式碼區塊與連結，
    但對未成對的底線、星號與中途切斷的程式碼區塊很敏感。這裡保留常用樣式，
    並把 Telegram 不支援的 Markdown 表格改成 fenced code block，避免送出失敗。
    """
    text = convert_markdown_tables_to_fenced_code(text)
    text = re.sub(r"^#{1,6}\s+(.+)$", lambda m: f"*{escape_telegram_markdown_inline(m.group(1).strip())}*", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]+)\*\*", lambda m: f"*{escape_telegram_markdown_inline(m.group(1))}*", text)
    text = re.sub(r"__([^_]+)__", lambda m: f"*{escape_telegram_markdown_inline(m.group(1))}*", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", lambda m: f"_{escape_telegram_markdown_inline(m.group(1))}_", text)
    text = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", lambda m: f"_{escape_telegram_markdown_inline(m.group(1))}_", text)
    return normalize_blank_lines(sanitize_telegram_markdown(text.strip()))


def convert_markdown_tables_to_fenced_code(text: str) -> str:
    lines = text.splitlines()
    output: list[str] = []
    index = 0
    while index < len(lines):
        if index + 1 < len(lines) and is_markdown_table_block(lines[index:index + 2]):
            table_lines = [lines[index], lines[index + 1]]
            index += 2
            while index < len(lines) and "|" in lines[index].strip() and lines[index].strip():
                table_lines.append(lines[index])
                index += 1
            rendered = render_markdown_table_block(table_lines)
            output.append(f"```\n{rendered}\n```")
            continue
        output.append(lines[index])
        index += 1
    return "\n".join(output)


def escape_telegram_markdown_inline(text: str) -> str:
    return text.replace("`", "'").replace("[", "\\[")


def sanitize_telegram_markdown(text: str) -> str:
    """Make legacy Markdown parsable while preserving supported visual formatting."""
    parts = re.split(r"(```[\s\S]*?```|`[^`\n]*`|\[[^\]]+\]\([^\)]+\))", text)
    sanitized: list[str] = []
    for part in parts:
        if not part:
            continue
        if part.startswith("```") or part.startswith("`") or re.match(r"^\[[^\]]+\]\([^\)]+\)$", part):
            sanitized.append(part)
            continue
        part = part.replace("[", "\\[")
        part = escape_unbalanced_markers(part, "*")
        part = escape_unbalanced_markers(part, "_")
        sanitized.append(part)
    return "".join(sanitized)


def escape_unbalanced_markers(text: str, marker: str) -> str:
    positions = [m.start() for m in re.finditer(re.escape(marker), text)]
    if len(positions) % 2 == 0:
        return text
    last = positions[-1]
    return text[:last] + "\\" + text[last:]


def markdown_to_telegram_html(text: str) -> str:
    text = convert_markdown_tables(text, html_mode=True)
    protected_blocks: list[str] = []

    def protect(block: str) -> str:
        protected_blocks.append(block)
        return f"@@TGHTMLBLOCK{len(protected_blocks) - 1}@@"

    def stash_code_block(match: re.Match[str]) -> str:
        language = match.group(1) or ""
        code = match.group(2).strip("\n")
        escaped_code = html.escape(code)
        if language:
            escaped_code = f"{html.escape(language)}\n{escaped_code}"
        return protect(f"<pre>{escaped_code}</pre>")

    text = re.sub(r"```([^\n`]*)\n([\s\S]*?)```", stash_code_block, text)

    def stash_existing_pre(match: re.Match[str]) -> str:
        return protect(match.group(0))

    text = re.sub(r"<pre>[\s\S]*?</pre>", stash_existing_pre, text)
    text = html.escape(text)

    text = re.sub(
        r"^#{1,6}\s+(.+)$",
        lambda m: f"<b>{m.group(1).strip()}</b>",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"(?:^&gt; ?.*(?:\n|$))+",
        lambda m: "<blockquote>" + re.sub(r"^&gt; ?", "", m.group(0), flags=re.MULTILINE).strip() + "</blockquote>",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(r"`([^`]+)`", lambda m: protect(f"<code>{m.group(1)}</code>"), text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{html.escape(html.unescape(m.group(2)), quote=True)}">{m.group(1)}</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__([^_]+)__", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"<i>\1</i>", text)
    for i, block in enumerate(protected_blocks):
        text = text.replace(f"@@TGHTMLBLOCK{i}@@", block)
    return compact_pre_blocks(normalize_blank_lines(text.strip()))


def normalize_blank_lines(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def compact_pre_blocks(text: str) -> str:
    def compact(match: re.Match[str]) -> str:
        inner = re.sub(r"\n\s*\n+", "\n", match.group(1).strip("\n"))
        return f"<pre>{inner}</pre>"

    return re.sub(r"<pre>([\s\S]*?)</pre>", compact, text)


def add_raw_links(text: str, owner: str | None, repo: str | None, branch: str | None, issue_comment_id: str | None) -> str:
    if not all([owner, repo, branch, issue_comment_id]):
        return text
    pattern = re.compile(rf"artifacts/{re.escape(issue_comment_id)}/([^\s)]+)")
    seen: list[str] = []
    for match in pattern.finditer(text):
        filename = match.group(1).rstrip(".,")
        if filename.startswith(".pi") or "/.pi/" in filename:
            continue
        if filename not in seen:
            seen.append(filename)
    if not seen:
        return text
    links = ["", "檔案連結："]
    for filename in seen:
        links.append(f"- {filename}: https://github.com/{owner}/{repo}/blob/{branch}/artifacts/{issue_comment_id}/{filename}?raw=true")
    return text.rstrip() + "\n" + "\n".join(links)


def split_units(text: str) -> list[str]:
    sections = re.split(r"\n(?=\S)", text)
    units: list[str] = []
    for section in sections:
        paragraphs = re.split(r"\n\s*\n", section.strip())
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            bullet_lines = paragraph.splitlines()
            if len(bullet_lines) > 1 and any(re.match(r"^\s*(?:[-*]|\d+[.)])\s+", line) for line in bullet_lines):
                buffer: list[str] = []
                for line in bullet_lines:
                    if re.match(r"^\s*(?:[-*]|\d+[.)])\s+", line) and buffer:
                        units.append("\n".join(buffer).strip())
                        buffer = [line]
                    else:
                        buffer.append(line)
                if buffer:
                    units.append("\n".join(buffer).strip())
            else:
                units.append(paragraph.strip())
    return units


def hard_split(text: str, limit: int) -> Iterable[str]:
    text = text.strip()
    if not text:
        return

    total = max(1, (len(text) + limit - 1) // limit)
    target = max(1, (len(text) + total - 1) // total)
    parts: list[str] = []

    while len(text) > limit:
        preferred = min(limit, max(target, len(text) - limit * (total - len(parts) - 1)))
        cut = text.rfind("\n\n", 0, preferred + 1)
        if cut < preferred // 2:
            cut = text.rfind("\n", 0, preferred + 1)
        if cut < preferred // 2:
            cut = text.rfind(" ", 0, preferred + 1)
        if cut < preferred // 2:
            cut = preferred
        parts.append(text[:cut].strip())
        text = text[cut:].strip()

    if text:
        parts.append(text)
    yield from (part for part in parts if part)


def protect_markdown_fences_for_batch(text: str) -> str:
    """Keep every batch independently parsable by closing/reopening code blocks at boundaries."""
    return text


def split_markdown_safe(text: str, limit: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    in_fence = False
    for line in text.splitlines(keepends=True):
        candidate = current + line
        if len(candidate) > limit and current:
            closing = "\n```" if in_fence and not current.rstrip().endswith("```") else ""
            chunk = (current.rstrip() + closing).strip()
            chunks.append(chunk)
            current = ("```\n" if in_fence else "") + line
        else:
            current = candidate
        if line.strip().startswith("```"):
            in_fence = not in_fence
    if current.strip():
        if in_fence and not current.rstrip().endswith("```"):
            current = current.rstrip() + "\n```"
        chunks.append(current.strip())
    final: list[str] = []
    for chunk in chunks:
        if len(chunk) <= limit:
            final.append(chunk)
        else:
            final.extend(hard_split(chunk, limit))
    return final


def balanced_batch_limit(max_chars: int, total: int) -> int:
    """Reserve enough room for the largest possible batch prefix."""
    if total <= 1:
        return max_chars
    prefix_len = len(f"第 {total}/{total} 則\n")
    return max_chars - prefix_len


def rebalance_batches(batches: list[str], max_chars: int, parse_mode: str = "html") -> list[str]:
    """Make batch sizes more even while keeping final messages under max_chars."""
    clean_batches = [batch.strip() for batch in batches if batch.strip()]
    if len(clean_batches) <= 1:
        return clean_batches

    content = "\n\n".join(clean_batches)
    total = max(2, (len(content) + max_chars - 1) // max_chars)
    while True:
        limit = balanced_batch_limit(max_chars, total)
        if limit <= 0:
            raise ValueError("max_chars is too small for batch prefix")
        next_total = max(2, (len(content) + limit - 1) // limit)
        if next_total == total:
            break
        total = next_total

    target = max(1, (len(content) + total - 1) // total)
    units = split_units(content)
    balanced: list[str] = []
    current = ""

    for unit in units:
        if len(unit) > limit:
            if current:
                balanced.append(current.strip())
                current = ""
            splitter = split_markdown_safe if parse_mode == "markdown" else hard_split
            balanced.extend(part.strip() for part in splitter(unit, limit) if part.strip())
            continue

        candidate = f"{current}\n\n{unit}".strip() if current else unit
        should_close = current and len(candidate) > target and len(balanced) < total - 1
        if len(candidate) <= limit and not should_close:
            current = candidate
        else:
            if current:
                balanced.append(current.strip())
            current = unit

    if current:
        balanced.append(current.strip())

    if len(balanced) > total:
        merged: list[str] = []
        for batch in balanced:
            candidate = f"{merged[-1]}\n\n{batch}".strip() if merged else batch
            if merged and len(candidate) <= limit:
                merged[-1] = candidate
            else:
                merged.append(batch)
        balanced = merged

    return balanced


def split_with_prefix_budget(batches: list[str], max_chars: int, parse_mode: str = "html") -> list[str]:
    """Add batch prefixes without producing any message over max_chars."""
    if len(batches) <= 1:
        return batches

    result = rebalance_batches(batches, max_chars, parse_mode)
    while True:
        total = len(result)
        prefixed: list[str] = []
        changed = False
        for index, batch in enumerate(result, start=1):
            prefix = f"第 {index}/{total} 則\n"
            budget = max_chars - len(prefix)
            if budget <= 0:
                raise ValueError("max_chars is too small for batch prefix")
            if len(batch) <= budget:
                prefixed.append(prefix + batch)
                continue
            changed = True
            splitter = split_markdown_safe if parse_mode == "markdown" else hard_split
            prefixed.extend(prefix + part for part in splitter(batch, budget))
        if not changed and all(len(message) <= max_chars for message in prefixed):
            return prefixed
        result = [message.split("\n", 1)[1] if message.startswith("第 ") and "\n" in message else message for message in prefixed]


def validate_telegram_html(text: str) -> Optional[str]:
    token_re = re.compile(r"</?(b|strong|i|em|u|ins|s|strike|del|code|pre|blockquote)(?:\s[^>]*)?>|<a\s+href=\"[^\"]*\">|</a>", re.I)
    aliases = {"strong": "b", "em": "i", "ins": "u", "strike": "s", "del": "s"}
    stack: list[str] = []
    for match in token_re.finditer(text):
        token = match.group(0)
        closing = token.startswith("</")
        name_match = re.match(r"</?([a-z]+)", token, re.I)
        if not name_match:
            continue
        name = aliases.get(name_match.group(1).lower(), name_match.group(1).lower())
        if closing:
            if not stack or stack[-1] != name:
                expected = stack[-1] if stack else "none"
                return f"unmatched end tag {token}, expected </{expected}>"
            stack.pop()
        else:
            stack.append(name)
    if stack:
        return f"unclosed tag <{stack[-1]}>"
    return None


def batch_messages(text: str, max_chars: int, parse_mode: str = "html") -> List[str]:
    protected_blocks: list[str] = []

    def protect(match: re.Match[str]) -> str:
        protected_blocks.append(match.group(0))
        return f"@@BATCHPRE{len(protected_blocks) - 1}@@"

    protected_pattern = r"<pre>[\s\S]*?</pre>" if parse_mode == "html" else r"```[\s\S]*?```"
    protected_text = re.sub(protected_pattern, protect, text)
    units = split_units(protected_text)
    batches: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}".strip() if current else unit
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            batches.append(current)
            current = ""
        if len(unit) <= max_chars:
            current = unit
        else:
            if parse_mode == "markdown":
                batches.extend(split_markdown_safe(unit, max_chars))
            else:
                batches.extend(hard_split(unit, max_chars))
    if current:
        batches.append(current)

    for block_index, block in enumerate(protected_blocks):
        batches = [batch.replace(f"@@BATCHPRE{block_index}@@", block) for batch in batches]

    expanded: list[str] = []
    for batch in batches:
        if len(batch) <= max_chars:
            expanded.append(batch)
        else:
            if parse_mode == "markdown":
                expanded.extend(split_markdown_safe(batch, max_chars))
            else:
                expanded.extend(hard_split(batch, max_chars))

    return split_with_prefix_budget(expanded, max_chars, parse_mode)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_path")
    parser.add_argument("--parse-mode", default="html", choices=sorted(SUPPORTED_PARSE_MODES))
    parser.add_argument("--max-chars", type=int, default=3500)
    parser.add_argument("--owner")
    parser.add_argument("--repo")
    parser.add_argument("--branch")
    parser.add_argument("--issue-comment-id")
    args = parser.parse_args()

    result_path = Path(args.result_path)
    source = result_path.read_text(encoding="utf-8")
    if args.parse_mode == "plain":
        converted = markdown_to_plain(source)
    elif args.parse_mode == "markdown":
        converted = markdown_to_markdown(source)
    else:
        converted = markdown_to_telegram_html(source)
    converted = add_raw_links(converted, args.owner, args.repo, args.branch, args.issue_comment_id)
    if args.parse_mode == "html":
        html_error = validate_telegram_html(converted)
        if html_error:
            raise SystemExit(f"invalid Telegram HTML: {html_error}")

    messages = batch_messages(converted, args.max_chars, args.parse_mode)

    artifact_dir = result_path.parent
    txt_path = artifact_dir / "telegram-message.txt"
    json_path = artifact_dir / "telegram-message.json"
    txt_path.write_text("\n\n".join(f"--- message {i}/{len(messages)} ---\n{message}" for i, message in enumerate(messages, 1)), encoding="utf-8")
    payload = {
        "parse_mode": args.parse_mode,
        "source": str(result_path),
        "count": len(messages),
        "max_chars": args.max_chars,
        "messages": [
            {"index": i, "total": len(messages), "text": message, "length": len(message)}
            for i, message in enumerate(messages, 1)
        ],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if any(len(message) > args.max_chars for message in messages):
        raise SystemExit("generated message exceeds max_chars")
    print(f"wrote {txt_path} and {json_path} ({len(messages)} message(s))")


if __name__ == "__main__":
    main()
