// P0.5 project/SD/Center regression tests.
// npm install --no-save --no-package-lock jsdom@24 jszip@3
// node tools/menu-editor/test-p05.cjs
const fs=require("node:fs");
const path=require("node:path");
const assert=require("node:assert/strict");
const {TextEncoder,TextDecoder}=require("node:util");
const {JSDOM,VirtualConsole}=require("jsdom");
const JSZip=require("jszip");
const html=fs.readFileSync(path.join(__dirname,"mibr-menu-editor-nav-views-mockup.html"),"utf8");
const errors=[],downloads=[];
const virtualConsole=new VirtualConsole();
virtualConsole.on("jsdomError",e=>errors.push(String(e)));
const dom=new JSDOM(html,{url:"https://localhost.local/index.html",runScripts:"dangerously",virtualConsole,
  beforeParse(w){
    w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;
    w.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}});
    w.scrollTo=()=>{};w.confirm=()=>true;
    let uid=0;
    w.URL.createObjectURL=blob=>{const url="blob:test-"+(++uid);downloads.push({url,blob});return url};
    w.URL.revokeObjectURL=()=>{};
    const original=w.HTMLAnchorElement.prototype.click;
    w.HTMLAnchorElement.prototype.click=function(){if(this.download)return;return original.call(this)};
  }
});
const w=dom.window,d=w.document,$=s=>d.querySelector(s),$$=s=>Array.from(d.querySelectorAll(s));
const click=s=>{assert.ok($(s),"Missing "+s);$(s).click()};
const set=(s,val,event="change")=>{const e=$(s);assert.ok(e,"Missing "+s);if(e.type==="checkbox")e.checked=!!val;else e.value=val;e.dispatchEvent(new w.Event(event,{bubbles:true}));};
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function clone(x){return JSON.parse(JSON.stringify(x))}
async function main(){
  await delay(40);
  assert.deepEqual(errors,[],"Startup errors");
  const sourceJS=fs.readFileSync(path.join(__dirname,"mibr-project-controller.js"),"utf8").trim();
  const sourceSVG=fs.readFileSync(path.join(__dirname,"mibr-center-preview.svg"),"utf8").trim();
  assert.equal($("#mibr-project-controller").textContent.trim(),sourceJS,"Standalone HTML project controller matches its source");
  assert.ok(html.includes(sourceSVG),"Standalone HTML Center SVG matches its source");
  assert.ok(w.MIBR_project,"Unified project API");
  assert.equal($$("#tabs button").length,4,"Four top tabs");
  assert.equal(w.MIBR_project.capture().schema,"mibr-project/1");
  assert.equal(w.MIBR_project.capture().menu.v,2);
  assert.equal(w.MIBR_project.capture().viewProfiles.schema,"mibr.nav-view-profiles/2");
  assert.ok($("header #projectLoad")&&$("header #projectSave")&&$("header #sdExport"),"Global project commands");

  click('#tabs [data-t=nav]');
  assert.ok($("#navv-center-svg")&&!$("#navv-center-preview").hidden,"Center mockup");
  assert.ok($("#center-right-turn"),"Right dial arrow");
  assert.ok($("#center-top-lanes"),"Upper lanes");
  assert.ok($("#center-dial-lanes"),"Right dial lanes");
  assert.ok($("#center-bottom-distance")&&$("#center-bottom-eta"),"Bottom guidance");
  assert.ok($("#center-map-route"),"Layered route geometry");
  const scaleLabels=$$("#center-left-dial .c-gauge-labels text, #center-right-dial .c-gauge-labels text");
  assert.ok(scaleLabels.length>=17,"Stable individual gauge numbers; found "+scaleLabels.length+"; left "+$("#center-left-dial").querySelectorAll("text").length+" right "+$("#center-right-dial").querySelectorAll("text").length);
  assert.ok(scaleLabels.every(n=>!n.hasAttribute("transform")),"Gauge numerals must be upright, not tangentially distorted");
  assert.ok($("#center-speed")&&$("#center-left-info"),"Dedicated static instrument layers");
  assert.ok($("#center-top-status")&&$("#center-footer"),"Independent upper and lower status layers");
  click("#navv-preview-zoom");
  assert.ok($("#navv-center-preview").classList.contains("preview-expanded"),"Large preview opens");
  click("#navv-preview-close");
  assert.ok(!$("#navv-center-preview").classList.contains("preview-expanded"),"Large preview closes");
  set('[data-navv-section="native"][data-navv-key="topSymbol"]',"lanes");
  assert.notEqual($("#center-top-lanes").style.display,"none","Top lanes enable");
  set('[data-navv-section="native"][data-navv-key="topSymbol"]',"off");
  assert.equal($("#center-top-lanes").style.display,"none","Top lanes hide");
  set('[data-navv-section="native"][data-navv-key="topText"]',"distance");
  assert.notEqual($("#center-top-text").style.display,"none","Upper text enables");
  set('[data-navv-section="native"][data-navv-key="tube"]',"off");
  assert.equal($("#center-right-turn").style.display,"none","Right arrow hides");
  set('[data-navv-section="native"][data-navv-key="tube"]',"on");
  set('[data-navv-section="native"][data-navv-key="dialLanes"]',false);
  assert.equal($("#center-dial-lanes").style.display,"none","Right lane strip hides");
  set("#navv-bgmode","plain");
  assert.equal($("#center-grid").style.display,"none","Grid hides");
  assert.equal($("#center-map-route").style.display,"none","Neutral background also hides route");
  set("#navv-bgmode","grid");
  assert.notEqual($("#center-grid").style.display,"none","Grid shows");
  assert.notEqual($("#center-map-route").style.display,"none","Map route returns");

  click('#tabs [data-t=safe]');
  assert.ok($(".sa-views")&&$(".sa-menu"),"Dedicated Safe Area controls");
  $$(".sa-views button")[2].click(); // Center calibration geometry
  set("#sa-x","400","input");
  assert.equal(w.MIBR_project.capture().viewProfiles.views.center.safeArea.x,400,"Safe area in project");

  const before=clone(w.MIBR_project.capture());
  assert.equal(before.viewProfiles.views.center.mockup.background,"grid");
  assert.equal(before.viewProfiles.views.center.native.dialLanes,false);
  assert.equal(before.menu.brand,before.vehicle.brand,"Shared brand");
  await delay(200);
  const autosave=JSON.parse(w.localStorage.getItem("mibr-project/1:autosave"));
  assert.equal(autosave.viewProfiles.views.center.safeArea.x,400,"Unified browser autosave");
  assert.equal(autosave.menu.v,2);

  const native=w.MIBR_project.nativeFile();
  assert.ok(native.startsWith("MIBR_MENU/1\n"),"Native menu header");
  assert.match(native,/\ncrc32=[0-9a-f]{8}\n$/,"CRC32 on native file");
  const zipped=w.MIBR_project.zipFiles([{path:"mibr-menu/mibr-menu.txt",text:native}]);
  const archive=await JSZip.loadAsync(Buffer.from(zipped));
  assert.equal(await archive.file("mibr-menu/mibr-menu.txt").async("string"),native,"ZIP entry exact match");
  assert.equal(Object.keys(archive.files).length,1,"Only runtime-supported output is exported");

  let folderName="",fileName="",written="";
  w.showDirectoryPicker=async ()=>({
    getDirectoryHandle:async (name,opts)=>{folderName=name;assert.ok(opts.create);return{
      getFileHandle:async (fname,opts)=>{fileName=fname;
        if(!opts){const e=new Error("Missing file");e.name="NotFoundError";throw e}
        return {createWritable:async()=>({write:async text=>{written=text},close:async()=>{},abort:async()=>{}})}
      }
    }}
  });
  click("#sdExport");await delay(50);
  assert.equal(folderName,"mibr-menu");assert.equal(fileName,"mibr-menu.txt");
  assert.equal(written,native,"SD write must be native menu only");

  set("#unitModel","MU1447");
  assert.throws(()=>w.MIBR_project.nativeFile(),/MU1440/,"Unverified hardware must be blocked");
  w.MIBR_project.apply(before); // Restore project and hardware together
  assert.equal(w.MIBR_project.capture().vehicle.headUnit,"MU1440");
  assert.equal(w.MIBR_project.capture().viewProfiles.views.center.safeArea.x,400);

  const altered=clone(before);altered.vehicle.brand="vw";
  assert.throws(()=>w.MIBR_project.validate(altered),/Fahrzeug|vehicle/i,"Reject mixed brands");
  click("#projectSave");
  assert.ok(downloads.length,"Project save fallback emits a download");
  const local=JSON.parse(w.localStorage.getItem("mibr-project/1:autosave"));
  assert.equal(local.schema,"mibr-project/1");

  click('#tabs [data-t=menu]');
  assert.ok($("#pv")&&$("#tree"),"Menu editor survived");
  click('#langSeg [data-l=en]');
  await delay(10); // global project toolbar updates after the language handler
  assert.equal($("#projectSave").textContent,"Save project");
  assert.equal($("#appTitle").textContent,"MIB configurator");
  assert.deepEqual(errors,[],"Browser runtime exceptions");
  w.close();console.log("P0.5 project + Center + SD tests PASS");
}
main().catch(err=>{process.stderr.write(err.stack+"\n"+errors.join("\n")+"\n");process.exitCode=1;w.close()});
