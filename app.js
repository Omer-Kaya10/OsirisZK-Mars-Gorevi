import {Renderer,I,T,S,RX,RY,RZ,TR,matmul,V,clamp,lerp,len,sub,terrainHeight,gradientTerrain,transformPoint,forwardOf,rightOf,angleDiff,moveToward} from './engine.js';
import {TARGETS,buildTerrain,buildEnvironment,buildRover,buildDrone,buildExtra,ROVER_WHEELS,ROVER_WHEEL_RADIUS,terrainMeshHeight} from './scene.js';
import {INGENUITY_REFERANS,gerekliHavadaKalmaItisi,itisAnalizi} from './ingenuity.js';
import {GamepadInput,PAD} from './gamepad.js';

const $=id=>document.getElementById(id);
const canvas=$('glcanvas');
const keys=new Set();
const pressed=k=>keys.has(k);
const axis=(pos,neg)=>(pos.some(pressed)?1:0)-(neg.some(pressed)?1:0);
const MARS_G=INGENUITY_REFERANS.marsYercekimiMps2;
// Oyun ayarları (gerçek Perseverance ~0.04 m/s ile gider; burada oynanabilirlik için hızlandırıldı).
const ROVER_MAX=5.2, ROVER_TURBO=8.2, ROVER_REVERSE=2.6;
const DRONE_SPEED=3.1, DRONE_YAW_RATE=1.75;
const TRACK_A=[.21,.095,.065], TRACK_B=[.30,.14,.095];
const effects={dust:[],tracks:[],trackLast:null,trackDirty:false,trackClock:0,trackTread:0};
const gamepad=new GamepadInput({
 onConnect:g=>{notify('🎮 Kumanda bağlandı • A: kalkış/iniş · Y: araç değiştir · ⧉: kılavuz');addLog(`Kumanda bağlandı: ${String(g?.id||'').slice(0,42)}`,'success');},
 onDisconnect:()=>{notify('Kumanda bağlantısı kesildi');addLog('Kumanda bağlantısı kesildi','warn');}});
const ZERO_ROVER={thr:0,steer:0,boost:false,brake:false};
// Klavye ve kumanda tek bir analog girişte birleşir (-1…1). Çubuk/tetik yarım basılırsa araç da yarım tepki verir.
function readInput(){const g=gamepad.connected?gamepad:null,c=v=>clamp(v,-1,1);
 return {
  drone:{fwd:c(axis(['w','arrowup'],['s','arrowdown'])-(g?g.ly:0)),strafe:c(axis(['d'],['a'])+(g?g.lx:0)),
   rise:c(axis([' '],['shift'])+(g?g.rt-g.lt:0)),turn:c(axis(['arrowleft','q'],['arrowright','e'])-(g?g.rx:0))},
  rover:{thr:c(axis(['w','arrowup'],['s','arrowdown'])+(g?g.rt-g.lt-g.ly:0)),steer:c(axis(['d','arrowright'],['a','arrowleft'])+(g?g.lx:0)),
   boost:pressed('shift')||!!g?.held(PAD.RB),brake:pressed(' ')||!!g?.held(PAD.B)}};}

function makeRover(){const r={x:0,z:16,y:0,yaw:0,battery:92,speed:0,accel:0,steer:0,yawRate:0,pitch:0,roll:0,
  dynPitch:0,dynRoll:0,dynPitchV:0,dynRollV:0,mode:'drive',dustClock:0,wheels:ROVER_WHEELS.map(()=>({steer:0,spin:0,susp:0}))};
 updateRoverPose(r,0,true);return r;}
function makeDrone(){return {x:0,z:16,y:0,yaw:0,yawRate:0,vx:0,vy:0,vz:0,tiltP:0,tiltR:0,battery:100,docked:true,rotorAngle:0,rotorSpeed:0,thrust:1.0,dustClock:0,riseLatch:false};}
const state={
  time:0,running:true,selected:'drone',cameraMode:'cinematic',auto:false,phase:'ready',targetIndex:0,phaseTime:0,
  rover:makeRover(),
  drone:makeDrone(),
  collected:[false,false,false],sent:0,dataPackets:0,evening:false,events:[],
  camera:{yaw:.57,pitch:.37,distance:17,focus:[0,2.4,15],eye:[11,9,30],dragging:false,yawOffset:.45,heading:0},
};
let renderer, assets;
let toastTimer=0;
let uiTimer=0, frameCount=0,fpsTime=0,fps=0,lastFrame=0;
const roverY=()=>state.rover.y;
// Rover frames: chassis follows the terrain (wheels hang from it); body adds the suspension sway on top.
function roverChassis(r){return matmul(matmul(T(r.x,r.y,r.z),RY(r.yaw)),matmul(RX(r.pitch),RZ(r.roll)));}
function roverBody(r){return matmul(roverChassis(r),matmul(RX(r.dynPitch),RZ(r.dynRoll)));}
const dronePad=()=>transformPoint(roverBody(state.rover),[0,1.52,.30]);
const headingDeg=yaw=>((-yaw*180/Math.PI)%360+360)%360;
const altitude=()=>state.drone.docked?0:Math.max(0,state.drone.y-terrainHeight(state.drone.x,state.drone.z)-.47);
const groundDistance=(a,b)=>Math.hypot(a.x-b.x,a.z-b.z);
const vecDist=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y,a.z-b.z);
const fmt=v=>v.toFixed(1);
const stamp=()=>{const s=Math.floor(state.time);return `${String(Math.floor(s/3600)).padStart(2,'0')}:${String(Math.floor(s/60)%60).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`;};
function addLog(message,type='info'){
 const item={stamp:stamp(),message,type};state.events.unshift(item);state.events=state.events.slice(0,28);
 const panel=$('eventLog');panel.innerHTML=state.events.slice(0,12).map(e=>`<div class="log-line ${e.type}"><b>${e.stamp}</b>${escapeHTML(e.message)}</div>`).join('');
}
function escapeHTML(value){return String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));}
function notify(message){const t=$('toast');t.textContent=message;t.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.classList.remove('show'),3000);}
function selectVehicle(which){state.selected=which;$('selectDrone').classList.toggle('selected',which==='drone');$('selectRover').classList.toggle('selected',which==='rover');$('selectDrone').querySelector('.status-pill')?.remove();for(const b of ['selectDrone','selectRover']){const old=$(b).querySelector('.status-pill');if(old)old.remove();}const badge=document.createElement('span');badge.className='status-pill';badge.textContent='ACTIVE';$(which==='drone'?'selectDrone':'selectRover').append(badge);addLog(which==='drone'?'UD-07 kontrol devralındı':'RV-01 kontrol devralındı');}
function setCamera(which){state.cameraMode=which;document.querySelectorAll('.camera-btn').forEach(b=>b.classList.toggle('active',b.dataset.camera===which));$('viewModeLabel').textContent=({cinematic:'SİNEMATİK',drone:'DRONE TAKİP',rover:'GEZGİN TAKİP',top:'YÜZEY HARİTASI'})[which];
 state.camera.zoomStep=0;
 if(which==='top'){state.camera.pitch=1.46;state.camera.distance=48;}
 else if(which==='drone'){state.camera.pitch=.32;state.camera.distance=9.5;state.camera.yawOffset=.5;state.camera.heading=state.drone.yaw;}
 else if(which==='rover'){state.camera.pitch=.30;state.camera.distance=14;state.camera.yawOffset=.42;state.camera.heading=state.rover.yaw;}
 else {state.camera.pitch=.37;state.camera.distance=17;state.camera.yaw=.57;}
 state.camera.baseDistance=state.camera.distance;}
