---
name: skill-exporter
description: Use this skill when you need to export, package, document, validate, install, or import an Agent Skill so it can be reused in another 小龍蝦 workspace or repository. This includes one-click skill export, creating .skill archives, generating install manifests, copying bundled scripts/references/assets, and writing README documentation for portable skill distribution.
---

# Skill Exporter

Use this skill to export an existing skill folder into a portable bundle that another 小龍蝦 workspace can import or install reliably.

## Goals

- Locate and validate a source skill directory.
- Confirm required skill files are present and safe to package.
- Generate or refresh user-facing documentation.
- Create a portable `.skill` archive and checksum.
- Produce an install manifest describing how to install the skill elsewhere.
- Keep export output self-contained, predictable, and easy to transfer.

## Inputs

Required:

- `skill_path`: path to the skill directory, for example `.agents/skills/telegram-result-message`.

Optional:

- `output_dir`: export destination. Default: `artifacts/{issue-comment-id}/skill-export/` when an issue comment id is known, otherwise `artifacts/skill-export/`.
- `include_docs`: whether to generate or refresh `README.md`. Default: `true`.
- `archive_name`: custom archive filename. Default: `{skill-name}.skill`.
- `install_target`: suggested installation path in the receiving workspace. Default: `.agents/skills/{skill-name}`.

## Recommended workflow

Use the bundled exporter for repeatable one-command exports:

```bash
python .agents/skills/skill-exporter/scripts/export_skill.py \
  .agents/skills/{skill-name} \
  --output-dir artifacts/{issue-comment-id}/skill-export
```

To export without changing or generating README documentation:

```bash
python .agents/skills/skill-exporter/scripts/export_skill.py \
  .agents/skills/{skill-name} \
  --output-dir artifacts/{issue-comment-id}/skill-export \
  --no-docs
```

The script validates the skill before packaging and writes all export files into the output directory.

## Output

A successful export creates:

- `{skill-name}.skill`: portable zip archive using the `.skill` extension.
- `{skill-name}.sha256`: checksum for transfer verification.
- `install-manifest.json`: machine-readable install metadata.
- `INSTALL.md`: human-readable install guide.
- `export-report.md`: summary of included files, warnings, and validation results.

## Export rules

### 1. Validate the source skill

Before exporting, check that:

- `SKILL.md` exists.
- `SKILL.md` has YAML frontmatter with `name` and `description`.
- The frontmatter `name` matches a safe skill identifier: lowercase letters, numbers, and hyphens.
- Referenced bundled directories such as `scripts/`, `references/`, or `assets/` are included when present.

If validation fails, stop and report what must be fixed before export.

### 2. Keep the bundle portable

Include normal skill resources:

- `SKILL.md`
- `README.md`
- `githubclaw.json` or other manifest files
- `scripts/`
- `references/`
- `assets/`
- `evals/` when the skill includes reusable tests

Exclude transient or unsafe files:

- `.git/`
- `.pi/`
- `__pycache__/`
- `.pytest_cache/`
- `.DS_Store`
- `*.pyc`
- temporary logs or local-only workspace output

### 3. Generate documentation like a reusable tool

When `include_docs` is enabled and `README.md` is missing, create it with:

1. Skill name and short purpose.
2. Appropriate use cases.
3. Inputs.
4. Main workflow or commands.
5. Exported or generated outputs.
6. Installation instructions for another workspace.
7. Validation checklist.

Do not overwrite an existing `README.md` unless the user explicitly asks to refresh it.

### 4. Install manifest format

Write `install-manifest.json` with this shape:

```json
{
  "schema_version": "1.0",
  "skill_name": "example-skill",
  "archive": "example-skill.skill",
  "sha256": "...",
  "created_at": "2026-05-17T00:00:00Z",
  "source_path": ".agents/skills/example-skill",
  "install_target": ".agents/skills/example-skill",
  "included_files": ["SKILL.md", "README.md"]
}
```

### 5. Installation guidance

In `INSTALL.md`, explain the simplest install path:

```bash
mkdir -p .agents/skills/{skill-name}
python - <<'PY'
import zipfile
zipfile.ZipFile('path/to/{skill-name}.skill').extractall('.agents/skills/{skill-name}')
PY
```

Then tell the receiving 小龍蝦 to verify that `.agents/skills/{skill-name}/SKILL.md` exists and that the skill appears in the available skills list on the next run.

## Validation checklist

Before reporting success:

- Confirm the `.skill` archive exists and is not empty.
- Confirm the archive contains `SKILL.md` at its root.
- Confirm `README.md`, `INSTALL.md`, `install-manifest.json`, and checksum files were created when expected.
- Open the archive with Python `zipfile` or `unzip -l` to verify file names.
- Confirm excluded files such as `.pi`, `.git`, `__pycache__`, and `*.pyc` are not present.
- Confirm install instructions reference the correct skill name and target path.

## When manual export is needed

If the script cannot be used, manually copy the skill to a staging directory, remove excluded files, zip the staged contents so `SKILL.md` is at the archive root, calculate SHA-256, and write the same manifest and install guide files described above.
