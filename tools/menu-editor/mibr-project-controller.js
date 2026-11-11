/* MIB-Konfigurator P0.5: shared browser project + SD export.
   Embedded in the standalone HTML by the release workflow.
   The vehicle runtime currently knows only /mibr-menu/mibr-menu.txt. */
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
function capture(){var v=car(),n=window.MIBR_views.get();n.vehicle=clone(v);
  return {schema:SCHEMA,version:1,vehicle:clone(v),menu:window.MIBR_menu.get(),viewProfiles:n};}
function identical(a,b){return JSON.stringify(a)===JSON.stringify(b)}
function validate(p){
  if(!p||p.schema!==SCHEMA||p.version!==1||!p.vehicle||!p.menu||!p.viewProfiles)throw Error(tr("Kein gültiges MIB-Projekt","Invalid MIB project"));
  var v=p.vehicle;
  if(!["skoda","vw","seat","audi"].includes(v.brand)||!["MU1440","MU1409","MU1447"].includes(v.headUnit)||!["AID10","other"].includes(v.cluster))throw Error(tr("Unbekanntes Fahrzeugprofil","Unknown vehicle profile"));
  if(p.menu.brand!==v.brand||!p.viewProfiles.vehicle||!identical(p.viewProfiles.vehicle,v))throw Error(tr("Fahrzeugkontext stimmt nicht überein","Vehicle contexts disagree"));
  var m=window.MIBR_menu.validate(p.menu);
  window.MIBR_views.validate(p.viewProfiles);
  return {errors:m.errors||[]};
}
function persist(){
  if(applying)return;
  try{var p=capture();localStorage.setItem(STORE,JSON.stringify(p));
    status(savedSnapshot===JSON.stringify(p)?
      tr("Projekt aktuell · Browser-Sicherung aktiv","Project current · browser backup active"):
      tr("Im Browser gesichert · Projektdatei ggf. aktualisieren","Saved in browser · project file may need updating"));
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
  }catch(e){
    try{window.MIBR_menu.set(old.menu);window.MIBR_setHardware(old.vehicle);window.MIBR_views.set(old.viewProfiles)}catch(ignored){}
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
function fallbackZip(text){
  download("mibr-sd-menu.zip",zipFiles([{path:"mibr-menu/mibr-menu.txt",text:text}]),"application/zip");
  status(tr("ZIP-Download gestartet. Ordner mibr-menu auf die SD-Karte entpacken; keine View-Profile enthalten.","ZIP download started. Extract mibr-menu to SD card; view profiles excluded."));
}
async function sdExport(){
  var text;
  try{text=nativeFile()}catch(e){status(e.message,true);return}
  if(typeof window.showDirectoryPicker!=="function"){
    if(window.confirm(tr("Direkter Ordnerzugriff nicht verfügbar. ZIP mit /mibr-menu/mibr-menu.txt herunterladen?","No direct folder access. Download a ZIP with /mibr-menu/mibr-menu.txt?")))fallbackZip(text);
    return;
  }
  try{
    var root=await window.showDirectoryPicker({mode:"readwrite",id:"mibr-sd"});
    if(!window.confirm(tr("Bitte bestätigen: gewählter Ordner ist das SD-Karten-Stammverzeichnis. Nur mibr-menu/mibr-menu.txt wird geschrieben.","Confirm: the selected folder is the SD-card root. Only mibr-menu/mibr-menu.txt will be written.")))return;
    var folder=await root.getDirectoryHandle("mibr-menu",{create:true}),found=null;
    try{found=await folder.getFileHandle("mibr-menu.txt")}catch(e){if(e.name!=="NotFoundError")throw e}
    if(found&&!window.confirm(tr("Die Menüdatei ist vorhanden. Überschreiben?","Menu file exists. Overwrite?")))return;
    var handle=found||await folder.getFileHandle("mibr-menu.txt",{create:true});
    var writer=await handle.createWritable();
    try{await writer.write(text);await writer.close()}catch(e){try{await writer.abort()}catch(ignored){}throw e}
    status(tr("SD-Datei geschrieben: /mibr-menu/mibr-menu.txt · View-Profile nicht enthalten","SD file written: /mibr-menu/mibr-menu.txt · view profiles excluded"));
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
function labels(){
  $("projectLoad").textContent=tr("Projekt laden","Load project");
  $("projectSave").textContent=tr("Projekt speichern","Save project");
  $("sdExport").textContent=tr("Auf SD-Karte exportieren","Export to SD card");
}
$("projectLoad").addEventListener("click",function(){$("projectFileIn").value="";$("projectFileIn").click()});
$("projectFileIn").addEventListener("change",function(){readProject(this.files&&this.files[0])});
$("projectSave").addEventListener("click",saveProject);
$("sdExport").addEventListener("click",sdExport);
$("langSeg").addEventListener("click",function(){setTimeout(labels,0)});
["mibr:menuchange","mibr:viewschange","mibr:safechange","mibr:vehiclechange"].forEach(function(name){window.addEventListener(name,schedule)});
try{var raw=localStorage.getItem(STORE);if(raw)applyProject(JSON.parse(raw));else persist()}
catch(e){status(tr("Vorherige Einstellungen erhalten. Projekt-Wiederherstellung gescheitert: ","Previous settings preserved. Project restore failed: ")+e.message,true)}
labels();
window.MIBR_project={capture:capture,validate:validate,apply:applyProject,nativeFile:nativeFile,zipFiles:zipFiles};
})();
