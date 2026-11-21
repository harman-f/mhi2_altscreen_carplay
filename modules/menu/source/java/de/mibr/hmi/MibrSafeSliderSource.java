package de.mibr.hmi;

import de.vw.mib.animation.animations.KeyframeAnimation;
import de.vw.mib.animation.easing.EasingParams;
import de.vw.mib.graphics.Color;
import de.vw.mib.graphics.Gradient;
import de.vw.mib.graphics.Insets;
import de.vw.mib.graphics.Point;
import de.vw.mib.graphics.image.Image;
import de.vw.mib.hmi.internal.ServiceManagerCommon;
import de.vw.mib.properties.values.LayoutAttribs;
import de.vw.mib.skin.SkinAnimationPool;
import de.vw.mib.skin.SkinImagePool;
import de.vw.mib.widgets.Button;
import de.vw.mib.widgets.Container;
import de.vw.mib.widgets.ListItem;
import de.vw.mib.widgets.Slider;
import de.vw.mib.widgets.StaticImage;
import de.vw.mib.widgets.TextArea;
import de.vw.mib.graphics.font.FontAttribs;
import de.vw.mib.widgets.ui.TextAreaUI;
import de.vw.mib.widgets.controller.DefaultListItemController;
import de.vw.mib.widgets.controller.DefaultPushButtonController;
import de.vw.mib.widgets.controller.DefaultSliderController;
import de.vw.mib.widgets.interfaces.WidgetCloneData;
import de.vw.mib.widgets.interfaces.WidgetCloneFactory;
import de.vw.mib.widgets.interfaces.WidgetCloneable;
import de.vw.mib.widgets.models.AbstractButtonModel;
import de.vw.mib.widgets.models.ContainerModel;
import de.vw.mib.widgets.models.ListItemModel;
import de.vw.mib.widgets.models.StaticImageModel;
import de.vw.mib.widgets.models.TextAreaModel;
import de.vw.mib.widgets.models.WidgetModel;
import de.vw.mib.widgets.ui.ButtonUI;
import de.vw.mib.widgets.ui.ContainerUI;
import de.vw.mib.widgets.ui.ListItemUI;
import de.vw.mib.widgets.ui.SliderUI;
import de.vw.mib.widgets.ui.StaticImageUI;
import java.lang.reflect.Field;

/**
 * r15e (owner 2026-11-19, option A): the safe-area slider row is OUR OWN item built from OEM widget classes, the way
 * the OEM tree builder does it (WidgetFactoryImpl type 43 = new Slider(); ControllerFactoryImpl
 * DefaultSliderController / DefaultPushButtonController; SliderUI, ButtonUI, StaticImageUI, ContainerUI, ListItemUI),
 * with init argument lists that match the stock sound-menu row ("SubItem"); skin resources are read by name at
 * runtime (WidgetInit.init* forwards 1:1 to Widget.init).
 *
 * No foreign handler is loaded and the row has NO de.vw.mib.view.internal.CloneData. r15d car log: a Tsmv clone in the
 * Ssm list reached Ssm-generated code that dispatches on CloneData.masterId (Tsmv SubItem 1 == Ssm ConnectionType 1)
 * and AbstractWithServicesViewHandler.cdOf threw "List item border crossing". Our own WidgetCloneData (like the
 * car-proven owned HOME tile, MibrHomeList.createTile) never reaches that code; the owned Ssm list clones our rows
 * through {@link #factory} and its transfer is MibrOwnedSsmRows.
 *
 * Resources: images, easing and keyframes by index from the global skin pools; literal values by NAME from the
 * skin's own generated SkinLiteralPool (read reflectively at runtime, nothing copied). Any missing piece -> FAILED and
 * the page keeps the plain edge rows. Skoda MU1440 P4526 only.
 */
final class MibrSafeSliderSource {
    static final String PROFILE="skoda-mu1440-p4526";
    static final String LITERALS="generated.de.vw.mib.view.internal.SkinLiteralPool";
    /** Owned row id (negative like the owned HOME tile -8800); child ids are the stock Tsmv ones. */
    static final int ROW=-8900;
    static final int CONTAINER=33195449,SLIDER=29388966,DECREASE=126088095,INCREASE=77397852;
    static final int PENDING=0,READY=1,FAILED=2;
    /** Native size of the stock row (Tsmv SubItem 1139 wide, 94 high; -/+ buttons 108 wide). */
    static final int WIDTH=1139,HEIGHT=94,BUTTON=108;

