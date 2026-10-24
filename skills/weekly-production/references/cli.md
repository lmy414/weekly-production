# CLI 运行

命令入口为本 Skill 的 `scripts/weekly.py`。需要 Python 3.11 以上、Node.js、Chromium 和 FFmpeg。安装依赖：

```text
python -m pip install -r <Skill>/scripts/requirements.txt
npm install --prefix <Skill>/scripts --ignore-scripts --no-audit --no-fund
```

FFmpeg 优先读取 `WEEKLY_FFMPEG` 或 PATH，最后使用 imageio-ffmpeg。Node.js 可设 `WEEKLY_NODE`；浏览器可设 `WEEKLY_CHROME`；Puppeteer 模块可设 `WEEKLY_PUPPETEER`。默认支持 PATH 上的浏览器和常见 Playwright 缓存，无需原项目 `.private/renderer.json`。

```text
python <Skill>/scripts/weekly.py doctor --json
python <Skill>/scripts/weekly.py validate --episode <本期>/episode.json --character <角色>/character.json --json
python <Skill>/scripts/weekly.py plan --episode <本期>/episode.json --character <角色>/character.json --output <成品.mp4> --json
python <Skill>/scripts/weekly.py build --episode <本期>/episode.json --character <角色>/character.json --output <成品.mp4> --json
python <Skill>/scripts/weekly.py verify --output <成品.mp4> --json
```

路径包含空格时加引号。`build` 可选 `--workers 1`、`2` 或 `3`，默认 2。成功结果写标准输出，构建进度写标准错误；`--json` 表明调用者使用机器可读接口，当前结果始终是 JSON。

成功退出码为 0，输入错误为 2，运行或验证失败为 1，中断为 130。`validate` 的 `ready=false` 表示仍有内容需要准备，不能直接构建。

## 分析本地原片

```text
python <Skill>/scripts/weekly.py analyze --episode <本期>/episode.json --character <角色>/character.json --json
```

时间轴与证据存到本期目录的 `.weekly-analysis/`，返回每条作品的证据和图片路径。需要转写时安装 `requirements-analysis.txt`，预先缓存 Whisper small，调用时加 `--asr`。分析命令只使用已缓存模型，不下载模型。

## 成片与内部文件

`--output` 是 MP4 文件路径。内部目录位于其旁边的 `.weekly-production/<成品文件名>/`，保存节目计划、输入锁定、捕获、音频、片段缓存与质量报告。同一成品禁止并发构建，操作系统锁在进程结束后释放。

构建先核对数据、文件和素材，再启动临时回环服务捕获画面。浏览器页面只访问本机服务，不请求远程素材。捕获缓存核对所有图像哈希，作品缓存核对原片、图层、配方、帧数与输出哈希。失败保留可恢复记录，最终成品只在编码与质检通过后替换。

`verify` 需要对应内部记录和原输入，验证目标成片哈希、绑定版本、实际音视频流、图层、选段首尾和配乐。自动检查不会代替人工主题与漏收审核。
