package de.mibr.hmi;

import de.vw.mib.graphics.Color;
import de.vw.mib.graphics.Color4b;
import de.vw.mib.graphics.image.Image;
import de.vw.mib.hmi.internal.ServiceManagerCommon;
import de.vw.mib.skin.SkinImagePool;
import de.vw.mib.widgets.Button;

/** OEM Ssm_5458 bindings: stock skin1/skin2; custom skin3 uses skin1. */
public final class MibrOemDropdownStyle {
    final Image[] background, arrow, radio, buttonBackground;
    final Color[] stateColors, textColors;
    private MibrOemDropdownStyle(Image[] background, Image[] arrow, Image[] radio,
            Image[] buttonBackground, Color[] stateColors, Color[] textColors) {
        this.background=background; this.arrow=arrow; this.radio=radio;
        this.buttonBackground=buttonBackground; this.stateColors=stateColors; this.textColors=textColors;
    }
    public static MibrOemDropdownStyle resolve() {
        try {
            int skin = ServiceManagerCommon.configurationManager.getCurrentSkinId();
            if (skin != 1 && skin != 2 && skin != 3) return null;
            SkinImagePool pool = ServiceManagerCommon.skinImagePool;
            // Stock skin1/skin2 literals; custom skin3 intentionally follows skin1.
            // That pool lives in a separate native skin loader, not the boot JAR.
            Color[] state = stateColors();
            Color[] text = textColors();
            Image[] radio=pool.getImageArray(823), arrow=pool.getImageArray(698);
            Image[] background=pool.getImageArray(skin==2 ? 215 : 213);
            Image[] buttons=pool.getImageArray(147);
            if (radio==null || radio.length<14 || arrow==null || arrow.length<14 ||
                state==null || state.length<14 || text==null || text.length<14 ||
                background==null || background.length==0 || buttons==null) return null;
            return new MibrOemDropdownStyle(background,arrow,radio,buttons,state,text);
        } catch (Throwable unavailable) {
            System.err.println("MIBR_DROPDOWN_STYLE_UNAVAILABLE " + unavailable);
            return null;
        }
    }
    private static Color[] stateColors() {
        Color[] colors=new Color[18];
        for(int i=0;i<colors.length;i++)colors[i]=new Color(new Color4b(i<4?0x4BFFFFFF:-1));
        return colors;
    }
    private static Color[] textColors() {
        Color[] colors=new Color[18];
        for(int i=0;i<colors.length;i++)colors[i]=i<14
            ?new Color(new Color4b(i<4?-9408400:-1))
            :new Color(new Color4b(-14690816),new Color4b(-14690816),new Color4b(-1),new Color4b(-1),true);
        return colors;
    }
    void bind(Button button, boolean option) {
        button.set_imagesBackground(buttonBackground);
        button.set_imagesState(option ? radio : arrow);
        button.set_imageStateColors(stateColors);
        button.set_textColors(textColors);
    }
}