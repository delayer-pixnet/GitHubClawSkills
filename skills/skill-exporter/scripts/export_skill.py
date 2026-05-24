#!/usr/bin/env python3
"""Export an Agent Skill as a portable .skill archive with docs and manifest."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

EXCLUDED_DIRS = {".git", ".pi", "__pycache__", ".pytest_cache"}
EXCLUDED_FILES = {".DS_Store"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp"}
SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")


def parse_frontmatter(skill_md: Path) -> dict[str, str]:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter delimited by ---")
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError("SKILL.md frontmatter closing --- not found")
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line or line.strip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"\'')
    return data


def should_include(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in EXCLUDED_DIRS for part in rel.parts):
        return False
    if path.name in EXCLUDED_FILES:
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def ensure_readme(skill_path: Path, name: str, description: str, install_target: str) -> bool:
    readme = skill_path / "README.md"
    if readme.exists():
        return False
    readme.write_text(f"""# {name}

{description}

## 適合情境

- 需要使用 `{name}` 技能完成其描述的工作。
- 需要將此技能安裝到其他小龍蝦工作區重複使用。

## 主要能力

請參考 `SKILL.md` 的完整技能指引。

## 安裝方式

將匯出的 `{name}.skill` 解壓縮到：

```text
{install_target}
```

確認 `{install_target}/SKILL.md` 存在後，下一次執行即可使用。

## 驗證清單

- `SKILL.md` 存在。
- frontmatter 包含 `name` 與 `description`。
- 需要的 `scripts/`、`references/` 或 `assets/` 已一併複製。
""", encoding="utf-8")
    return True


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Export an Agent Skill to a portable .skill archive")
    parser.add_argument("skill_path", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/skill-export"))
    parser.add_argument("--archive-name")
    parser.add_argument("--install-target")
    parser.add_argument("--no-docs", action="store_true")
    args = parser.parse_args()

    skill_path = args.skill_path.resolve()
    if not skill_path.is_dir():
        raise SystemExit(f"Skill path not found: {skill_path}")
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        raise SystemExit("Validation failed: SKILL.md is required")

    meta = parse_frontmatter(skill_md)
    name = meta.get("name", "")
    description = meta.get("description", "")
    if not name or not description:
        raise SystemExit("Validation failed: SKILL.md frontmatter requires name and description")
    if not SAFE_NAME.match(name):
        raise SystemExit(f"Validation failed: unsafe skill name: {name}")

    install_target = args.install_target or f".agents/skills/{name}"
    readme_created = False
    if not args.no_docs:
        readme_created = ensure_readme(skill_path, name, description, install_target)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_name = args.archive_name or f"{name}.skill"
    if not archive_name.endswith(".skill"):
        archive_name += ".skill"
    archive_path = output_dir / archive_name

    files = sorted([p for p in skill_path.rglob("*") if should_include(p, skill_path)], key=lambda p: str(p.relative_to(skill_path)))
    if skill_md not in files:
        raise SystemExit("Validation failed: SKILL.md would not be included")

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, path.relative_to(skill_path).as_posix())

    digest = sha256_file(archive_path)
    sha_path = output_dir / f"{Path(archive_name).stem}.sha256"
    sha_path.write_text(f"{digest}  {archive_name}\n", encoding="utf-8")

    included = [p.relative_to(skill_path).as_posix() for p in files]
    manifest = {
        "schema_version": "1.0",
        "skill_name": name,
        "archive": archive_name,
        "sha256": digest,
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_path": str(args.skill_path),
        "install_target": install_target,
        "included_files": included,
    }
    (output_dir / "install-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    install_md = f"""# Install {name}

## Files

- `{archive_name}`
- `{sha_path.name}`
- `install-manifest.json`

## Install

From the receiving workspace root:

```bash
mkdir -p {install_target}
python - <<'PY'
import zipfile
zipfile.ZipFile('path/to/{archive_name}').extractall('{install_target}')
PY
```

## Verify

```bash
test -f {install_target}/SKILL.md
python - <<'PY'
import zipfile
with zipfile.ZipFile('path/to/{archive_name}') as z:
    assert 'SKILL.md' in z.namelist()
print('archive ok')
PY
```
"""
    (output_dir / "INSTALL.md").write_text(install_md, encoding="utf-8")

    with zipfile.ZipFile(archive_path) as zf:
        names = zf.namelist()
    forbidden = [n for n in names if any(part in EXCLUDED_DIRS for part in Path(n).parts) or n.endswith(tuple(EXCLUDED_SUFFIXES))]
    report = f"""# Skill Export Report

## Status

✅ Export completed.

## Skill

- Name: `{name}`
- Source: `{args.skill_path}`
- Archive: `{archive_path}`
- SHA-256: `{digest}`
- README created: `{str(readme_created).lower()}`

## Validation

- `SKILL.md` included: `{'SKILL.md' in names}`
- Archive file count: `{len(names)}`
- Forbidden files found: `{len(forbidden)}`

## Included files

""" + "\n".join(f"- `{item}`" for item in included) + "\n"
    (output_dir / "export-report.md").write_text(report, encoding="utf-8")

    if forbidden:
        raise SystemExit(f"Export created but forbidden files were found: {forbidden}")
    print(json.dumps({"archive": str(archive_path), "sha256": digest, "files": len(included)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
