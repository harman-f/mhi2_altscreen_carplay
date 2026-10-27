package de.mibr.hmi;

import de.vw.mib.animation.animations.KeyframeAnimation;
import de.vw.mib.animation.easing.EasingParams;
import de.vw.mib.datapool.LocalListItemControl;
import de.vw.mib.graphics.Color;
import de.vw.mib.graphics.Gradient;
import de.vw.mib.graphics.Insets;
import de.vw.mib.graphics.Point;
import de.vw.mib.graphics.Rectangle;
import de.vw.mib.graphics.image.Image;
import de.vw.mib.widgets.Button;
import de.vw.mib.widgets.DropDown;
import de.vw.mib.widgets.DropDownButton;
import de.vw.mib.widgets.InactiveArea;
import de.vw.mib.widgets.ListItem;
import de.vw.mib.widgets.StaticImage;
import de.vw.mib.widgets.TextArea;
import de.vw.mib.widgets.WidgetList;
import de.vw.mib.widgets.controller.DefaultDropDownButtonController;
import de.vw.mib.widgets.controller.DefaultInactiveAreaController;
import de.vw.mib.widgets.controller.DefaultListItemController;
import de.vw.mib.widgets.controller.DefaultPushButtonController;
import de.vw.mib.widgets.controller.DefaultWidgetListController;
import de.vw.mib.widgets.event.OutEventAdapter;
import de.vw.mib.widgets.models.AbstractButtonModel;
import de.vw.mib.widgets.models.ListItemModel;
import de.vw.mib.widgets.models.TextAreaModel;
import de.vw.mib.widgets.models.ViewModel;
import de.vw.mib.widgets.models.WidgetModel;
import de.vw.mib.widgets.list.ListItemTransfer;
import de.vw.mib.widgets.ui.DropDownButtonUI;
import de.vw.mib.widgets.ui.DropDownUI;
import de.vw.mib.widgets.ui.ContainerUI;
import de.vw.mib.widgets.ui.ListItemUI;
import de.vw.mib.widgets.ui.StaticImageUI;
import de.vw.mib.widgets.ui.WidgetListUI;
import java.util.Vector;

/** One owned popup. No factory13/14 hook, OEM event mapping or pooled clones. */
public final class MibrNativeDropdownEditor {
    public interface Sink { void changed(); void committed(int index); }
    public interface RowSink { void pressed(DropDownButton button); void released(); }
    private final MibrPopupEditorModel model;
    private final Sink sink;
    private final ViewModel view;
    private final TextAreaModel textStyle;
    private final MibrOemDropdownStyle style;
    private final int width, height;
    private DropDown popup;
    private InactiveArea inactive;
    private WidgetList options;
    private DropDownButton opener;
    private DefaultDropDownButtonController openerController;
    private boolean popupInitStarted, inactiveInitStarted, activated;
    private ListItem[] items;
    private OutEventAdapter[] itemEvents;
    private final OutEventAdapter events = new OutEventAdapter() {
        public void outHMIEventFired(String event) {
            if ("dropDownClosed".equals(event)) cancelAfterNativeDispatch(model);
        }
    };

    private static void cancelAfterNativeDispatch(final MibrPopupEditorModel model) {
        final int token=model.operationToken();
        // OEM automatic close may precede the option's buttonReleased callback.
        de.vw.mib.widgets.internal.ServiceManager.eventDispatcher.invoke(new Runnable(){
            public void run(){model.cancelIfOperation(token);}
        });
    }

    public MibrNativeDropdownEditor(ViewModel view, TextAreaModel textStyle,
            MibrPopupEditorModel model, Sink sink, int width, int height) {
        this.view=view; this.textStyle=textStyle; this.model=model; this.sink=sink;
        this.width=width; this.height=height; style=MibrOemDropdownStyle.resolve();
        model.setAvailable(style!=null && textStyle!=null && textStyle.get_font()!=null);
    }
    public boolean available() { return model.available(); }

