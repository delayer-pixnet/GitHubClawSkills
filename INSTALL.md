# 安裝 GitHubClawSkills

本文件說明如何把本倉庫的 Skills 安裝到另一個小龍蝦工作區。

## 前置需求

- 目標 Repo 根目錄可建立 `.agents/skills/`。
- 已安裝 Python 3。
- 若使用 `telegram-result-message`，需要有可讀取的 `artifacts/{issue-comment-id}/result.md`。

## 安裝全部 Skills

在目標 Repo 根目錄執行：

```bash
mkdir -p .agents/skills
cp -R skills/skill-exporter .agents/skills/
cp -R skills/telegram-result-message .agents/skills/
```

## 只安裝單一 Skill

```bash
mkdir -p .agents/skills
cp -R skills/skill-exporter .agents/skills/
```

或：

```bash
mkdir -p .agents/skills
cp -R skills/telegram-result-message .agents/skills/
```

## 使用 `.skill` 封裝檔安裝

```bash
mkdir -p .agents/skills/skill-exporter
python - <<'PY'
import zipfile
zipfile.ZipFile('path/to/skill-exporter.skill').extractall('.agents/skills/skill-exporter')
PY
```

```bash
mkdir -p .agents/skills/telegram-result-message
python - <<'PY'
import zipfile
zipfile.ZipFile('path/to/telegram-result-message.skill').extractall('.agents/skills/telegram-result-message')
PY
```

## 安裝後確認

```bash
test -f .agents/skills/skill-exporter/SKILL.md
test -f .agents/skills/telegram-result-message/SKILL.md
python .agents/skills/skill-exporter/scripts/export_skill.py --help
python .agents/skills/telegram-result-message/scripts/convert_result.py --help
```

下一次啟動工作區時，已安裝的 Skills 應會出現在可用技能清單中。
