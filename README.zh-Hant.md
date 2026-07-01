# claude-code-inline-poscolor

為 [Claude Code](https://claude.com/claude-code) 提供的常駐**詞性著色**。
每則助手訊息都會直接在終端機裡重新著色：名詞和動詞用醒目的對比色，形容詞和副詞各用其暗色變體，
其餘文字為淺灰。專為更快、更適合 ADHD 的閱讀而設計。

**[English](README.md) · [简体中文](README.zh-Hans.md)**

![同一句話：先是純文字，再按詞性著色](examples/before-after.svg)

| 詞性 | 顏色 *(預設配色)* | 256 色碼 |
|---|---|---|
| 名詞 / 專有名詞 | 亮青 | 45 |
| 形容詞 | 暗青 | 31 |
| 動詞 | 亮橙 | 208 |
| 副詞 | 暗橙 | 130 |
| 其他 | 灰 | 250 |

內建五種配色 —— 用 `bin/palettes` 預覽並切換：

![同一句話在五種配色下的效果](examples/palettes.svg)

## 安裝

```bash
git clone https://github.com/LiudengZhang/claude-code-inline-poscolor.git
cd claude-code-inline-poscolor
pip install -r requirements.txt
./install.sh          # 下載模型並註冊 MessageDisplay 掛鉤
```

新開一個 Claude Code 工作階段即可啟用著色。`install.sh` 會把掛鉤合併進
`~/.claude/settings.json`，不會覆蓋你的其他設定。

## 運作原理

一個 `MessageDisplay` 掛鉤（`src/messagedisplay_hook.py`）會累積每則串流訊息，並在最後一個
分塊時把它替換為著色版本。常駐的 spaCy 守護行程（`src/mdcolor_daemon.py`）會常駐載入
`en_core_web_sm`，因此在一次性約 4 秒冷啟動後，每則訊息只需約 7 毫秒的本地通訊端往返。
故障即淨：若守護行程無法啟動，則原樣顯示文字。

## 控制

```bash
touch ~/.claude/mdcolor_off                       # 立即關閉（rm 即可重新開啟）
bin/palettes                                      # 預覽 5 種配色
bin/palettes pink-green                           # 切換（即時生效，無需重啟）
echo en_core_web_trf > ~/.claude/mdcolor_model    # 更換模型（隨後重啟守護行程）
```

## 按需命令列工具

```bash
bin/pos-color notes.txt --legend                          # 按詞性自動標註檔案
echo '<n>PARP</n> <v>inhibits</v> <n>repair</n>' | bin/colorize   # 自行標註
```

## 已知限制

一旦出現任何 ANSI 顏色，聊天算繪器就會退回到僅支援行內的 markdown：**粗體**、`行內程式碼`
和 ```程式碼區塊``` 仍可算繪，但區塊標題（`##`）和表格會顯示為原始符號。著色會跳過程式碼、
表格和行內片段，但無法在著色訊息中保留它們的*結構*。串流輸出也會被抑制，因此著色訊息會
一次性整體出現。若需要乾淨的表格，請使用關閉開關。

## 相依套件

Python 3.7+ · 帶 `en_core_web_sm` 的 [spaCy](https://spacy.io) · 支援 256 色的終端機。

## 授權

MIT —— 見 [LICENSE](LICENSE)。
