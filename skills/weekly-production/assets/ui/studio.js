/* SPDX-License-Identifier: GPL-3.0-only */
(() => {
  'use strict';
  const query=new URLSearchParams(location.search);
  const stage=document.getElementById('stage');
  const wrap=document.getElementById('stage-wrap');
  const video=document.getElementById('work-video');
  let mode='cover';
  function fit(){
    const available=document.body.classList.contains('clean')?Math.min(innerWidth,innerHeight*16/9):Math.min(wrap.parentElement.clientWidth,Math.max(360,innerHeight-254)*16/9);
    const width=Math.min(available,1920);
    wrap.style.width=`${width}px`;wrap.style.height=`${width*9/16}px`;
    stage.style.transform=`scale(${width/1920})`;
  }
  function setImmersive(value){
    stage.classList.toggle('immersive',value&&mode==='podium');
    document.getElementById('immersive').textContent=value?'回到名次与数据':'切到作品全屏';
  }
  function setWork(work,rule,rank){
    const number=value=>!Number.isFinite(value)?'—':value>=10000?`${(value/10000).toFixed(1).replace(/\.?0+$/,'')}万`:value.toLocaleString('zh-CN');
    document.getElementById('work-title').textContent=work.title;
    document.getElementById('work-author').textContent=`UP主 / ${work.author}`;
    document.getElementById('work-bvid').textContent=work.bvid;
    document.getElementById('view-value').textContent=Number(work.score).toLocaleString('zh-CN');
    for(const [id,key] of [['play','view'],['reply','reply'],['danmaku','danmaku'],['like','like'],['coin','coin'],['favorite','favorite']])document.getElementById(`${id}-value`).textContent=number(work.metrics[key]);
    if(rank!=null)document.getElementById('rank-number').textContent=String(rank).padStart(2,'0');
  }
  function setMode(next){
    mode=next;stage.dataset.mode=mode;stage.classList.remove('immersive');
    document.querySelector('.ranking-layout').hidden=!['ranking','podium'].includes(mode);
    document.querySelector('.transition-layout').hidden=true;
    document.querySelector('.news-layout').hidden=mode!=='news';
    document.querySelector('.cover-layout').hidden=mode!=='cover';
    document.getElementById('immersive').hidden=mode!=='podium';
    document.getElementById('immersive').textContent='切到作品全屏';
    video.pause();
  }
  document.getElementById('mute').addEventListener('click',()=>{
    video.muted=!video.muted;
    document.getElementById('mute').textContent=video.muted?'开启原片声音':'关闭原片声音';
    document.getElementById('mute').setAttribute('aria-pressed',String(video.muted));
    if(['ranking','podium'].includes(mode))video.play().catch(()=>{});
  });
  document.getElementById('immersive').addEventListener('click',()=>setImmersive(!stage.classList.contains('immersive')));
  video.addEventListener('timeupdate',()=>{if(video.duration>0)document.getElementById('playback-fill').style.width=`${video.currentTime/video.duration*100}%`;});
  window.addEventListener('resize',fit);
  if(query.get('clean')==='1')document.body.classList.add('clean');
  if(query.has('still'))stage.classList.add('still');
  setMode('cover');fit();
  window.weeklyStudio=Object.freeze({setMode,setImmersive,setWork,ready:document.fonts.ready});
})();