    /** One owned slider row (a list master or one of the list's clones of it). */
    static final class Row {
        final ListItem item;final Slider slider;final Button decrease,increase;
        Row(ListItem item,Slider slider,Button decrease,Button increase){
            this.item=item;this.slider=slider;this.decrease=decrease;this.increase=increase;
        }
    }
    /** Our own clone identity: never a de.vw.mib.view.internal.CloneData. kind: SLIDER_KIND or ITEM_KIND. */
    static final class Data implements WidgetCloneData { final int kind; Data(int kind){this.kind=kind;} }
    static final int SLIDER_KIND=0,ITEM_KIND=1;
    /** r15h: owned header row = stock Tsmv "Item" (label left, mini-slider preview or value right). */
    static final int ITEM_ROW=-8901,ITEM_BUTTON=13202141,ITEM_LABEL=125759675,ITEM_VALUE=94632801,ITEM_PREVIEW=47558440;
    /** Stock Tsmv mini-slider preview arrays 01..09 (resourceIconsGeneralMinisliderSound*, both skins). */
    static final int PREVIEW_FIRST=808,PREVIEW_STEPS=9;
    static final class Item {
        final ListItem item;final Button button;final TextArea label,value;final StaticImage preview;
        Item(ListItem item,Button button,TextArea label,TextArea value,StaticImage preview){
            this.item=item;this.button=button;this.label=label;this.value=value;this.preview=preview;
        }
    }
    Image[] previewImages(int step){return imgs(PREVIEW_FIRST+Math.max(0,Math.min(PREVIEW_STEPS-1,step)));}
    static Item itemParts(ListItem item){
        return new Item(item,(Button)MibrOemSsmTemplate.target(item,ITEM_BUTTON,Button.class),
            (TextArea)MibrOemSsmTemplate.target(item,ITEM_LABEL,TextArea.class),
            (TextArea)MibrOemSsmTemplate.target(item,ITEM_VALUE,TextArea.class),
            (StaticImage)MibrOemSsmTemplate.target(item,ITEM_PREVIEW,StaticImage.class));
    }
    /** A new owned header row, or null (then FAILED). */
    Item createItem(){
        if(state!=READY)return null;
        try{return buildItem();}
        catch(Throwable failure){fail("CREATE_ITEM "+failure);return null;}
    }

    private int state=PENDING;
    private int skin;
    private SkinImagePool images;
    private SkinAnimationPool animations;
    private Class literals;
    private int width=WIDTH;

    MibrSafeSliderSource(){MibrSafeArea.sliderRows=false;}
    int state(){return state;}

    /**
     * Resolve once; true when slider rows may be shown. Never throws.
     * @param rowWidth width of the stock Ssm row, @param skinLoader class loader of the skin view handlers
     */
    boolean resolve(int rowWidth,ClassLoader skinLoader){
        if(state!=PENDING)return state==READY;
        try{
            if(!PROFILE.equals(MibrOemProfiles.current().id()))throw new IllegalStateException("PROFILE_NOT_QUALIFIED");
            int id=ServiceManagerCommon.configurationManager.getCurrentSkinId();
            if(id!=1&&id!=2&&id!=3)throw new IllegalStateException("SKIN_"+id);
            skin=id==2?2:1; // custom skin3 follows skin1, as MibrOemDropdownStyle
            images=ServiceManagerCommon.skinImagePool;
            animations=ServiceManagerCommon.skinAnimationPool;
            if(images==null||animations==null)throw new IllegalStateException("SKIN_POOLS");
            literals=Class.forName(LITERALS,true,skinLoader);
            if(rowWidth>=4*BUTTON)width=rowWidth;
            // Build one row now: a missing literal/image/class fails here, before the page shows slider rows.
            Row probe=build();
            dispose(probe.item);
            Item header=buildItem();
            dispose(header.item);
            previewImages(PREVIEW_STEPS-1);
            state=READY;
            MibrSafeArea.sliderRows=true;
            MibrOemSsmTemplate.diag("MIBR_SAFE_SLIDER_READY kind=owned skin="+id+" width="+width);
            return true;
        }catch(Throwable failure){
            fail("RESOLVE "+failure);
            return false;
        }
    }
    void fail(String why){
        if(state!=FAILED)MibrOemSsmTemplate.diag("MIBR_SAFE_SLIDER_FAILED "+why);
        state=FAILED;MibrSafeArea.sliderRows=false;
    }
    void dispose(){MibrSafeArea.sliderRows=false;if(state==READY)state=FAILED;}

