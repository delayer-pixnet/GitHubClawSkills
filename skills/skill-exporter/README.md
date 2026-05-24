# Skill Exporter

一鍵匯出 Agent Skill，產生可在其他小龍蝦工作區匯入或安裝的 `.skill` 封裝檔，並附上安裝文件、清單與校驗碼。

## 適合情境

- 需要把 `.agents/skills/{skill-name}` 打包給其他 Repo 或其他小龍蝦使用。
- 需要確認技能資料夾包含 `SKILL.md`、文件、腳本與參考資料。
- 需要產生可交付的 `.skill` 檔、`INSTALL.md` 與 `install-manifest.json`。
- 需要避免把 `.git`、`.pi`、快取或暫存檔一起打包。

## 主要能力

- 驗證 `SKILL.md` frontmatter 的 `name` 與 `description`。
- 自動補上缺少的 `README.md`。
- 打包技能資料夾內容，並讓 `SKILL.md` 位於壓縮檔根目錄。
- 產生 SHA-256 校驗檔。
- 產生安裝清單與安裝說明。
- 產生匯出報告，列出包含檔案與驗證結果。

## 基本用法

```bash
python .agents/skills/skill-exporter/scripts/export_skill.py \
  .agents/skills/telegram-result-message \
  --output-dir artifacts/4471181575/skill-export
```

## 輸出檔案

```text
artifacts/{issue-comment-id}/skill-export/{skill-name}.skill
artifacts/{issue-comment-id}/skill-export/{skill-name}.sha256
artifacts/{issue-comment-id}/skill-export/install-manifest.json
artifacts/{issue-comment-id}/skill-export/INSTALL.md
artifacts/{issue-comment-id}/skill-export/export-report.md
```

## 安裝到其他小龍蝦

把 `.skill` 檔複製到目標工作區後執行：

```bash
mkdir -p .agents/skills/{skill-name}
python - <<'PY'
import zipfile
zipfile.ZipFile('path/to/{skill-name}.skill').extractall('.agents/skills/{skill-name}')
PY
```

確認 `.agents/skills/{skill-name}/SKILL.md` 存在。下一次執行時，技能應會出現在可用技能清單中。

## 驗證重點

- `.skill` 檔不是空檔。
- 壓縮檔根目錄含有 `SKILL.md`。
- 沒有包含 `.pi`、`.git`、`__pycache__` 或 `*.pyc`。
- `install-manifest.json` 的技能名稱、壓縮檔名與校驗碼正確。
