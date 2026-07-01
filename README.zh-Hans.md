# claude-code-inline-poscolor

为 [Claude Code](https://claude.com/claude-code) 提供的常驻**词性着色**。
每条助手消息都会直接在终端里重新着色：名词和动词用醒目的对比色，形容词和副词各用其暗色变体，
其余文字为浅灰。专为更快、更适合 ADHD 的阅读而设计。

**[English](README.md) · [繁體中文](README.zh-Hant.md)**

![同一句话：先是纯文本，再按词性着色](examples/before-after.svg)

| 词性 | 颜色 *(默认配色)* | 256 色码 |
|---|---|---|
| 名词 / 专有名词 | 亮青 | 45 |
| 形容词 | 暗青 | 31 |
| 动词 | 亮橙 | 208 |
| 副词 | 暗橙 | 130 |
| 其他 | 灰 | 250 |

内置五种配色 —— 用 `bin/palettes` 预览并切换：

![同一句话在五种配色下的效果](examples/palettes.svg)

## 安装

两种方式都需先安装一次 spaCy 和模型：

```bash
pip install spacy && python -m spacy download en_core_web_sm
```

**方式 A —— 作为 Claude Code 插件**（附带 `/poscolor:*` 命令）：

```
/plugin marketplace add LiudengZhang/claude-code-inline-poscolor
/plugin install poscolor@inline-poscolor
```

**方式 B —— 手动安装**，不使用插件系统：

```bash
git clone https://github.com/LiudengZhang/claude-code-inline-poscolor.git
cd claude-code-inline-poscolor
./install.sh          # 把 MessageDisplay 钩子合并进 ~/.claude/settings.json
```

新开一个 Claude Code 会话即可启用着色。

## 工作原理

一个 `MessageDisplay` 钩子（`src/messagedisplay_hook.py`）会累积每条流式消息，并在最后一个
分块时把它替换为着色版本。常驻的 spaCy 守护进程（`src/mdcolor_daemon.py`）会常驻加载
`en_core_web_sm`，因此在一次性约 4 秒冷启动后，每条消息只需约 7 毫秒的本地套接字往返。
故障即净：若守护进程无法启动，则原样显示文本。

## 控制

使用插件时，三个斜杠命令：

```
/poscolor:toggle              # 着色 开 <-> 关
/poscolor:palette pink-green  # 切换配色（不带参数则列出全部）
/poscolor:model en_core_web_trf   # 更换模型（不带参数则显示当前）
```

或直接操作（用不用插件都可以）：

```bash
touch ~/.claude/mdcolor_off                       # 立即关闭（rm 即可重新开启）
bin/palettes                                      # 预览 5 种配色
bin/palettes pink-green                           # 切换（即时生效，无需重启）
echo en_core_web_trf > ~/.claude/mdcolor_model    # 更换模型（随后重启守护进程）
```

## 按需命令行工具

```bash
bin/pos-color notes.txt --legend                          # 按词性自动标注文件
echo '<n>PARP</n> <v>inhibits</v> <n>repair</n>' | bin/colorize   # 自行标注
```

## 已知限制

一旦出现任何 ANSI 颜色，聊天渲染器就会退回到仅支持行内的 markdown：**加粗**、`行内代码`
和 ```代码块``` 仍可渲染，但块级标题（`##`）和表格会显示为原始符号。着色会跳过代码、
表格和行内片段，但无法在着色消息中保留它们的*结构*。流式输出也会被抑制，因此着色消息会
一次性整体出现。若需要干净的表格，请使用关闭开关。

## 依赖

Python 3.7+ · 带 `en_core_web_sm` 的 [spaCy](https://spacy.io) · 支持 256 色的终端。

## 许可证

MIT —— 见 [LICENSE](LICENSE)。
