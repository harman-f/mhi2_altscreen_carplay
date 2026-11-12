// P0.9 visual browser acceptance: real Chromium screenshots in desktop and iPhone-sized viewports.
// Run with: npm install --no-save playwright-core@1.55.0 && node tools/menu-editor/test-p09-visual.cjs
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {pathToFileURL} = require("node:url");
const {chromium} = require("playwright-core");

const source=path.join(__dirname,"mibr-menu-editor-nav-views-mockup.html");
const reviewFile=path.join(__dirname,"mibr-menu-editor-nav-views-p096.html");
assert.equal(fs.readFileSync(reviewFile,"utf8"),fs.readFileSync(source,"utf8"),"P0.9.6 standalone review HTML must match canonical source");
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
    const common=await page.evaluate(v=>{
      const svg=document.getElementById("navv-"+v+"-svg");
      const a=id=>svg.querySelector("#"+v+"-"+id);
      return {
        clockX:a("top-status").querySelector('text[text-anchor="middle"]').getAttribute("x"),
        clockSize:a("top-status").querySelector('text[text-anchor="middle"]').getAttribute("font-size"),
        temperatureX:a("top-status").querySelectorAll("text")[2].getAttribute("x"),
        roadX:a("top-label").getAttribute("x"),
        distanceX:a("bottom-distance").querySelector("text").getAttribute("x"),
        etaX:a("bottom-eta-label").getAttribute("x"),
        footerX:a("footer").querySelector("text").getAttribute("x")
      };
    },view);
    assert.deepEqual(common,{clockX:"505",clockSize:"24",temperatureX:"640",roadX:"505",distanceX:"437",etaX:"550",footerX:"387"},view+" shared layout");
    assert.equal(await page.locator("#"+view+"-seatbelt-warning").count(),1,view+" seatbelt SVG");
    assert.equal(await page.locator("#"+view+"-yellow-road-guidance path").count(),2,view+" two yellow road paths");
    if(view==="wide"){
      const turn=page.locator("#wide-right-turn");
      assert.equal(await turn.locator("path").count(),1,"Wide uses one arrow silhouette");
      assert.equal(await page.locator("#wide-turn-silhouette").getAttribute("stroke"),"#f7fcff");
    }
        const calibrated=await page.evaluate(v=>{
      const svg=document.getElementById("navv-"+v+"-svg");
      if(v==="wide")return {clip:svg.querySelector("#w-map-clip path").getAttribute("d")};
      if(v==="full")return {clip:svg.querySelector("#f-mainclip path").getAttribute("d")};
      return {left:svg.querySelector("#center-left-dial").getAttribute("transform"),right:svg.querySelector("#center-right-dial").getAttribute("transform")};
    },view);
    if(view==="wide")assert.equal(calibrated.clip,"M188 37H830L738 329H272Z","Grid-aligned Wide");
    else if(view==="full")assert.ok(calibrated.clip.includes("L737 350H273"),"Grid-aligned Full cutout");
    else assert.deepEqual(calibrated,{left:"translate(-43.18 -11.04) scale(1.06)",right:"translate(-17.42 -11.04) scale(1.06)"},"Grid-aligned Center");
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
    // Exercise the actual 'Links / Rechts / Oben' maneuver-card positions.
    await page.locator('[data-navv-section="carplay"][data-navv-key="surface"]').selectOption("map");
    await page.locator("#navv-bgmode").selectOption("map");
    await page.locator('[data-navv-section="native"][data-navv-key="topText"]').selectOption("distance");
    await page.locator('[data-navv-section="native"][data-navv-key="topSymbol"]').selectOption("lanes");
    const positions={};
    for(const pos of ["left","right","top"]){
      await page.locator('[data-navv-section="carplay"][data-navv-key="maneuver"]').selectOption(pos);
      const overlay=page.locator("#"+view+"-carplay-overlay");
      assert.equal(await overlay.isVisible(),true,view+" "+pos+" overlay visible");
      positions[pos]=await b(overlay);
      assert(positions[pos],"Overlay has a measurable box");
    }
    assert(positions.left.x<positions.right.x,view+" left and right map placement");
    assert(positions.top.y<positions.left.y,view+" top placement above lower placements");
    const upper=await b(page.locator("#"+view+"-top-text"));
    assert.equal(Math.round(overlap(positions.top,upper)),0,view+" top maneuver preview does not cover native road text");
    const lower=await b(page.locator("#"+view+"-bottom-info"));
    assert.equal(Math.round(overlap(positions.top,lower)),0,view+" top maneuver preview does not cover bottom info");
    await page.locator(".navv-view-preview").screenshot({path:path.join(output,sc.name+"-"+view+"-maneuver-top.png"),animations:"disabled"});
    results.push({scenario:sc.name,view,surface:"maneuver-top",
      overlay:{x:Math.round(positions.top.x),y:Math.round(positions.top.y)},
      overlapStatusRoad:Math.round(overlap(upper,await b(page.locator("#"+view+"-top-status")))),
      overlapLowerFooter:0});
    await page.locator('[data-navv-section="carplay"][data-navv-key="maneuver"]').selectOption("off");
    await page.locator('[data-navv-section="native"][data-navv-key="topText"]').selectOption("off");
    await page.locator('[data-navv-section="native"][data-navv-key="topSymbol"]').selectOption("off");
    if(sc.name==="iphone"){
     // A standalone mobile screenshot also includes the selection context, not just the SVG.
     await page.locator(".navv-view-selector").screenshot({path:path.join(output,"iphone-"+view+"-selector.png")});
    }
   }
   // Screenshot Safe Area with the OEM assist in both visual modes and confirm no geometry changes.
   await page.locator('[data-navv-view="center"]').click();
   await page.locator('#tabs [data-t="safe"]').click();
   const originalEdges=await page.locator("#sa-x").inputValue();
   await page.locator("#sa-oem-show").check();
   assert.equal(await page.locator("#sa-grid-numbers").isVisible(),false,"Grid labels hidden when assist enabled");
   assert.equal(await page.locator("#sa-current-area").getAttribute("stroke"),"#2dd4bf","Distinct configured Safe Area outline");
   await page.locator("#sa-oem-opacity").evaluate(el=>{el.value="100";el.dispatchEvent(new Event("input",{bubbles:true}))});
   assert.equal(await page.locator("#sa-oem-preview").evaluate(el=>el.style.opacity),"1");
   for(const view of ["center","wide","full"]){
     const safeKey=view==="full"?"voll":view;
     await page.locator(".sa-views button").nth(view==="full"?0:view==="wide"?1:2).click();
     assert.equal(await page.locator("#sa-oem-mask").getAttribute("data-view"),view);
     await page.locator("#sa-oem-mode").selectOption("both");
     assert.equal(await page.locator("#sa-oem-mask > *").count(),6,view+" approximate mask has common and per-view geometry");
     const edge=page.locator("#sa-oem-edge-shell");
     assert.equal(await edge.getAttribute("data-view"),view,view+" edge shell accompanies selected OEM view");
     assert.equal(await edge.locator('[data-safe-edge]').count(),2,view+" two perimeter joints");
     assert.equal(await edge.locator("rect").count(),4,view+" common header and footer backplanes");
     if(view==="center"){
       const leftTransform=await page.locator("#sa-oem-mask > circle").first().getAttribute("transform");
       const rightTransform=await page.locator("#sa-oem-mask > circle").last().getAttribute("transform");
       assert.equal(leftTransform,"translate(-43.18 -11.04) scale(1.06)","Center Safe Area mask matches left scaled gauge");
       assert.equal(rightTransform,"translate(-17.42 -11.04) scale(1.06)","Center Safe Area mask matches right scaled gauge");
     }
     assert.ok(await page.locator('#sa-oem-preview [data-safe-origin="top-status"]').count(),view+" reuses OEM top status");
     await page.locator(".sa-pic").screenshot({path:path.join(output,sc.name+"-safe-"+view+"-both.png"),animations:"disabled"});
     // Quantitative grid reference overlay over the opaque OEM perimeter.
     await page.locator("#sa-oem-grid-labels").check();
     assert.equal(await page.locator("#sa-grid-foreground").isVisible(),true,view+" front grid labels remain visible");
     await page.locator(".sa-pic").screenshot({path:path.join(output,sc.name+"-safe-"+view+"-grid-overlay.png"),animations:"disabled"});
     await page.locator("#sa-oem-grid-labels").uncheck();
     await page.locator("#sa-oem-mode").selectOption("mask");
     assert.equal(await page.locator("#sa-oem-preview").isVisible(),false);
     await page.locator(".sa-pic").screenshot({path:path.join(output,sc.name+"-safe-"+view+"-mask.png"),animations:"disabled"});
   }
   await page.locator(".sa-views button").nth(2).click();
   await page.locator("#sa-oem-mode").selectOption("both");
   await page.locator("#sa-oem-grid-labels").check();
   assert.equal(await page.locator("#sa-grid-numbers").isVisible(),false,"Original background grid remains behind opaque OEM");
   assert.equal(await page.locator("#sa-grid-foreground").isVisible(),true,"Opt-in calibration labels appear in front of OEM");
   assert.ok(await page.locator("#sa-grid-foreground text").count()>100,"All numeric columns visible for comparison");
   await page.locator(".sa-pic").screenshot({path:path.join(output,sc.name+"-safe-center-grid-numbers.png"),animations:"disabled"});
   await page.locator("#sa-oem-grid-labels").uncheck();
   assert.equal(await page.locator("#sa-grid-foreground").isVisible(),false);
   assert.equal(await page.locator("#sa-x").inputValue(),originalEdges,"OEM assistant never alters Center safe area");
   await page.locator("#sa-oem-show").uncheck();
   assert.equal(await page.locator("#sa-oem-mask").isVisible(),false);
   assert.deepEqual(exceptions,[],sc.name+" browser exceptions");
   await context.close();
  }
  fs.writeFileSync(path.join(output,"geometry.json"),JSON.stringify(results,null,2)+"\n");
  console.log("P0.9 Chromium visual PASS; "+results.length+" screenshot scenarios; browser="+executablePath);
  console.log(JSON.stringify(results.map(x=>({scenario:x.scenario,view:x.view,surface:x.surface,svg:x.svg,overlapStatusRoad:x.overlapStatusRoad,overlapLowerFooter:x.overlapLowerFooter})),null,2));
 }finally{await browser.close()}
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