function takeoff(){const d=state.drone;if(!d.docked){notify('UD-07 zaten uçuşta. İniş için F tuşunu kullan.');return false;}if(d.battery<8){notify('Yetersiz enerji. Önce batarya değişimi yap.');return false;}
 d.docked=false;const p=dronePad();d.x=p[0];d.y=p[1]+.04;d.z=p[2];d.vx=0;d.vy=0;d.vz=0;state.selected='drone';selectVehicle('drone');addLog('UD-07 rotorlar çalıştı • Kalkış başladı','success');gamepad.rumble(.3,.65,380);notify('Kalkış izni verildi • SPACE ile yüksel');return true;}
function dock(){const d=state.drone,r=state.rover;if(d.docked){notify('Helikopter zaten platformda kenetli.');return true;}
 const p=dronePad();const hd=Math.hypot(d.x-p[0],d.z-p[2]);const vd=Math.abs(d.y-p[1]);
 if(hd>1.6||vd>1.45){notify('Kenetlenmek için gezginin iniş platformuna yaklaş ve alçal.');return false;}
 d.docked=true;d.vx=d.vy=d.vz=0;d.x=p[0];d.y=p[1];d.z=p[2];addLog('UD-07 iniş platformuna kenetlendi','success');gamepad.rumble(.75,.3,200);notify('Güvenli kenetlenme tamamlandı');return true;}
function swapBattery(){if(!state.drone.docked){notify('Batarya değişimi için helikopter platformda olmalı.');return;}
 if(state.rover.battery<10){notify('Gezginde yeterli enerji yok.');return;}
 const d=state.drone,needed=100-d.battery,available=state.rover.battery*.8,transferred=Math.min(needed,available);d.battery+=transferred;state.rover.battery-=transferred*1.2;gamepad.rumble(.2,.5,160);addLog(`Batarya değişimi +${Math.round(transferred)}% • Gezgin rezervi kullanıldı`,'success');notify(`Batarya yenilendi: %${Math.round(d.battery)}`);}
function transmit(){if(state.dataPackets<=0){notify('Gönderilecek bilimsel veri bulunmuyor.');return;}
 if(!state.drone.docked){notify('Veri aktarmak için helikopterin gezgine kenetlenmesi gerekiyor.');return;}
 const amount=state.dataPackets;state.dataPackets=0;state.sent+=amount;addLog(`${amount} bilimsel veri paketi Dünya'ya aktarıldı (simülasyon)`,'success');notify(`${amount} veri paketi görev merkezine gönderildi`);}
function collect(index,method='drone'){if(state.collected[index])return;state.collected[index]=true;state.dataPackets++;const target=TARGETS[index];addLog(`${target.label} / ${target.name}: ${method==='drone'?'hava':'yüzey'} taraması tamam`,'success');notify(`✦ ${target.name} numunesi analiz edildi`);gamepad.rumble(.25,.85,260);}
function scan(){const d=state.drone,r=state.rover;const isDrone=state.selected==='drone';const near=TARGETS.map((t,i)=>({i,dist:Math.hypot(t.x-(isDrone?d.x:r.x),t.z-(isDrone?d.z:r.z))})).sort((a,b)=>a.dist-b.dist)[0];
 if(!near||near.dist>(isDrone?5:4.8)){notify('Tarama için işaretli kaya hedefine yaklaş.');return;}
 if(isDrone&&(d.docked||altitude()<1.2)){notify('Helikopter tarama için en az 1,2 m yüksekte uçmalı.');return;}
 if(state.collected[near.i]){notify('Bu hedef daha önce tarandı.');return;}
 collect(near.i,isDrone?'drone':'rover');}
function startMission(){if(state.auto){state.auto=false;state.phase='manual';addLog('Otonom görev durduruldu • Manuel kontrol aktif','warn');notify('Otonom uçuş iptal edildi');return;}
 if(state.collected.every(Boolean)){notify('Tüm numuneler toplandı. Görevi sıfırlayabilirsin.');return;}
 if(state.drone.battery<20){notify('Otonom uçuş için drone bataryası en az %20 olmalı.');return;}
 if(state.drone.docked&&!takeoff())return;
 state.auto=true;state.phase='takeoff';state.phaseTime=0;state.targetIndex=state.collected.findIndex(v=>!v);selectVehicle('drone');setCamera('drone');addLog('JZR-03 otonom keşif rotası başlatıldı','success');notify('Otonom keşif: 3 kaya hedefi • Ardından üsse dönüş');}
