// P0.9 visual browser acceptance: real Chromium screenshots in desktop and iPhone-sized viewports.
// Run with: npm install --no-save playwright-core@1.55.0 && node tools/menu-editor/test-p09-visual.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {pathToFileURL} = require("node:url");
const {chromium} = require("playwright-core");

const source=path.join(__dirname,"mibr-menu-editor-nav-views-mockup.html");
const output=path.join(process.cwd(),"p09-visual-artifacts");
fs.mkdirSync(output,{recursive:true});
const chromeCandidates=[process.env.CHROME_PATH,process.env.CHROMIUM_PATH,
 "/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium",
 "/opt/google/chrome/chrome"].filter(Boolean);
const executablePath=chromeCandidates.find(p=>fs.existsSync(p));
if(!executablePath)throw Error("No installed Chrome/Chromium for real-browser visual test");
const scenarios=[
 {name:"desktop",viewport:{width:1440,height:900},deviceScaleFactor:1,isMobile:false},
 {name:"iphone",viewport:{width:390,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true}
];
const views=["center","wide","full"],surfaces=["map","app","off"],results=[];
const b=async(s)=>await s.boundingBox();
function overlap(a,b){
 if(!a||!b)return 0;
 return Math.max(0,Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x))
     *Math.max(0,Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y));
}
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath,args:["--no-sandbox","--disable-gpu"]});
 try{
  for(const sc of scenarios){
   const context=await browser.newContext({...sc,locale:"de-DE",colorScheme:"light"});
   const page=await context.newPage(),exceptions=[];
   page.on("pageerror",e=>exceptions.push(e.message));
   await page.goto(pathToFileURL(source).href,{waitUntil:"domcontentloaded"});
   await page.locator('#tabs [data-t="nav"]').click();
   await page.locator("#navv-layer").waitFor({state:"visible"});
   for(const view of views){
    await page.locator('[data-navv-view="'+view+'"]').click();
    assert.equal(await page.locator('[data-navv-view="'+view+'"]').getAttribute("aria-pressed"),"true");
    assert.equal(await page.locator('#navv-viewname').innerText(),view==="full"?"Voll":view==="wide"?"Wide":"Center");
    const active=page.locator("#navv-"+view+"-svg");
    assert.equal(await active.isVisible(),true,view+" visible");
    for(const other of views.filter(x=>x!==view))assert.equal(await page.locator("#navv-"+other+"-svg").isVisible(),false,other+" hidden");
    for(const surface of surfaces){
     await page.locator('[data-navv-section="carplay"][data-navv-key="surface"]').selectOption(surface);
     if(surface==="map")await page.locator("#navv-bgmode").selectOption("map");
     const svg=await b(active),holder=await b(page.locator("#navv-center-preview"));
     assert(svg&&holder,sc.name+" "+view+" has measurable SVG");
     assert(svg.width>100,sc.name+" "+view+" SVG not collapsed");
     assert(svg.width<=sc.viewport.width+1,sc.name+" "+view+" SVG wider than viewport");
     assert.equal(await page.locator("#navv-bgmode").isDisabled(),surface!=="map");
     if(surface==="map"){
      assert.equal(await page.locator("#"+view+"-map-route").isVisible(),true,view+" visible route");
      assert.equal(await page.locator("#"+view+"-app-placeholder").isVisible(),false);
      assert.equal(await page.locator("#"+view+"-off-placeholder").isVisible(),false);
     }else{
      assert.equal(await page.locator("#"+view+"-map-route").isVisible(),false);
      assert.equal(await page.locator("#"+view+"-"+surface+"-placeholder").isVisible(),true);
     }
     const file=sc.name+"-"+view+"-"+surface+".png";
     await page.locator(".navv-view-preview").screenshot({path:path.join(output,file),animations:"disabled"});
     const road=await b(page.locator("#"+view+"-top-text"));
     const status=await b(page.locator("#"+view+"-top-status"));
     const footer=await b(page.locator("#"+view+"-footer"));
     const lower=await b(page.locator("#"+view+"-bottom-info"));
     results.push({scenario:sc.name,view,surface,png:file,
       svg:{width:Math.round(svg.width),height:Math.round(svg.height)},
       overlapStatusRoad:Math.round(overlap(road,status)),
       overlapLowerFooter:Math.round(overlap(lower,footer)),
       scrollWidth:await page.evaluate(()=>document.documentElement.scrollWidth)});
    }
    if(sc.name==="iphone"){
     // A standalone mobile screenshot also includes the selection context, not just the SVG.
     await page.locator(".navv-view-selector").screenshot({path:path.join(output,"iphone-"+view+"-selector.png")});
    }
   }
   assert.deepEqual(exceptions,[],sc.name+" browser exceptions");
   await context.close();
  }
  fs.writeFileSync(path.join(output,"geometry.json"),JSON.stringify(results,null,2)+"\n");
  console.log("P0.9 Chromium visual PASS; "+results.length+" screenshot scenarios; browser="+executablePath);
  console.log(JSON.stringify(results.map(x=>({scenario:x.scenario,view:x.view,surface:x.surface,svg:x.svg,overlapStatusRoad:x.overlapStatusRoad,overlapLowerFooter:x.overlapLowerFooter})),null,2));
 }finally{await browser.close()}
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
