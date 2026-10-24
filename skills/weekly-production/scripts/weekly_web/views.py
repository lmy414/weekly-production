# SPDX-License-Identifier: GPL-3.0-only
"""Shared pixel studio components for all public pages."""
from html import escape

from .settings import Settings


def e(value):
    return escape(str(value), quote=True)


def number(value):
    return f"{value:,}"


def short(value):
    return f"{value/10000:.1f}万" if value >= 10000 else str(value)


def icon(name):
    paths = {
        "arrow": '<path d="M4 12h15m-6-6 6 6-6 6"/>',
        "download": '<path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/>',
        "share": '<path d="M9 11 18 5M9 13l9 6"/><circle cx="6" cy="12" r="3"/><circle cx="19" cy="4" r="3"/><circle cx="19" cy="20" r="3"/>',
        "play": '<path d="m8 4 13 8-13 8Z"/>',
        "spark": '<path d="m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3Z"/>',
        "search": '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
        "copy": '<path d="M8 8h13v13H8zM3 16V3h13"/>',
    }
    return f'<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7">{paths.get(name, paths["spark"])}</svg>'


def brand(site=None):
    site=site or Settings()
    return f'<a class="brand" href="/" aria-label="{e(site.site_name)}首页"><span class="brand-stamp">AI</span><span><strong>{e(site.site_name)}</strong><small>AI GIRL WEEKLY</small></span><span class="brand-star">✦</span></a>'


def header(active="latest",site=None):
    site=site or Settings()
    main=f'<a class="mother-site" href="{e(site.main_url)}">{e(site.main_name)} {icon("arrow")}</a>' if site.main_url else ""
    links = [("latest", "/", "本期周刊"), ("archive", "/issues/", "往期档案"), ("rules", "/rules/", "收录与计分")]
    nav = ''.join(f'<a href="{url}"{chr(32)+"aria-current=page" if key==active else ""}>{label}</a>' for key, url, label in links)
    return f'<header class="site-header"><div class="header-inner">{brand(site)}<nav aria-label="主导航">{nav}</nav>{main}</div></header>'


def footer(site=None):
    site=site or Settings()
    main=f'<a href="{e(site.main_url)}">{e(site.main_name)}</a>' if site.main_url else ""
    return f'<footer class="site-footer"><div>{brand(site)}<p>模型下班，角色上场。</p></div><div class="footer-links"><a href="/issues/">期刊档案</a><a href="/rules/">收录与计分</a>{main}<a href="https://github.com/lmy414/weekly-production">制作工具</a></div><p class="footer-note">{e(site.schedule)}<br>作品版权归原作者所有，点击标题前往原作支持创作者。</p></footer>'


