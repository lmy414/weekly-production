/* SPDX-License-Identifier: GPL-3.0-only */
(() => {
  'use strict';
  const studio = window.weeklyStudio;
  const stage = document.getElementById('stage');
  const video = document.getElementById('work-video');
  const escape = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = n => Number(n ?? 0).toLocaleString('zh-CN');
  const panel = document.createElement('section');
  panel.className='program-scene';panel.hidden=true;stage.append(panel);
  let payload, playerTimer, playerPosition=0, podiumPending=false;
  video.addEventListener('timeupdate',()=>{
    if(podiumPending && video.currentTime>=7){podiumPending=false;studio.setImmersive(true);}
  });
  const board=(title,subtitle,content,bar='本期放映室')=>`<div class="program-heading">${escape(title)}<span>${escape(subtitle)}</span></div><div class="program-board pixel-window"><div class="window-bar"><span>${escape(bar)}</span><span>AI娘周刊</span></div><div class="program-content">${content}</div></div>`;
  const card=(label,heading,text,cls='')=>`<div class="program-card ${cls}"><b>${escape(label)}</b><h3>${escape(heading)}</h3><p>${escape(text)}</p></div>`;
  const hero=(kicker,heading,sub,art='transition',extra='')=>`<div class="program-hero"><div class="program-hero-card pixel-window"><div class="window-bar"><span>AI娘周刊</span><span>✦</span></div><div class="program-hero-copy"><p class="program-kicker">${escape(kicker)}</p><h2>${heading}</h2>${extra}<p>${escape(sub).replaceAll('\n','<br>')}</p></div></div><img src="/preview-assets/${art}.png" alt="本期角色插画"></div>`;
  const table=(rows,context)=>`<table class="program-table"><thead><tr><th>名次</th><th>作品</th><th>得分</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${String(r.rank).padStart(2,'0')}</td><td title="${escape(r.title)}">${escape(context.work_copy?.[r.bvid]?.short_title||r.title)}</td><td>${fmt(r.score)}</td></tr>`).join('')}</tbody></table>`;

  async function render(scene, context, options={}) {
    await studio.ready;
    podiumPending=false;
    const t=scene.template;
    const art=scene.host_art||({cover:'cover',opening:'welcome',ranking:'watching',podium:'champion',news:'news-update',end:'goodbye'})[t]||'transition';
    const number=context.issue_number||context.episode_id.split('-').at(-1)||'001';
    const inaugural=context.kind==='cumulative';
    const subject=inaugural?`近 ${context.window_days||28} 天 AI 娘新作`:'本周 AI 娘作品';
    const strip=document.querySelector('.episode-strip');
    strip.querySelector('b').textContent=inaugural?'创刊特辑':`第 ${number} 期`;
    strip.querySelector('span').textContent=subject;
    strip.querySelector('span:last-child').textContent='ISSUE '+number;
    document.querySelector('.cover-edition b').textContent=number;
    document.querySelector('.cover-edition span:last-child').textContent=inaugural?'创刊号':'第 '+number+' 期';
    document.querySelector('.cover-subtitle').textContent=subject;
    studio.setMode(['ranking','podium','news','cover','opening'].includes(t)?(t==='opening'?'cover':t):'cover',false);
    panel.hidden=true;panel.innerHTML='';panel.dataset.template=t;
    stage.classList.toggle('program-export',!!options.forExport);
    document.getElementById('status-label').textContent=({opening:'本期开始',cover:'本期封面',rundown:'本期榜单',scoring:'名次怎么算',scoring_details:'名次怎么算',scope:'本期怎么统计',news:'模型圈周报',ranking:'作品放映中',podium:'作品放映中',next:'下一位上场',summary:'再看一眼片单',statistics:'下期想看谁',outro:'感谢观看',credits:'制作名单',end:'下期见'})[t]||scene.title||'AI娘周刊';
    document.getElementById('stage-note').textContent=inaugural?'创刊特辑 · 近 28 天 AI 娘新作':'本周 AI 娘新作 · '+context.begin.slice(5,10)+'—'+context.end.slice(5,10);
    document.querySelector('.stage-footnote>span:last-child').textContent='AI GIRL WEEKLY / 本期片单';
    document.querySelector('.score-label').innerHTML=`综合得分 <span>${inaugural?'本期累计数据':'本期各项增量'}</span>`;
    if(['ranking','podium'].includes(t)) {
      document.querySelector('.host-art').src=`/preview-assets/${art}.png`;
      video.style.visibility=options.forExport?'hidden':'visible';
      studio.setWork(scene.row,context.rule,scene.row.rank);
      document.getElementById('rank-state').textContent=inaugural?'创刊期':'周榜';
      if(!options.forExport) {
        podiumPending=t==='podium';
        video.src=`/program-media/${scene.row.bvid}.mp4`;video.loop=false;
        video.onloadedmetadata=()=>{video.currentTime=0;if(!new URLSearchParams(location.search).has('still'))video.play().catch(()=>{});};
      } else {video.pause();video.style.visibility='hidden';}
    } else if(t==='news') {
      document.querySelector('.news-host>img').src=`/preview-assets/${art}.png`;
      document.getElementById('news-period').textContent=context.news_window.replace(' · 按事件日期','');
      const n=scene.news_index||1;
      document.querySelector('.news-board .window-bar>span:first-child').textContent=`本周速读 / ${String(n).padStart(2,'0')}`;
      document.querySelector('.news-meta>span:first-child').textContent=scene.category||'模型更新';
      document.querySelector('.news-meta>span:last-child').textContent=`${String(n).padStart(2,'0')} / ${String(scene.news_total||3).padStart(2,'0')}`;
      if(!scene.fact_checked||!scene.source_url)throw new Error('新闻事实与原始来源尚未就绪');
      document.querySelector('.news-board .window-bar>span:last-child').textContent=`${scene.published_date} / ${scene.source_label}`;
      document.querySelector('.news-story h3').textContent=scene.headline;
      document.querySelector('.news-deck').textContent=scene.summary;
      document.querySelectorAll('.news-questions li p').forEach((p,i)=>p.textContent=scene[['release','change','availability'][i]]);
      const newsCopy=context.news_copy?.[scene.news_id]||{};
      document.querySelectorAll('.news-questions li strong').forEach((p,i)=>p.textContent=(newsCopy.labels||['这次更新','值得关注','现在进展'])[i]);
      document.querySelector('.news-source p').textContent=`${scene.source_label} · ${new URL(scene.source_url).hostname}`;
      document.querySelector('.news-source>b').textContent='原文链接在简介';
      document.querySelectorAll('.news-queue>div').forEach((d,i)=>{d.classList.toggle('active',i===n-1);d.querySelector('span').textContent=context.news_queue?.[i]||'本周进展';});
      document.querySelector('.queue-time').textContent=`这一周，关注这 ${scene.news_total} 件事`;
    } else if(!['cover','opening'].includes(t)) {
      document.querySelector('.cover-layout').hidden=true;panel.hidden=false;
      const r=scene.row;
      const views={
        chapter:()=>hero('NOW SHOWING',escape(scene.heading||'开始放映'),scene.subheading||`从第 ${context.rank_count} 名开始`,art),
        next:()=>hero('NEXT / 下一位上场',`第 <span class="program-rank-big">${String(scene.next_rank||4).padStart(2,'0')}</span> 名`,'',art),
        podium_reveal:()=>hero('TOP THREE / 本期前三',`第 <span class="program-rank-big">${String(r?.rank||3).padStart(2,'0')}</span> 名`,context.work_copy?.[r?.bvid]?.short_title||r?.title||context.selected[2]?.title,art,`<div class="program-score-note">综合得分 ${fmt(r?.score||context.selected[2]?.score)} 分</div>`),
        summary:()=>board('刚才那一段，你最喜欢哪部？','本期片单 · 记得收藏',`<div class="program-row-pair">${table(context.selected.slice(0,8),context)}${table(context.selected.slice(8,16),context)}</div>`),
        statistics:()=>hero('下期片单 / 等你推荐','下一期，<br>你想看谁？','评论区留下角色名和作品 BV 号。\n新角色、新故事，都想看看。',art),
        pickup:()=>hero('PICK UP / 片单之外','这一部，<br>想多留一会儿。','有些作品，看完还想再聊两句。',art),
        subrank:()=>board('还有这些，也别错过。','更多 AI 娘新作',table(context.selected.slice(6,12),context)),
        history:()=>hero('REWIND / 往期回顾','回到那一周。','再看一遍，还是会记得那个瞬间。',art),
        correction:()=>board('这一处，我们来更正。','更正说明',`<div class="program-grid">${card('更正内容',scene.correction_title||'作品、名次或数据修正',scene.correction_text||'更正后的内容与影响范围，列在这里。','accent')}${card('更正依据','把来龙去脉说清楚',scene.correction_source||'相关来源与更新后的计分结果，见本期简介。','gold')}</div>`),
        news_chapter:()=>hero('WEEKLY NEWS / 镜头转回模型圈','片单看完，<br>模型圈也挺热闹。',context.news_window.replace(' · 按事件日期',''),art),
        outro:()=>hero('THANKS FOR WATCHING','喜欢的那一段，<br>去原作再看一遍。','给作者一个赞，也把这份片单分享给同好。\n'+context.update_schedule,art),
        credits:()=>board('这期节目，谢谢各位。','AI GIRL WEEKLY',`<div class="program-list"><div><b>策划 · 选片 · 制作</b><span>站长</span></div><div><b>作品 · 原声</b><span>本期片单中的各位 UP 主</span></div><div><b>节目 BGM</b><span>${context.audio.bgm?`《${escape(context.audio.bgm.title)}》 / ${escape(context.audio.bgm.artist)}`:'AI 娘周刊原创配乐'}</span></div><div><b>作品与音乐出处</b><span>原视频、歌曲原曲、完整计分明细，请看简介。</span></div></div>`),
        end:()=>hero('AI GIRL WEEKLY / ISSUE '+number,'下期见。',context.update_schedule,art),
      };
      if(!views[t]&&!window.weeklyEditorial.supports(t)) throw new Error('Unknown program template: '+t);
      panel.innerHTML=window.weeklyEditorial.render(scene,context)||views[t]();
    } else {
      document.querySelector('.cover-portrait img').src=`/preview-assets/${art}.png`;
      document.querySelector('.cover-kicker').textContent='AI 娘创作放映室';
      document.querySelector('.cover-bottom>b').textContent=inaugural?'创刊特辑':'本周片单';
      document.querySelector('.cover-bottom>span').textContent='模型下班，角色上场。';
      document.querySelectorAll('.cover-note>span')[0].textContent=`${context.rank_count} 部新作，一起开看`;
      document.querySelectorAll('.cover-note>span')[1].textContent='原视频 · 计分规则见简介';
    }
    const copy=context.copy||{};
    const assign=(selector,key)=>{if(copy[key]!==undefined){const e=stage.querySelector(selector);if(e)e.textContent=copy[key];}};
    if(['opening','cover'].includes(t)){
      assign('.cover-kicker','opening_kicker');assign('.cover-subtitle','opening_subtitle');
      assign('.cover-bottom>span','opening_tagline');assign('.cover-note>span:first-child','opening_note');
    }
    const textKey={statistics:'statistics_text',outro:'outro_text',end:'end_text'}[t];
    if(textKey)assign('.program-hero-copy>p:last-child',textKey);
    if(t==='credits'&&context.branding?.producer){const e=panel.querySelector('.program-list>div:first-child>span');if(e)e.textContent=context.branding.producer;}
    const animated=window.weeklyMotion.configure(scene,{forExport:!!options.forExport,still:new URLSearchParams(location.search).has('still'),timeline:!!options.timeline});
    await document.fonts.ready;
    await Promise.all([...stage.querySelectorAll('img')].filter(i=>i.getBoundingClientRect().width>0).map(i=>i.decode().catch(()=>{})));
    return {template:t,page:scene.page||null,host_art:art,animated,viewport:['ranking','podium'].includes(t)?{x:44,y:184,width:1400,height:788}:null};
  }

  function example(template,page) {
    const scene=payload.scenes.find(s=>s.template===template&&(!page||s.page===page))||payload.scenes.find(s=>s.template===template);
    if(scene)return scene;
    return {template,title:payload.catalogue.find(t=>t.id===template)?.title,row:payload.context.selected[2],next_rank:4};
  }

  async function catalogue() {
    const response=await fetch('/program-data',{cache:'no-store'});
    if(!response.ok) throw new Error('整期模板计划尚未生成');
    payload=await response.json();
    const nav=document.querySelector('.preview-toolbar nav');nav.className='program-nav';nav.replaceChildren();
    const select=document.createElement('select');select.className='catalogue-select';select.setAttribute('aria-label','选择节目固定模板');
    for(const item of payload.catalogue){const o=document.createElement('option');o.value=item.id;o.textContent=item.title+' / '+item.usage;select.append(o);}
    nav.append(select);
    const pageButton=document.createElement('button');pageButton.className='catalogue-page';pageButton.hidden=true;nav.append(pageButton);
    const link=document.createElement('a');link.href='/watch.html';link.target='_blank';link.className='catalogue-link';link.textContent='播放完整成片 ↗';nav.append(link);
    const gallery=document.createElement('a');gallery.href='hosts.html';gallery.target='_blank';gallery.className='catalogue-link';gallery.textContent='角色素材 ↗';nav.append(gallery);
    const clips=document.createElement('a');clips.href='clips.html';clips.target='_blank';clips.className='catalogue-link';clips.textContent='作品选段 ↗';nav.append(clips);
    let currentPage;
    const show=async(id,page)=>{
      const scene=example(id,page);currentPage=scene.page;
      await render(scene,payload.context);
      const pages=payload.scenes.filter(s=>s.template===id&&s.page);
      const pageIndex=pages.findIndex(s=>s.page===currentPage);
      pageButton.hidden=pages.length<2;
      pageButton.textContent=`说明 ${pageIndex+1} / ${pages.length} · 下一页`;
      document.getElementById('mode-heading').textContent=payload.catalogue.find(t=>t.id===id)?.title||id;
      document.getElementById('mode-description').textContent=scene.clip_selection?`第 ${scene.clip_selection.part} P · ${scene.clip_selection.start.toFixed(2)} 至 ${scene.clip_selection.end.toFixed(2)} 秒 / ${scene.clip_selection.summary}`:'整期固定模板库 / 综合计分 / 可选栏目保留，创刊期按编排启用。';
      document.getElementById('mode-index').textContent=String(payload.catalogue.findIndex(t=>t.id===id)+1).padStart(2,'0')+' / '+payload.catalogue.length;
      document.getElementById('load-state').textContent=`本期编排 ${Math.floor(payload.duration/60)}分${Math.round(payload.duration%60)}秒 / ${payload.scenes.length} 段 / 1920 × 1080 · 30 fps`;
      const query=new URLSearchParams(location.search);query.set('catalog','1');query.set('template',id);
      if(currentPage)query.set('page',currentPage);else query.delete('page');
      const cleanQuery=new URLSearchParams(query);cleanQuery.set('clean','1');
      document.querySelector('.preview-actions a').href='?'+cleanQuery;
      history.replaceState(null,'','?'+query);
    };
    const oldPlay=document.getElementById('sequence');const play=oldPlay.cloneNode(true);oldPlay.replaceWith(play);
    let playing=false;
    select.onchange=()=>{playing=false;clearTimeout(playerTimer);play.textContent='播放编排';play.setAttribute('aria-pressed','false');show(select.value);};
    pageButton.onclick=()=>{
      playing=false;clearTimeout(playerTimer);play.textContent='播放编排';play.setAttribute('aria-pressed','false');
      const pages=payload.scenes.filter(s=>s.template===select.value&&s.page);
      show(select.value,pages[(pages.findIndex(s=>s.page===currentPage)+1)%pages.length].page);
    };
    play.onclick=async()=>{
      if(playing){playing=false;clearTimeout(playerTimer);video.pause();play.textContent='播放编排';play.setAttribute('aria-pressed','false');return;}
      playing=true;playerPosition=0;play.textContent='暂停编排';play.setAttribute('aria-pressed','true');
      const next=async()=>{if(!playing)return;const scene=payload.scenes[playerPosition++];if(!scene){playing=false;play.textContent='播放编排';play.setAttribute('aria-pressed','false');return;}select.value=scene.template;pageButton.hidden=true;await render(scene,payload.context,{timeline:true});if(!playing)return;playerTimer=setTimeout(next,scene.duration*1000);};next();
    };
    const params=new URLSearchParams(location.search);
    const requested=params.get('template')||({transition:'news_chapter'})[params.get('mode')]||params.get('mode');
    const initial=payload.catalogue.some(t=>t.id===requested)?requested:'opening';
    select.value=initial;await show(initial,params.get('page'));
  }
  window.programTemplates=Object.freeze({render,renderAt:seconds=>window.weeklyMotion.renderAt(seconds)});
  if(!new URLSearchParams(location.search).has('render')) catalogue().catch(e=>{document.getElementById('load-state').textContent=e.message;});
})();
