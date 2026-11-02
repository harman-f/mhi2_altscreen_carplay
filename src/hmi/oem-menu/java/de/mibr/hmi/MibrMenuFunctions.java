package de.mibr.hmi;

/** Function ID of the menu file -> row of the popup editor model. */
final class MibrMenuFunctions {
    private MibrMenuFunctions(){}
    private static final Object[][] VIRTUAL={
        {"engine.type",new Integer(MibrPopupEditorModel.ENGINE)},
        {"view.follow",new Integer(MibrPopupEditorModel.VIEW_FOLLOW)},
        {"view.now",new Integer(MibrPopupEditorModel.VIEW_POS)},
        {"view.resync",new Integer(MibrPopupEditorModel.VIEW_RS)},
        {"view.area_voll",new Integer(MibrPopupEditorModel.VIEW_MAP0)},
        {"view.area_wide",new Integer(MibrPopupEditorModel.VIEW_MAP1)},
        {"view.area_center",new Integer(MibrPopupEditorModel.VIEW_MAP4)},
        {"view.sport",new Integer(MibrPopupEditorModel.VIEW_SPORT)},
        {"scaling.main.zoomFactor",new Integer(MibrPopupEditorModel.SCALE_MAIN)},
        {"scaling.cluster.zoomFactor",new Integer(MibrPopupEditorModel.SCALE_CLUSTER)},
        {"scaling.cluster.physicalSize",new Integer(MibrPopupEditorModel.SCALE_PHYSICAL)},
        {"scaling.main.physicalSize",new Integer(MibrPopupEditorModel.SCALE_MAIN_PHYSICAL)},
        {"menu.language",new Integer(MibrPopupEditorModel.MENU_LANGUAGE)},
        {"gps.demo",new Integer(MibrPopupEditorModel.GPS_DEMO)},
        {"carplay_nav",new Integer(MibrPopupEditorModel.CARPLAY_NAV)},
        {"sd_log",new Integer(MibrPopupEditorModel.SD_LOG)},
        {"nav_source",new Integer(MibrPopupEditorModel.NAV_SOURCE)},
        {"nav_display",new Integer(MibrPopupEditorModel.NAV_DISPLAY)},
        {"nav_line",new Integer(MibrPopupEditorModel.NAV_TEXT)},
        {"nav_bottom",new Integer(MibrPopupEditorModel.NAV_BOTTOM)},
        {"nav_side",new Integer(MibrPopupEditorModel.NAV_SIDE)},
        {"nav_lanes",new Integer(MibrPopupEditorModel.NAV_LANES)},
        {"nav_night",new Integer(MibrPopupEditorModel.NAV_NIGHT)},
        {"nav_demo",new Integer(MibrPopupEditorModel.NAV_DEMO)},
        {"expert.mode",new Integer(MibrPopupEditorModel.EXPERT_MODE)},
        {"calib.image",new Integer(MibrPopupEditorModel.CALIB_IMAGE)},
    };
    private static final String[] SAFE={"safe_voll.","safe_wide.","safe_center."};
    private static final String[] SAFE_FIELDS={"x","y","w","h","reset"};

    /** The row, or -1 for an ID without a function in this build. */
    static int key(String id){
        for(int i=0;i<VIRTUAL.length;i++)
            if(id.equals(VIRTUAL[i][0]))return ((Integer)VIRTUAL[i][1]).intValue();
        for(int a=0;a<SAFE.length;a++)for(int f=0;f<SAFE_FIELDS.length;f++)
            if(id.equals(SAFE[a]+SAFE_FIELDS[f]))return MibrPopupEditorModel.SAFE_FIRST+5*a+f;
        for(int i=0;i<MibrSettingsCatalog.KEYS.length;i++)
            if(id.equals(MibrSettingsCatalog.KEYS[i]))return i;
        return -1;
    }
}