    /** A new owned row, or null (then FAILED). */
    Row create(){
        if(state!=READY)return null;
        try{return build();}
        catch(Throwable failure){fail("CREATE "+failure);return null;}
    }
    /** Clone factory for the owned Ssm list: our rows are rebuilt by us, every other item goes to the stock one. */
    WidgetCloneFactory factory(final WidgetCloneFactory stock){
        return new WidgetCloneFactory(){
            public WidgetCloneable createWidgetCloneable(WidgetCloneable source){
                if(source!=null&&source.getCloneData() instanceof Data){
                    ListItem clone=build0(((Data)source.getCloneData()).kind);
                    if(clone==null)throw new IllegalStateException("MIBR_SAFE_SLIDER_CLONE_UNAVAILABLE");
                    return clone;
                }
                return stock.createWidgetCloneable(source);
            }
            public void destroyWidgetCloneable(WidgetCloneable clone){
                if(clone!=null&&clone.getCloneData() instanceof Data){dispose((WidgetModel)clone);return;}
                stock.destroyWidgetCloneable(clone);
            }
        };
    }
    /** A list clone is built even after a later FAILED (the list may still clone a shown master); null on error. */
    private ListItem build0(int kind){
        if(literals==null)return null;
        try{return kind==ITEM_KIND?buildItem().item:build().item;}catch(Throwable failure){fail("CLONE "+failure);return null;}
    }
    static boolean owned(Object item){
        return item instanceof ListItem&&((ListItem)item).getCloneData() instanceof Data;
    }
    /** Slider and -/+ inside one of our rows (master or list clone). */
    static Row parts(ListItem item){
        WidgetModel container=MibrOemSsmTemplate.target(item,CONTAINER,ContainerModel.class);
        Slider slider=(Slider)MibrOemSsmTemplate.target(container,SLIDER,Slider.class);
        Button dec=(Button)MibrOemSsmTemplate.target(item,DECREASE,Button.class);
        Button inc=(Button)MibrOemSsmTemplate.target(item,INCREASE,Button.class);
        return new Row(item,slider,dec,inc);
    }
    /** Same teardown as an owned HOME tile: children first, never a stock factory. */
    static void dispose(WidgetModel widget){
        if(widget instanceof ContainerModel){
            WidgetModel[] children=((ContainerModel)widget).getChildren();
            for(int i=0;children!=null&&i<children.length;i++)if(children[i]!=null)dispose(children[i]);
            ((ContainerModel)widget).setChildren(new WidgetModel[0]);
        }
        try{widget.deInit();}catch(Throwable ignored){}
    }

    /* ---- the row, argument for argument as Tsmv initContainerWidgetListSubItemCloneData (skin1 | skin2) ---- */

    private Object lit(String name) throws Exception {
        Field f=literals.getField(name);
        Object v=f.get(null);
        if(v==null)throw new IllegalStateException("LITERAL_NULL "+name);
        return v;
    }
    private Insets ins(String n) throws Exception {return (Insets)lit(n);}
    private Color[] colors(String n) throws Exception {return (Color[])lit(n);}
    private LayoutAttribs layout(String n) throws Exception {return (LayoutAttribs)lit(n);}
    private Image img(int i){return images.getImage(i);}
    private Image[] imgs(int i){
        Image[] a=images.getImageArray(i);
        if(a==null)throw new IllegalStateException("IMAGE_ARRAY "+i);
        return a;
    }
    private EasingParams[] ease(int i){return animations.getEasingParamsArray(i);}
    private KeyframeAnimation[] keys(int i){return animations.getKeyframeAnimationArray(i);}
    private int s(int one,int two){return skin==2?two:one;}
    private String rowLayout(){return skin==2?"LAYOUT_ATTRIBS_12":"LAYOUT_ATTRIBS_11";}
    private String buttonLayout(){return skin==2?"LAYOUT_ATTRIBS_51":"LAYOUT_ATTRIBS_55";}