function setAutoPhase(phase){state.phase=phase;state.phaseTime=0;}
function autoVelocity(dt){const d=state.drone,r=state.rover,phase=state.phase;let dest=null,desiredSpeed=3.45;
 if(d.battery<9&&!['return','land'].includes(phase)){setAutoPhase('return');addLog('Kritik enerji • Acil üsse dönüş','warn');}
 if(state.phase==='takeoff'){
  dest={x:d.x,y:roverY()+4.9,z:d.z};desiredSpeed=2.1;
  if(Math.abs(d.y-dest.y)<.25)setAutoPhase('travel');
 }else if(state.phase==='travel'){
  const site=TARGETS[state.targetIndex];if(!site){setAutoPhase('return');return [0,0,0];}
  dest={x:site.x,y:terrainHeight(site.x,site.z)+5.3,z:site.z};
  if(groundDistance(d,dest)<2.15&&Math.abs(d.y-dest.y)<1.4){setAutoPhase('scan');addLog(`${site.label}: multispektral gözlem başladı`);}
 }else if(state.phase==='scan'){
  state.phaseTime+=dt;
  const site=TARGETS[state.targetIndex];if(site&&state.phaseTime>=2.6){collect(state.targetIndex);const next=state.collected.findIndex(v=>!v);if(next>=0){state.targetIndex=next;setAutoPhase('travel');}else{setAutoPhase('return');addLog('Tüm hedefler tarandı • Üsse dönüş başladı','success');}}
  return [0,0,0];
 }else if(state.phase==='return'){
  const pad=dronePad();dest={x:pad[0],y:roverY()+4.2,z:pad[2]};
  if(groundDistance(d,dest)<.85&&Math.abs(d.y-dest.y)<.7)setAutoPhase('land');
 }else if(state.phase==='land'){
  const p=dronePad();dest={x:p[0],y:p[1]+.06,z:p[2]};desiredSpeed=.95;
  if(vecDist(d,dest)<.20){d.x=p[0];d.y=p[1];d.z=p[2];d.docked=true;d.vx=d.vy=d.vz=0;state.auto=false;state.phase='completed';addLog('UD-07 güvenli iniş • JZR-03 görev döngüsü tamamlandı','success');gamepad.rumble(.75,.3,200);notify('✓ Otonom keşif tamamlandı • Veri aktarımı hazır');return [0,0,0];}
 }
 if(!dest)return [0,0,0];
 const dx=dest.x-d.x,dy=dest.y-d.y,dz=dest.z-d.z,horizontal=Math.hypot(dx,dz);
 let speed=Math.min(desiredSpeed,horizontal*1.6);if(state.phase==='takeoff')speed=0;
 const vy=clamp(dy*1.25,-1.25,1.65);return [horizontal>.01?dx/horizontal*speed:0,vy,horizontal>.01?dz/horizontal*speed:0];
}
/* ───────────── GEZGİN (RV-01) — sürüş dinamiği ─────────────
   • İvme / fren / sürtünme ataleti, eğimde Mars yerçekimi etkisi (yokuşta yavaşlar, inişte hızlanır)
   • Perseverance tipi 4 köşe tekerden direksiyon (ön ve arka tekerler zıt yöne döner)
   • Dururken direksiyon: köşe tekerleri ~38° açılır ve araç olduğu yerde döner
   • Gövde araziye göre eğilir, her teker ayrı süspansiyonla zemine basar, gövde ivmede/virajda yaylanır */
function updateRoverPose(r,dt,snap=false){
 const c=Math.cos(r.yaw),s=Math.sin(r.yaw);
 const h=ROVER_WHEELS.map(([lx,,lz])=>terrainMeshHeight(r.x+lx*c+lz*s,r.z-lx*s+lz*c));
 const front=(h[0]+h[1])/2,rear=(h[4]+h[5])/2,left=(h[0]+h[2]+h[4])/3,right=(h[1]+h[3]+h[5])/3;
 const tp=Math.atan2(front-rear,2.23),tr=Math.atan2(right-left,2.90),ty=h.reduce((a,b)=>a+b,0)/6+.73+ROVER_WHEEL_RADIUS;
 const k=snap?1:clamp(dt*7,0,1);r.pitch=lerp(r.pitch,tp,k);r.roll=lerp(r.roll,tr,k);r.y=lerp(r.y,ty,snap?1:clamp(dt*10,0,1));
 const chassis=roverChassis(r);
 ROVER_WHEELS.forEach(([lx,ly,lz],i)=>{const p=transformPoint(chassis,[lx,ly,lz]);const want=clamp(h[i]+ROVER_WHEEL_RADIUS-p[1],-.24,.24);
  const w=r.wheels[i];w.susp=snap?want:lerp(w.susp,want,clamp(dt*14,0,1));});
}
function updateRover(dt,ctl){const r=state.rover;
 const {thr,steer:steerIn,boost,brake}=ctl;
 const [fx,fz]=forwardOf(r.yaw);
 const slope=(terrainHeight(r.x+fx*1.1,r.z+fz*1.1)-terrainHeight(r.x-fx*1.1,r.z-fz*1.1))/2.2;
 const pivot=!brake&&Math.abs(thr)<.06&&Math.abs(steerIn)>.12&&Math.abs(r.speed)<.35;
 r.mode=pivot?'pivot':'drive';
 // Boylamsal hız
 let v=r.speed;
 if(brake)v=moveToward(v,0,7.5*dt);
 else if(Math.abs(thr)<.06||pivot)v=moveToward(v,0,1.9*dt);
 else if(v*thr<-.05)v+=thr*6.2*dt;                       // ters yöne basıldı: önce fren
 else{const target=thr>0?thr*(boost?ROVER_TURBO:ROVER_MAX):thr*ROVER_REVERSE;
  v+=(clamp((target-v)*1.5,-4,boost?3.3:2.6)-MARS_G*slope*1.2)*dt;}
 v=clamp(v,-ROVER_REVERSE-1,ROVER_TURBO+1.5);
 r.accel=lerp(r.accel,(v-r.speed)/dt,clamp(dt*6,0,1));r.speed=v;
 // Direksiyon: hız arttıkça dönüş yarıçapı büyür (devrilmeye karşı)
 r.steer=moveToward(r.steer,pivot?0:steerIn,dt*2.6);
 const speedAbs=Math.abs(r.speed),kappa=r.steer/(1.8+.55*speedAbs);
 let maxErr=0;
 r.wheels.forEach((w,i)=>{const [lx,,lz]=ROVER_WHEELS[i];
  const target=pivot?Math.atan(lz/(-lx)):Math.abs(kappa)<1e-4?0:Math.atan(lz/(1/kappa-lx));
  w.steer=moveToward(w.steer,target,dt*3.4);maxErr=Math.max(maxErr,Math.abs(target-w.steer));});
 const ready=clamp(1-maxErr/.3,0,1);                       // yerinde dönüş tekerler açılınca başlar
 const wantYaw=pivot?-steerIn*.8*ready:-r.speed*kappa;
 r.yawRate=lerp(r.yawRate,wantYaw,clamp(dt*7,0,1));r.yaw+=r.yawRate*dt;
 const [nfx,nfz]=forwardOf(r.yaw);
 r.x=clamp(r.x+nfx*r.speed*dt,-93,93);r.z=clamp(r.z+nfz*r.speed*dt,-93,93);
 // Her teker kendi yuvarlanma hızıyla döner (virajda iç/dış farkı, yerinde dönüşte sağ/sol zıt)
 r.wheels.forEach((w,i)=>{const [lx,,lz]=ROVER_WHEELS[i];const c=Math.cos(w.steer),s=Math.sin(w.steer);
  w.spin-=(r.speed*c+r.yawRate*(lx*c-lz*s))*dt/ROVER_WHEEL_RADIUS;});
 // Gövde yaylanması (ivmede burun kalkar, frende dalar, virajda dışa yatar)
 const tP=clamp(r.accel*.013,-.055,.055),tR=clamp(-r.speed*r.yawRate*.02,-.05,.05);
 r.dynPitchV+=((tP-r.dynPitch)*70-r.dynPitchV*10)*dt;r.dynPitch+=r.dynPitchV*dt;
 r.dynRollV+=((tR-r.dynRoll)*70-r.dynRollV*10)*dt;r.dynRoll+=r.dynRollV*dt;
 updateRoverPose(r,dt);
 if(speedAbs>.02||Math.abs(r.yawRate)>.02)r.battery=Math.max(0,r.battery-dt*(.004+.0045*speedAbs+Math.abs(r.yawRate)*.004+(boost&&thr>.06?.006:0)));
 // Toz ve teker izi
 const scuff=speedAbs>.7?speedAbs*2.4:Math.abs(r.yawRate)>.3?2.5:0;
 r.dustClock+=dt*scuff;
 if(r.dustClock>=1){const chassis=roverChassis(r);
  while(r.dustClock>=1){r.dustClock-=1;
   for(const i of speedAbs>.7?[4,5]:[0,1,4,5]){if(Math.random()<.45)continue;const [lx,,lz]=ROVER_WHEELS[i];const p=transformPoint(chassis,[lx,-.73-ROVER_WHEEL_RADIUS*.6,lz]);
    spawnDust(p[0],p[2],-nfx*r.speed*.25+(Math.random()-.5)*.6,.25+Math.random()*.35,-nfz*r.speed*.25+(Math.random()-.5)*.6,.22+Math.random()*.16,1.4+Math.random()*1.0);}}}
 layTrack(r);
}
function spawnDust(x,z,vx,vy,vz,size,life){if(effects.dust.length>120)effects.dust.shift();effects.dust.push({x,y:terrainMeshHeight(x,z)+.1,z,vx,vy,vz,size,age:0,life});}
function trackLanes(r){const c=Math.cos(r.yaw),s=Math.sin(r.yaw),pt=(lx,lz)=>[r.x+lx*c+lz*s,r.z-lx*s+lz*c];return [pt(-1.45,.95),pt(1.45,.95)];}
function layTrack(r){const [L,R]=trackLanes(r),last=effects.trackLast;
 if(!last){effects.trackLast={L,R};return;}
 const moved=Math.max(Math.hypot(L[0]-last.L[0],L[1]-last.L[1]),Math.hypot(R[0]-last.R[0],R[1]-last.R[1]));
 if(moved<.32)return;
 if(moved<3){const col=(effects.trackTread++&1)?TRACK_A:TRACK_B,data=new Float32Array(108);let o=0;
  const put=(x,z)=>{data.set([x,terrainMeshHeight(x,z)+.035,z,0,1,0,col[0],col[1],col[2]],o);o+=9;};
  for(const [a,b] of [[last.L,L],[last.R,R]]){const dx=b[0]-a[0],dz=b[1]-a[1],l=Math.hypot(dx,dz)||1,nx=-dz/l*.16,nz=dx/l*.16;
   put(a[0]+nx,a[1]+nz);put(b[0]+nx,b[1]+nz);put(b[0]-nx,b[1]-nz);put(a[0]+nx,a[1]+nz);put(b[0]-nx,b[1]-nz);put(a[0]-nx,a[1]-nz);}
  effects.tracks.push(data);if(effects.tracks.length>900)effects.tracks.shift();effects.trackDirty=true;}
 effects.trackLast={L,R};}
