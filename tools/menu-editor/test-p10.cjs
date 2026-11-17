// P0.10 unit settings tests: per-view keys, options/keys in the project, backward compatibility.
// npm install --no-save --no-package-lock jsdom@24 jszip@3
// node tools/menu-editor/test-p10.cjs
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
const w=dom.window,d=w.document,$=s=>d.querySelector(s);
const clone=x=>JSON.parse(JSON.stringify(x));
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const throwsMsg=(fn,label)=>assert.throws(fn,undefined,label);
async function main(){
  await delay(40);
  assert.deepEqual(errors,[],"Startup errors");
  const sys=w.MIBR_system;
  assert.ok(sys,"system module");
  // ---- defaults follow the unit sources
  const def=clone(sys.defaults());
  assert.deepEqual(def.keys,{viewStep:"4/40",viewResyncLong:"4/40",carplaySwitchLong:"4/44",menu:16,zoomWheelSource:40,zoomWheelAuto:false});
  assert.deepEqual(def.options,{carplayNav:false,language:"AUTO",expertMode:false,sdLog:false,scaling:{mainZoom:"AUTO",clusterZoom:"AUTO",mainPhysical:"BASE",clusterPhysical:"BASE"}});
  // key table: no power key; long-press selects only offer long-capable keys
  const table=clone(sys.keyTable());
  assert.ok(!table.some(k=>k.code==="13/88"),"power key not offered");
  assert.deepEqual(table.map(k=>k.code),["4/40","4/41","4/53","4/46","4/47","4/44","4/50","13/116","13/78"]);
  const opts=id=>Array.from($(id).options).map(o=>o.value);
  assert.deepEqual(opts("#sys-keys-viewStep"),table.map(k=>k.code));
  assert.deepEqual(opts("#sys-keys-viewResyncLong"),["4/40","4/41","4/44"]);
  assert.deepEqual(opts("#sys-keys-carplaySwitchLong"),["4/40","4/41","4/44"]);
  // ---- per-view keys: defaults, project round-trip, conf round-trip
  const views=clone(w.MIBR_views.get());
  for(const id of ["center","wide","full"]){
    assert.equal(views.views[id].carplay.speedLimit,"user");
    assert.equal(views.views[id].carplay.compass,"user");
    assert.equal(views.views[id].carplay.mapNight,"auto");
    assert.equal(views.views[id].guidance.display,"side");
    assert.equal(views.views[id].guidance.line,"dist");
  }
  const edited=clone(views);
  edited.views.wide.mode="custom";
  Object.assign(edited.views.wide.carplay,{speedLimit:"no",compass:"yes",mapNight:"dark"});
  Object.assign(edited.views.wide.guidance,{display:"both",line:"street"});
  w.MIBR_views.set(edited);
  const conf=w.MIBR_views.nativeConf();
  for(const line of ["view.wide.carplay.speedLimit=no","view.wide.carplay.compass=yes","view.wide.carplay.mapNight=dark","view.wide.guidance.display=both","view.wide.guidance.line=street"])
    assert.ok(conf.split("\n").includes(line),"conf has "+line);
  // inherit mode: new keys are not exported
  const inh=clone(edited);inh.views.wide.mode="inherit";w.MIBR_views.set(inh);
  assert.ok(!w.MIBR_views.nativeConf().includes("view.wide.carplay.speedLimit"),"not exported in inherit mode");
  w.MIBR_views.set(edited);
  // conf import through the file input
  const file=new w.File([conf],"p.conf");
  const input=$("#navv-input");
  Object.defineProperty(input,"files",{value:[file],configurable:true});
  input.dispatchEvent(new w.Event("change"));
  await delay(80);
  const back=clone(w.MIBR_views.get());
  assert.deepEqual(back.views.wide.carplay,edited.views.wide.carplay,"carplay round trip via conf");
  assert.deepEqual(back.views.wide.guidance,edited.views.wide.guidance,"guidance round trip via conf");
  // older v3 .conf without per-view guidance keys: views take the imported globals
  {
    const crc=b=>(require("node:zlib").crc32(Buffer.from(b,"utf8"))>>>0).toString(16).padStart(8,"0");
    let lines=conf.split("\n").filter(l=>l&&!l.startsWith("crc32=")&&!/^view\.[a-z]+\.guidance\.(display|line)=/.test(l));
    lines=lines.map(l=>l.startsWith("global.legacyDisplay=")?"global.legacyDisplay=both":l.startsWith("global.legacyLine=")?"global.legacyLine=street":l);
    const body=lines.join("\n")+"\n",oldConf=body+"crc32="+crc(body)+"\n";
    Object.defineProperty(input,"files",{value:[new w.File([oldConf],"old.conf")],configurable:true});
    input.dispatchEvent(new w.Event("change"));
    await delay(80);
    const got=clone(w.MIBR_views.get());
    assert.equal(got.global.legacyDisplay,"both","old conf global display imported");
    for(const id of ["center","wide","full"]){
      assert.equal(got.views[id].guidance.display,"both",id+" display falls back to imported global");
      assert.equal(got.views[id].guidance.line,"street",id+" line falls back to imported global");
    }
    w.MIBR_views.set(edited);
  }
  // older v1/v2 .conf with custom views: newly added per-view keys are optional and take defaults
  for(const v of ["1","2"]){
    const crc=b=>(require("node:zlib").crc32(Buffer.from(b,"utf8"))>>>0).toString(16).padStart(8,"0");
    let lines=conf.split("\n").filter(l=>l&&!l.startsWith("crc32=")&&!/^view\.[a-z]+\.(carplay\.(speedLimit|compass|mapNight)|guidance\.(display|line))=/.test(l));
    lines[0]="MIBR_NAV_VIEW_PROFILES/"+v;
    lines=lines.map(l=>l.startsWith("version=")?"version="+v:l);
    const body=lines.join("\n")+"\n",oldConf=body+"crc32="+crc(body)+"\n";
    Object.defineProperty(input,"files",{value:[new w.File([oldConf],"v"+v+".conf")],configurable:true});
    input.dispatchEvent(new w.Event("change"));
    await delay(80);
    const st=$("#navv-status").textContent;
    assert.ok(st.startsWith("Erfolgreich importiert"),"v"+v+" conf imported: "+st);
    const got=clone(w.MIBR_views.get());
    assert.equal(got.views.wide.mode,"custom");
    assert.equal(got.views.wide.carplay.speedLimit,"user","v"+v+" speedLimit default");
    assert.equal(got.views.wide.carplay.mapNight,"auto","v"+v+" mapNight default");
    assert.equal(got.views.wide.guidance.display,got.global.legacyDisplay,"v"+v+" display from global");
    w.MIBR_views.set(edited);
  }
  // invalid per-view values rejected
  for(const [sec,key,val] of [["carplay","speedLimit","maybe"],["carplay","mapNight","night"],["guidance","display","left"],["guidance","line","x"]]){
    const bad=clone(edited);bad.views.wide[sec][key]=val;
    throwsMsg(()=>w.MIBR_views.validate(bad),"reject "+key);
  }
  // views JSON without the new keys (older v3 file) loads with defaults
  const old=clone(edited);delete old.views.full.carplay.speedLimit;delete old.views.full.carplay.compass;delete old.views.full.carplay.mapNight;delete old.views.full.guidance.display;delete old.views.full.guidance.line;
  old.views.full.mode="custom";
  const loaded=clone(w.MIBR_views.validate(old));
  assert.equal(loaded.views.full.carplay.speedLimit,"user");
  assert.equal(loaded.views.full.guidance.display,loaded.global.legacyDisplay);
  // ---- options/keys in the project
  const p0=clone(w.MIBR_project.capture());
  assert.deepEqual(p0.options,def.options);assert.deepEqual(p0.keys,def.keys);
  const p1=clone(p0);
  p1.options={carplayNav:true,language:"en",expertMode:true,sdLog:true,scaling:{mainZoom:"125",clusterZoom:"85",mainPhysical:"P30",clusterPhysical:"P50"}};
  p1.keys={viewStep:"4/46",viewResyncLong:"4/41",carplaySwitchLong:"4/40",menu:33,zoomWheelSource:44,zoomWheelAuto:true};
  w.MIBR_project.apply(p1);
  const p2=JSON.parse(JSON.stringify(w.MIBR_project.capture()));
  assert.deepEqual(p2.options,p1.options);assert.deepEqual(p2.keys,p1.keys);
  assert.equal($("#sys-keys-menu").value,"33","UI shows loaded menu key");
  assert.equal($("#sys-scaling-mainZoom").value,"125");
  assert.equal($("#sys-options-carplayNav").value,"true");
  // UI change flows into capture
  const sel=$("#sys-keys-viewStep");sel.value="13/78";sel.dispatchEvent(new w.Event("change"));
  assert.equal(w.MIBR_project.capture().keys.viewStep,"13/78");
  const chk=$("#sys-keys-zoomWheelAuto");chk.checked=false;chk.dispatchEvent(new w.Event("change"));
  assert.equal(w.MIBR_project.capture().keys.zoomWheelAuto,false);
  // old project without options/keys: defaults
  const legacy=clone(p0);delete legacy.options;delete legacy.keys;
  w.MIBR_project.apply(legacy);
  const p3=clone(w.MIBR_project.capture());
  assert.deepEqual(p3.options,def.options);assert.deepEqual(p3.keys,def.keys);
  // partial: missing parts default
  const part=clone(p0);part.options={language:"de"};delete part.keys;
  w.MIBR_project.apply(part);
  assert.equal(w.MIBR_project.capture().options.language,"de");
  assert.equal(w.MIBR_project.capture().options.scaling.mainZoom,"AUTO");
  // ---- invalid values rejected, state unchanged
  const before=JSON.stringify(w.MIBR_project.capture());
  const bads=[["keys","viewStep","13/88"],["keys","viewStep","99/1"],["keys","viewResyncLong","4/53"],["keys","carplaySwitchLong","13/116"],
    ["keys","menu",99],["keys","zoomWheelSource",41],["keys","zoomWheelAuto","yes"],["options","language","fr"],["options","carplayNav","on"],["options","sdLog",1]];
  for(const [grp,k,v] of bads){const b=clone(p0);b[grp][k]=v;throwsMsg(()=>w.MIBR_project.validate(b),grp+"."+k+"="+v);throwsMsg(()=>w.MIBR_project.apply(b),"apply "+k);}
  for(const [k,v] of [["mainZoom","90"],["clusterPhysical","P40"]]){const b=clone(p0);b.options.scaling[k]=v;throwsMsg(()=>w.MIBR_project.validate(b),k);}
  throwsMsg(()=>w.MIBR_project.validate(Object.assign(clone(p0),{keys:"x"})),"keys not an object");
  assert.equal(JSON.stringify(w.MIBR_project.capture()),before,"rejected project leaves state unchanged");
  assert.deepEqual(errors,[],"No runtime errors");
  console.log("P0.10 unit settings tests PASS");
}
main().catch(e=>{console.error(e);process.exit(1)});
