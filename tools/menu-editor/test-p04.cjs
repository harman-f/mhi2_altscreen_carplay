// Browser-level regression smoke test for the P0.4 standalone menu editor.
// Usage: npm install --no-save jsdom@24 && node tools/menu-editor/test-p04.cjs
const fs = require("node:fs");
const {TextEncoder,TextDecoder} = require("node:util");
const path = require("node:path");
const assert = require("node:assert/strict");
const {JSDOM, VirtualConsole} = require("jsdom");

const html = fs.readFileSync(path.join(__dirname, "mibr-menu-editor-nav-views-mockup.html"),"utf8");
const failures = [];
const vc = new VirtualConsole();
vc.on("jsdomError", err => failures.push(String(err)));
const dom = new JSDOM(html, {
  url:"https://localhost.local/mibr-menu-editor.html",
  runScripts:"dangerously",
  virtualConsole:vc,
  beforeParse(window){
    window.TextEncoder=TextEncoder;
    window.TextDecoder=TextDecoder;
    window.matchMedia = () => ({matches:false, addEventListener(){},removeEventListener(){}});
    window.scrollTo = () => {};
    window.confirm = () => true;
  }
});
const {window:w} = dom, d=w.document;
const query=s=>d.querySelector(s);
const click=s=>{const e=query(s);assert.ok(e, "Missing element: "+s);e.click();return e};
const change=(s,val,event="change")=>{
  const e=query(s);assert.ok(e, "Missing input: "+s);e.value=val;
  e.dispatchEvent(new w.Event(event,{bubbles:true}));return e;
};
async function main(){
  await new Promise(resolve=>setTimeout(resolve,20));
  assert.deepEqual(failures,[],"Startup runtime exception");
  assert.equal(query("#appTitle").textContent,"MIB-Konfigurator");
  assert.equal(d.querySelectorAll("#tabs button").length,3);
  assert.ok(d.querySelectorAll("#tree .row").length>15,"Missing existing menu tree");
  assert.ok(query("#menuTools")&&!query("#menuTools").hidden);
  assert.ok(query("#menuWorkspaceControls").contains(query("#menuTools")), "Menu toolbar must be owned by menu workspace");
  assert.ok(query("#menuWorkspaceControls").contains(query("#menuSections")), "Menu sub-navigation must be owned by menu workspace");
  assert.ok(!query("#menuWorkspaceControls").hidden, "Menu workspace should be visible at startup");
  assert.ok(!query("header").contains(query("#menuTools")), "Menu toolbar cannot be in global header");
  assert.equal(w.getComputedStyle(query("#menuWorkspaceControls")).display === "none",false);
  assert.ok(query("#menuTools").contains(query("#save")), "Menu save must stay in menu workspace");
  assert.ok(query("#menuTools").contains(query("#load")), "Menu load must stay in menu workspace");
  assert.ok(query("#menuSections [data-pane=preview]"));
  click('#menuSections [data-pane=file]');
  assert.ok(query("#filetext").textContent.startsWith("MIBR_MENU/1"),"Legacy menu output missing");
  assert.ok(query("#filetext").textContent.includes("crc32="));
  click('#menuSections [data-pane=preview]');
  assert.ok(query("#pv"),"Menu preview missing");

  click('#tabs [data-t=nav]');
  assert.equal(query("#menuTools").hidden,true);
  assert.equal(query("#menuWorkspaceControls").hidden,true);
  assert.equal(query("#menuSections").hidden,true);
  assert.equal(w.getComputedStyle(query("#menuWorkspaceControls")).display,"none", "Menu tools visually leaked into View configurator");
  assert.ok(query("#navv-layer").contains(query("#navv-json")), "View profile export must be owned by View configurator");
  assert.ok(query(".navv-filebar").contains(query("#navv-import")), "View profile import must be directly available in View tab");
  assert.ok(query(".navv-filebar").contains(query("#navv-conf")), "View profile .conf export missing");
  assert.ok(query(".navv-filebar")&&!query(".navv-filebar").closest("details"), "View file controls should not be hidden in collapsed accordion");
  assert.equal(query("#navv-layer").hidden,false);
  assert.ok(query('#navv-safe-tools .sa-menu'),"Integrated safe area missing");
  assert.equal(JSON.parse(query("#navv-out").textContent).schema,"mibr.nav-view-profiles/2");

  change('#navv-safe-tools #sa-x',"400","input");
  let profile=JSON.parse(query("#navv-out").textContent);
  // Updating the safe area writes to state; JSON preview refreshes when other controls change.
  click('[data-navv-view=wide]');
  profile=JSON.parse(query("#navv-out").textContent);
  assert.equal(profile.views.center.safeArea.x,400,"Safe area did not become part of the view profile");
  assert.ok(profile.views.wide.safeArea.w>100,"Wide safe area missing");
  change("#navv-mode","custom");
  assert.ok(query('[data-navv-section=native][data-navv-key=topText]')&&!query('[data-navv-section=native][data-navv-key=topText]').disabled);

  click('#tabs [data-t=help]');
  assert.equal(query("#menuWorkspaceControls").hidden,true, "Menu controls leaked into help tab");
  assert.ok(query("#vbody").textContent.includes("THIRD_PARTY_NOTICES.md"),"Attribution not visible");
  click('#langSeg [data-l=en]');
  assert.equal(query("#appTitle").textContent,"MIB configurator");
  click('#themeSeg [data-theme-choice=dark]');
  assert.equal(d.documentElement.getAttribute("data-theme"),"dark");
  click('#tabs [data-t=menu]');
  assert.ok(!query("#menuTools").hidden);
  assert.ok(!query("#menuWorkspaceControls").hidden, "Menu tools did not return on menu tab");
  assert.notEqual(w.getComputedStyle(query("#menuWorkspaceControls")).display,"none");
  await new Promise(resolve=>setTimeout(resolve,20));
  assert.deepEqual(failures,[],"Runtime exceptions during interactions");
  w.close();
  process.stdout.write("P0.4 smoke tests PASS\n");
}
main().catch(err=>{process.stderr.write(err.stack+"\n"+failures.join("\n")+"\n");process.exitCode=1;w.close()});
