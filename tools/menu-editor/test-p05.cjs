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
  for(const profile of ["wide","full"]){
    const source=fs.readFileSync(path.join(__dirname,"mibr-"+profile+"-preview.svg"),"utf8").trim();
    assert.ok(html.includes(source),"Embedded "+profile+" SVG must exactly match its source");
  }
  assert.ok(w.MIBR_project,"Unified project API");
  assert.equal(w.MIBR_views.activeView(),"center","New project opens Center view");
  assert.equal(w.MIBR_safe.activeView(),"center","Calibration initially follows active cockpit view");
  assert.ok($("#navv-guidance-advanced").tagName==="DETAILS","Experimental mapping stays available but collapsed");
  assert.equal($("#navv-guidance-advanced").open,false,"Guidance mapping is secondary");
  assert.equal($$("#tabs button").length,4,"Four top tabs");
  assert.ok($("#navv-view-workspace").children[0].classList.contains("navv-view-selector"),"Full width view selector first");
  assert.ok($("#navv-view-workspace").children[1].classList.contains("navv-view-preview"),"Single preview comes before settings");
  assert.ok($("#navv-view-workspace").children[2].classList.contains("navv-settings-grid"),"Two-column settings below preview");
  assert.equal($$("#navv-center-preview > svg").length,3,"Three SVG views preloaded, only one to be rendered");
  assert.ok($("#navv-profile-advanced").tagName==="DETAILS","Secondary profile controls are collapsible");
  assert.equal($("#navv-profile-advanced").open,false,"Profile management starts collapsed");
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
  assert.equal($("#center-map-route").style.display,"none","Calibration grid has no route; schematic map is separate");
  assert.equal($("#center-bottom-info").getAttribute("font-size"),"14.5","Center lower status font reduced");
  assert.equal($("#center-side-metrics text").getAttribute("y"),"129","Center side tick aligned with marker");
  assert.ok($("#center-right-turn g").getAttribute("transform").includes("scale(.9)"),"Center arrow inset");
  set('[data-navv-section="carplay"][data-navv-key="surface"]',"app");
  assert.notEqual($("#center-app-placeholder").style.display,"none","App mode has distinct editor visualization");
  assert.equal($("#center-grid").style.display,"none","App mode hides grid");
  assert.equal($("#navv-bgmode").disabled,true,"Background mode disabled outside map");
  set('[data-navv-section="carplay"][data-navv-key="surface"]',"off");
  assert.notEqual($("#center-off-placeholder").style.display,"none","Off mode has distinct editor state");
  assert.equal($("#center-app-placeholder").style.display,"none","App placeholder hidden in off mode");
  set('[data-navv-section="carplay"][data-navv-key="surface"]',"map");
  assert.equal($("#navv-bgmode").disabled,false,"Background mode enabled for map");
  for(const view of ["center","wide","full"]){
    click('[data-navv-view='+view+']');
    const overlay=$("#"+view+"-carplay-overlay");
    set('[data-navv-section="carplay"][data-navv-key="maneuver"]',"left");
    const left=overlay.getAttribute("transform");
    set('[data-navv-section="carplay"][data-navv-key="maneuver"]',"right");
    const right=overlay.getAttribute("transform");
    set('[data-navv-section="carplay"][data-navv-key="maneuver"]',"top");
    const top=overlay.getAttribute("transform");
    assert.notEqual(left,right,view+" maneuver left and right differ");
    assert.notEqual(top,left,view+" maneuver top differs");
    assert.notEqual(overlay.style.display,"none",view+" maneuver preview visible");
    set('[data-navv-section="carplay"][data-navv-key="maneuver"]',"off");
    assert.equal(overlay.style.display,"none",view+" maneuver preview hidden");
  }
  click('[data-navv-view=center]');


  // Wide: angled side modules and right-hand native guidance, not enlarged Center circles.
  click('[data-navv-view=wide]');
  assert.equal(w.MIBR_safe.activeView(),"wide","Wide selection also selects Wide calibration");
  assert.equal($("#navv-center-svg").style.display,"none","Center SVG hidden on Wide in Safari");
  assert.equal($("#navv-full-svg").style.display,"none","Full SVG hidden on Wide in Safari");
  assert.equal($("#navv-wide-svg").style.display,"block","Wide SVG visible");
  assert.ok($("#wide-side-panels")&&$("#wide-right-media")&&$("#wide-left-info"),"Wide trapezoid modules and independent content");
  assert.equal($("#wide-bottom-info").getAttribute("font-size"),"14.5","Wide lower status font reduced");
  assert.equal($("#wide-side-metrics text").getAttribute("y"),"133","Wide side tick aligned with marker");
  set('[data-navv-section="carplay"][data-navv-key="surface"]',"app");
  assert.notEqual($("#wide-app-placeholder").style.display,"none","Wide app editor visualization");
  set('[data-navv-section="carplay"][data-navv-key="surface"]',"off");
  assert.notEqual($("#wide-off-placeholder").style.display,"none","Wide off editor visualization");
  set('[data-navv-section="carplay"][data-navv-key="surface"]',"map");
  assert.ok($("#wide-right-turn")&&$("#wide-dial-lanes")&&$("#wide-dial-distance"),"Wide right native navigation");
  assert.ok($("#wide-map-surface")&&$("#wide-top-status")&&$("#wide-footer"),"Wide map + status");
  assert.equal($("#navv-mode").value,"custom","New Wide profile defaults to individual");
  assert.equal($("#wide-top-text").style.display,"none","Fresh Wide profile starts without top text");
  set("#navv-mode","inherit");
  assert.notEqual($("#wide-top-text").style.display,"none","Global inheritance shows legacy top text");
  set("#navv-mode","custom");
  assert.notEqual($("#wide-top-text").style.display,"none","Customizing inherited Wide retains shown global top text");
  set('[data-navv-section="native"][data-navv-key="topSymbol"]',"lanes");
  assert.notEqual($("#wide-top-lanes").style.display,"none","Wide upper lane guidance appears");
  set('[data-navv-section="native"][data-navv-key="tube"]',"off");
  assert.equal($("#wide-right-turn").style.display,"none","Wide right arrow hides independently");
  set('[data-navv-section="native"][data-navv-key="tube"]',"on");
  assert.notEqual($("#wide-right-turn").style.display,"none","Wide right arrow returns");
  set('[data-navv-section="native"][data-navv-key="dialLanes"]',false);
  assert.equal($("#wide-dial-lanes").style.display,"none","Wide right lane strip hides separately");
  set("#navv-bgmode","map");
  assert.notEqual($("#wide-map-visual").style.display,"none","Wide optional map visual");
  assert.notEqual($("#wide-map-route").style.display,"none","Wide optional route visual");
  set("#navv-bgmode","plain");
  assert.equal($("#wide-grid").style.display,"none","Wide calibration grid off");
  assert.equal($("#wide-map-route").style.display,"none","Wide route off on neutral background");
  click("#navv-preview-zoom");
  assert.ok($("#navv-center-preview").classList.contains("preview-expanded"),"Wide zoom opens");
  click("#navv-preview-close");
  assert.ok(!$("#navv-center-preview").classList.contains("preview-expanded"),"Wide zoom closes");

  // Full: the photo shows one continuous map without a separate right tube.
  click('[data-navv-view=full]');
  assert.equal(w.MIBR_safe.activeView(),"full","Full selection also selects Full calibration");
  assert.equal($("#navv-center-svg").style.display,"none","Center SVG hidden on Full");
  assert.equal($("#navv-wide-svg").style.display,"none","Wide SVG hidden on Full");
  assert.equal($("#navv-full-svg").style.display,"block","Full SVG visible");
  assert.ok($("#full-lower-corners")&&$("#full-map-surface")&&$("#full-speed"),"Full map and shaped lower cutouts");
  assert.ok($("#f-mainclip path").getAttribute("d").includes("V274H841"),"Full clip shares lower corner geometry");
  assert.equal($("#full-bottom-info").getAttribute("font-size"),"14.5","Full lower status font reduced");
  assert.equal($("#full-side-metrics text").getAttribute("y"),"135","Full side tick aligned with marker");
  set('[data-navv-section="carplay"][data-navv-key="surface"]',"app");
  assert.notEqual($("#full-app-placeholder").style.display,"none","Full app editor visualization");
  set('[data-navv-section="carplay"][data-navv-key="surface"]',"off");
  assert.notEqual($("#full-off-placeholder").style.display,"none","Full off editor visualization");
  set('[data-navv-section="carplay"][data-navv-key="surface"]',"map");
  assert.ok($("#full-top-text")&&$("#full-top-lanes")&&$("#full-bottom-distance")&&$("#full-bottom-eta"),"Full navigation zones");
  assert.equal($("#full-right-turn"),null,"Full must not invent a right-hand tube");
  assert.equal($('[data-navv-section="native"][data-navv-key="tube"]').disabled,true,"Full right tube control inapplicable");
  assert.equal($('[data-navv-section="native"][data-navv-key="dialLanes"]').disabled,true,"Full right lane strip inapplicable");
  set("#navv-mode","custom");
  assert.equal($('[data-navv-section="native"][data-navv-key="tube"]').disabled,true,"Full tube stays disabled in individual profile");
  set('[data-navv-section="native"][data-navv-key="topSymbol"]',"lanes");
  assert.notEqual($("#full-top-lanes").style.display,"none","Full top lanes can be shown");
  set('[data-navv-section="native"][data-navv-key="bottomDistance"]',false);
  assert.equal($("#full-bottom-distance").style.display,"none","Full bottom distance is independent");
  set('[data-navv-section="native"][data-navv-key="bottomEta"]',false);
  assert.equal($("#full-bottom-eta").style.display,"none","Full arrival time is independent");
  set("#navv-bgmode","map");
  assert.notEqual($("#full-map-visual").style.display,"none","Full map variant");
  set("#navv-bgmode","grid");
  assert.notEqual($("#full-grid").style.display,"none","Full calibration grid returns");
  assert.equal($("#full-map-route").style.display,"none","Full grid remains calm, no route imposed");
  click("#navv-preview-zoom");
  assert.ok($("#navv-center-preview").classList.contains("preview-expanded"),"Full zoom opens");
  click('[data-navv-view=center]');
  assert.ok(!$("#navv-center-preview").classList.contains("preview-expanded"),"View switch closes full-size preview");
  assert.equal($("#navv-center-svg").style.display,"block","Center still available");
  assert.equal($("#navv-wide-svg").style.display,"none","Wide hidden after switching back");
  const profiles=w.MIBR_project.capture().viewProfiles.views;
  assert.equal(profiles.wide.mockup.background,"plain","Wide preview background is saved independently");
  assert.equal(profiles.full.mockup.background,"grid","Full preview background is saved independently");
  assert.equal(profiles.center.mockup.background,"grid","Center preview settings remain unchanged");
  assert.equal(profiles.wide.native.dialLanes,false,"Wide navigation settings preserved");
  assert.equal(profiles.full.native.bottomDistance,false,"Full navigation settings preserved");


  // Copying a navigation profile must not silently overwrite another view's geometry.
  const safeBefore=clone(w.MIBR_project.capture().viewProfiles.views.wide.safeArea);
  const bgBefore=w.MIBR_project.capture().viewProfiles.views.wide.mockup.background;
  click("#navv-profile-advanced summary");
  set("#navv-copy-target","wide");
  click("#navv-copy");
  const copied=w.MIBR_project.capture().viewProfiles.views.wide;
  assert.deepEqual(clone(copied.safeArea),safeBefore,"Copy must preserve target safe-area geometry");
  assert.equal(copied.mockup.background,bgBefore,"Copy must preserve target preview background");
  assert.equal(copied.mode,"custom","Copy activates individual profile");
  assert.equal($("#navv-wide-svg").style.display,"block","Copy selects target view immediately");
  const originalSafe=clone(copied.safeArea);
  click("#navv-reset-view");
  assert.deepEqual(clone(w.MIBR_project.capture().viewProfiles.views.wide.safeArea),originalSafe,"Reset must preserve calibrated safe-area");
  click('[data-navv-view=center]');

  click('#tabs [data-t=safe]');
  assert.ok($(".sa-views")&&$(".sa-menu"),"Dedicated Safe Area controls");
  assert.equal(w.MIBR_safe.activeView(),"center","Safe Area follows selected cockpit view");
  $$(".sa-views button")[1].click(); // Wide calibration context
  assert.equal(w.MIBR_views.activeView(),"wide","Safe Area selection updates View configurator");
  assert.equal(w.MIBR_safe.activeView(),"wide","Same active Wide in both workspaces");
  assert.equal($$(".sa-views button")[1].getAttribute("aria-pressed"),"true","Wide calibration active");
  $$(".sa-views button")[2].click(); // Center calibration geometry
  assert.equal(w.MIBR_views.activeView(),"center","Returning to Center synchronizes both workspaces");
  set("#sa-x","400","input");
  assert.equal(w.MIBR_project.capture().viewProfiles.views.center.safeArea.x,400,"Safe area in project");
  click('#tabs [data-t=nav]');click('[data-navv-view=full]');click("#navv-edit-safe");
  assert.equal($("#app").dataset.tab,"safe","Shortcut opens Safe Area workspace");
  assert.equal(w.MIBR_safe.activeView(),"full","Shortcut preserves Full calibration view");
  assert.equal($$(".sa-views button")[0].getAttribute("aria-pressed"),"true","Full calibration selected via shortcut");
  click('#tabs [data-t=nav]');click('[data-navv-view=center]');

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