function rebuildTracks(){const all=new Float32Array(effects.tracks.length*108);effects.tracks.forEach((seg,i)=>all.set(seg,i*108));renderer.update(assets.extra.tracks,all);effects.trackDirty=false;effects.trackClock=0;}
function clearEffects(){effects.dust.length=0;effects.tracks.length=0;effects.trackLast=null;effects.trackDirty=true;}
function updateEffects(dt){
 for(const p of effects.dust){p.age+=dt;p.x+=p.vx*dt;p.y+=p.vy*dt;p.z+=p.vz*dt;const drag=Math.max(0,1-dt*1.6);p.vx*=drag;p.vz*=drag;p.vy=p.vy*drag-.05*dt;}
 effects.dust=effects.dust.filter(p=>p.age<p.life);
 effects.trackClock+=dt;if(effects.trackDirty&&effects.trackClock>.15)rebuildTracks();
}
/* ───────────── HELİKOPTER (UD-07) ─────────────
   ← / → veya Q / E: kendi ekseni etrafında dönüş (yaw). W/S ve ↑/↓ burnun baktığı yöne uçar. */
function updateDrone(dt,ctl){const d=state.drone,r=state.rover;
 const solar=state.evening?.012:.065;                       // güneş paneli şarjı, %/s
 d.rotorSpeed=moveToward(d.rotorSpeed,d.docked?0:1,dt*(d.docked?.45:1.6));
 if(d.docked){const p=dronePad();d.x=p[0];d.y=p[1];d.z=p[2];d.yaw=r.yaw;d.yawRate=0;d.vx=d.vy=d.vz=0;d.tiltP=d.tiltR=0;d.thrust=0;d.battery=clamp(d.battery+dt*solar,0,100);
  if(state.selected==='drone'&&!state.auto&&ctl.rise>.5&&!d.riseLatch)takeoff();}      // SPACE / RT platformdayken kalkış yaptırır
 else{
  const manual=state.selected==='drone'&&!state.auto;
  const {fwd,strafe,rise,turn}=manual?ctl:{fwd:0,strafe:0,rise:0,turn:0};
  let requested=[0,0,0],wantYawRate=turn*DRONE_YAW_RATE;
  if(d.battery<=0){state.auto=false;requested=[0,-.6,0];wantYawRate=0;}
  else if(state.auto){requested=autoVelocity(dt);const hs=Math.hypot(requested[0],requested[2]);
   if(hs>.45)wantYawRate=clamp(angleDiff(Math.atan2(-requested[0],-requested[2]),d.yaw)*2.4,-1.5,1.5);else wantYawRate=0;}
  else if(manual){const [fx,fz]=forwardOf(d.yaw),[rx,rz]=rightOf(d.yaw);
   requested=[(fx*fwd+rx*strafe)*DRONE_SPEED,rise*1.9,(fz*fwd+rz*strafe)*DRONE_SPEED];}
  if(!d.docked){                                              // autoVelocity may have just landed it
   d.yawRate=lerp(d.yawRate,wantYawRate,clamp(dt*5,0,1));d.yaw+=d.yawRate*dt;
   // Velocity response with smoothing. This is deliberately not a certified rotorcraft model.
   const alpha=Math.min(1,dt*3.4),ovx=d.vx,ovz=d.vz;
   d.vx=lerp(d.vx,requested[0],alpha);d.vy=lerp(d.vy,requested[1],Math.min(1,dt*2.9));d.vz=lerp(d.vz,requested[2],alpha);
   d.x=clamp(d.x+d.vx*dt,-96,96);d.z=clamp(d.z+d.vz*dt,-96,96);d.y+=d.vy*dt;
   const minY=terrainHeight(d.x,d.z)+.49,maxY=terrainHeight(d.x,d.z)+19;
   if(d.y<minY){d.y=minY;d.vy=Math.max(0,d.vy);}if(d.y>maxY){d.y=maxY;d.vy=Math.min(0,d.vy);}
   // Rotor diski hızlanılan/gidilen yöne eğilir: ileri giderken burun aşağı, sağa kayarken sağa yatış.
   const [fx,fz]=forwardOf(d.yaw),[rx,rz]=rightOf(d.yaw),ax=(d.vx-ovx)/dt,az=(d.vz-ovz)/dt;
   const vF=d.vx*fx+d.vz*fz,vR=d.vx*rx+d.vz*rz,aF=ax*fx+az*fz,aR=ax*rx+az*rz,k=clamp(dt*6,0,1);
   d.tiltP=lerp(d.tiltP,clamp(-(vF*.035+aF*.055),-.24,.24),k);d.tiltR=lerp(d.tiltR,clamp(-(vR*.035+aR*.055),-.24,.24),k);
   const drain=.28+Math.hypot(d.vx,d.vz)*.014+Math.abs(d.vy)*.032+Math.abs(d.yawRate)*.02;
   d.battery=clamp(d.battery-dt*(drain-solar*.8),0,100);
   // Shown thrust ratio is illustrative, not a full aerodynamic computation.
   const estimated=Math.max(0,1+d.vy*.075+Math.max(0,requested[1]-d.vy)*.12);
   d.thrust=itisAnalizi(gerekliHavadaKalmaItisi(INGENUITY_REFERANS.kutleKg)*estimated).itisOrani;
   if(d.battery<=0)d.thrust=.85;
   // Alçak uçuşta rotor akımı yerden toz kaldırır
   const alt=altitude();if(alt<3.2&&d.rotorSpeed>.5){d.dustClock+=dt*(3.2-alt)*6;
    while(d.dustClock>=1){d.dustClock-=1;const a=Math.random()*Math.PI*2,rad=.35+Math.random()*.6,ox=Math.cos(a),oz=Math.sin(a);
     spawnDust(d.x+ox*rad,d.z+oz*rad,ox*(1.1+Math.random()*.8),.08+Math.random()*.2,oz*(1.1+Math.random()*.8),.13+Math.random()*.1,1.0+Math.random()*.6);}}
  }
 }
 d.riseLatch=ctl.rise>.5;
 d.rotorAngle+=dt*d.rotorSpeed*INGENUITY_REFERANS.rotorDevirRpm*Math.PI*2/60*.12; // slower visible animation for display
}
function updatePhysics(dt){if(!state.running||!(dt>0))return;state.time+=dt;
 const r=state.rover;
 const inp=readInput();
 updateRover(dt,state.selected==='rover'?inp.rover:ZERO_ROVER);
 r.battery=clamp(r.battery+dt*(state.evening?.00003:.003),0,100);
 updateDrone(dt,inp.drone);
 updateEffects(dt);
}
const isFollowCam=()=>state.cameraMode==='drone'||state.cameraMode==='rover';
function cameraFrame(dt){const c=state.camera,d=state.drone,r=state.rover;
 let target,followYaw=null;
 if(state.cameraMode==='drone'){target=[d.x,d.y+.45,d.z];followYaw=d.yaw;}
 else if(state.cameraMode==='rover'){const [fx,fz]=forwardOf(r.yaw);target=[r.x+fx*.9,r.y+.9,r.z+fz*.9];followYaw=r.yaw;}
 else if(state.cameraMode==='top')target=[(d.x+r.x)*.5,1,(d.z+r.z)*.5];
 else{const p=state.selected==='drone'?d:{x:r.x,y:roverY(),z:r.z};target=[p.x,p.y,p.z-1.25];}
 const blend=clamp(dt*2.8,0,1);c.focus=c.focus.map((v,i)=>lerp(v,target[i],blend));
 // Takip kameraları aracın arkasına gecikmeli döner: önce aracın döndüğünü görürsün, sonra kamera arkasına geçer.
 if(followYaw!==null)c.heading+=angleDiff(followYaw,c.heading)*clamp(dt*1.7,0,1);
 const p=c.pitch,y=followYaw!==null?c.heading+c.yawOffset:c.yaw,distance=c.distance;
 const dest=[c.focus[0]+Math.sin(y)*Math.cos(p)*distance,c.focus[1]+Math.sin(p)*distance,c.focus[2]+Math.cos(y)*Math.cos(p)*distance];
 c.eye=c.eye.map((v,i)=>lerp(v,dest[i],Math.min(1,dt*3.1)));
 // Prevent the camera from passing below a dune.
 c.eye[1]=Math.max(c.eye[1],terrainHeight(c.eye[0],c.eye[2])+1.1);
 return {eye:c.eye,target:c.focus};}