    private StaticImage image(String name,int id,int height,Image image,boolean visible,int w,int x,int y,boolean icon)
            throws Exception {
        StaticImage v=new StaticImage();
        v.setUI(new StaticImageUI());
        Color c16=(Color)lit("COLOR_16");
        v.init(true,255,true,c16,0,c16,icon,ease(icon?s(25,26):s(117,125)),true,c16,0,false,(Gradient)lit("GRADIENT_0"),
            colors("COLOR__ARRAY1_47"),height,image,true,name,id,ins("INSETS_18"),visible,w,x,y);
        return v;
    }
    private Container container(String name,int id,int height,String layoutName,int w,int x,int y) throws Exception {
        Container v=new Container();
        v.setUI(new ContainerUI());
        Image none=img(s(686,692));
        v.init(true,255,none,false,true,ease(s(117,125)),true,height,keys(2463),true,layout(layoutName),name,
            255,none,0,false,id,ins("INSETS_18"),true,w,x,y);
        return v;
    }
    private Button button(String name,int id,int stateArray,StaticImageModel background,StaticImageModel icon,int x)
            throws Exception {
        Button v=new Button();
        v.setController(new DefaultPushButtonController());
        v.setUI(new ButtonUI());
        Image none=img(s(686,692));
        Color[] c47=colors("COLOR__ARRAY1_47");
        v.init(false,255,none,false,true,1,c47,c47,ease(s(99,106)),ease(s(89,95)),true,name,colors("COLOR__ARRAY1_22"),
            88,background,null,imgs(s(240,241)),imgs(1365),imgs(stateArray),imgs(1365),colors("COLOR__ARRAY1_10"),icon,null,
            true,keys(2463),true,layout(buttonLayout()),name,false,255,none,0,false,
            500,200,false,800,4000,6,id,(TextAreaModel[])lit("TEXT_AREA_MODEL__ARRAY1_0"),new TextAreaModel[0],
            colors("COLOR__ARRAY1_30"),colors("COLOR__ARRAY1_7"),ins("INSETS_18"),(Point[])lit("POINT__ARRAY1_1"),
            true,BUTTON,x,10);
        return v;
    }

    private Row build() throws Exception {
        int sliderWidth=width-2*BUTTON;
        Image none=img(s(686,692));
        Color[] c47=colors("COLOR__ARRAY1_47");

        StaticImage rowBackground=image("Background",68015711,104,img(76),true,width,0,0,false);
        StaticImage trackBackground=image("Background",76191479,104,img(77),true,sliderWidth,0,0,false);
        StaticImage foreground=image("Foreground",129686901,0,null,false,0,0,0,false);
        StaticImage thumb=image("Slider",56596286,104,null,true,137,164,0,false);

        Slider slider=new Slider();
        slider.setController(new DefaultSliderController());
        slider.setUI(new SliderUI());
        slider.setChildren(new WidgetModel[]{trackBackground,foreground,thumb});
        slider.init(false,255,none,false,true,c47,c47,c47,colors("COLOR__ARRAY1_44"),ease(s(12,13)),ease(s(117,125)),
            true,100,c47,104,null,foreground,(StaticImageModel[])lit("STATIC_IMAGE_MODEL__ARRAY1_0"),null,
            imgs(1365),imgs(1365),thumb,44,40,imgs(1365),imgs(1365),imgs(1365),imgs(s(184,186)),true,keys(2463),true,
            layout(rowLayout()),"Slider",0,60,24,false,255,none,0,false,false,6,1,SLIDER,ins("INSETS_18"),0,false,false,
            0,0,true,sliderWidth,false,BUTTON,0);

        StaticImage decBackground=image("Background",71751718,88,null,true,BUTTON,0,0,false);
        StaticImage decIcon=image("Icon",48915167,52,null,true,BUTTON,0,0,true);
        Container decGlow=container("IconGlowContainer",90393412,52,buttonLayout(),BUTTON,44,24);
        decGlow.setChildren(new WidgetModel[]{decIcon});
        Button decrease=button("ButtonDecrease",DECREASE,690,decBackground,decIcon,0);
        decrease.setChildren(new WidgetModel[]{decBackground,decGlow});

        StaticImage incBackground=image("Background",96013554,88,null,true,BUTTON,0,0,false);
        StaticImage incIcon=image("Icon",117004623,52,null,true,BUTTON,0,0,true);
        Container incGlow=container("IconGlowContainer",92258669,52,buttonLayout(),BUTTON,20,24);
        incGlow.setChildren(new WidgetModel[]{incIcon});
        Button increase=button("ButtonIncrease",INCREASE,707,incBackground,incIcon,width-BUTTON);
        increase.setChildren(new WidgetModel[]{incBackground,incGlow});

        Container box=container("Container",CONTAINER,104,rowLayout(),width,0,-9);
        box.setChildren(new WidgetModel[]{rowBackground,slider,decrease,increase});

        ListItem item=new ListItem();
        item.setController(new DefaultListItemController());
        item.setUI(new ListItemUI());
        item.setChildren(new WidgetModel[]{box});
        item.init(false,new AbstractButtonModel[0],-1,255,none,false,0.0f,true,ins("INSETS_9"),0,0,false,
            ins("INSETS_18"),0,null,0,0,ins("INSETS_18"),null,ease(s(117,125)),new WidgetModel[0],true,new boolean[0],
            HEIGHT,keys(2463),true,layout(rowLayout()),-1,true,"MibrSafeSliderRow",null,null,0L,0.0f,0.0f,0.0f,10000.0f,
            60.0f,1.0f,0,255,none,0,false,0.0f,0.0f,0.0f,1.0f,1.0f,1.0f,false,new AbstractButtonModel[]{slider},
            new ListItemModel[0],ROW,ins(skin==2?"INSETS_52":"INSETS_50"),true,width,0,0,0);
        item.setCloneData(new Data(SLIDER_KIND));
        return new Row(item,slider,decrease,increase);
    }

