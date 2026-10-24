# 使用说明

## 配置浏览器

工具需要 Chrome / Chromium 来绘制模板，运行时使用无头模式。浏览器只读取临时本地服务与提供的素材。

已安装浏览器时，将 `WEEKLY_CHROME` 设为浏览器可执行文件的实际绝对路径。Windows PowerShell 示例：

```powershell
$env:WEEKLY_CHROME = "C:\Program Files\Google\Chrome\Application\chrome.exe"
python weekly.py doctor --json
```

Linux shell 示例：

```sh
export WEEKLY_CHROME=/usr/bin/chromium
python weekly.py doctor --json
```

路径必须指向本机存在的文件。Windows 示例是 Chrome 的常见安装位置，实际位置以你的安装为准。

没有浏览器时，可使用 Puppeteer 的[浏览器安装工具](https://pptr.dev/browsers-api#cli)下载 Chrome for Testing：

```sh
npx @puppeteer/browsers install chrome@stable
```

下载后，将命令返回的可执行文件路径设为 `WEEKLY_CHROME`。Linux 还需要浏览器运行库，按 [Puppeteer 系统要求](https://pptr.dev/guides/system-requirements)安装。当前项目已验证 Windows 制作，Linux / macOS 尚未完成整期验证。

## 安装独立 Skill

Release 中的 `weekly-production-1.0.0.zip` 包含可独立运行的 Skill 文件夹。把文件夹放入你的助手所支持的 Skill 目录，保留内部结构，然后安装依赖：

```sh
python -m pip install -r "你的Skill目录/weekly-production/scripts/requirements.txt"
npm ci --prefix "你的Skill目录/weekly-production/scripts" --ignore-scripts --no-audit --no-fund
python "你的Skill目录/weekly-production/scripts/weekly.py" doctor --json
```

不同助手的 Skill 安装位置各不相同。目录中必须保留 `SKILL.md`、`scripts/`、`references/` 与 `assets/`。制作时直接调用该目录下的 `scripts/weekly.py`，无需再依赖仓库根目录。

## 检查输入与导出

```sh
python weekly.py validate --episode "本期/episode.json" --character "角色/character.json" --json
python weekly.py build --episode "本期/episode.json" --character "角色/character.json" --output "成品/第002期.mp4" --json
python weekly.py verify --output "成品/第002期.mp4" --json
```

`validate` 返回两个状态：`ok` 表示字段与已有文件有效，`ready` 表示制作材料已齐。`ok=true, ready=false` 时，按 `missing` 补齐选段，再执行构建。

`build` 完成后会返回成片路径、时长、帧数、文件大小与哈希。日志同时显示当前制作阶段。可选 `--workers 1`、`2` 或 `3`，默认 2；内存紧张时先使用 1。

最终 MP4 通过检查后才会替换目标文件。导出中断时，保留原输入与成品旁的工作目录，重新执行相同命令即可继续利用有效缓存。

## 给长视频选段

在 `episode.json` 的每条作品中填写本地原片与连续范围：

```json
{
  "video": "videos/work-a.mp4",
  "clip": {
    "start": 35,
    "end": 92,
    "summary": "从问题出现到解决，保留完整剧情。"
  }
}
```

起止秒数相对于这份本地文件，并对齐 30 fps 帧边界。短原作不超过 60 秒时可省略 `clip`，工具整条保留。长原作需要明确范围。

可先导出本地时间轴图片，供你或 AI 选择：

```sh
python weekly.py analyze --episode "本期/episode.json" --character "角色/character.json" --json
```

结果包含时间轴与证据文件的路径。选好后把范围写回输入，再构建成片。可选本地语音转写的安装与模型要求见 [CLI 参考](../skills/weekly-production/references/cli.md#分析本地原片)。

## 换文案、角色与音乐

文案写入 `copy`。可替换开场副标题、短句、征集说明和片尾文字，字段见[输入包说明](../INPUT_OUTPUT.md)。模板按内容排版；过长时会返回具体页面的排版错误。

换角色时，切换 `--character` 指向的文件。至少需要 `images.default` 对应的一张透明 PNG，欢迎、转场、前三名等用途可以逐步补充。已经配置的图片必须真实存在。

换配乐时，修改 `music.file`，同时填写曲名、作者和来源。`start_seconds` 控制起播点，`gain_db` 控制包装配乐相对音量。工具保留作品原声，BGM 用在包装部分。

## 环境与文件

| 设置 | 用途 |
| --- | --- |
| `WEEKLY_CHROME` | 指定 Chrome / Chromium 可执行文件 |
| `WEEKLY_NODE` | 指定 Node.js 可执行文件 |
| `WEEKLY_FFMPEG` | 指定 FFmpeg 可执行文件 |
| `WEEKLY_PUPPETEER` | 在使用自定义安装位置时指定 Puppeteer 模块 |

依赖默认从系统 PATH 和已知安装位置查找。`doctor` 会报告实际使用的工具和版本。

成品旁的 `.weekly-production/<成品名>/` 保存缓存与检查记录。只分享视频时发送 MP4 即可；需要重制或重新执行 `verify` 时，保留原输入、素材、工具版本和这个目录。私有素材与工作目录不要提交到公开仓库。

## 常见问题

| 提示或情况 | 处理方式 |
| --- | --- |
| 找不到 Chromium | 设置 `WEEKLY_CHROME`，再运行 `doctor`。 |
| 找不到 Puppeteer | 在当前 Skill 的 `scripts/` 安装 Node.js 依赖。 |
| `ready=false` | 查看 `missing`，为长原片补充连续选段。 |
| 得分或名次不一致 | 核对输入指标与统计口径，或修正填入的 `score`、`rank` 核对值。 |
| 文案溢出 | 按错误位置缩短文字，再导出。 |
| 制作期间输入发生变化 | 等材料保存完成后，重新执行同一构建命令。 |
| `verify` 提示记录缺失或版本不同 | 使用对应的原输入、工作目录和制作版本。独立播放 MP4 不需要这些文件。 |
