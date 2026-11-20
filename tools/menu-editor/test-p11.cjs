// P0.11 menu preview sliders (r15 OEM slider rows): safe-area edges and zoom steps.
// npm install --no-save --no-package-lock jsdom@24
// node tools/menu-editor/test-p11.cjs
const fs=require("node:fs");
const path=require("node:path");
const assert=require("node:assert/strict");
const {TextEncoder,TextDecoder}=require("node:util");
const {JSDOM,VirtualConsole}=require("jsdom");
const html=fs.readFileSync(path.join(__dirname,"mibr-menu-editor-nav-views-mockup.html"),"utf8");
const errors=[];
const vc=new VirtualConsole();vc.on("jsdomError",e=>errors.push(String(e)));
const dom=new JSDOM(html,{url:"https://localhost.local/index.html",runScripts:"dangerously",virtualConsole:vc,
  beforeParse(w){w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;
    w.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}});w.scrollTo=()=>{};w.confirm=()=>true;}});
const w=dom.window,d=w.document;
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const rows=()=>Array.from(d.querySelectorAll("#pv .pvl > .pr"));
const row=label=>{const r=rows().find(x=>x.querySelector(".lbl").textContent===label);assert.ok(r,"row "+label);return r};
const click=label=>row(label).dispatchEvent(new w.MouseEvent("click",{bubbles:true}));
const sub=()=>d.querySelectorAll("#pv .prs");
const num=()=>d.querySelector("#pv .pr.sl.o .num").textContent;
const btn=i=>d.querySelectorAll("#pv .prs .slb")[i];
const press=(i,n)=>{for(let k=0;k<n;k++)btn(i).dispatchEvent(new w.MouseEvent("click",{bubbles:true}))};
const key=(k,n,shift)=>{for(let i=0;i<n;i++)d.querySelector("#pv .prs .slt").dispatchEvent(new w.KeyboardEvent("keydown",{key:k,shiftKey:!!shift,bubbles:true}))};
const val=label=>{const v=row(label).querySelector(".val");return v&&v.textContent};
async function main(){
  await delay(40);
  assert.deepEqual(errors,[],"Startup errors");
  click("Ansichten");click("Safe Area Voll");
  // collapsed: four edge rows with a mini slider, nothing open, hint below reset
  const edges=["Linke Kante","Obere Kante","Rechte Kante","Untere Kante"];
  for(const e of edges){assert.ok(row(e).classList.contains("sl"),e+" is a slider row");assert.ok(row(e).querySelector(".mini"),e+" mini preview")}
  assert.equal(sub().length,0,"no row open");
  assert.equal(val("Zurücksetzen"),"Standard");
  assert.match(rows().at(-1).textContent,/Wirkt nach CarPlay-Neuverbindung/);
  // open: value on the right, -/track/+ row below, only one open at a time
  click("Linke Kante");
  assert.equal(sub().length,1);assert.equal(num(),"10");
  assert.ok(row("Linke Kante").nextElementSibling.classList.contains("prs"),"slider row directly below");
  press(1,2);assert.equal(num(),"12","+ moves 1 px");
  assert.equal(val("Zurücksetzen"),"Geändert");
  press(0,20);assert.equal(num(),"0","stops at 0");
  key("ArrowRight",200,true);assert.equal(num(),"900","left edge keeps 100 px to the right edge");
  click("Untere Kante");assert.equal(sub().length,1,"only one row open");assert.equal(num(),"270");
  press(1,200);assert.equal(num(),"376","bottom edge stops at 376");
  press(0,400);assert.equal(num(),"190","bottom edge keeps 60 px to the top edge");
  click("Untere Kante");assert.equal(sub().length,0,"tap closes the row");
  click("Zurücksetzen");assert.equal(val("Zurücksetzen"),"Standard","reset restores the view default");
  click("Linke Kante");assert.equal(num(),"10");
  // zoom: fixed steps
  d.querySelector("#pv .pvb").click();d.querySelector("#pv .pvb").click();
  click("Erweitert");click("Skalierung");
  const z="Zoomfaktor Virtual Cockpit";
  assert.ok(row(z).classList.contains("sl"),"zoom is a slider row");
  click(z);assert.equal(num(),"Automatisch");
  assert.equal(d.querySelectorAll("#pv .prs .tick").length,6,"six fixed steps");
  press(1,3);assert.equal(num(),"100 %");press(1,9);assert.equal(num(),"150 %","last step");press(0,9);assert.equal(num(),"Automatisch");
  assert.ok(Array.from(d.querySelectorAll(".pvnote")).some(n=>/Fahrzeugseite folgt/.test(n.textContent)),"zoom note");
  // SEAT: same rows, note that the brand look is not documented
  const b=d.getElementById("brand");b.value="seat";b.dispatchEvent(new w.Event("change",{bubbles:true}));await delay(20);
  assert.ok(row(z).classList.contains("sl"),"slider rows for SEAT");
  assert.ok(Array.from(d.querySelectorAll(".pvnote")).some(n=>/SEAT-Firmwares/.test(n.textContent)),"SEAT slider note");
  // SEAT head unit: platform test-profile defaults (seat-mu14xx.conf) for safe areas and wheel zoom
  const um=d.getElementById("unitModel");um.value="MU1409";um.dispatchEvent(new w.Event("change",{bubbles:true}));await delay(20);
  assert.equal(w.MIBR_system.defaults().keys.zoomWheelAuto,true,"SEAT: zoom.wheel_auto=1");
  d.querySelector("#pv .pvb").click();d.querySelector("#pv .pvb").click();
  click("Ansichten");click("Safe Area Voll");click("Zurücksetzen");click("Linke Kante");
  assert.equal(num(),"264","SEAT voll default left edge");click("Obere Kante");assert.equal(num(),"56");
  um.value="MU1440";um.dispatchEvent(new w.Event("change",{bubbles:true}));await delay(20);
  assert.equal(w.MIBR_system.defaults().keys.zoomWheelAuto,false,"Skoda: zoom.wheel_auto=0");
  click("Zurücksetzen");click("Linke Kante");assert.equal(num(),"10","Skoda voll default again");
  // Safe Area tab follows the r15 car steps and names what w/h store
  d.querySelector('#tabs [data-t=safe]').click();await delay(20);
  assert.equal(d.getElementById("sa-x").step,"10","slider snaps to 10 px");
  assert.deepEqual(Array.from(d.querySelectorAll(".sa-menu .sa-row")[0].querySelectorAll(".sa-steps button")).map(b=>b.textContent).slice(0,6),["-50","-10","-1","+1","+10","+50"]);
  const keys=Array.from(d.querySelectorAll(".sa-menu .sa-key")).map(e=>e.textContent);
  assert.match(keys[2],/\.w: rechte Kante; gespeichert wird die Breite w/);assert.match(keys[3],/\.h: untere Kante; gespeichert wird die Höhe h/);
  assert.deepEqual(errors,[],"No runtime errors");
  console.log("P0.11 menu preview slider tests PASS");
}
main().catch(e=>{console.error(e);process.exit(1)});
