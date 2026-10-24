// SPDX-License-Identifier: GPL-3.0-only
// This is the offline graphics renderer, not automation of a user's browser.
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import path from 'node:path';

const output=path.resolve(process.argv[2]);
const url=process.argv[3];
const program=JSON.parse(await readFile(path.join(output,'program.json'),'utf8'));
const copyOnly=false;
const require=createRequire(import.meta.url);
const puppeteer=require(process.env.WEEKLY_PUPPETEER||'puppeteer-core');
const chrome=process.env.WEEKLY_CHROME;
if(!chrome)throw new Error('Chromium executable missing');
const browser=await puppeteer.launch({executablePath:chrome,headless:true,defaultViewport:{width:1920,height:1080,deviceScaleFactor:1},args:['--disable-dev-shm-usage']});
const assets=path.join(output,'plates');await mkdir(assets,{recursive:true});
const catalogue=path.join(output,'catalogue');await mkdir(catalogue,{recursive:true});
const renderInput=structuredClone(program);delete renderInput.publication;
const results={render_input:renderInput,scenes:[],catalogue:[],motion:[],errors:[]};
try {
  const page=await browser.newPage();
  await page.setRequestInterception(true);
  page.on('request',request=>{const u=request.url();if(u.startsWith(url+'/')||u.startsWith('data:'))request.continue();else request.abort();});
  page.on('pageerror',e=>results.errors.push(String(e)));
  await page.goto(url+'/?render=1&clean=1&still=1',{waitUntil:'networkidle0'});
  await page.waitForFunction(()=>window.programTemplates?.render);
  async function capture(scene,file){
    const info=await page.evaluate(async ({scene,context})=>{
      const info=await window.programTemplates.render(scene,context,{forExport:true});
      const regions={
        '顶部栏目':'.show-header','封面主文案':'.cover-copy','封面期号':'.cover-edition','封面底栏':'.cover-note',
        '页面标题':'.editorial-heading','开场榜单':'.editorial-lineup','统计口径':'.editorial-scope-copy',
        '总分公式':'.editorial-total-formula','变量说明':'.editorial-variables','计分构成':'.editorial-contributions',
        '计分补充':'.editorial-score-note','修正系数':'.editorial-coefficient-list','排序细则':'.editorial-rule-list',
        '页面脚注':'.editorial-footer','栏目标题':'.program-heading','栏目内容':'.program-board',
        '转场窗口栏':'.program-hero-card>.window-bar','转场主文案':'.program-hero-copy','名次与数据':'.rank-panel','角色画面':'.host-panel',
        '作品窗口栏':'.work-window>.window-bar','作品出处':'.work-caption','新闻栏目':'.news-topline','新闻窗口栏':'.news-board>.window-bar','新闻正文':'.news-story','新闻角色画面':'.news-host',
        '新闻目录':'.news-queue','底部常驻':'.stage-footnote'
      };
      return {...info,fontReady:document.fonts.check('24px FusionPixel')&&document.fonts.check('32px WeeklySans'),
        display_text:document.getElementById('stage').innerText,
        characterDialogue:document.querySelectorAll('#stage .host-bubble').length>0||[...document.querySelectorAll('#stage .cover-kicker,#stage .show-status,#stage .host-label,#stage .host-nameplate,#stage .news-topline,#stage .news-host-desk,#stage .stage-footnote,#stage .program-kicker')].some(e=>/本期值班|本期主持|本鲸|鲸鱼娘收工|鲸鱼娘的放映室|鲸鱼娘的周末简报/.test(e.innerText)),
        copy_blocks:Object.entries(regions).flatMap(([placement,selector])=>[...document.querySelectorAll('#stage '+selector)].filter(e=>e.getBoundingClientRect().width>0).map(e=>({placement,text:e.innerText}))),
        brokenImages:[...document.querySelectorAll('#stage img')].filter(i=>i.getBoundingClientRect().width>0&&(!i.complete||!i.naturalWidth)).map(i=>i.alt),
        forbiddenText:/模板预演|待人工确认|新闻版式示例|核实后填入|待填并核实/.test(document.getElementById('stage').innerText),
        overflow:[...document.querySelectorAll('#stage h1,#stage h2,#stage h3,#stage .program-board,#stage .editorial,#stage .editorial-total-formula,#stage .editorial-coefficient-list,#stage .news-story')].filter(e=>e.getBoundingClientRect().width>0&&(e.scrollWidth>e.clientWidth+2||(e.matches('.program-board,.editorial,.news-story')&&e.scrollHeight>e.clientHeight+2))&&getComputedStyle(e).textOverflow!=='ellipsis').map(e=>e.className||e.tagName)};
    },{scene,context:program.context});
    if(!info.fontReady||info.brokenImages.length||info.forbiddenText||info.characterDialogue)throw new Error('Graphics readiness failed: '+JSON.stringify(info));
    if(!copyOnly)await page.screenshot({path:file,type:'png'});
    return info;
  }
  for(const scene of program.scenes){
    const info=await capture(scene,path.join(assets,scene.id+'.png'));
    results.scenes.push({id:scene.id,...info});
    if(scene.animation&&!copyOnly){
      if(!info.animated)throw new Error('Motion template is missing: '+scene.id);
      const directory=path.join(output,'motion',scene.id);await mkdir(directory,{recursive:true});
      const fps=scene.animation.fps;
      const count=Math.ceil(scene.duration*fps);
      for(let index=0;index<count;index++){
        await page.evaluate(seconds=>window.programTemplates.renderAt(seconds),index/fps);
        await page.screenshot({path:path.join(directory,`frame-${String(index+1).padStart(4,'0')}.png`),type:'png'});
      }
      results.motion.push({id:scene.id,frames:count,fps,version:scene.animation.version});
    }
    process.stdout.write(JSON.stringify({step:'capture',scene:scene.id,template:scene.template})+'\n');
  }
  for(const template of program.catalogue){
    const scene=program.scenes.find(s=>s.template===template.id)||{template:template.id,title:template.title,row:program.context.selected[Math.min(2,program.context.selected.length-1)],next_rank:4};
    const info=await capture(scene,path.join(catalogue,template.id+'.png'));
    results.catalogue.push({id:template.id,...info});
    for(const extra of program.scenes.filter(s=>s.template===template.id&&s.page&&s.page!==scene.page)){
      const id=template.id+'-'+extra.page;
      results.catalogue.push({id,...await capture(extra,path.join(catalogue,id+'.png'))});
    }
  }
} finally {await browser.close();}
await writeFile(path.join(output,copyOnly?'copy-capture.json':'capture-report.json'),JSON.stringify(results,null,2));
if(results.errors.length)throw new Error('Browser graphics errors: '+results.errors.join('; '));
if([...results.scenes,...results.catalogue].some(s=>s.overflow.length))throw new Error('Text layout overflow; inspect capture-report.json');
process.stdout.write(JSON.stringify({captured:results.scenes.length,catalogue:results.catalogue.length,overflow:results.catalogue.filter(s=>s.overflow.length)})+'\n');
