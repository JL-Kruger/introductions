// js/starfield.js — ambient ember+spectral particle field (canvas-2D). Spec: STARFIELD-SPEC.md
// Constants: DPR_CAP=1.5 DENSITY_DIVISOR=12000 COUNT_MIN=24 COUNT_MAX=110 EMBER_FRACTION=0.35
// Embers (Phase 2.5.5): pixel-art sprites on an 8-step warm ramp (sun→fire→rust→pigment→sun),
// colour-cycled by the shimmer rAF via --shimmer-deg (inline-style read — no getComputedStyle).
// Twinkle layer (Phase 2.5.6): #stars canvas inside the sky sandwich (under the campfire
// glow), driven from the SAME rAF at a ~20fps redraw throttle. Pixel squares, locked palette.
const SPEC =[['94,154,14', .40],['232,226,218',.35],['14,77,14', .10],['242,198,42',.15]];
const STAR_COLORS=[['232,226,218',.55],['242,198,42',.20],['94,154,14',.10],['235,117,19',.08],['165,44,22',.07]];
const RAMP_KEYS=[[242,198,42],[235,117,19],[165,44,22],[105,25,13]]; // sun fire rust pigment
const EMBER_SIZES=[6,9,12];

const canvas=document.getElementById('starfield');
if(canvas){
  const ctx=canvas.getContext('2d'),mq=window.matchMedia('(prefers-reduced-motion: reduce)');
  let reduced=mq.matches,visible=!document.hidden,onscreen=true;
  let dpr=1,cssW=0,cssH=0,particles=[],sprites=new Map();
  let rafId=null,lastTs=null,resizeTimer=null;
  const rand=(a,b)=>a+Math.random()*(b-a);
  const pick=w=>{let r=Math.random();for(const[c,p]of w)if((r-=p)<=0)return c;return w[0][0];};

  // soft radial sprite — spectral motes only
  const glow=rgb=>{
    if(sprites.has(rgb))return sprites.get(rgb);
    const c=document.createElement('canvas');c.width=c.height=48;
    const g=c.getContext('2d'),gr=g.createRadialGradient(24,24,0,24,24,24);
    gr.addColorStop(0,`rgba(${rgb},1)`);gr.addColorStop(.25,`rgba(${rgb},.55)`);gr.addColorStop(1,`rgba(${rgb},0)`);
    g.fillStyle=gr;g.fillRect(0,0,48,48);sprites.set(rgb,c);return c;
  };

  // pixel-art ember sprites: 8 ramp colours × 3 discrete sizes.
  // 3×3 hard-edged spark pattern upscaled once with smoothing off — crisp at
  // draw time with zero per-frame state toggling. Hard core = "brighter".
  const PAT=[[.35,.85,.35],[.85,1,.85],[.35,.85,.35]];
  const emberSprites=[];
  for(let i=0;i<8;i++){
    const t=i/8*4,s0=t|0,f=t-s0,a=RAMP_KEYS[s0%4],b=RAMP_KEYS[(s0+1)%4];
    const rgb=a.map((v,k)=>Math.round(v+(b[k]-v)*f)).join(',');
    const base=document.createElement('canvas');base.width=base.height=3;
    const bg=base.getContext('2d');
    PAT.forEach((row,y)=>row.forEach((al,x)=>{bg.fillStyle=`rgba(${rgb},${al})`;bg.fillRect(x,y,1,1);}));
    emberSprites.push(EMBER_SIZES.map(s=>{
      const c=document.createElement('canvas');c.width=c.height=s;
      const g=c.getContext('2d');g.imageSmoothingEnabled=false;
      g.drawImage(base,0,0,s,s);return c;
    }));
  }
  // current ramp rotation — shimmer.js writes --shimmer-deg on <html> each frame
  const rampBase=()=>{
    const v=document.documentElement.style.getPropertyValue('--shimmer-deg');
    return v?(parseFloat(v)/45)|0:0; // 360° / 8 steps
  };

  const mkE=()=>{const si=(Math.random()*3)|0;return{type:1,x:rand(0,cssW),y:rand(cssH*.75,cssH),vx:0,
    vy:rand(8,22),size:EMBER_SIZES[si],sizeIdx:si,ramp:(Math.random()*8)|0,
    baseAlpha:rand(.55,.90),alpha:0,phase:rand(0,7),freq:rand(.2,.6),spawnY:cssH};};
  const mkS=()=>{const rgb=pick(SPEC);return{type:0,x:rand(0,cssW),y:rand(0,cssH),
    vx:rand(-10,10),vy:rand(-10,10),size:rand(8,22),baseAlpha:rand(.30,.65),
    alpha:0,phase:rand(0,7),freq:rand(.15,.5),sprite:glow(rgb)};};

  const countTarget=()=>Math.max(24,Math.min(+(canvas.dataset.max||110),Math.round(cssW*cssH/12000)));

  // ── twinkle layer (#stars, sky sandwich) ─────────────────────────────────
  const starsCv=document.getElementById('stars');
  const starsCtx=starsCv?starsCv.getContext('2d'):null;
  let bgStars=[],lastStarDraw=-1;

  function genStars(){
    if(!starsCtx)return;
    starsCv.width=Math.round(cssW*dpr);starsCv.height=Math.round(cssH*dpr);
    starsCtx.setTransform(dpr,0,0,dpr,0,0);
    const n=Math.max(120,Math.min(360,Math.round(cssW*cssH/4500)));
    bgStars=[];
    for(let i=0;i<n;i++){
      const r=Math.random();
      bgStars.push({x:(Math.random()*cssW)|0,y:(Math.random()*cssH)|0,
        s:r<.55?1:r<.85?2:3,                       // px squares — pixel-art language
        base:rand(.20,.75),phase:rand(0,6.28),
        spd:Math.random()<.12?0:rand(.3,1.1),      // ~12% steady, rest twinkle
        col:pick(STAR_COLORS)});
    }
    drawStars(0,true);
  }

  function drawStars(t,force){
    if(!starsCtx)return;
    if(!force&&t-lastStarDraw<.05)return;          // ~20fps redraw is plenty
    lastStarDraw=t;
    starsCtx.clearRect(0,0,cssW,cssH);
    for(const s of bgStars){
      const a=(s.spd===0||reduced)?s.base
        :Math.max(.05,Math.min(1,s.base+Math.sin(t*s.spd+s.phase)*.3));
      starsCtx.fillStyle=`rgba(${s.col},${a})`;
      starsCtx.fillRect(s.x,s.y,s.s,s.s);
    }
  }

  function resize(){
    dpr=Math.min(window.devicePixelRatio||1,1.5);
    cssW=canvas.clientWidth;cssH=canvas.clientHeight;
    canvas.width=Math.round(cssW*dpr);canvas.height=Math.round(cssH*dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);
    const t=countTarget();
    while(particles.length<t)particles.push(Math.random()<.35?mkE():mkS());
    if(particles.length>t)particles.length=t;
    for(const p of particles){if(p.x>cssW)p.x=rand(0,cssW);if(p.y>cssH)p.y=rand(0,cssH);}
    genStars();
    if(!rafId)draw(0);
  }

  function step(p,t,dt){
    if(p.type){
      p.y-=p.vy*dt;p.x+=Math.sin(t*p.freq+p.phase)*11*dt;
      const rise=(p.spawnY-p.y)/p.spawnY;p.alpha=p.baseAlpha*Math.max(0,1-rise);
      if(p.y<-p.size)Object.assign(p,mkE());
    }else{
      p.x+=p.vx*dt;p.y+=p.vy*dt;
      const m=40;
      if(p.x<-m)p.x+=cssW+2*m;if(p.x>cssW+m)p.x-=cssW+2*m;
      if(p.y<-m)p.y+=cssH+2*m;if(p.y>cssH+m)p.y-=cssH+2*m;
      p.alpha=p.baseAlpha*(0.55+0.45*Math.sin(t*p.freq+p.phase));
    }
  }

  function draw(t){
    ctx.clearRect(0,0,cssW,cssH);ctx.globalCompositeOperation='lighter';
    const rb=rampBase();
    for(const p of particles){
      ctx.globalAlpha=Math.max(0,p.alpha);
      if(p.type){ // ember: integer-snapped pixel spark, ramp-cycled colour
        const spr=emberSprites[(rb+p.ramp)%8][p.sizeIdx];
        ctx.drawImage(spr,Math.round(p.x-p.size/2),Math.round(p.y-p.size/2));
      }else{
        ctx.drawImage(p.sprite,p.x-p.size/2,p.y-p.size/2,p.size,p.size);
      }
    }
    ctx.globalAlpha=1;ctx.globalCompositeOperation='source-over';
  }

  function tick(ts){
    if(lastTs===null)lastTs=ts;
    const dt=Math.min((ts-lastTs)/1000,.05),t=ts/1000;lastTs=ts;
    for(const p of particles)step(p,t,dt);
    draw(t);drawStars(t);rafId=requestAnimationFrame(tick);
  }

  const shouldRun=()=>!reduced&&visible&&onscreen;
  function reconcile(){
    if(shouldRun()){if(rafId===null){lastTs=null;rafId=requestAnimationFrame(tick);}}
    else{if(rafId!==null){cancelAnimationFrame(rafId);rafId=null;}
      if(reduced){draw(0);drawStars(0,true);}}     // static frames, stars visible
  }

  mq.addEventListener('change',e=>{reduced=e.matches;reconcile();});
  document.addEventListener('visibilitychange',()=>{visible=!document.hidden;reconcile();});
  new IntersectionObserver(es=>{onscreen=es[0].isIntersecting;reconcile();},{threshold:0}).observe(canvas);
  window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(resize,150);},{passive:true});

  resize();reconcile();
}
