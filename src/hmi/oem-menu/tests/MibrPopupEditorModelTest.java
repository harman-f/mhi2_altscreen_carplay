package de.mibr.hmi;

/** Host reducer checks only. Native rendering/touch require a later vehicle run. */
public final class MibrPopupEditorModelTest {
    private static void check(boolean b,String message){if(!b)throw new AssertionError(message);}
    private static int index(String key){
        for(int i=0;i<MibrSettingsCatalog.KEYS.length;i++)if(key.equals(MibrSettingsCatalog.KEYS[i]))return i;
        throw new AssertionError(key);
    }
    public static void main(String[] args){
        MibrPopupEditorModel model=new MibrPopupEditorModel();
        int visible=0,hidden=0;
        for(int i=0;i<MibrSettingsCatalog.KEYS.length;i++){
            if(MibrPopupEditorModel.visible(i))visible++;else hidden++;
        }
        check(visible==9&&hidden==39&&MibrSettingsCatalog.KEYS.length==48,"9/39/48 filter");
        int view=index("viewarea.selected"),surface=index("navigation.surface"),fps=index("maxFPS");
        check(!model.open(view),"missing donor fails closed"); model.setAvailable(true);
        check(!model.directToggle(view) && !model.liveViewGated(view) && model.open(view),
              "r14 view dropdown (Voll/Wide) opens: live TEMP index, saved like the navigation values");model.cancel();
        check(model.options(view).length==3 && "2".equals(model.options(view)[0]) &&
              "1".equals(model.options(view)[1]) && "0".equals(model.options(view)[2]),"Center, Voll, Wide wire order");
        check(model.options(fps).length==2&&"30".equals(model.options(fps)[0])&&"60".equals(model.options(fps)[1]),
              "FPS menu exposes only the approved paired presets");
        check(model.label(fps,"30").indexOf("20")>=0&&model.label(fps,"60").indexOf("180")>=0,
              "FPS labels identify paired keyframe cadence");
        int[] keys={surface,fps};int[] counts={3,2};
        for(int k=0;k<keys.length;k++){
            int key=keys[k];check(model.options(key).length==counts[k],"complete option count");
            check(model.selectedOption(key)==-1,"UNKNOWN has no selected radio");
            for(int n=0;n<counts[k];n++){
                check(model.open(key),"open");check(model.choose(n),"choose all options including fourth");
                check(model.opened()==-1&&model.selectedOption(key)==n,"closed and draft retained");
                check(model.current(key)==null,"draft cannot become CURRENT");
            }
        }
        String[] tri={"navigation.ETA","navigation.speedLimit","navigation.compass"};
        for(int k=0;k<tri.length;k++){
            String[] values=model.options(index(tri[k]));
            check(values.length==3&&"yes".equals(values[0])&&"no".equals(values[1])&&"user".equals(values[2]),"exact tristate");
            check(model.label(index(tri[k]),"user").indexOf("Automatic")<0,"no Automatic alias");
        }
        // r8: navigation.url is hidden from the HMI but its native readback is kept.
        int url=index("navigation.url");model.readback(url,"auto");
        check(!MibrPopupEditorModel.visible(url)&&!model.open(url)&&model.draft(url)==null,"hidden URL never editable");
        check("auto".equals(model.current(url)),"hidden native snapshot row still read back");
        int src=index("sourceVersion");
        check(model.open(src)&&!model.choose(2),"no fabricated third source version");model.cancel();
        check(model.open(src)&&model.choose(1)&&model.valueText(src).indexOf("DRAFT:")==0,"draft provenance");
        int enabled=index("carplay.enabled");
        int compass=index("navigation.compass");
        check(!model.directToggle(enabled) && !model.liveViewGated(enabled) && !model.directToggle(view) &&
              model.directToggle(compass) && model.directToggle(index("navigation.ETA")) &&
              model.directToggle(index("navigation.speedLimit")),"r23: yes/no checkboxes, carplay dropdown is the runtime pause");
        check(!model.open(compass) && model.toggle(compass) && "yes".equals(model.draft(compass)),"compass ON from unknown");
        check(model.toggle(compass) && "no".equals(model.draft(compass)),"compass OFF");
        model.readback(compass,"user");
        check(!model.checked(compass,"user"),"App-Vorgabe shows unchecked");
        check(MibrPopupEditorModel.saveAllowed(compass) && MibrPopupEditorModel.saveAllowed(index("navigation.maneuver")) &&
              MibrPopupEditorModel.saveAllowed(index("maxFPS")) && MibrPopupEditorModel.saveAllowed(enabled) &&
              MibrPopupEditorModel.saveAllowed(view),
              "save allowlist = navigation keys + Ansicht");
        check(!model.toggle(view) && model.draft(view)==null,
              "view dropdown is a choice, never a toggle");
        check(model.current(view)==null,"no viewarea effective readback inferred");
        model.readback(view,"1");
        check("1".equals(model.current(view)) && model.draft(view)==null,
              "readback shown, no draft");
        check(model.open(view) && model.choose(2) && "0".equals(model.draft(view)),"choose Wide (third entry)");model.cancel();
        check("Voll".equals(model.label(view,"1")) || "Full".equals(model.label(view,"1")),
              "neutral view index label until Center/Full mapping is proven");
        check(model.open(enabled)&&!model.toggle(enabled)&&model.draft(enabled)==null,"carplay.enabled opens as a dropdown");model.cancel();
        for(int i=0;i<MibrSettingsCatalog.KEYS.length;i++)if(!MibrPopupEditorModel.visible(i))check(!model.open(i),"hidden not editable");
        int[] widths={420,865,1280},heights={350,500,640},counts2={2,3,4,20,128};
        for(int a=0;a<widths.length;a++)for(int n=0;n<counts2.length;n++){
            MibrPopupEditorModel.Bounds b=new MibrPopupEditorModel.Bounds(widths[a],heights[a],heights[a]-20,counts2[n],96);
            check(b.x>=0&&b.y>=0&&b.x+b.width<=widths[a]&&b.y+b.height<=heights[a],"popup clamped");
            check(b.scroll==(counts2[n]*b.rowHeight>b.height-24),"all choices remain in bounded scroll");
        }
        model.open(surface);model.setAvailable(false);
        check(model.opened()==-1&&!model.open(surface)&&!model.toggle(enabled),"donor loss cancels and disables");
        check("60".equals(model.draft(fps)),"last local maxFPS draft");
        model.confirmTemp(fps,"60");
        check(model.draft(fps)==null && model.isTempConfirmed(fps) &&
              "60".equals(model.current(fps)),"only verified TEMP result clears draft");
        model.detach();check(model.draft(fps)==null&&model.draft(enabled)==null,"detach clears drafts");
        model.setAvailable(true);check(!model.toggle(view),
            "new lifecycle: view is not a toggle");model.cancel();
        System.out.println("MIBR_POPUP_EDITOR_MODEL_PASS 9_visible 39_hidden 48_retained draft_only no_effective_write");
    }
}
