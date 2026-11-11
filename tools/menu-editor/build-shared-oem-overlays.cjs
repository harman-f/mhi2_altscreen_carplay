"use strict";
// Single source of truth: all three AID10 mock-ups use the same OEM status geometry.
// Usage: node tools/menu-editor/build-shared-oem-overlays.cjs [--check]
const fs=require("node:fs"),path=require("node:path");
const root=__dirname,views=["center","wide","full"];
function sharedTop(v,p){
return `<!-- MIBR_SHARED_TOP_BEGIN: common OEM status coordinates across Center/Wide/Voll -->
<g id="${v}-top-status" fill="#f5f9ff">
  <path d="M384 31l-6 13h12z" fill="#e7f0fb"/><text x="399" y="43" font-size="15.5" font-weight="600">W</text>
  <text x="505" y="43" text-anchor="middle" font-size="24" font-weight="650" letter-spacing=".1">23:22</text>
  <g transform="translate(623 34)" stroke="#2bc7eb" stroke-width="1.8" stroke-linecap="round"><path d="M0-8V8M-7-4L7 4M-7 4L7-4"/></g>
  <text x="640" y="43" font-size="15.5" font-weight="600">4.0°C</text>
  <path d="M394 60H466l8 6h64l8-6h70" fill="none" stroke="#dce7f3" stroke-width="1.35" opacity=".83"/>
</g>
<g id="${v}-top-text" fill="#f7fbff" text-anchor="middle">
  <rect x="394" y="74" width="222" height="27" rx="3" fill="#0b1423" opacity=".84"/>
  <text id="${v}-top-label" x="505" y="93" font-size="15.5" font-weight="600">${p.road} m · Hauptstraße</text>
</g>
<!-- MIBR_SHARED_TOP_END -->`;
}
function sharedBottom(v,p){
return `<!-- MIBR_SHARED_BOTTOM_BEGIN: identical OEM navigation/assist baseline across views -->
<g id="${v}-bottom-info" fill="#edf5ff" font-size="14" font-weight="600">
  <g id="${v}-bottom-distance">
    <circle cx="420" cy="314" r="7.2" fill="none" stroke="#dce8f5" stroke-width="1.5"/>
    <path d="M420 302v24m-12-12h24" fill="none" stroke="#dce8f5" stroke-width="1.05"/>
    <text x="437" y="319">${p.distance} km</text>
  </g>
  <g id="${v}-bottom-eta">
    <text id="${v}-bottom-eta-label" x="550" y="319">${p.eta}</text>
    <circle cx="600" cy="314" r="7.8" stroke="#e4eef8" stroke-width="1.5" fill="none"/>
    <path d="M600 308v6l4 3" stroke="#e4eef8" fill="none" stroke-width="1.4"/>
  </g>
</g>
<g id="${v}-footer" fill="#d2deeb" font-size="11.5" font-weight="500">
  <path d="M371 333H659" stroke="#b6c8d9" stroke-width="1.15" opacity=".55"/>
  <rect x="377" y="335" width="286" height="27" rx="2" fill="#0c1728" opacity=".64"/>
  <text x="387" y="353">trip 5936.7 km</text>
  <!-- Demonstration icons only; not evidence of independently writable BAP channels. -->
  <g transform="translate(487 346)" fill="none" stroke="#f33f4b" stroke-width="1.5" stroke-linecap="round">
    <circle cx="3" cy="-4" r="2" fill="#f33f4b" stroke="none"/>
    <path d="M2 0l5 4m-3-4l-1 7m-5-5l4 1"/>
  </g>
  <path d="M516 358l7-20h11l7 20" fill="#6c8097" opacity=".83"/>
  <path d="M522 339l-6 19m18-19l7 19" fill="none" stroke="#becbd9" stroke-width="1.55"/>
  <path d="M566 354l5-10 5 10m7 0l5-10 5 10" fill="none" stroke="#f8d843" stroke-width="1.6" stroke-linejoin="round" opacity=".92"/>
  <g fill="none" stroke="#cbd9e7" stroke-width="1.15" opacity=".84">
    <path d="M608 354a8 8 0 1 1 13 0M614.5 350l3-4"/>
  </g>
  <text x="633" y="353" font-size="10">--- km/h</text>
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
for(const name of ["mibr-menu-editor-nav-views-mockup.html","mibr-menu-editor-nav-views-p091.html"]){
 const file=path.join(root,name),original=fs.readFileSync(file,"utf8"),generated=rebuildHtml(original,svgOut);
 if(original!==generated){
  dirty=true;
  if(!process.argv.includes("--check"))fs.writeFileSync(file,generated);
  else console.error("OUT OF SYNC:",name);
 }
}
if(process.argv.includes("--check")&&dirty)process.exitCode=1;
else console.log("Shared AID10 OEM overlays synchronized: "+views.join(", "));
