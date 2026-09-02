(function(){
  'use strict';
  const root=document.documentElement;
  const body=document.body;
  function buildCosmos(){
    if(document.querySelector('.lf-cosmos')) return;
    const layer=document.createElement('div'); layer.className='lf-cosmos'; layer.setAttribute('aria-hidden','true');
    layer.innerHTML='<div class="lf-nebula n1"></div><div class="lf-nebula n2"></div><div class="lf-orbital-haze"></div>';
    const frag=document.createDocumentFragment();
    for(let i=0;i<46;i++){
      const s=document.createElement('i'); s.className='lf-star';
      const size=(0.65+Math.random()*1.7).toFixed(2)+'px';
      s.style.setProperty('--s',size); s.style.setProperty('--x',(Math.random()*100).toFixed(2)+'%'); s.style.setProperty('--y',(Math.random()*100).toFixed(2)+'%');
      s.style.setProperty('--a',(0.35+Math.random()*0.55).toFixed(2)); s.style.setProperty('--d',(3.5+Math.random()*8).toFixed(2)+'s'); s.style.setProperty('--delay',(-Math.random()*8).toFixed(2)+'s'); s.style.setProperty('--depth',(0.2+Math.random()*0.8).toFixed(2)); frag.append(s);
    }
    layer.append(frag); body.prepend(layer);
  }
  function syncRoute(){ const active=document.querySelector('.screen.active'); body.dataset.scene=active?.dataset.screen||'home'; }
  function observeRoute(){
    const screens=[...document.querySelectorAll('.screen')];
    const observer=new MutationObserver(syncRoute); screens.forEach(s=>observer.observe(s,{attributes:true,attributeFilter:['class']})); syncRoute();
  }
  function parallax(){
    let tx=0,ty=0,raf=0; const stars=()=>document.querySelectorAll('.lf-star');
    window.addEventListener('pointermove',e=>{tx=(e.clientX/window.innerWidth-.5)*10;ty=(e.clientY/window.innerHeight-.5)*8;if(raf)return;raf=requestAnimationFrame(()=>{root.style.setProperty('--mx',tx+'px');root.style.setProperty('--my',ty+'px');stars().forEach(n=>{n.style.transform=`translate3d(${tx*parseFloat(n.style.getPropertyValue('--depth')||.4)}px,${ty*parseFloat(n.style.getPropertyValue('--depth')||.4)}px,0)`});raf=0})},{passive:true});
  }
  function boot(){buildCosmos();observeRoute();parallax();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