    /** Allocate an uninitialized owned opener; host initializes it exactly once. */
    public DropDownButton createOpener(String name,int id,int x,int y,int w,int h,final RowSink row) {
        final DropDownButton b=new DropDownButton();
        b.init(false,255,true,null,true,h,true,name,id,new Insets(),true,w,x,y);
        b.set_interactive(true); b.set_openDropDown(false);
        b.setController(new DefaultDropDownButtonController()); b.setUI(new DropDownButtonUI());
        b.getController().addOutEventListener(new OutEventAdapter(){
            public void outHMIEventFired(String event) {
                if("pressed".equals(event)) row.pressed(b);
                else if("released".equals(event)) row.released();
            }
        });
        if (style!=null) {
            StaticImage arrow=image(name+"Arrow",id-100,w-52,(h-40)/2,40,40);
            style.bind(b,false); b.set_imageStateRef(arrow); b.setChildren(new WidgetModel[]{arrow});
        }
        return b;
    }
    private StaticImage image(String name,int id,int x,int y,int w,int h) {
        StaticImage image=new StaticImage();
        // Exact donor images and state colours are assigned by the native Button.
        image.init(true,255,true,Color.WHITE,0,Color.WHITE,false,new EasingParams[0],true,
            Color.WHITE,0,false,new Gradient(),new Color[0],h,null,true,name,id,new Insets(),true,w,x,y);
        image.setUI(new StaticImageUI()); return image;
    }
    /** Prepare on native pressed; the controller opens once on subsequent release. */
    public void prepare(DropDownButton button,int index) {
        if(opener==button && popup!=null && popup.is_visible())return;
        close();
        if (!model.open(index)) return;
        opener=button; openerController=(DefaultDropDownButtonController)button.getController();
        try {
            String[] values=model.options(index);
            int fontSize=textStyle.get_font().getSize();
            Insets padding=textStyle.get_padding();
            int labelWidth=width-24-24-84-(padding==null?0:padding.left+padding.right);
            if(labelWidth<fontSize)throw new IllegalStateException("DROPDOWN_LABEL_BOUNDS");
            int rowHeight=72;
            for(int v=0;v<values.length;v++){
                // Conservative Latin glyph bound; all current option labels are Latin.
                int lines=(model.label(index,values[v]).length()*fontSize+labelWidth-1)/labelWidth;
                int textHeight=lines*(fontSize+Math.max(0,textStyle.get_lineSpacing()))+
                    (padding==null?0:padding.top+padding.bottom)+18;
                rowHeight=Math.max(rowHeight,textHeight);
            }
            MibrPopupEditorModel.Bounds b=new MibrPopupEditorModel.Bounds(width,height,button.get_y(),values.length,rowHeight);
            options=new WidgetList();
            Insets zero=new Insets();
            // Ssm_5458 native WidgetList ABI; fixed owned masters, one item each.
            options.init(true,0,0,255,128,128,null,false,true,0,true,null,false,false,null,zero,false,
                new EasingParams[0],true,-1,0,0,new ListItemModel[0],false,0,120,b.height-24,true,
                values.length,b.rowHeight,false,new Point[0],new KeyframeAnimation[0],true,null,false,
                0,null,false,null,true,500,false,"MibrChoices",false,0,zero,255,null,0,false,0,
                3,-1,new Image[0],new Insets[0],0,0,0,0,0,-8100,zero,true,b.width-24,12,12);
            options.setController(new DefaultWidgetListController()); options.setUI(new WidgetListUI());
            options.setListItemTransfer(new ListItemTransfer(){
                public boolean transferData(ListItemModel item,int first,int second){return true;}
            });
            WidgetModel[] rows=new WidgetModel[values.length];
            items=new ListItem[values.length]; itemEvents=new OutEventAdapter[values.length];
            for(int i=0;i<rows.length;i++) rows[i]=option(index,i,values[i],b.width-24,b.rowHeight);
            options.setChildren(rows);
            popup=new DropDown();
            popup.init(true,255,null,false,true,false,0,0,0,new Color[0],style.background,1,options,
                new EasingParams[0],true,new int[0],new int[0],new Image[0],0,b.height,
                new KeyframeAnimation[0],true,0,null,false,"MibrChoicePopup",255,null,0,false,0,-8101,
                zero,false,b.width,b.x,b.y,0);
            popup.setUI(new DropDownUI()); popup.setChildren(new WidgetModel[]{options});
            inactive=new InactiveArea();
            inactive.init(false,255,true,null,true,height,true,"MibrChoiceOutside",-8102,zero,false,width,0,0);
            inactive.set_exclusionArea(new Rectangle(b.x,b.y,b.width,b.height));
            inactive.setController(new DefaultInactiveAreaController()); inactive.setUI(new ContainerUI());
            // Host adds the two roots, then one recursive init per root. No child double-init.
            attachRoots();
            popupInitStarted=true; popup.init(view);
            inactiveInitStarted=true; inactive.init(view);
            if (view.is_activated()) { activated=true; popup.activate(); inactive.activate(); }
            button.set_dropDownRef(popup); button.set_inactiveAreaRef(inactive);
            button.set_openDropDown(true); button.getController().addOutEventListener(events);
        } catch(Throwable failure) {
            close(); model.setAvailable(false);
            System.err.println("MIBR_DROPDOWN_OPEN_FAILED " + failure); sink.changed();
        }
    }
    private ListItem option(final int catalog,final int rank,String value,int w,int h) {
        Button button=MibrOwnedWidgets.createTouchButton(null,null,"MibrOptionButton"+rank,-8200-rank,0,0,w,h);
        // Preserve native ListItem -> buttonReleased(index) propagation.
        button.setController(new DefaultPushButtonController());
        StaticImage dot=image("MibrRadio"+rank,-8300-rank,8,(h-52)/2,52,52);
        TextArea label=MibrOwnedWidgets.createLabel(null,textStyle,model.label(catalog,value),
            "MibrOptionLabel"+rank,-8400-rank,72,4,w-84,h-8);
        label.set_lineBreakMode(TextAreaModel.LINEBREAKMODE_CHARACTER); label.set_shorten(false);
        style.bind(button,true); button.set_imageStateRef(dot);
        button.setChildren(new WidgetModel[]{dot,label});
        button.set_textAreaRefs(new TextAreaModel[]{label});
        // Native option radio uses activated state (ListItem.activatedIndex), not focus selection.
        button.set_activated(rank==model.selectedOption(catalog));
        ListItem item=new ListItem();
        Insets z=new Insets(); AbstractButtonModel[] refs=new AbstractButtonModel[]{button};
        item.init(true,refs,rank==model.selectedOption(catalog)?0:-1,255,null,false,0.0f,true,z,0,0,false,z,
            0,null,0,0,z,null,new EasingParams[0],new WidgetModel[0],true,new boolean[0],h,
            new KeyframeAnimation[0],true,null,-1,true,"MibrOption"+rank,null,null,0L,
            0.0f,0.0f,0.0f,10000.0f,60.0f,1.0f,0,255,null,0,false,0.0f,0.0f,0.0f,1.0f,1.0f,1.0f,
            true,refs,new ListItemModel[0],-8500-rank,z,true,w,0,0,0);
        item.setController(new DefaultListItemController()); item.setUI(new ListItemUI());
        item.setChildren(new WidgetModel[]{button}); item.setListItemControl(new LocalListItemControl(1));
        itemEvents[rank]=new OutEventAdapter(){
            public void outListItemEventFired(String event,int absolute,int action,int destination,int dropdown,String sender,long object) {
                if ("buttonReleased".equals(event) && model.choose(rank)) {
                    // Leave hidden roots alive until the next user action/detach:
                    // this ListItem is still on the native event dispatch stack.
                    openerController.fire_closeDropDown(); sink.committed(catalog); sink.changed();
                }
            }
        };
        item.getController().addOutEventListener(itemEvents[rank]); items[rank]=item;
        return item;
    }
    private void attachRoots() {
        de.vw.mib.widgets.models.ContainerModel host=(de.vw.mib.widgets.models.ContainerModel)opener.getParent();
        WidgetModel[] old=host.getChildren(), next=new WidgetModel[old.length+2];
        System.arraycopy(old,0,next,0,old.length); next[old.length]=inactive; next[old.length+1]=popup;
        host.setChildren(next);
    }
    private void removeRoots() {
        if(opener==null || !(opener.getParent() instanceof de.vw.mib.widgets.models.ContainerModel))return;
        de.vw.mib.widgets.models.ContainerModel host=(de.vw.mib.widgets.models.ContainerModel)opener.getParent();
        WidgetModel[] old=host.getChildren(); int n=0;
        for(int i=0;i<old.length;i++)if(old[i]!=popup&&old[i]!=inactive)n++;
        WidgetModel[] next=new WidgetModel[n];n=0;
        for(int i=0;i<old.length;i++)if(old[i]!=popup&&old[i]!=inactive)next[n++]=old[i];
        host.setChildren(next);
    }
    public boolean isOpen() { return model.opened()>=0; }
    public void close() {
        // Native close must run while opener and both references still exist.
        if(openerController!=null)try{openerController.fire_closeDropDown();}catch(Throwable t){
            System.err.println("MIBR_DROPDOWN_CLOSE_FAILED "+t);
        }
        if(opener!=null) {
            opener.getController().removeOutEventListener(events);
            opener.set_openDropDown(false); opener.set_dropDownRef(null); opener.set_inactiveAreaRef(null);
        }
        removeRoots();
        if(items!=null)for(int i=0;i<items.length;i++)if(items[i]!=null)
            items[i].getController().removeOutEventListener(itemEvents[i]);
        if(activated){try{popup.deActivate();}catch(Throwable ignored){}try{inactive.deActivate();}catch(Throwable ignored){}}
        if(popupInitStarted)try{popup.deInit();}catch(Throwable t){System.err.println("MIBR_DROPDOWN_DISPOSE_FAILED "+t);}
        if(inactiveInitStarted)try{inactive.deInit();}catch(Throwable t){System.err.println("MIBR_DROPDOWN_DISPOSE_FAILED "+t);}
        popup=null; inactive=null; options=null; opener=null; openerController=null; items=null; itemEvents=null;
        popupInitStarted=false; inactiveInitStarted=false; activated=false;
        model.cancel();
    }
    public void detach() { close(); model.detach(); }