def layout(title, body, *, active="latest", path="/", description="AI 娘二创的每周相遇。阅读榜单、发现作品，导出分享图。", image="/assets/site-og.jpg", revision="1", site=None):
    site=site or Settings()
    canonical = site.site_url + path
    canonical_tag=f'<link rel="canonical" href="{e(canonical)}"><meta property="og:url" content="{e(canonical)}">' if site.site_url else ""
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(title)} · {e(site.site_name)}</title><meta name="description" content="{e(description)}"><meta name="theme-color" content="#f6f1e2">{canonical_tag}<meta property="og:type" content="website"><meta property="og:title" content="{e(title)} · {e(site.site_name)}"><meta property="og:description" content="{e(description)}"><meta property="og:image" content="{e(site.site_url+image)}"><meta name="twitter:card" content="summary_large_image"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="preload" href="/assets/fonts/pixel.woff2" as="font" type="font/woff2" crossorigin><link rel="stylesheet" href="/assets/site.css?v={e(revision)}"><script defer src="/assets/app.js?v={e(revision)}"></script></head><body><a class="skip" href="#main">跳到正文</a>{header(active,site)}<main id="main" class="site-main">{body}</main>{footer(site)}<div id="notice" class="notice" role="status" aria-live="polite" hidden></div><dialog class="share-dialog" id="share-dialog"><div class="dialog-bar"><strong>把喜欢的作品分享出去</strong><button type="button" data-close-dialog aria-label="关闭分享预览">×</button></div><img id="share-preview" alt="分享图预览"><div class="dialog-actions"><a class="button primary" id="share-download" download>{icon("download")} 保存 PNG</a><button class="button" id="share-copy" type="button">{icon("copy")} 复制图片</button></div><p class="dialog-hint">手机端可长按图片保存。图片保留名次、作者与原作信息。</p></dialog></body></html>'''


def window_bar(title, label=""):
    return f'<div class="window-bar"><span>▧ {e(title)}</span><span>{e(label)} <i>−</i> <i>□</i> <i>×</i></span></div>'


def share_button(url, label="分享作品", *, entire=False):
    return f'<a class="button {"primary" if entire else "subtle"}" href="{e(url)}" download data-share="{e(url)}" aria-label="{e(label)}">{icon("download" if entire else "share")}{e(label)}</a>'


def hero(issue,site=None):
    site=site or Settings()
    return f'''<section class="hero window">{window_bar("本期 AI 娘创作放映室", "ISSUE "+issue["number"])}<div class="hero-grid"><div class="hero-copy"><div class="kicker"><span class="label coral">{e(issue["label"])}</span><span>VOL. {e(issue["number"])} / {e(issue["date"])}</span></div><h1>模型下班，<br><em>角色上场。</em></h1><p class="hero-deck">{e(issue["deck"])}</p><div class="hero-actions"><a class="button primary" href="#ranking">阅读本期 {icon("arrow")}</a>{share_button(issue["share"],"导出榜单长图",entire=False)}</div><div class="hero-meta"><span><b>{len(issue["works"])}</b> 部作品</span><span><b>{issue["authors"]}</b> 位创作者</span><span>{e(issue["basis_label"])}</span></div></div><div class="hero-art" aria-hidden="true"><span class="hero-circle"></span><span class="sticker issue-sticker">ISSUE <b>{e(issue["number"])}</b><br>每一份创作，都值得被看见</span><img src="{e(issue["host"])}" alt="" width="700" height="900" fetchpriority="high"><span class="hero-spark first">✦</span><span class="hero-spark second">✚</span><span class="sticker schedule-sticker">{e(site.schedule)}</span></div></div><div class="hero-bottom"><span>▸ {e(issue["title"])}</span><span class="on-air"><i></i> 本期已更新</span></div></section>'''


def highlights(issue):
    items=[]
    for w in issue['works'][:3]:
        items.append(f'<a class="highlight rank-{w["rank"]}" href="#work-{w["bvid"]}"><div class="highlight-image"><img src="{e(w["cover"])}" alt="{e(w["title"])}" width="480" height="270"><span class="rank-label">NO. <b>{w["rank"]:02d}</b></span></div><div class="highlight-copy"><span class="mini-label">本期第 {w["rank"]} 名</span><h3>{e(w["short_title"])}</h3><p>{e(w["author"])}</p><span class="highlight-score">{number(w["score"])} <small>综合得分</small></span></div></a>')
    return '<section class="highlights-section"><div class="section-heading"><div><span class="eyebrow">THIS ISSUE / TOP THREE</span><h2>先和前三名见个面</h2></div><span class="small-note">点击卡片，跳到作品介绍 ↓</span></div><div class="highlights">'+''.join(items)+'</div></section>'


def work_card(work, issue_id):
    w=work; m=w['metrics']
    metrics=''.join(f'<div><dt>{label}</dt><dd title="{number(m[key])}">{short(m[key])}</dd></div>' for key,label in [('view','播放'),('coin','投币'),('favorite','收藏'),('like','点赞')])
    extra=''.join(f'<span>{label} <b>{number(m[key])}</b></span>' for key,label in [('view','播放'),('reply','评论'),('danmaku','弹幕'),('coin','投币'),('favorite','收藏'),('like','点赞'),('share','分享')])
    extra+=f'<span>分P数 <b>{w["part_count"]}</b></span><span>数据观测 <b>{e(w["observed_at"])}（北京时间）</b></span>'
    text=' '.join([w['title'],w['author'],w['bvid'],w['category'],w['summary']])
    return f'''<article class="work-card window rank-{w["rank"]}" id="work-{w["bvid"]}" data-work data-search="{e(text.lower())}" data-category="{e(w["category"])}"><div class="work-rank"><span>NO.</span><b>{w["rank"]:02d}</b><small>{"TOP THREE" if w["rank"]<=3 else "WEEKLY RANK"}</small></div><a class="work-cover" href="{e(w["source_url"])}" target="_blank" rel="noopener noreferrer" aria-label="观看原作：{e(w["title"])}"><img src="{e(w["cover"])}" alt="{e(w["title"])}" width="480" height="270" loading="lazy"><span>{icon("play")} 前往原作</span></a><div class="work-body"><div class="work-topline"><span class="label">{e(w["category"])}</span><span class="work-published">投稿 {e(w["published_date"])}</span></div><h3><a href="{e(w["source_url"])}" target="_blank" rel="noopener noreferrer">{e(w["title"])}</a></h3><p class="work-author">UP主 / {e(w["author"])}</p><p class="work-summary">{e(w["summary"])}</p><dl class="work-metrics">{metrics}</dl><details class="work-details"><summary>查看完整指标与节目时间</summary><div>{extra}<span>正片位置 <b>{e(w["timestamp"])}</b></span><span>BV号 <b>{e(w["bvid"])}</b></span></div></details></div><div class="work-score"><span class="mini-label">综合得分</span><strong>{number(w["score"])}</strong>{share_button(w["share"],"导出作品卡")}<a class="permalink" href="/issues/{e(issue_id)}/#{e('work-'+w['bvid'])}" data-copy-link>复制作品链接</a></div></article>'''


def ranking(issue):
    categories=['全部']+list(dict.fromkeys(w['category'] for w in issue['works']))
    filters=''.join(f'<button type="button" data-filter="{e(c)}" aria-pressed="{str(i==0).lower()}">{e(c)}</button>' for i,c in enumerate(categories))
    cards=''.join(work_card(w, issue['id']) for w in issue['works'])
    return f'<section id="ranking" class="ranking-section"><div class="section-heading"><div><span class="eyebrow">THE WEEKLY LINEUP</span><h2>本期主榜 <span class="count-badge">{len(issue["works"]):02d}</span></h2></div><a class="text-link" href="/rules/">排名怎么算？ {icon("arrow")}</a></div><div class="ranking-toolbar"><div class="filter-tabs" aria-label="作品类型">{filters}</div><label class="search">{icon("search")}<input id="work-search" type="search" placeholder="搜索作品、作者、BV号" aria-label="搜索作品、作者或BV号"></label></div><p class="ranking-caption"><span id="result-count">{len(issue["works"])} 部作品</span> · 按综合得分排序 · {e(issue["basis_label"])}<span>作品标题可直接跳转 B 站原作 ↗</span></p><div class="work-list">{cards}</div><p class="empty-state window" id="empty-state" hidden>本期没有找到相符的作品，换个词试试。</p></section>'


def sidebar(issue,site=None):
    site=site or Settings()
    toc=''.join(f'<a href="#work-{w["bvid"]}"><span>{w["rank"]:02d}</span>{e(w["short_title"])}</a>' for w in issue['works'])
    return f'<aside class="sidebar"><section class="window"><div class="aside-heading">▧ 本期手记</div><div class="aside-body"><span class="eyebrow">ISSUE {issue["number"]}</span><h2>{e(issue["label"])}</h2><p>{e(issue["intro"])}</p><dl class="issue-facts"><div><dt>投稿区间</dt><dd>{e(issue["period_label"])}<small class="fact-detail">{e(issue["period_begin"].replace("T"," "))}<br>至 {e(issue["period_end"].replace("T"," "))}<br>北京时间；起点包含、终点不包含</small></dd></div><div><dt>计分口径</dt><dd>{e(issue["basis_label"])}</dd></div><div><dt>观测时间</dt><dd>{e(issue["observed_label"])}</dd></div><div><dt>页面更新</dt><dd>{e(issue["updated_at"][:16].replace("T"," "))}</dd></div><div><dt>固定更新</dt><dd>{e(site.schedule)}</dd></div></dl></div></section><section class="window share-aside">{window_bar("把本期带走")}<div class="aside-body"><div class="mini-poster"><span>AI 娘周刊</span><b>{issue["number"]}</b><small>{len(issue["works"])} 部作品 / {e(issue["date"])}</small></div><p>把整期榜单存成一张图，<br>发给和你喜欢同一部作品的人。</p>{share_button(issue['share'],'导出本期长图',entire=True)}</div></section><section class="window toc-window"><div class="aside-heading">本期目录</div><nav class="issue-toc" aria-label="本期作品目录">{toc}</nav></section></aside>'


def issue_body(issue,site=None):
    site=site or Settings()
    main=f'<a class="button" href="{e(site.main_url)}">前往{e(site.main_name)} {icon("arrow")}</a>' if site.main_url else ""
    return hero(issue,site)+highlights(issue)+f'<div class="reading-layout">{ranking(issue)}{sidebar(issue,site)}</div><section class="closing window"><span>THANKS FOR CREATING</span><h2>喜欢，就去原作留个言。</h2><p>一条评论、一次收藏，都是给创作者的下一份灵感。</p>{main}</section>'


def archive(issues):
    cards=''.join(f'<article class="archive-card window"><a href="/issues/{e(i["id"])}/"><img src="{e(i["cover"])}" alt="{e(i["title"])}" width="800" height="450" loading="lazy"><div class="archive-copy"><span class="eyebrow">ISSUE {e(i["number"])} / {e(i["date"])}</span><h2>{e(i["title"])}</h2><p>{len(i["works"])} 部作品 · {e(i["basis_label"])}</p><span class="text-link">阅读本期 {icon("arrow")}</span></div></a></article>' for i in issues)
    return '<section class="page-heading"><span class="eyebrow">THE WEEKLY ARCHIVE</span><h1>每一期，<em>都有新故事。</em></h1><p>从创刊开始，把每周喜欢的作品留在这里。</p></section><div class="archive-grid">'+cards+'</div>'


def rules(rule):
    coefficients=''.join(f'<article class="coefficient window"><span>{e(k)}</span><code>{e(v.replace("round_half_up", "round"))}</code></article>' for k,v in rule['coefficients'].items())
    return f'''<section class="page-heading"><span class="eyebrow">HOW THE RANKING WORKS</span><h1>好作品值得看见，<br><em>怎么算，也写清楚。</em></h1><p>本期与往期页面保留当时的口径和指标。规则版本：{e(rule['id'])}</p></section><div class="rules-layout"><article class="rules-main window">{window_bar("计分说明")}<div class="prose"><h2>先确认统计口径</h2><p>创刊特辑使用近 28 天投稿作品的累计指标。常规周榜先计算播放、评论、弹幕、收藏和投币的周期净增量，再代入同一公式。每期投稿区间和实际观测时间会在期刊页展示。</p><h2>综合得分</h2><div class="formula">S = (V × P × A + R × B × 50<br>+ K × C × 20 + F × C) × D</div><p>V 为播放，R 为评论，M 为弹幕，F 为收藏，K 为投币，N 为分 P 数。点赞和分享单独展示，不参与当前版本计分。</p><div class="coefficients">{coefficients}</div><h2>精度与同分</h2><p>{e(rule['rounding'])}</p><p>{e(rule['tie_break'])}</p><h2>零值与周期增量</h2><p>{e(rule['zero_handling'])}</p><p>周期净增量为负、旧稿缺少期初快照或缺少期末快照时，先复核数据，再决定本期是否收录。不能用两次累计综合得分相减，代替各指标净增量计分。</p><h2>收录什么作品</h2><p>围绕 AI 产品、模型或助手的拟人角色展开的二创。剧情、动画、漫画、翻唱和整活都可以，制作方式不限。每期根据已经发现并经过主题检查的作品整理片单。</p><h2>出处与勘误</h2><p>每条作品保留原作者和原作链接。发现错字、误收或来源问题，请联系本期制作方。规则或内容更正会更新对应期数，并在页面记录修订日期。</p><p>综合公式参考<a href="{e(rule['sources'][0])}" target="_blank" rel="noopener">周刊哔哩哔哩排行榜 #852 的公开计分说明</a>，零值、舍入、同分与缺失基线处理按本文执行。</p></div></article><aside class="rules-aside window"><span class="eyebrow">A SMALL NOTE</span><h2>排名是一个入口。</h2><p>从一份片单出发，<br>遇见你喜欢的角色，<br>也认识背后的创作者。</p><a class="button primary" href="/">回到本期 {icon("arrow")}</a></aside></div>'''