function drawScene(dt){const {eye,target}=cameraFrame(dt);renderer.evening=state.evening?.78:0;renderer.begin(eye,target,state.time);
 renderer.draw(assets.terrain,I());
 renderer.draw(assets.extra.tracks,I(),.62);
 renderer.draw(assets.environment.scenery,I());renderer.draw(assets.environment.route,I(),.56,.14);
 const r=state.rover,d=state.drone;
 const chassis=roverChassis(r),body=matmul(chassis,matmul(RX(r.dynPitch),RZ(r.dynRoll)));
 const shadowRover=matmul(T(r.x,terrainMeshHeight(r.x,r.z)+.07,r.z),matmul(matmul(RY(r.yaw),matmul(RX(r.pitch),RZ(r.roll))),S(1.8,1,2.0)));renderer.draw(assets.drone.shadow,shadowRover,.33);
 renderer.draw(assets.rover.body,body);
 ROVER_WHEELS.forEach(([x,y,z],i)=>{const w=r.wheels[i];renderer.draw(assets.rover.wheel,matmul(chassis,matmul(T(x,y+w.susp,z),matmul(RY(w.steer),RX(w.spin)))));});
 // Landing pad marker and scan beacon.
 renderer.draw(assets.extra.pad,matmul(body,T(0,1.065,.30)),1,.3);
 let droneRoot;
 if(d.docked)droneRoot=matmul(body,T(0,1.52,.30));
 else{const alt=altitude();renderer.draw(assets.drone.shadow,matmul(T(d.x,terrainMeshHeight(d.x,d.z)+.08,d.z),matmul(RY(d.yaw),S(1.25,1,.95))),.33*clamp(1-alt/24,.35,1));
  const bob=alt>.25?Math.sin(state.time*2.3)*.018+Math.sin(state.time*5.1)*.006:0;
  droneRoot=matmul(TR(d.x,d.y+bob,d.z,d.yaw),matmul(RX(d.tiltP),RZ(d.tiltR)));}
 renderer.draw(assets.drone.body,droneRoot);
 renderer.draw(assets.drone.top,matmul(droneRoot,matmul(T(0,.61,0),RY(d.rotorAngle))),1,.13);
 renderer.draw(assets.drone.bottom,matmul(droneRoot,matmul(T(0,.33,0),RY(-d.rotorAngle*1.05))),1,.06);
 for(const p of effects.dust){const t=p.age/p.life,size=p.size*(1+t*2.4),fade=(1-t)*(t<.12?t/.12:1);
  renderer.draw(assets.extra.dust,matmul(T(p.x,p.y,p.z),S(size,size,size)),.42*fade,.22);}
 renderer.gl.bindVertexArray(null);
 updateWorldLabels();}
