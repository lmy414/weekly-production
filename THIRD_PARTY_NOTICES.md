# 第三方资源说明

本项目代码、模板、演示生成器与合成示例采用 GPL-3.0-only。字体遵循下面列出的原许可；字体文件及许可证随 Skill 一起分发。

| 资源 | 来源 | 随附许可 |
| --- | --- | --- |
| Fusion Pixel 12px | [TakWolf/fusion-pixel-font](https://github.com/TakWolf/fusion-pixel-font)，版本与文件名见 [SOURCE.json](skills/weekly-production/assets/ui/fonts/SOURCE.json) | [SIL Open Font License](skills/weekly-production/assets/ui/fonts/OFL.txt) 及 [上游字体许可](skills/weekly-production/assets/ui/fonts/LICENSES/) |
| Noto Sans SC | [google/fonts](https://github.com/google/fonts/tree/a85815a42757630ce188fdad368c2dfc444d4773/ofl/notosanssc)，文件来源见 [SOURCE.json](skills/weekly-production/assets/ui/fonts/noto-sans-sc/SOURCE.json) | [SIL Open Font License](skills/weekly-production/assets/ui/fonts/noto-sans-sc/OFL.txt) |

程序通过包管理器安装 Pillow、NumPy、PyAV、imageio-ffmpeg 与 Puppeteer Core。分发的 Skill 包不内置这些依赖、浏览器或 FFmpeg 二进制文件。使用时请保留相应软件的许可。

综合计分方案的公开出处列于 [RANKING.md](RANKING.md)。本项目独立实现该公式，未复制上游视频、角色或歌曲作为公开素材。

`examples/make_demo.py` 从几何形状、虚构文本、音符合成和虚构指标生成演示材料。README 截图、转场动画与 Release 演示视频均来自这些材料。示例中的 BV 标识只作为格式测试值，不代表对应的真实投稿。

你提供的作品、角色、BGM、数据和节目内容适用各自授权，不因使用本工具而自动改用本项目代码许可。