    /* ---- r15h: header row, argument for argument as Tsmv initContainerWidgetListItemCloneData (skin1 or skin2) ---- */
    private TextArea text(String name,int id,int alignment,boolean visible,int w,int x,int y) throws Exception {
        TextArea v=new TextArea();
        v.setUI(new TextAreaUI());
        Color c0=(Color)lit("COLOR_0"),c16=(Color)lit("COLOR_16");
        Color[] c47=colors("COLOR__ARRAY1_47");
        v.init(true,alignment,0,255,true,0,0,0,c0,c16,c0,c47,c47,c0,0,0,ease(s(94,101)),true,(FontAttribs)lit("FONT_ATTRIBS_19"),
            (int[])lit(skin==2?"INT__ARRAY1_91":"INT__ARRAY1_92"),c16,0,false,47,true,0,53,name,ins("INSETS_18"),true,false,id,"",
            false,ins("INSETS_18"),visible,1,w,x,y);
        return v;
    }
    private Item buildItem() throws Exception {
        Image none=img(s(686,692));
        Color[] c47=colors("COLOR__ARRAY1_47");
        StaticImage scale=image("ScaleImage",59058568,94,null,true,width,0,0,false);
        // skin1: label left, value right; the stock skin2 row is mirrored (label x 235, value x 30)
        TextArea label=text("TextLabel",ITEM_LABEL,skin==2?2:0,true,874,s(30,235),23);
        TextArea value=text("CurrentValue",ITEM_VALUE,skin==2?0:2,false,195,s(914,30),23);
        StaticImage preview=image("Image_Minislider",ITEM_PREVIEW,30,null,false,142,0,0,true);
        Container glow=container("Image_MinisliderGlowContainer",92625219,30,buttonLayout(),142,s(1011,-19),31);
        glow.setChildren(new WidgetModel[]{preview});
        Button button=new Button();
        button.setController(new DefaultPushButtonController());
        button.setUI(new ButtonUI());
        button.setChildren(new WidgetModel[]{scale,label,glow,value});
        button.init(false,255,none,false,true,0,c47,c47,ease(s(99,106)),ease(s(89,95)),false,"Button",colors("COLOR__ARRAY1_22"),
            94,scale,null,imgs(147),imgs(1365),previewImages(0),imgs(1365),colors("COLOR__ARRAY1_10"),preview,null,
            true,keys(2463),true,layout(rowLayout()),"Button",false,255,none,0,false,0,0,false,0,0,6,ITEM_BUTTON,
            (TextAreaModel[])lit("TEXT_AREA_MODEL__ARRAY1_0"),new TextAreaModel[]{label,value},
            colors("COLOR__ARRAY1_30"),colors("COLOR__ARRAY1_7"),ins("INSETS_18"),(Point[])lit("POINT__ARRAY1_1"),
            true,width,0,0);
        button.set_interactive(true);
        ListItem item=new ListItem();
        item.setController(new DefaultListItemController());
        item.setUI(new ListItemUI());
        item.setChildren(new WidgetModel[]{button});
        item.init(true,new AbstractButtonModel[0],-1,255,none,false,0.0f,true,ins("INSETS_18"),0,0,false,
            ins("INSETS_18"),0,null,0,0,ins("INSETS_18"),null,ease(s(117,125)),new WidgetModel[0],false,new boolean[0],
            HEIGHT,keys(2463),true,layout(rowLayout()),-1,true,"MibrSafeEdgeRow",null,null,0L,0.0f,0.0f,0.0f,10000.0f,
            60.0f,1.0f,0,255,none,0,false,0.0f,0.0f,0.0f,1.0f,1.0f,1.0f,true,new AbstractButtonModel[]{button},
            new ListItemModel[0],ITEM_ROW,ins(skin==2?"INSETS_52":"INSETS_50"),true,width,0,0,0);
        item.setCloneData(new Data(ITEM_KIND));
        return new Item(item,button,label,value,preview);
    }
}
