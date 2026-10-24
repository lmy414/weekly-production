/* SPDX-License-Identifier: GPL-3.0-only */
(() => {
  'use strict';
  const escape = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const templates = new Set(['rundown','scope','scoring','scoring_details']);
  const portrait = role => `<div class="editorial-portrait"><span class="editorial-orbit" aria-hidden="true"></span><img src="/preview-assets/${encodeURIComponent(role)}.png" alt="鲸鱼娘"></div>`;
  const heading = (kicker,title) => `<header class="editorial-heading"><p class="editorial-kicker">${escape(kicker)}</p><h2>${title}</h2></header>`;
  const footer = (text,rule='') => `<footer class="editorial-footer"><span>${text}</span><span>${escape(rule)}</span></footer>`;
  const fraction = (top,bottom) => `<span class="editorial-fraction"><span>${top}</span><span>${bottom}</span></span>`;
  const shortDate = value => value.slice(5,10).replace('-','.');

  function render(scene,context) {
    if(!templates.has(scene.template)) return null;
    const inaugural=context.kind==='cumulative';
    let contents, variant=scene.template;
    if(scene.template==='rundown') {
      const groups=[];
      for(let offset=0;offset<context.selected.length;offset+=5)groups.push(context.selected.slice(offset,offset+5));
      contents=`${heading('本期榜单 / ISSUE '+context.issue_number,'今天的片单，她们都在。')}<div class="editorial-lineup">${groups.map(rows=>`<ol>${rows.map(row=>`<li class="${row.rank<=3?'lineup-podium':''}"><b>${String(row.rank).padStart(2,'0')}</b><div><h3>${escape(context.work_copy?.[row.bvid]?.short_title||row.title)}</h3><p><span>${escape(row.author)}</span><strong>${Number(row.score).toLocaleString('zh-CN')} 分</strong></p></div></li>`).join('')}</ol>`).join('')}</div>${footer('计分和收录规则见视频结尾。','共 '+context.rank_count+' 部作品')}`;
    } else if(scene.template==='scope' && scene.page==='inclusion') {
      variant='scoring_details';
      contents=`${heading('收录规则 / AI 拟人二创','哪些作品，会出现在这里？')}<div class="editorial-rule-list"><section><span>01 / 角色与题材</span><h3>AI 模型与助手的拟人二创</h3><p>剧情、动画、漫画、翻唱、整活，都可以。</p></section><section><span>02 / 内容判断</span><h3>围绕 AI 拟人角色展开</h3><p>结合标题、简介与实际画面，制作方式不限。</p></section></div>${portrait(scene.host_art||'scope')}${footer('有好作品，欢迎在评论区留下 BV 号。','收录规则')}`;
    } else if(scene.template==='scope') {
      variant='period';
      contents=`${heading(inaugural?'创刊特辑 / AI 拟人二创':'本周主榜 / AI 拟人二创',inaugural?'近 '+Number(context.window_days||28)+' 天，<br>AI 娘新作集合。':'这一周，<br>谁的新作被看见？')}<div class="editorial-scope-copy"><p class="editorial-scope-dates">${escape(shortDate(context.begin))}<span>—</span>${escape(shortDate(context.end))}</p><p class="editorial-scope-basis">${inaugural?'本期用累计数据计分':'本期用各项周期净增量计分'}</p><p class="editorial-scope-next">${inaugural?'常规周榜：各项周期增量代入同一公式':'播放、互动，一起算进综合得分'}</p></div>${portrait(scene.host_art||'scope')}${footer('投稿起止与实际观测时间见简介。',inaugural?'累计特辑':'周期增量')}`;
    } else if(scene.template==='scoring' && scene.page!=='coefficients') {
      variant='formula';
      contents=`${heading('名次怎么算 / 综合得分','播放与互动，合成这一分。')}<div class="editorial-total-formula">${escape(context.rule.formula.replaceAll('*',' × '))}</div><div class="editorial-variables">V 播放　R 评论　M 弹幕　F 收藏　K 投币　N 分 P 数</div><div class="editorial-contributions"><div><span>播放</span><strong>V × P × A</strong></div><div><span>评论</span><strong>R × B × 50</strong></div><div><span>投币</span><strong>K × C × 20</strong></div><div><span>收藏</span><strong>F × C</strong></div></div><div class="editorial-score-note"><b>四项相加，再乘 D</b><p>弹幕参与 C、D 修正；点赞与分享作展示。</p></div>${portrait(scene.host_art||'score')}${footer('公式参考：周刊娘 #852','完整计分明细见简介')}`;
    } else if(scene.template==='scoring') {
      variant='coefficients';
      const rows=[['P','4','N + 3','分 P 修正 · 三位小数'],['A','1,000,000 + V','2 × V','上限 1 · 保留原精度'],['B','20 × F + 10 × K','V + 10 × K + 50 × R','上限 1 · 两位小数'],['C','50 × R + M','2 × V + 10 × F + 20 × K','上限 1 · 两位小数'],['D','log₁₀(R + M + 10)','log₁₀(V + F + K + 10)','三位小数']];
      contents=`${heading('名次怎么算 / 修正系数','公式里的 P、A、B、C、D。')}<div class="editorial-coefficient-list">${rows.map(([key,top,bottom,note])=>`<div class="editorial-coefficient"><b>${key}</b><span class="editorial-equals">=</span>${fraction(top,bottom)}<small>${note}</small></div>`).join('')}</div>${portrait(scene.host_art||'score')}${footer('V = 0 时 A = 1；B、C 分母为 0 时取 0。','小数按四舍五入处理')}`;
    } else {
      contents=`${heading('名次怎么算 / 排序','得分高的，排在前面。')}<div class="editorial-rule-list"><section><span>01 / 总分</span><h3>四舍五入，取整数</h3><p>按最终综合得分从高到低排列。</p></section><section><span>02 / 同分</span><h3>按 BV 号升序排列</h3><p>BV 号按区分大小写的字典顺序比较。</p></section></div>${portrait(scene.host_art||'thinking')}${footer('完整公式、统计区间、单片得分，随本期简介一起公开。','计分版本 v1')}`;
    }
    return `<section class="editorial editorial-${variant}" data-editorial-page="${variant}">${contents}</section>`;
  }
  window.weeklyEditorial=Object.freeze({supports:name=>templates.has(name),render});
})();
