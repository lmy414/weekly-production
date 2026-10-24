# 合成演示材料

运行下面的命令，生成一套可以直接制作视频的输入包：

```sh
python examples/make_demo.py --directory demo
python weekly.py build --episode demo/episode/episode.json --character demo/character/character.json --output output/demo.mp4 --json
```

需要先按[项目首页](../README.md#先跑一遍演示)安装依赖与浏览器。生成目标目录必须尚不存在，程序不会覆盖已有材料。

演示包括 5 条各 12 秒的短片、程序绘制的透明像素角色、6 个角色用途映射、合成配乐，以及可阅读的 `episode.json` 和 `character.json`。这些材料与真实节目采用同一套制作模板。

作品、作者、指标和 BV 标识都是虚构测试值，BV 标识不代表真实投稿。画面和角色由几何图形绘制，音乐按音符合成。所有演示材料都由本目录的代码生成，按 GPL-3.0-only 分发。画面中的字体保留其原许可。

也可以从 [v1.0.0 Release](https://github.com/lmy414/weekly-production/releases/tag/v1.0.0)下载生成好的输入包或完整演示 MP4。
