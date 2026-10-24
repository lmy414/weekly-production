# 两个输入包

入口均为 UTF-8 JSON 对象。媒体使用本地路径，相对路径分别基于入口文件目录。全部指标必须真实提供；工具不会下载、采集或补造缺失数字。

## 每期数据 episode.json

必填项为 `schema`、`id`、`title`、`period`、`metric_basis`、`works` 和 `music`。

- `schema`：`weekly-production/episode-v1`。
- `id`：小写字母、数字与连接号，最长 80 字符。
- `period`：`begin`、`end` 为带时区 ISO 时间或 Unix 秒数，`timezone` 为 `Asia/Shanghai`。起点包含，终点不包含。
- `metric_basis`：`cumulative` 或 `weekly_delta`。周榜输入明确的周期净增量，快照采集和增量依据由外部准备。
- `works`：本期入选集合，当前固定版式接收 1 至 15 条作品。

每条作品必填 `bvid`、`title`、`author`、`source_url`、`published_at`、`observed_at`、`part_count`、`metrics`、`video`。日期均带时区，来源保留原作品链接。

`metrics` 完整提供 `view`、`reply`、`danmaku`、`favorite`、`coin`、`like`、`share`，均为非负整数。`part_count` 为正整数。公开综合公式用于核算；点赞与分享只展示。`score`、`rank` 可选，若提供则必须与计算结果一致。

`video` 指向本地原片或已有连续入片素材。`clip` 用 `start` 和 `end` 指定该本地文件的起止秒数，可另存 `summary`。时间对齐 30 fps，例如一帧为 `1/30` 秒。未指定的短视频按整条保留，长作品返回缺项。可用 `short_title` 指定片单短标题，原题保留。

`music` 必填 `file`、`title`、`artist`、`source_url`。可选 `gain_db` 为 -30 至 0，默认 -1.5；`start_seconds` 默认 0。可提供 `sha256` 核对已确认音源，省略时工具自动计算。来源必须为 HTTPS 原曲链接。

`copy` 可选，当前支持 `opening_kicker`、`opening_subtitle`、`opening_tagline`、`opening_note`、`statistics_text`、`outro_text`、`end_text`。值为文字，固定规则、公式与真实口径不能通过这些字段替换。未知字段报错，长文案在捕获时检查排版。

`branding` 可选，字段为 `producer`、`website_name`、`website_url`、`update_schedule`。`producer` 进入制作署名，`update_schedule` 进入片尾。网站信息保留在本期计划供后续用途，不增加当前成品以外的交付。

## 角色素材 character.json

必填 `schema=weekly-production/character-v1`、`id`、`name` 和 `images.default`。默认图必须是含透明像素的 PNG。

可配置用途为 `welcome`、`watching`、`transition`、`scope`、`score`、`thinking`、`applause`、`surprise`、`top3`、`top2`、`champion`、`goodbye` 和可选 `cover`。未配置的用途使用 `default`。已配置的文件若缺失或无真实透明度，返回错误。

角色包无需提供 UI、字体或动画。名称用于素材识别，不能自动生成角色对白。