function updateWorldLabels(){TARGETS.forEach((site,i)=>{
 const id=['rockA','rockB','rockC'][i],label=$(id),pt=renderer.project([site.x,terrainHeight(site.x,site.z)+3,site.z]);
 const focus=state.camera.eye,dist=Math.hypot(focus[0]-site.x,focus[2]-site.z);
 if(!pt||!pt.visible||dist>78){label.style.display='none';return;}
 label.style.display='flex';label.style.left=`${pt.x}px`;label.style.top=`${pt.y}px`;
 if(state.collected[i]){label.style.borderColor='#7dd5bd';label.querySelector('.target-icon').textContent='✓';label.querySelector('small').textContent='TARAMA TAMAMLANDI';}
 });}
function drawMap(){const canvas=$('minimap'),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;
 ctx.clearRect(0,0,w,h);ctx.fillStyle='#192934';ctx.fillRect(0,0,w,h);
 const scale=2.30,originX=w/2,originZ=h*.72;
 const xy=(x,z)=>[originX+x*scale,originZ+(z-10)*scale];
 for(let z=-60;z<=55;z+=4)for(let x=-120;x<=120;x+=4){let h1=terrainHeight(x,z);if(h1>0.35){const [px,py]=xy(x,z);ctx.fillStyle=`rgba(210,148,100,${Math.min(.22,.035+h1*.027)})`;ctx.fillRect(px,py,10,10);}}
 ctx.strokeStyle='#334858';ctx.lineWidth=.5;for(let x=-120;x<=120;x+=10){const [px]=xy(x,0);ctx.beginPath();ctx.moveTo(px,0);ctx.lineTo(px,h);ctx.stroke();}for(let z=-60;z<=55;z+=10){const [,py]=xy(0,z);ctx.beginPath();ctx.moveTo(0,py);ctx.lineTo(w,py);ctx.stroke();}
 const d=state.drone,r=state.rover;const route=[[r.x,r.z],...TARGETS.filter((_,i)=>!state.collected[i]).map(t=>[t.x,t.z])];
 ctx.strokeStyle='rgba(215,159,103,.7)';ctx.setLineDash([4,6]);ctx.beginPath();route.forEach(([x,z],i)=>{const [px,py]=xy(x,z);i?ctx.lineTo(px,py):ctx.moveTo(px,py);});ctx.stroke();ctx.setLineDash([]);
 TARGETS.forEach((t,i)=>{const [x,y]=xy(t.x,t.z);ctx.strokeStyle=state.collected[i]?'#75cabb':'#e4a76d';ctx.lineWidth=1.6;ctx.beginPath();ctx.arc(x,y,5,0,Math.PI*2);ctx.stroke();ctx.fillStyle=state.collected[i]?'#75cabb':'#d9a06e';ctx.font='bold 10px Consolas';ctx.fillText(`${i+1}`,x+9,y-3);});
 const marker=(p,col,size)=>{const [x,y]=xy(p.x,p.z),[fx,fz]=forwardOf(p.yaw);ctx.strokeStyle=col;ctx.beginPath();ctx.arc(x,y,size+5,0,Math.PI*2);ctx.stroke();ctx.fillStyle=col;ctx.beginPath();ctx.arc(x,y,size,0,Math.PI*2);ctx.fill();
  ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x+fx*(size+5),y+fz*(size+5));ctx.lineTo(x+fx*(size+13),y+fz*(size+13));ctx.stroke();ctx.lineWidth=1.6;};
 marker(r,'#77d0bf',4.5);marker(d,'#ffc284',3.2);
 ctx.fillStyle='#94adb8';ctx.font='10px Consolas';ctx.fillText('LOCAL MAP / 220 × 78 m',10,h-9);
}
function drawScience(){const can=$('scienceChart'),ctx=can.getContext('2d'),w=can.width,h=can.height;
 ctx.clearRect(0,0,w,h);ctx.strokeStyle='#29424b';ctx.lineWidth=1;for(let n=1;n<4;n++){ctx.beginPath();ctx.moveTo(0,n*h/4);ctx.lineTo(w,n*h/4);ctx.stroke();}
 ctx.strokeStyle='#79c8ae';ctx.lineWidth=2;ctx.beginPath();for(let x=0;x<w;x+=3){const k=x/w;const y=h*.58-(Math.sin(k*16+state.time*.13)*.14+Math.sin(k*46+state.time*.08)*.045)*h -state.collected.filter(Boolean).length*h*.055;if(x===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);}ctx.stroke();
 ctx.fillStyle='#a2bdc5';ctx.font='10px Consolas';ctx.fillText('SENSOR RETURN  //  NOMINAL',9,14);}
