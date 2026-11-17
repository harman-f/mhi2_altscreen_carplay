"use strict";
// Single source of truth: all three AID10 mock-ups use the same OEM status geometry.
// Usage: node tools/menu-editor/build-shared-oem-overlays.cjs [--check]
const fs=require("node:fs"),path=require("node:path");
const root=__dirname,views=["center","wide","full"];

// P0.9.10 (wide/full): top bar fill, dark scrim y 37..96, full-view rounded display corners. Coordinates from AID10_CLUSTER_GEOMETRY_P099.json.
const BAR="M0 0H1010V37H555L536 50.5H476L455 37H0Z";
const FULL_CORNERS="M0 0H94C70 2 30 8 0 16ZM1010 0H910C940 4 985 16 1010 27Z";
function topBackdrop(v){
 const full=v==="full";
 return `<defs><linearGradient id="${v}-scrim-grad" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#04070d" stop-opacity=".66"/><stop offset=".55" stop-color="#04070d" stop-opacity=".5"/><stop offset="1" stop-color="#04070d" stop-opacity="0"/></linearGradient>${full?`<linearGradient id="full-bar-grad" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#18263c" stop-opacity=".4"/><stop offset=".15" stop-color="#18263c" stop-opacity=".8"/><stop offset=".85" stop-color="#18263c" stop-opacity=".8"/><stop offset="1" stop-color="#18263c" stop-opacity=".4"/></linearGradient>`:""}</defs>
<rect id="${v}-top-scrim" x="0" y="37" width="1010" height="59" fill="url(#${v}-scrim-grad)"/>
<path id="${v}-top-bar" d="${BAR}" fill="${full?"url(#full-bar-grad)":"#18263c"}"/>
${full?`<path id="full-top-corners" d="${FULL_CORNERS}" fill="#05080e"/>\n`:""}`;
}
function sharedTop(v,p){
return `<!-- MIBR_SHARED_TOP_BEGIN: common OEM status coordinates across Center/Wide/Voll (P0.9.10: measured on rectified photos, per-view bar/scrim/arrow box) -->
${v==="center"?"":topBackdrop(v)}<g id="${v}-top-status" fill="#f5f9ff">
  <path d="M296 13l-6 17h12z" fill="#e7f0fb"/><text x="304" y="30" font-size="22" font-weight="600">W</text>
  <text x="505" y="40" text-anchor="middle" font-size="31" font-weight="600" letter-spacing=".5">23:22</text>
  <g transform="translate(654 22)" stroke="#2bc7eb" stroke-width="2.2" stroke-linecap="round"><path d="M0-10V10M-8.7-5L8.7 5M-8.7 5L8.7-5"/></g>
  <text x="665" y="30" font-size="22" font-weight="600">4.0°C</text>
  <path d="${v==="center"?"M0 38H454L474 51H539L559 38H1010":"M0 37H455L476 50.5H536L555 37H1010"}" fill="none" stroke="#dce7f3" stroke-width="1.6" opacity=".83"/>
</g>
<g id="${v}-top-text" fill="#f7fbff" text-anchor="middle">
  ${v==="center"?`<rect x="395" y="60" width="220" height="27" rx="3" fill="#0b1423" opacity=".5"/>`:`<rect id="${v}-top-text-zone" x="367" y="60" width="275" height="24" rx="3" fill="#0b1423" opacity=".5"/>`}
  <text id="${v}-top-label" x="505" y="${v==="center"?80:77}" font-size="21" font-weight="600">${p.road} m · Hauptstraße</text>
</g>
${v==="center"?"":`<rect id="${v}-arrow-box" x="367" y="89" width="275" height="35" fill="#4d5566"/>
`}<!-- MIBR_SHARED_TOP_END -->`;
}

// P0.9.10: bottom band items differ per view (measured: Wide distance at x 366 / ETA 570, Voll distance 311 / ETA 633..709). Center keeps its P0.9.9 values.
const BOTTOM={center:{dcx:376,dtx:392,etx:562,ecx:631},wide:{dcx:376,dtx:392,etx:570,ecx:634},full:{dcx:321.5,dtx:339,etx:633,ecx:698}};
function bottomStrip(v){
 const poly=v==="wide"?"224.1 306H786L780.3 334H229.7Z":"186.9 306H822.4L798.4 334H210.2Z";
 return `<path id="${v}-bottom-strip" d="M${poly}" fill="#3b4354"${v==="full"?` fill-opacity=".8"`:""}/>\n`;
}
function sharedBottom(v,p){
const B=BOTTOM[v];
return `<!-- MIBR_SHARED_BOTTOM_BEGIN: identical OEM navigation/assist baseline across views (P0.9.10: measured on rectified photos, per-view band positions) -->
${v==="center"?"":bottomStrip(v)}<g id="${v}-bottom-info" fill="#edf5ff" font-size="21" font-weight="600">
  <g id="${v}-bottom-distance">
    <circle cx="${B.dcx}" cy="321" r="8.5" fill="none" stroke="#dce8f5" stroke-width="1.8"/>
    <path d="M${B.dcx} 309v24m-12-12h24" fill="none" stroke="#dce8f5" stroke-width="1.2"/>
    <text x="${B.dtx}" y="328">${p.distance} km</text>
  </g>
  <g id="${v}-bottom-eta">
    <text id="${v}-bottom-eta-label" x="${B.etx}" y="328">${p.eta}</text>
    <circle cx="${B.ecx}" cy="321" r="9" stroke="#e4eef8" stroke-width="1.8" fill="none"/>
    <path d="M${B.ecx} 314v7l5 4" stroke="#e4eef8" fill="none" stroke-width="1.6"/>
  </g>
</g>
<g id="${v}-footer" fill="#d2deeb" font-size="21" font-weight="500">
  ${v==="center"?`<path d="M216 335H816" stroke="#b6c8d9" stroke-width="1.3" opacity=".6"/>
  <rect x="262" y="336" width="486" height="40" fill="#0c1728" opacity=".8"/>`:`<rect id="${v}-bottom-bar" x="0" y="334" width="1010" height="42" fill="#0c1728"/>
  <path d="M0 334.5H1010" stroke="#b6c8d9" stroke-width="1.3" opacity=".7"/>`}
  <text x="${v==="center"?283:285}" y="362"><tspan font-size="15">trip</tspan> 5936.7 km</text>
  <!-- Demonstration icons only; not evidence of independently writable BAP channels. -->
  <g id="${v}-seatbelt-warning" transform="translate(${v==="center"?"453 342":"454 338"}) scale(1.15)" fill="none" stroke="#ff3047" stroke-linecap="round" stroke-linejoin="round">
    <!-- Seated occupant, lap/shoulder restraint and buckle: warning pictogram, not a pedestrian. -->
    <circle cx="7" cy="3.5" r="2.5" fill="#ff3047" stroke="none"/>
    <path d="M5 8.5L4 15q0 2 3 3h5l4 3" stroke-width="2"/>
    <path d="M6.2 9l8 9.3" stroke-width="2.4"/>
    <path d="M3 11v9h13" stroke-width="1.6"/>
    <path d="M11 12.5l5.5 5.5" stroke-width="1.6"/>
    <rect x="12.5" y="18" width="3.8" height="2.4" rx=".6" fill="#ff3047" stroke="none"/>
  </g>
  ${v==="center"?`<path d="M484 376l11-38h20l11 38" fill="#6c8097" opacity=".83"/>
  <path d="M494 338l-10 38m31-38l10 38" fill="none" stroke="#becbd9" stroke-width="1.8"/>`:`<path d="M478 371l11-34h22l11 34" fill="#6c8097" opacity=".83"/>
  <path d="M489 337l-11 34m33-34l11 34" fill="none" stroke="#becbd9" stroke-width="1.8"/>`}
  <g id="${v}-yellow-road-guidance" transform="translate(576 345) scale(1.5 1.4) translate(-566 -341)" fill="none" stroke="#f8d843" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
    <!-- Perspective road edges and an unmistakable dashed centre line, not two chevrons. -->
    <path d="M566 356l5-15M588 356l-5-15"/>
    <path d="M577 342v4m0 4v5" stroke-width="1.7"/>
  </g>
  <g transform="translate(613 344) scale(2) translate(-607 -342)" fill="none" stroke="#cbd9e7" stroke-width="1.15" opacity=".84">
    <path d="M608 354a8 8 0 1 1 13 0M614.5 350l3-4"/>
  </g>
  <text x="647" y="362">--- km/h</text>
</g>
<!-- MIBR_SHARED_BOTTOM_END -->`;
}
function upgradeSvg(src,v){
 const p={center:{road:"200",distance:"1.3",eta:"23:23"},wide:{road:"300",distance:"1.4",eta:"23:22"},full:{road:"100",distance:"1.2",eta:"23:23"}}[v];
 if(!p)throw Error("Unknown view "+v);
 const top=sharedTop(v,p)+"\n",bottom=sharedBottom(v,p)+"\n";
 const topRe=src.includes("<!-- MIBR_SHARED_TOP_BEGIN")?/<!-- MIBR_SHARED_TOP_BEGIN[\s\S]*?<!-- MIBR_SHARED_TOP_END -->\n?/:new RegExp(`<g id="${v}-top-status"[\\s\\S]*?(?=<g id="${v}-top-lanes")`);
 const bottomRe=src.includes("<!-- MIBR_SHARED_BOTTOM_BEGIN")?/<!-- MIBR_SHARED_BOTTOM_BEGIN[\s\S]*?<!-- MIBR_SHARED_BOTTOM_END -->\n?/:new RegExp(`<g id="${v}-bottom-info"[\\s\\S]*?(?=<g id="${v==="full"?"full-speed":v+"-side-metrics"}")`);
 if(!topRe.test(src)||!bottomRe.test(src))throw Error("Missing OEM overlay block "+v);
 return src.replace(topRe,top).replace(bottomRe,bottom);
}
function rebuildHtml(src,svgs){
 for(const v of ["center","wide","full"]){
  const re=new RegExp(`<svg id="navv-${v}-svg"[\\s\\S]*?<\\/svg>`);
  if(!re.test(src))throw Error("Missing HTML inline SVG "+v);
  src=src.replace(re,svgs[v].trim());
 }
 return src;
}
const svgOut={};
let dirty=false;
for(const v of views){
 const file=path.join(root,"mibr-"+v+"-preview.svg");
 const original=fs.readFileSync(file,"utf8"),generated=upgradeSvg(original,v);
 svgOut[v]=generated;
 if(original!==generated){
   dirty=true;
   if(!process.argv.includes("--check"))fs.writeFileSync(file,generated);
   else console.error("OUT OF SYNC:",path.basename(file));
 }
}
for(const name of ["mibr-menu-editor-nav-views-mockup.html"]){
 const file=path.join(root,name),original=fs.readFileSync(file,"utf8"),generated=rebuildHtml(original,svgOut);
 if(original!==generated){
  dirty=true;
  if(!process.argv.includes("--check"))fs.writeFileSync(file,generated);
  else console.error("OUT OF SYNC:",name);
 }
}
if(process.argv.includes("--check")&&dirty)process.exitCode=1;
else console.log("Shared AID10 OEM overlays synchronized: "+views.join(", "));
