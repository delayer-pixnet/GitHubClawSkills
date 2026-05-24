# GitHubClawSkills

可重複使用的小龍蝦 Agent Skills 集合。本倉庫目前整理並同步以下技能，提供外部使用者下載、安裝與匯入到自己的工作區。

## 目前提供的 Skills

| Skill | 說明 |
|---|---|
| `skill-exporter` | 將 `.agents/skills/{skill-name}` 打包成可攜式 `.skill` 封裝，並產生安裝文件、清單、校驗碼與匯出報告。 |
| `telegram-result-message` | 將 `artifacts/{issue-comment-id}/result.md` 轉成 Telegram 可發送訊息，支援 HTML/Markdown 格式與超長內容分批。 |

## 快速安裝

### 方法一：直接複製技能資料夾

在你的 Repo 根目錄執行：

```bash
mkdir -p .agents/skills
cp -R skills/skill-exporter .agents/skills/
cp -R skills/telegram-result-message .agents/skills/
```

確認檔案存在：

```bash
test -f .agents/skills/skill-exporter/SKILL.md
test -f .agents/skills/telegram-result-message/SKILL.md
```

### 方法二：使用 `.skill` 封裝檔安裝

下載 Releases 或 artifacts 中的 `.skill` 檔後，在目標 Repo 根目錄執行：

```bash
mkdir -p .agents/skills/skill-exporter
python - <<'PY'
import zipfile
zipfile.ZipFile('path/to/skill-exporter.skill').extractall('.agents/skills/skill-exporter')
PY

mkdir -p .agents/skills/telegram-result-message
python - <<'PY'
import zipfile
zipfile.ZipFile('path/to/telegram-result-message.skill').extractall('.agents/skills/telegram-result-message')
PY
```

## 使用方式

### skill-exporter

```bash
python .agents/skills/skill-exporter/scripts/export_skill.py \
  .agents/skills/telegram-result-message \
  --output-dir artifacts/{issue-comment-id}/skill-export
```

輸出包含：

- `{skill-name}.skill`
- `{skill-name}.sha256`
- `install-manifest.json`
- `INSTALL.md`
- `export-report.md`

### telegram-result-message

```bash
python .agents/skills/telegram-result-message/scripts/convert_result.py \
  artifacts/{issue-comment-id}/result.md \
  --parse-mode html \
  --max-chars 3500
```

輸出包含：

- `telegram-message.txt`
- `telegram-message.json`

## 建議 Repo 結構

```text
GitHubClawSkills/
├── README.md
├── INSTALL.md
└── skills/
    ├── skill-exporter/
    │   ├── README.md
    │   ├── SKILL.md
    │   └── scripts/
    └── telegram-result-message/
        ├── README.md
        ├── SKILL.md
        ├── githubclaw.json
        └── scripts/
```

## 驗證

安裝後可用以下方式檢查：

```bash
find .agents/skills/skill-exporter -maxdepth 2 -type f | sort
find .agents/skills/telegram-result-message -maxdepth 2 -type f | sort
python .agents/skills/skill-exporter/scripts/export_skill.py --help
python .agents/skills/telegram-result-message/scripts/convert_result.py --help
```

## 授權

請依你的新 Repo 需求補上授權條款，例如 MIT、Apache-2.0 或內部使用授權。
