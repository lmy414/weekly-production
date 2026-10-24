(()=>{'use strict';
const $=s=>document.querySelector(s);let timer;
function notice(text){const n=$('#notice');n.textContent=text;n.hidden=false;clearTimeout(timer);timer=setTimeout(()=>n.hidden=true,3200);}
const cards=[...document.querySelectorAll('[data-work]')];let category='全部';
function filter(){const term=($('#work-search')?.value||'').trim().toLowerCase();let count=0;for(const card of cards){card.hidden=!((category==='全部'||card.dataset.category===category)&&(!term||card.dataset.search.includes(term)));if(!card.hidden)count++;}if($('#result-count'))$('#result-count').textContent=count+' 部作品';if($('#empty-state'))$('#empty-state').hidden=count!==0;}
$('#work-search')?.addEventListener('input',filter);
for(const button of document.querySelectorAll('[data-filter]'))button.addEventListener('click',()=>{category=button.dataset.filter;for(const b of document.querySelectorAll('[data-filter]'))b.setAttribute('aria-pressed',String(b===button));filter();});
const dialog=$('#share-dialog');let shareUrl='';
for(const a of document.querySelectorAll('[data-share]'))a.addEventListener('click',event=>{if(!dialog?.showModal)return;event.preventDefault();shareUrl=a.dataset.share;$('#share-preview').src=shareUrl;$('#share-download').href=shareUrl;$('#share-download').download=shareUrl.split('/').pop();$('#share-copy').disabled=false;dialog.showModal();});
$('[data-close-dialog]')?.addEventListener('click',()=>dialog.close());
dialog?.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
$('#share-copy')?.addEventListener('click',async()=>{const button=$('#share-copy');if(!navigator.clipboard?.write||!window.ClipboardItem){notice('当前浏览器请使用“保存 PNG”或长按图片。');return;}button.disabled=true;try{const response=await fetch(shareUrl);if(!response.ok)throw Error('image');const blob=await response.blob();await navigator.clipboard.write([new ClipboardItem({'image/png':blob})]);notice('图片已复制，可以直接粘贴分享。');}catch{notice('图片复制未完成，可以点击“保存 PNG”。');}finally{button.disabled=false;}});
for(const a of document.querySelectorAll('[data-copy-link]'))a.addEventListener('click',async event=>{event.preventDefault();const url=new URL(a.getAttribute('href'),location.href);try{await navigator.clipboard.writeText(url.href);notice('作品链接已复制。');}catch{location.hash=url.hash;notice('已定位作品，可复制浏览器地址。');}});
})();
