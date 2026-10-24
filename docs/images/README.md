# 演示图片来源

本目录的视频截图、网站截图、榜单长图、作品卡和公众号封面，均来自 `examples/make_demo.py` 生成的五部虚构短片与像素角色。演示材料按 GPL-3.0-only 分发，字体保留原许可。

网站和分享图使用 `export` 命令，从已验证的演示 MP4 导出。网站截图来自 `v1.2.0` 的浏览器实际渲染；手机截图使用 390px 视口，组合图只裁去滚动条并将两种视图并排展示。公众号封面已使用 `v1.2.1` 重新导出：一张 2538 × 1080 上传母版、整图缩放预览和居中方形裁切预览，后两张没有单独重新排版。主 README 同时提供单独大图与完整网站演示包。

可以按以下命令生成同一套演示：

```sh
python examples/make_demo.py --directory demo
python weekly.py build --episode demo/episode/episode.json --character demo/character/character.json --output output/demo.mp4 --web-output output/website --json
```

公众号正文图片由主 README 链接到独立的 MIT 项目 WeChat Article Studio，使用该项目自绘 SVG 与虚构数据，不属于本仓库的视频模板输出。
