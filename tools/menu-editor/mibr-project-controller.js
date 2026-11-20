/* MIB-Konfigurator P0.5: shared browser project + SD export.
   Embedded in the standalone HTML by the release workflow.
   The vehicle runtime currently loads only /mibr-menu/mibr-menu.txt; the SD export
   also writes /mibr-config/{view-profiles.conf,keys.conf,options.conf,mibr-project.json}
   with one shared export.id (vehicle loaders follow).
   Options/keys (unit system settings) are optional top-level fields.
   P0.9.10: optional working folder (File System Access API, Chrome/Edge):
   chosen once, handle kept in IndexedDB, project auto-saved to and
   auto-loaded from <folder>/mibr-project.json. Same HTML online and offline;
   other browsers keep browser backup + download/import. */
(function(){
"use strict";
var SCHEMA="mibr-project/1",STORE="mibr-project/1:autosave",timer=0,applying=false;
var savedSnapshot=null,saveHandle=null,projectFile="mibr-project.json";
function $(id){return document.getElementById(id)}
function en(){return document.documentElement.lang==="en"}
function tr(de,english){return en()?english:de}
function status(msg,error){var e=$("projectStatus");e.textContent=msg;e.classList.toggle("problem",!!error)}
function clone(x){return JSON.parse(JSON.stringify(x))}
function car(){return window.MIBR_getVehicle()}
function system(){return window.MIBR_system}
function capture(){var v=car(),n=window.MIBR_views.get();n.vehicle=clone(v);
  var s=system().get();
  return {schema:SCHEMA,version:1,vehicle:clone(v),menu:window.MIBR_menu.get(),viewProfiles:n,options:s.options,keys:s.keys};}
function identical(a,b){return JSON.stringify(a)===JSON.stringify(b)}
function validate(p){
  if(!p||p.schema!==SCHEMA||p.version!==1||!p.vehicle||!p.menu||!p.viewProfiles)throw Error(tr("Kein gültiges MIB-Projekt","Invalid MIB project"));
  var v=p.vehicle;
  if(!["skoda","vw","seat","audi"].includes(v.brand)||!["MU1440","MU1409","MU1447"].includes(v.headUnit)||!["AID10","other"].includes(v.cluster))throw Error(tr("Unbekanntes Fahrzeugprofil","Unknown vehicle profile"));
  if(p.menu.brand!==v.brand||!p.viewProfiles.vehicle||!identical(p.viewProfiles.vehicle,v))throw Error(tr("Fahrzeugkontext stimmt nicht überein","Vehicle contexts disagree"));
  var m=window.MIBR_menu.validate(p.menu);
  window.MIBR_views.validate(p.viewProfiles);
  /* options/keys are optional (older project files): missing parts take the unit defaults, invalid values are rejected. */
  system().validate({options:p.options,keys:p.keys});
  return {errors:m.errors||[]};
}
function persist(){
  if(applying)return;
  try{var p=capture();localStorage.setItem(STORE,JSON.stringify(p));
    status(savedSnapshot===JSON.stringify(p)?
      (folderReady?tr("Projekt aktuell · Arbeitsordner „","Project current · working folder \u201c")+folderName()+tr("“","\u201d"):
      tr("Projekt aktuell · Browser-Sicherung aktiv","Project current · browser backup active")):
      tr("Im Browser gesichert · Projektdatei ggf. aktualisieren","Saved in browser · project file may need updating"));
    folderSchedule(p);
  }catch(e){status(tr("Browser-Sicherung fehlgeschlagen: ","Browser backup failed: ")+e.message,true)}
}
function schedule(){if(applying)return;clearTimeout(timer);timer=setTimeout(persist,150)}
function applyProject(p){
  validate(p);
  var old=capture();applying=true;
  try{
    window.MIBR_menu.set(p.menu);
    window.MIBR_setHardware(p.vehicle);
    window.MIBR_views.set(p.viewProfiles);
    system().set({options:p.options,keys:p.keys});
  }catch(e){
    try{window.MIBR_menu.set(old.menu);window.MIBR_setHardware(old.vehicle);window.MIBR_views.set(old.viewProfiles);system().set({options:old.options,keys:old.keys})}catch(ignored){}
    throw e;
  }finally{applying=false}
  persist();
}
function download(name,bytes,type){
  var object=new Blob([bytes],{type:type}),url=URL.createObjectURL(object);
  var a=document.createElement("a");a.href=url;a.download=name;a.hidden=true;document.body.appendChild(a);a.click();a.remove();
  setTimeout(function(){URL.revokeObjectURL(url)},5000);
}
function encode(s){return new TextEncoder().encode(s)}
function w16(dst,n){dst.push(n&255,(n>>>8)&255)}
function w32(dst,n){dst.push(n&255,(n>>>8)&255,(n>>>16)&255,(n>>>24)&255)}
function crc32(bytes){var v=0xFFFFFFFF;for(var i=0;i<bytes.length;i++){v^=bytes[i];for(var j=0;j<8;j++)v=(v>>>1)^((v&1)?0xEDB88320:0)}return (v^0xFFFFFFFF)>>>0}
function zipFiles(files){
  var bytes=[],cd=[],offset=0;
  files.forEach(function(file){
    var name=encode(file.path),data=encode(file.text),size=data.length,crc=crc32(data),flags=0x800;
    w32(bytes,0x04034b50);w16(bytes,20);w16(bytes,flags);w16(bytes,0);w16(bytes,0);w16(bytes,0);
    w32(bytes,crc);w32(bytes,size);w32(bytes,size);w16(bytes,name.length);w16(bytes,0);
    bytes.push.apply(bytes,Array.from(name));bytes.push.apply(bytes,Array.from(data));
    w32(cd,0x02014b50);w16(cd,20);w16(cd,20);w16(cd,flags);w16(cd,0);w16(cd,0);w16(cd,0);
    w32(cd,crc);w32(cd,size);w32(cd,size);w16(cd,name.length);w16(cd,0);w16(cd,0);
    w16(cd,0);w16(cd,0);w32(cd,0);w32(cd,offset);cd.push.apply(cd,Array.from(name));
    offset=bytes.length;
  });
  var centralSize=cd.length;bytes.push.apply(bytes,cd);
  w32(bytes,0x06054b50);w16(bytes,0);w16(bytes,0);w16(bytes,files.length);w16(bytes,files.length);
  w32(bytes,centralSize);w32(bytes,offset);w16(bytes,0);
  return new Uint8Array(bytes);
}
function nativeFile(){
  var v=car();
  if(v.brand!=="skoda"||v.headUnit!=="MU1440"||v.cluster!=="AID10")
    throw Error(tr("SD-Export ist nur für Škoda MU1440/AID10 freigegeben.","SD export is enabled only for Škoda MU1440/AID10."));
  return window.MIBR_menu.nativeText();
}
/* SD export (requirements 1.2): the menu file stays byte-identical to MIBR_MENU/1;
   the config files carry one shared export.id and end with crc32 over all lines before it. */
var SD_LIMIT=16384;
function hex8(n){return ("0000000"+(n>>>0).toString(16)).slice(-8)}
function exportId(){
  var stamp=new Date().toISOString().replace(/[-:]/g,"").replace(/\.\d+Z$/,"Z"),r=new Uint8Array(4);
  if(window.crypto&&window.crypto.getRandomValues)window.crypto.getRandomValues(r);else for(var i=0;i<4;i++)r[i]=Math.floor(Math.random()*256);
  return stamp+"-"+Array.from(r).map(function(b){return ("0"+b.toString(16)).slice(-2)}).join("");
}
function withCrc(lines){var body=lines.join("\n")+"\n";return body+"crc32="+hex8(crc32(encode(body)))+"\n"}
function onOff(b){return b?"on":"off"}
function profileText(id){
  var lines=window.MIBR_views.nativeConf().split("\n").filter(function(l){return l&&!/^crc32=/.test(l)&&!/^export\.id=/.test(l)});
  lines.splice(2,0,"export.id="+id);
  return withCrc(lines);
}
function keysText(id,k){
  return withCrc(["MIBR_KEYS/1","version=1","export.id="+id,"key.view_step="+k.viewStep,"key.view_resync_long="+k.viewResyncLong,
    "key.carplay_switch_long="+k.carplaySwitchLong,"key.menu="+k.menu,"zoom.wheel_source="+k.zoomWheelSource,"zoom.wheel_auto="+(k.zoomWheelAuto?1:0)]);
}
function optionsText(id,o){
  return withCrc(["MIBR_OPTIONS/1","version=1","export.id="+id,"view_config_mode="+(o.viewConfigMode==="perView"?"per_view":"global"),
    "carplay_nav="+onOff(o.carplayNav),"menu.language="+o.language,"expert_mode="+onOff(o.expertMode),"sd_log="+onOff(o.sdLog),
    "scaling.main.zoomFactor="+o.scaling.mainZoom,"scaling.cluster.zoomFactor="+o.scaling.clusterZoom,
    "scaling.main.physicalSize="+o.scaling.mainPhysical,"scaling.cluster.physicalSize="+o.scaling.clusterPhysical]);
}
/* All SD files, validated; throws (with the reason) instead of exporting a partial set. */
function sdFiles(id){
  var menu=nativeFile(),p=capture();validate(p);id=id||exportId();
  var files=[{path:"mibr-menu/mibr-menu.txt",text:menu},
    {path:"mibr-config/view-profiles.conf",text:profileText(id)},
    {path:"mibr-config/keys.conf",text:keysText(id,p.keys)},
    {path:"mibr-config/options.conf",text:optionsText(id,p.options)},
    {path:"mibr-config/mibr-project.json",text:JSON.stringify(Object.assign({exportId:id},p),null,2)+"\n"}];
  files.forEach(function(f){if(!/\.json$/.test(f.path)&&encode(f.text).length>SD_LIMIT)throw Error(tr("Datei zu groß: ","File too large: ")+f.path)});
  return files;
}
function sdList(files){return files.map(function(f){return "/"+f.path}).join(", ")}
function sdDone(files,how){
  status(how+tr(" · Heute lädt die Unit nur das Menü; Ansichtsprofile, Tasten und Optionen: Fahrzeugseite folgt."," · The unit loads only the menu today; view profiles, keys and options: vehicle side follows."));
}
function fallbackZip(files){
  download("mibr-sd-export.zip",zipFiles(files),"application/zip");
  sdDone(files,tr("ZIP-Download gestartet. Inhalt ins SD-Stammverzeichnis entpacken: ","ZIP download started. Extract into the SD-card root: ")+sdList(files));
}
async function sdExport(){
  var files;
  try{files=sdFiles()}catch(e){status(e.message,true);return}
  if(typeof window.showDirectoryPicker!=="function"){
    if(window.confirm(tr("Direkter Ordnerzugriff nicht verfügbar. ZIP mit allen SD-Dateien herunterladen?","No direct folder access. Download a ZIP with all SD files?")))fallbackZip(files);
    return;
  }
  try{
    var root=await window.showDirectoryPicker({mode:"readwrite",id:"mibr-sd"});
    if(!window.confirm(tr("Bitte bestätigen: gewählter Ordner ist das SD-Karten-Stammverzeichnis. Geschrieben werden: ","Confirm: the selected folder is the SD-card root. Files written: ")+sdList(files)))return;
    var dirs={},existing=[];
    for(var f of files){
      var parts=f.path.split("/"),dn=parts[0];
      if(!dirs[dn])dirs[dn]=await root.getDirectoryHandle(dn,{create:true});
      try{await dirs[dn].getFileHandle(parts[1]);existing.push("/"+f.path)}catch(e){if(e.name!=="NotFoundError")throw e}
    }
    if(existing.length&&!window.confirm(tr("Vorhandene Dateien überschreiben: ","Overwrite existing files: ")+existing.join(", ")+"?"))return;
    for(var g of files){
      var q=g.path.split("/"),handle=await dirs[q[0]].getFileHandle(q[1],{create:true}),writer=await handle.createWritable();
      try{await writer.write(g.text);await writer.close()}catch(e){try{await writer.abort()}catch(ignored){}throw e}
    }
    sdDone(files,tr("SD-Dateien geschrieben: ","SD files written: ")+sdList(files));
  }catch(e){if(e&&e.name==="AbortError")return;status(tr("SD-Export fehlgeschlagen: ","SD export failed: ")+e.message,true)}
}
function saveProject(){
  var p;
  try{p=capture();validate(p)}catch(e){status(e.message,true);return}
  var txt=JSON.stringify(p,null,2)+"\n";
  if(typeof window.showSaveFilePicker==="function"){
    window.showSaveFilePicker({suggestedName:projectFile,startIn:saveHandle||undefined,
      types:[{description:"MIB-Projekt (JSON)",accept:{"application/json":[".json"]}}]})
    .then(async function(h){var stream=await h.createWritable();await stream.write(txt);await stream.close();
      saveHandle=h;projectFile=h.name||"mibr-project.json";savedSnapshot=JSON.stringify(p);persist();status(tr("Projekt gespeichert: ","Project saved: ")+projectFile)})
    .catch(function(e){if(e&&e.name==="AbortError")return;status(tr("Projekt-Speichern fehlgeschlagen: ","Project save failed: ")+e.message,true)});
  }else{
    download(projectFile,txt,"application/json;charset=utf-8");
    status(tr("Projekt-Download gestartet: ","Project download started: ")+projectFile);
  }
}
function readProject(file){
  if(!file)return;
  if(file.size>2000000){status(tr("Projektdatei ist zu groß.","Project file too large."),true);return}
  var reader=new FileReader();
  reader.onload=function(){
    try{var p=JSON.parse(String(reader.result)),check=validate(p);
      if(!window.confirm(tr("Aktuelle Konfiguration durch dieses Projekt ersetzen?","Replace current configuration with this project?")))return;
      applyProject(p);savedSnapshot=JSON.stringify(capture());projectFile=file.name||"mibr-project.json";persist();
      status(tr("Projekt geladen: ","Project loaded: ")+projectFile+(check.errors.length?tr(" · Menü hat Prüffehler"," · menu has validation errors"):""));
    }catch(e){status(tr("Projektimport abgelehnt: ","Project import rejected: ")+e.message,true)}
  };
  reader.onerror=function(){status(tr("Projektdatei nicht lesbar.","Unable to read project file."),true)};
  reader.readAsText(file);
}

/* ---- P0.9.10 working folder ------------------------------------------- */
var FOLDER_FILE="mibr-project.json",DB="mibr-workfolder",DBSTORE="handles",DBKEY="work";
var folder=null,folderReady=false,folderTimer=0,folderPending=null,folderWriting=false;
function folderSupported(){return typeof window.showDirectoryPicker==="function"&&typeof indexedDB!=="undefined"}
function idb(mode,fn){return new Promise(function(resolve,reject){
  var rq=indexedDB.open(DB,1);
  rq.onupgradeneeded=function(){rq.result.createObjectStore(DBSTORE)};
  rq.onerror=function(){reject(rq.error)};
  rq.onsuccess=function(){var db=rq.result,tx=db.transaction(DBSTORE,mode),r=fn(tx.objectStore(DBSTORE));
    tx.oncomplete=function(){db.close();resolve(r&&r.result)};tx.onerror=function(){db.close();reject(tx.error)}};
})}
function folderRemember(h){return idb("readwrite",function(st){return st.put(h,DBKEY)})}
function folderForget(){return idb("readwrite",function(st){return st.delete(DBKEY)})}
function folderStored(){return idb("readonly",function(st){return st.get(DBKEY)})}
async function folderPermission(h,ask){
  var o={mode:"readwrite"};
  if(await h.queryPermission(o)==="granted")return true;
  return ask?(await h.requestPermission(o))==="granted":false;
}
async function folderRead(h){
  var fh;
  try{fh=await h.getFileHandle(FOLDER_FILE)}catch(e){if(e.name==="NotFoundError")return null;throw e}
  var f=await fh.getFile();
  if(f.size>2000000)throw Error(tr("Projektdatei ist zu groß.","Project file too large."));
  return JSON.parse(await f.text());
}
async function folderWrite(p){
  var fh=await folder.getFileHandle(FOLDER_FILE,{create:true}),w=await fh.createWritable();
  try{await w.write(JSON.stringify(p,null,2)+"\n");await w.close()}catch(e){try{await w.abort()}catch(ignored){}throw e}
}
function folderName(){return folder&&folder.name?folder.name:"?"}
function folderSchedule(p){
  if(!folderReady)return;
  folderPending=p;clearTimeout(folderTimer);folderTimer=setTimeout(folderFlush,800);
}
async function folderFlush(){
  if(!folderReady||!folderPending||folderWriting)return;
  var p=folderPending;folderPending=null;folderWriting=true;
  try{validate(p);await folderWrite(p);savedSnapshot=JSON.stringify(p);
    status(tr("Automatisch gespeichert in Ordner „","Auto-saved to folder “")+folderName()+tr("“ → ","” → ")+FOLDER_FILE);
  }catch(e){status(tr("Speichern im Arbeitsordner fehlgeschlagen: ","Saving to working folder failed: ")+e.message,true)}
  finally{folderWriting=false;if(folderPending)folderFlush()}
}
/* Called after permission is granted: load the folder file or seed it. */
async function folderAttach(h){
  folder=h;folderReady=false;
  var p=await folderRead(h),cur=capture();
  if(p){
    validate(p);
    if(!identical(p,cur)){applyProject(p)}
    savedSnapshot=JSON.stringify(capture());folderReady=true;
    status(tr("Projekt automatisch geladen aus Ordner „","Project auto-loaded from folder “")+folderName()+tr("“ · Änderungen werden dort gespeichert","” · changes are saved there"));
  }else{
    folderReady=true;folderPending=cur;await folderFlush();
  }
  folderButtons();
}
async function folderChoose(){
  try{
    var h=await window.showDirectoryPicker({mode:"readwrite",id:"mibr-work"});
    if(!await folderPermission(h,true))return;
    var existing=await folderRead(h);
    if(existing&&!identical(existing,capture())&&!window.confirm(tr(
      "In diesem Ordner liegt schon eine "+FOLDER_FILE+". Laden? (Abbrechen = aktuellen Stand dort hineinschreiben)",
      "This folder already holds "+FOLDER_FILE+". Load it? (Cancel = write current state there instead)"))){
      folder=h;folderReady=true;await folderRemember(h);folderPending=capture();await folderFlush();folderButtons();return;
    }
    await folderRemember(h);await folderAttach(h);
  }catch(e){if(e&&e.name==="AbortError")return;status(tr("Arbeitsordner nicht verfügbar: ","Working folder unavailable: ")+e.message,true)}
}
async function folderReconnect(){
  try{var h=folder||await folderStored();if(!h)return folderChoose();
    if(!await folderPermission(h,true))return;await folderAttach(h);
  }catch(e){status(tr("Arbeitsordner nicht verfügbar: ","Working folder unavailable: ")+e.message,true)}
}
async function folderDisconnect(){
  clearTimeout(folderTimer);folderReady=false;folder=null;folderPending=null;
  try{await folderForget()}catch(ignored){}
  folderButtons();status(tr("Arbeitsordner getrennt · Browser-Sicherung bleibt aktiv","Working folder disconnected · browser backup stays active"));
}
var folderBtn=null,folderOff=null;
function folderButtons(){
  if(!folderBtn)return;
  folderBtn.textContent=folderReady?tr("Ordner: ","Folder: ")+folderName():
    folder?tr("Arbeitsordner verbinden","Reconnect working folder"):tr("Arbeitsordner wählen","Choose working folder");
  folderBtn.title=tr("Projekt automatisch in "+FOLDER_FILE+" in einem Ordner auf dem PC speichern und beim Öffnen wieder laden (Chrome/Edge).",
    "Auto-save the project to "+FOLDER_FILE+" in a folder on this PC and reload it on open (Chrome/Edge).");
  folderOff.hidden=!folder;
  folderOff.textContent=tr("Ordner trennen","Disconnect folder");
}
function folderInit(){
  if(!folderSupported())return;
  var bar=$("projectActions"),anchor=$("sdExport");
  folderBtn=document.createElement("button");folderBtn.type="button";folderBtn.id="folderConnect";
  folderOff=document.createElement("button");folderOff.type="button";folderOff.id="folderDisconnect";folderOff.hidden=true;
  bar.insertBefore(folderBtn,anchor.nextSibling);bar.insertBefore(folderOff,folderBtn.nextSibling);
  folderBtn.addEventListener("click",function(){folderReady?folderChoose():folderReconnect()});
  folderOff.addEventListener("click",folderDisconnect);
  folderButtons();
  folderStored().then(async function(h){
    if(!h)return;folder=h;folderButtons();
    if(await folderPermission(h,false))await folderAttach(h);
    else status(tr("Arbeitsordner „","Working folder “")+folderName()+tr("“ bekannt · zum Laden einmal „Arbeitsordner verbinden“ klicken","” known · click “Reconnect working folder” once to load"));
  }).catch(function(e){status(tr("Arbeitsordner nicht verfügbar: ","Working folder unavailable: ")+e.message,true)});
}
function labels(){
  $("projectLoad").textContent=tr("Projekt laden","Load project");
  $("projectSave").textContent=tr("Projekt speichern","Save project");
  $("sdExport").textContent=tr("Auf SD-Karte exportieren","Export to SD card");
  folderButtons();
}
$("projectLoad").addEventListener("click",function(){$("projectFileIn").value="";$("projectFileIn").click()});
$("projectFileIn").addEventListener("change",function(){readProject(this.files&&this.files[0])});
$("projectSave").addEventListener("click",saveProject);
$("sdExport").addEventListener("click",sdExport);
$("langSeg").addEventListener("click",function(){setTimeout(labels,0)});
["mibr:menuchange","mibr:viewschange","mibr:safechange","mibr:vehiclechange","mibr:systemchange"].forEach(function(name){window.addEventListener(name,schedule)});
try{var raw=localStorage.getItem(STORE);if(raw)applyProject(JSON.parse(raw));else persist()}
catch(e){status(tr("Vorherige Einstellungen erhalten. Projekt-Wiederherstellung gescheitert: ","Previous settings preserved. Project restore failed: ")+e.message,true)}
folderInit();
labels();
window.MIBR_project={capture:capture,validate:validate,apply:applyProject,nativeFile:nativeFile,zipFiles:zipFiles,sdFiles:sdFiles};
})();
