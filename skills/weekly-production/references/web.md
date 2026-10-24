# 文字网页与分享图

图文导出读取同一份 `episode.json`、`character.json` 和已验证 MP4。片单、名次、得分与作品时间均来自对应成片。输出纯静态文件，不包含原片、音源、输入锁定、账号或本机素材路径。

## 已有成片，直接导出

```sh
python <Skill>/scripts/weekly.py export --episode <本期>/episode.json --character <角色>/character.json --output <成品.mp4> --directory <图文目录> --json
```

成功结果含 `index`、`share_image`、`work_cards`、`wechat_covers` 和 `qr`。目录包含首页、每期固定页面、往期档案、计分说明、整期长图、作品卡和公众号封面。网页可搜索作品、作者与 BV 号，按类型筛选，并预览、下载 PNG。

同一目录再次导出时保留往期内容，同一期会更新。只会替换由此工具生成的目录，失败保留既有页面。成片与制作工作目录须保留；导出检查 MP4 哈希、输入哈希和锁定时间轴，不要求重新渲染旧版成片。

## 公众号封面

每次图文导出自动生成两张 JPEG，位于 `assets/issues/<期号>/`：

| 结果字段 | 文件名 | 尺寸 | 比例 |
| --- | --- | --- | --- |
| `wechat_covers.landscape` | `cover-wechat-2.35x1.jpg` | 1410 × 600 | 2.35:1 |
| `wechat_covers.square` | `cover-wechat-1x1.jpg` | 1080 × 1080 | 1:1 |

两种画幅分别排版刊名、期号、本期作品数和角色素材。横版突出人物上半身，方版保留角色素材全幅，不拉伸或裁切现成的视频封面。封面不叠加二维码或网站地址，不受分享卡的二维码开关影响。发布公众号时将两张图一并交付，按后台对应封面位置上传，并检查裁剪预览。

## 制作时一起导出

```sh
python <Skill>/scripts/weekly.py build --episode <本期>/episode.json --character <角色>/character.json --output <成品.mp4> --web-output <图文目录> --json
```

MP4 通过检查后才生成图文。如果图文导出失败，命令返回失败并保留已通过检查的 MP4。修好配置后使用 `export` 重试即可。

## 二维码默认关闭

不传二维码设置时，整期长图和作品卡都没有二维码。仅指定网站地址也不会自动开启。要开启，请配置自己的地址：

```sh
python <Skill>/scripts/weekly.py export --episode <本期>/episode.json --character <角色>/character.json --output <成品.mp4> --directory <图文目录> --qr --site-url https://weekly.example.com --json
```

默认来源为 `website`。整期图指向 `https://weekly.example.com/issues/<期号>/`，作品卡指向同页的 `#work-<BV号>`。不会自动添加查询参数或追踪码。

网站使用独立域名的根路径。`site_url` 只接受无账号、查询参数和锚点的 HTTP(S) 根地址。Unicode 域名自动转为可扫码的 IDNA 地址。缺少必需链接时明确报错，不回退到别人的站点。

可选链接来源如下：

| `--qr-source` | 整期长图 | 单条作品卡 |
| --- | --- | --- |
| `website`，默认 | 自己网站的本期地址 | 自己网站的作品锚点 |
| `original` | 自己网站的本期地址 | 数据包中的原作品链接 |
| `custom` | 自行配置的链接模板 | 同一个链接模板 |

`custom` 需要 `--qr-url`。模板只支持 `{issue_id}` 与 `{bvid}`，整期图的 `{bvid}` 为空。例：`https://example.com/weekly/{issue_id}/`。模板中的查询参数属于使用者显式配置，工具不另行添加。

## 保存可复用配置

用 `--web-config <文件.json>` 读取以下设置，CLI 参数覆盖文件中的同名项：

```json
{
  "site_url": "https://weekly.example.com",
  "site_name": "我的 AI 娘周刊",
  "schedule": "每周六 22:00 · 北京时间",
  "qr": {
    "enabled": false,
    "source": "website"
  }
}
```

把 `enabled` 改为 `true` 才会出二维码。`--no-qr` 可临时关闭已配置的二维码。`main_url/main_name` 可选，用于网页主站入口；二维码的自定义链接放在 `qr.url`。

数据包里的 `branding.website_url` 继续表示节目署名，不自动用作二维码来源。二维码只读取明确的图文配置。

## 公开介绍

制作前可在每条作品的 `provenance.website` 填 `summary` 和 `category`。已有锁定成片时，另写 `--editorial <文件.json>`：

```json
{
  "label": "本周主榜",
  "deck": "这一周，和喜欢的角色再见一面。",
  "works": {
    "BV1111111111": {
      "category": "剧情",
      "summary": "供观众阅读的作品介绍。"
    }
  }
}
```

`category` 支持剧情、音乐、整活、动画和其他。`published_at` 可指定本期发布日期，`intro` 用作本期手记。工具只读取这些公开字段，内部 `clip.summary` 和其他分析记录不会进入网页。

## 本地预览与上线

```sh
python -m http.server 8108 --bind 127.0.0.1 --directory <图文目录>
```

在浏览器打开 `http://127.0.0.1:8108/`。将整个导出目录交给已有的静态站部署流程即可上线。`export-manifest.json` 只保留公开显示字段，用于下次更新归档，不能替换为原始数据包。