function updateUI(){const d=state.drone,r=state.rover,a=altitude(),speed=state.selected==='rover'?Math.abs(r.speed):Math.hypot(d.vx,d.vz),ratio=d.thrust;
 const el=(id,v)=>{$(id).textContent=v;};
 el('altitude',a.toFixed(2));el('hudAlt',a.toFixed(1));el('speed',speed.toFixed(2));el('thrust',ratio.toFixed(2));const signal=clamp(Math.round(100-Math.hypot(r.x-d.x,r.z-d.z)*.33),30,100);el('signal',signal);
 $('padBadge').hidden=!gamepad.connected;const active=state.selected==='drone'?d:r;el('heading',String(Math.round(headingDeg(active.yaw))%360).padStart(3,'0'));
 for(const [id,v] of [['altBar',a/19*100],['speedBar',speed/(state.selected==='rover'?ROVER_TURBO:DRONE_SPEED+.4)*100],['thrustBar',ratio/1.8*100],['signalBar',signal]])$(id).style.width=`${clamp(v,0,100)}%`;
 el('droneBatteryText',`${Math.round(d.battery)}%`);el('roverBatteryText',`${Math.round(r.battery)}%`);$('droneBatteryBar').style.width=`${d.battery}%`;$('roverBatteryBar').style.width=`${r.battery}%`;
 el('samples',String(state.collected.filter(Boolean).length).padStart(2,'0'));$('samples').insertAdjacentHTML('beforeend',' <em>/ 03</em>');el('sent',String(state.sent).padStart(2,'0'));$('sent').insertAdjacentHTML('beforeend',' <em>PKT</em>');
 el('missionClock',stamp());el('flightTime','T+'+stamp());const coord=v=>(v<-.05?'-':'')+Math.abs(v).toFixed(1).padStart(5,'0');el('coordsLabel',`X ${coord(active.x)} / Z ${coord(active.z)}`);
 const phases={ready:'Görev öncesi kontrol',takeoff:'Otonom kalkış',travel:'Hedefe yaklaşma',scan:'Bilimsel tarama',return:'Üsse dönüş',land:'Hassas iniş',manual:'Manuel uçuş',completed:'Görev tamamlandı'};
 el('operationText',d.docked?(state.phase==='completed'?'Görev tamamlandı':'Platformda kenetli'):(phases[state.phase]||'Manuel uçuş'));
 el('flightBadge',d.docked?'KENETLİ':state.auto?'OTONOM':'UÇUŞTA');el('operationSub',state.auto?`ROTA JZR-03 · ${state.phase==='scan'?'TARAMA AKTİF':state.phase==='travel'?TARGETS[state.targetIndex]?.name:'NAVİGASYON'}`:d.docked?'Sistemler nominal • Kalkışa hazır':'Manuel kontrol · Uçuş parametreleri izleniyor');
 $('missionBtn').innerHTML=state.auto?'<span class="action-glyph">■</span><span>GÖREVİ DURDUR <small>MANUEL KONTROL</small></span>':'<span class="action-glyph">▶</span><span>OTONOM KEŞİF <small>3 HEDEFLİ UÇUŞ</small></span>';
 const progress=state.collected.filter(Boolean).length;const stage=state.phase==='completed'?4:state.auto?(state.phase==='land'||state.phase==='return'?3:Math.min(2,Math.max(0,state.targetIndex))):Math.min(3,progress);
 $('missionSteps').innerHTML=['KALKIŞ','KAYA 01','KAYA 02','KAYA 03','DÖNÜŞ'].map((label,i)=>`<div class="step ${i===0&&!d.docked||i>0&&i<=3&&state.collected[i-1]||i===4&&state.phase==='completed'?'done':state.auto&&(i===0&&state.phase==='takeoff'||i===state.targetIndex+1&&['travel','scan'].includes(state.phase)||i===4&&['return','land'].includes(state.phase))?'active':''}"><b>${i===4?'↵':i===0?'↑':i}</b><span>${label}</span></div>`).join('');
 el('missionDescription',state.auto?`Otonom mod etkin. ${state.phase==='scan'?`Hedef taranıyor: ${TARGETS[state.targetIndex]?.name}`:'Navigasyon ve irtifa kontrolü sürüyor.'}`:state.phase==='completed'?'Keşif tamamlandı. VERİYİ GÖNDER düğmesiyle bilimsel paketleri iletebilirsin.':`${progress}/3 hedef tarandı. Manuel keşif veya otonom görev başlatabilirsin.`);
 drawMap();drawScience();}
