/* SPDX-License-Identifier: GPL-3.0-only */
(() => {
  'use strict';
  const stage=document.getElementById('stage');
  const supported=new Set(['chapter','next','podium_reveal','news_chapter']);
  let scene=null,overlay=null,started=0,live=false,token=0;
  const clamp=value=>Math.max(0,Math.min(1,value));
  const ease=value=>{const t=clamp(value);return 1-Math.pow(1-t,3);};
  function renderAt(seconds){
    if(!scene||!overlay)return;
    const duration=scene.duration;
    const entrance=scene.template==='next' ? .36 : .6;
    const exit=scene.template==='next' ? .22 : .3;
    const entering=ease(seconds/entrance);
    const leaving=ease((seconds-(duration-exit))/exit);
    const card=document.querySelector('.program-scene .program-hero-card');
    const art=document.querySelector('.program-scene .program-hero>img');
    const stepped=Math.round(entering*10)/10;
    if(card){
      card.style.transform=`translateX(${Math.round((1-entering)*-110-leaving*60)}px)`;
      card.style.opacity=String(Math.min(1,entering*3)*(1-leaving));
    }
    if(art){
      const settle=Math.sin(clamp(seconds/entrance)*Math.PI)*-16;
      art.style.transform=`translate(${Math.round((1-stepped)*210+leaving*160)}px,${Math.round(settle)}px) rotate(${(1-stepped)*3}deg)`;
      art.style.opacity=String(Math.min(1,entering*2)*(1-leaving));
    }
    overlay.querySelectorAll('.motion-shutter').forEach((bar,index)=>{
      const delay=index*.024;
      const open=ease((seconds-delay)/.32);
      const close=ease((seconds-(duration-.24)-delay*.3)/.24);
      bar.style.transform=`translateX(${Math.round((-open+close)*104)}%)`;
    });
    overlay.querySelectorAll('.motion-spark').forEach((spark,index)=>{
      const appear=clamp((seconds-.24-index*.06)/.16);
      const blink=.72+Math.sin(Math.floor(seconds*6)*1.2+index)*.28;
      spark.style.opacity=String(appear*blink*(1-leaving));
      spark.style.transform=`translateY(${Math.round((1-appear)*28)}px) rotate(${index%2?-12:12}deg)`;
    });
    const progress=overlay.querySelector('.motion-progress>i');
    progress.style.transform=`scaleX(${clamp(seconds/entrance)})`;
    return {seconds,entrance:entering,exit:leaving};
  }
  function configure(value,{forExport=false,still=false,timeline=false}={}){
    token++;live=false;scene=null;
    overlay?.remove();overlay=null;
    stage.classList.remove('motion-scene');
    if(!supported.has(value.template))return false;
    scene={...value,duration:Number(value.duration)||(value.template==='next'?1.2:5)};
    stage.classList.add('motion-scene');
    overlay=document.createElement('div');overlay.className='motion-overlay';overlay.setAttribute('aria-hidden','true');
    overlay.innerHTML='<div class="motion-progress"><i></i></div>'+Array.from({length:6},(_,i)=>`<span class="motion-shutter shutter-${i}" style="top:${i*18}%"></span>`).join('')+'<b class="motion-spark spark-a">✦</b><b class="motion-spark spark-b">✦</b><b class="motion-spark spark-c">＋</b>';
    stage.append(overlay);
    renderAt(forExport||still?Math.min(.8,value.duration/2):0);
    if(!forExport&&!still){
      const current=token;started=performance.now();live=true;
      const limit=timeline?scene.duration:Math.min(.8,scene.duration*.6);
      const tick=now=>{if(!live||current!==token)return;renderAt(Math.min((now-started)/1000,limit));if(now-started<limit*1000)requestAnimationFrame(tick);};
      requestAnimationFrame(tick);
    }
    return true;
  }
  window.weeklyMotion=Object.freeze({configure,renderAt,supports:id=>supported.has(id)});
})();