    /** Uses the separately loaded Ssm's actual native popup and clone master. */
    public static final class StockBinding implements ListItemTransfer {
        private final MibrOemSsmTemplate.Binding stock;
        private final MibrPopupEditorModel model;
        private final Sink sink;
        private final ListItemTransfer originalTransfer;
        private final Vector listeners=new Vector();
        private DropDownButton opener;
        private DefaultDropDownButtonController controller;
        private int rowHeight;
        private final int originalPopupHeight,originalPopupY,originalOptionsHeight;
        // Auto-close may precede the native option's buttonReleased. Reject a
        // stale operation token before cleanup and original geometry restore.
        private void restoreAfterNativeDispatch(){
            final int token=model.operationToken();
            de.vw.mib.widgets.internal.ServiceManager.eventDispatcher.invoke(new Runnable(){
                public void run(){if(model.operationToken()==token)close();}
            });
        }
        private final OutEventAdapter closed=new OutEventAdapter(){
            public void outHMIEventFired(String event){
                if("dropDownClosed".equals(event))restoreAfterNativeDispatch();
            }
        };
        public StockBinding(MibrOemSsmTemplate.Binding stock,MibrPopupEditorModel model,Sink sink) {
            this.stock=stock;this.model=model;this.sink=sink;
            originalTransfer=stock.options.getListItemTransfer();
            originalPopupHeight=stock.popup.get_height();
            originalPopupY=stock.popup.get_y();
            originalOptionsHeight=stock.options.get_height();
            model.setAvailable(MibrOemDropdownStyle.resolve()!=null);
            stock.options.setListItemTransfer(this);
        }
        public void prepare(DropDownButton button,int key) {
            close();
            if(button.get_dropDownRef()!=stock.popup || button.get_inactiveAreaRef()==null ||
                    !(button.getController() instanceof DefaultDropDownButtonController))
                throw new IllegalStateException("MIBR_SSM_DROPDOWN_REFERENCE_MISMATCH");
            if(!model.open(key))return;
            opener=button;controller=(DefaultDropDownButtonController)button.getController();
            button.getController().addOutEventListener(closed);
            TextArea sample=(TextArea)MibrOemSsmTemplate.target(stock.option,
                MibrOemSsmTemplate.OPTION_TEXT_TARGET_ID,TextArea.class);
            rowHeight=stock.option.get_height(); // Stock option geometry, not text-derived
            String[] values=model.options(key);
            // A closed popup can be shorter than its hidden option list. Match
            // native frame sizing from LayoutAttribs, not those two heights.
            de.vw.mib.properties.values.LayoutAttribs insets=stock.popup.get_layoutAttribs();
            int chrome=MibrDropdownFrame.chrome(insets==null?0:insets.getInsetTop(),
                insets==null?0:insets.getInsetBottom());
            int available=stock.view.get_height()-24-chrome;
            if(sample.get_font()==null || sample.get_width()<=0 || rowHeight<=0 ||
               values.length==0 || chrome<0 || available<rowHeight || stock.popup.get_width()<=0 ||
               stock.popup.get_width()>stock.view.get_width())
                throw new IllegalStateException("MIBR_SSM_OPTION_VIEW_BOUNDS");
            int visibleRows=MibrDropdownFrame.rows(stock.view.get_height(),rowHeight,values.length,chrome);
            int height=visibleRows*rowHeight+chrome;
            stock.popup.set_height(height);
            stock.popup.set_y(Math.max(12,Math.min(originalPopupY,stock.view.get_height()-height-12)));
            stock.options.set_height(visibleRows*rowHeight);
            MibrHomeList.replaceOwnedSsmItems(stock.options,stock.view,new WidgetModel[0]);
            stock.option.set_activatedIndex(model.selectedOption(key));
            stock.option.setListItemControl(new LocalListItemControl(values.length));
            MibrHomeList.replaceOwnedSsmItems(stock.options,stock.view,new WidgetModel[]{stock.option});
            button.set_openDropDown(true);
        }
        public boolean transferData(final ListItemModel item,int ignored,int local) {
            int rank=item.getAbsoluteIndex();
            int key=model.opened();
            if(key<0 || rank<0 || rank>=model.options(key).length)return false;
            TextArea label=(TextArea)MibrOemSsmTemplate.target((WidgetModel)item,
                MibrOemSsmTemplate.OPTION_TEXT_TARGET_ID,TextArea.class);
            label.set_text(model.label(key,model.options(key)[rank]));
            // Preserve OEM font, width, button and row heights; allow native ellipsis.
            label.set_shorten(true);
            item.set_activatedIndex(model.selectedOption(key));
            boolean found=false;
            for(int i=0;i<listeners.size();i++)if(((OptionListener)listeners.elementAt(i)).item==item)found=true;
            if(!found){OptionListener event=new OptionListener(item);listeners.addElement(event);
                item.getController().addOutEventListener(event);}
            return true;
        }
        private final class OptionListener extends OutEventAdapter {
            final ListItemModel item;
            OptionListener(ListItemModel item){this.item=item;}
            public void outListItemEventFired(String event,int absolute,int a,int b,int c,String sender,long object){
                int index=model.opened();
                if("buttonReleased".equals(event) && index>=0 && model.choose(item.getAbsoluteIndex())) {
                    if(controller!=null)controller.fire_closeDropDown();
                    // A committed option also needs cleanup if its earlier
                    // native close callback was superseded by model.cancel().
                    restoreAfterNativeDispatch();
                    sink.committed(index);
                    sink.changed();
                }
            }
        }
        public boolean isOpen(){return model.opened()>=0;}
        public void close(){
            try{if(controller!=null)controller.fire_closeDropDown();}
            finally{
                if(opener!=null && opener.getController()!=null)opener.getController().removeOutEventListener(closed);
                for(int i=0;i<listeners.size();i++){OptionListener event=(OptionListener)listeners.elementAt(i);
                    if(event.item.getController()!=null)event.item.getController().removeOutEventListener(event);}
                listeners.removeAllElements();opener=null;controller=null;model.cancel();
                stock.popup.set_height(originalPopupHeight);
                stock.popup.set_y(originalPopupY);
                stock.options.set_height(originalOptionsHeight);
            }
        }
        public void detach(){try{close();}finally{stock.options.setListItemTransfer(originalTransfer);}}
    }
}