function reset(){state.time=0;state.running=true;$('pauseBtn').textContent='Ⅱ DURAKLAT';state.auto=false;state.phase='ready';state.phaseTime=0;state.targetIndex=0;state.collected=[false,false,false];state.sent=0;state.dataPackets=0;state.rover=makeRover();state.drone=makeDrone();Object.assign(state.drone,(([x,y,z])=>({x,y,z}))(dronePad()));clearEffects();keys.clear();state.events=[];setCamera('cinematic');selectVehicle('drone');addLog('Sistem sıfırlandı • JZR-03 göreve hazır','success');notify('Yeni görev simülasyonu başlatıldı');}
// Tarayıcıda çalışan yerel görev raporu. Gerçek bir NASA veri aktarımı değildir.
function exportMissionReport(){
 const d=state.drone,r=state.rover;
 const report={
  project:'OSIRISZK Mars Pathfinder 3D',version:'2.3',
  mode:'Educational 3D simulation (simplified physics)',
  missionTimeSeconds:Number(state.time.toFixed(2)),
  flight:{position:{x:d.x,y:d.y,z:d.z},headingDeg:Number(headingDeg(d.yaw).toFixed(1)),batteryPercent:d.battery,
    altitudeAGLMeters:altitude(),docked:d.docked},
  rover:{position:{x:r.x,z:r.z},headingDeg:Number(headingDeg(r.yaw).toFixed(1)),batteryPercent:r.battery},
  gravityMetersPerSecondSquared:INGENUITY_REFERANS.marsYercekimiMps2,
  targetObservations:TARGETS.map((t,i)=>({name:t.name,type:t.tag,collected:state.collected[i]})),
  storedPackets:state.dataPackets,transmittedPackets:state.sent,
  log:[...state.events].reverse()
 };
 const blob=new Blob([JSON.stringify(report,null,2)],{type:'application/json'});
 const link=document.createElement('a');link.href=URL.createObjectURL(blob);
 link.download='OSIRISZK_Gorev_Raporu.json';document.body.appendChild(link);link.click();link.remove();
 setTimeout(()=>URL.revokeObjectURL(link.href),1000);
 notify('Görev raporu bilgisayarına kaydedildi');addLog('Yerel görev raporu oluşturuldu','success');
}
function toggleSun(){state.evening=!state.evening;
 $('sunBtn').textContent=state.evening?'☀ GÜNDÜZ':'◑ GÜN BATIMI';
 addLog(state.evening?'Akşam ışık profiline geçildi':'Gündüz ışık profiline geçildi');
}
function togglePause(){state.running=!state.running;
 $('pauseBtn').textContent=state.running?'Ⅱ DURAKLAT':'▶ DEVAM ET';
 notify(state.running?'Simülasyon devam ediyor':'Simülasyon duraklatıldı');
}
function bindControls(){
 $('selectDrone').addEventListener('click',()=>selectVehicle('drone'));
 $('selectRover').addEventListener('click',()=>selectVehicle('rover'));
 $('missionBtn').addEventListener('click',startMission);
 $('takeoffBtn').addEventListener('click',takeoff);
 $('scanBtn').addEventListener('click',scan);
 $('dockBtn').addEventListener('click',dock);
 $('chargeBtn').addEventListener('click',swapBattery);
 $('transmitBtn').addEventListener('click',transmit);
 $('resetBtn').addEventListener('click',reset);
 $('sunBtn').addEventListener('click',toggleSun);
 $('pauseBtn').addEventListener('click',togglePause);
 $('reportBtn').addEventListener('click',exportMissionReport);
 document.querySelectorAll('[data-camera]').forEach(b=>b.addEventListener('click',()=>setCamera(b.dataset.camera)));
 const overlay=$('helpOverlay');$('helpBtn').addEventListener('click',()=>overlay.hidden=false);
 $('closeHelp').addEventListener('click',()=>overlay.hidden=true);$('helpDone').addEventListener('click',()=>overlay.hidden=true);
 overlay.addEventListener('click',e=>{if(e.target===overlay)overlay.hidden=true;});
 document.addEventListener('keydown',e=>{
  if(['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName))return;
  const key=e.key.toLowerCase();if([' ','arrowup','arrowdown','arrowleft','arrowright','tab'].includes(key))e.preventDefault();
  if(overlay.hidden===false){if(key==='escape'||key==='h')overlay.hidden=true;return;}
  if(!e.repeat){
   if(key==='tab'){selectVehicle(state.selected==='drone'?'rover':'drone');return;}
   if(key==='h'){overlay.hidden=false;return;}
   if('1234'.includes(key)&&key.length===1){setCamera(['cinematic','drone','rover','top'][Number(key)-1]);return;}
   if(key==='f'){dock();return;}if(key==='b'){swapBattery();return;}if(key==='t'){transmit();return;}
   if(key==='g'){scan();return;}if(key==='r'&&state.selected==='rover'){scan();return;}
   if(key==='m'){startMission();return;}
   if(key==='p'){togglePause();return;}
  }
  keys.add(key);
  if(state.auto&&state.selected==='drone'&&['w','a','s','d',' ','shift','q','e','arrowup','arrowdown','arrowleft','arrowright'].includes(key)){state.auto=false;state.phase='manual';addLog('Manuel müdahale • Otonom uçuş kesildi','warn');notify('Manuel kontrol devralındı');}
 });
 document.addEventListener('keyup',e=>keys.delete(e.key.toLowerCase()));
 window.addEventListener('blur',()=>keys.clear());
 canvas.addEventListener('pointerdown',e=>{if(e.button!==0)return;state.camera.dragging=true;state.camera.last=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);});
 canvas.addEventListener('pointermove',e=>{if(!state.camera.dragging)return;const [x,y]=state.camera.last;if(isFollowCam())state.camera.yawOffset-=(e.clientX-x)*.006;else state.camera.yaw-=(e.clientX-x)*.006;state.camera.pitch=clamp(state.camera.pitch+(e.clientY-y)*.005,.10,1.53);state.camera.last=[e.clientX,e.clientY];});
 canvas.addEventListener('pointerup',()=>state.camera.dragging=false);canvas.addEventListener('pointercancel',()=>state.camera.dragging=false);
 canvas.addEventListener('wheel',e=>{e.preventDefault();state.camera.distance=clamp(state.camera.distance*Math.exp(e.deltaY*.00115),3.6,88);},{passive:false});
}
const CAMERA_MODES=['cinematic','drone','rover','top'];
function handleGamepad(dt){if(!gamepad.poll())return;const g=gamepad,c=state.camera,overlay=$('helpOverlay');
 if(!overlay.hidden){if(g.pressed(PAD.A)||g.pressed(PAD.B)||g.pressed(PAD.VIEW))overlay.hidden=true;return;}
 if(g.pressed(PAD.VIEW)){overlay.hidden=false;return;}
 if(g.pressed(PAD.MENU))togglePause();
 if(g.pressed(PAD.A)){if(state.drone.docked)takeoff();else dock();}
 if(g.pressed(PAD.X))scan();
 if(g.pressed(PAD.Y))selectVehicle(state.selected==='drone'?'rover':'drone');
 if(g.pressed(PAD.LB))swapBattery();
 if(g.pressed(PAD.UP))startMission();
 if(g.pressed(PAD.DOWN))transmit();
 if(g.pressed(PAD.LEFT)||g.pressed(PAD.RIGHT)){const i=CAMERA_MODES.indexOf(state.cameraMode);setCamera(CAMERA_MODES[(i+(g.pressed(PAD.RIGHT)?1:CAMERA_MODES.length-1))%CAMERA_MODES.length]);}
 if(g.pressed(PAD.RS)){c.zoomStep=((c.zoomStep||0)+1)%3;c.distance=clamp((c.baseDistance||c.distance)*[1,.55,1.75][c.zoomStep],3.6,88);}
 // Sağ çubuk: gezginde kamerayı çevirir; helikopterde yatay ekseni dönüş için kullanılır, dikey ekseni her iki araçta kamera eğimi.
 if(state.selected==='rover'&&g.rx){if(isFollowCam())c.yawOffset-=g.rx*dt*2.2;else c.yaw-=g.rx*dt*2.2;}
 if(g.ry)c.pitch=clamp(c.pitch+g.ry*dt*1.1,.10,1.53);
 if(state.auto&&state.selected==='drone'&&(Math.hypot(g.lx,g.ly)>.35||Math.abs(g.rx)>.35||g.rt>.3||g.lt>.3)){state.auto=false;state.phase='manual';addLog('Manuel müdahale • Otonom uçuş kesildi','warn');notify('Manuel kontrol devralındı');}
}
function frame(timestamp){if(!lastFrame)lastFrame=timestamp;let dt=Math.min((timestamp-lastFrame)/1000,.05);lastFrame=timestamp;
 try{handleGamepad(dt);updatePhysics(dt);drawScene(dt);uiTimer+=dt;frameCount++;fpsTime+=dt;if(fpsTime>=.7){fps=Math.round(frameCount/fpsTime);$('fps').textContent=fps;fpsTime=0;frameCount=0;}if(uiTimer>=.15){uiTimer=0;updateUI();}}catch(err){console.error('OSIRISZK frame:',err);notify('Görselleştirme hatası: '+err.message);return;}
 requestAnimationFrame(frame);}
function init(){try{
 canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();$('webglError').hidden=false;$('webglError').querySelector('p').textContent='3B ekran kartı bağlantısı kesildi. Sayfayı yeniden yükleyin.';});
 canvas.addEventListener('webglcontextrestored',()=>location.reload());
 renderer=new Renderer(canvas);
 assets={terrain:buildTerrain(renderer),environment:buildEnvironment(renderer),rover:buildRover(renderer),drone:buildDrone(renderer),extra:buildExtra(renderer)};
 const pad=dronePad();Object.assign(state.drone,{x:pad[0],y:pad[1],z:pad[2]});
 bindControls();addLog('Yüzey haritası yüklendi • Jezero hedefleri hazır');addLog('UD-07 / RV-01 kontrol bilgisayarı aktif','success');addLog('NASA Ingenuity kütle/rotor referansı yüklendi');
 setCamera('cinematic');updateUI();$('loading').hidden=true;
 window.__OSIRISZK_TEST__={state,renderer,assets,effects,gamepad,takeoff,dock,scan,startMission,reset,selectVehicle,setCamera,updatePhysics,keys};
 requestAnimationFrame(frame);
 }catch(err){console.error('OSIRISZK startup:',err);$('loading').hidden=true;$('webglError').hidden=false;$('webglError').querySelector('p').textContent=err.message+' — Chrome veya Edge ile tekrar deneyin.';}}
init();
