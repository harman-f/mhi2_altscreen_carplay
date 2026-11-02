package de.mibr.hmi;

import de.vw.mib.datapool.LocalListItemControl;
import de.vw.mib.view.internal.AbstractViewHandler;
import de.vw.mib.widgets.Button;
import de.vw.mib.widgets.DropDownButton;
import de.vw.mib.widgets.ListItem;
import de.vw.mib.widgets.models.TextAreaModel;
import de.vw.mib.widgets.TextArea;
import de.vw.mib.widgets.event.OutEventAdapter;
import de.vw.mib.widgets.list.ListItemTransfer;
import de.vw.mib.widgets.models.ListItemModel;
import de.vw.mib.widgets.models.WidgetModel;
import java.util.Vector;

/** Actual independently loaded Ssm rows, title, Back and ConnectionType popup.
 * Every row is a clone of one of the three stock Ssm_5458 masters:
 * SelectDevice (PLAIN), ConnectionType (VALUE/dropdown), ExternalApps (CHECK).
 * Row content is plain OEM presentation: label, value, checkbox state.
 */
final class MibrOwnedSsmRows implements MibrCarPlayMenuModel.View,ListItemTransfer,
        MibrNativeDropdownEditor.Sink {
    private final AbstractViewHandler handler;
    private final MibrOemSsmTemplate.Binding stock;
    private final Runnable leave;
    private final MibrCarPlayMenuModel menu;
    private final MibrPopupEditorModel drafts;
    private final MibrCarPlayMenuModel.Snapshot resume;
    private final MibrNativeDropdownEditor.StockBinding editor;
    private final MibrControlSession control;
    private final MibrV3Session v3;
    private final WidgetModel[] original;
    private final ListItemTransfer originalTransfer;
    private final Vector listeners=new Vector();
    private ListItem[] masters=new ListItem[0];
    private boolean attached=true;
    private boolean detached;
    private boolean scalingPageVisible;
    private boolean advancedPageVisible;
    private int epoch;
    private int lastScreen=-1;
    private int lastGroup=-2,lastPage=-1,lastSelected=-2;
    private String lastTitle;
    private String[] labels=new String[0];

    private static final int PLAIN=0,VALUE=1,CHECK=2;
    private final OutEventAdapter back=new OutEventAdapter(){
        public void outHMIEventFired(String event){if("released".equals(event))queueBack();}
    };

    MibrOwnedSsmRows(AbstractViewHandler handler,MibrOemSsmTemplate.Binding stock,Runnable leave) {
        this(handler,stock,leave,new MibrPopupEditorModel(),null,null);
    }
    MibrOwnedSsmRows(AbstractViewHandler handler,MibrOemSsmTemplate.Binding stock,
                     Runnable leave,MibrPopupEditorModel preserved,
                     MibrCarPlayMenuModel.Snapshot snapshot) {
        this(handler,stock,leave,preserved,snapshot,null,null);
    }
    MibrOwnedSsmRows(AbstractViewHandler handler,MibrOemSsmTemplate.Binding stock,
                     Runnable leave,MibrPopupEditorModel preserved,
                     MibrCarPlayMenuModel.Snapshot snapshot,MibrControlClient client) {
        this(handler,stock,leave,preserved,snapshot,client,null);
    }
    MibrOwnedSsmRows(AbstractViewHandler handler,MibrOemSsmTemplate.Binding stock,
                     Runnable leave,MibrPopupEditorModel preserved,
                     MibrCarPlayMenuModel.Snapshot snapshot,MibrControlClient client,MibrV3Client v3Client) {
        if(preserved==null)throw new IllegalArgumentException("SSM_DRAFT_OWNER_REQUIRED");
        this.handler=handler;this.stock=stock;this.leave=leave;
        drafts=preserved;resume=snapshot;
        original=stock.mainList.getChildren();originalTransfer=stock.mainList.getListItemTransfer();
        menu=new MibrCarPlayMenuModel(this);
        editor=new MibrNativeDropdownEditor.StockBinding(stock,drafts,this);
        control=new MibrControlSession(client,drafts,new Runnable(){
            public void run(){MibrOwnedSsmRows.this.changed();}
        });
        v3=v3Client==null?null:new MibrV3Session(v3Client,drafts,new MibrV3Session.Dispatcher(){
            public void post(Runnable action){later(action);}
        },new Runnable(){public void run(){MibrOwnedSsmRows.this.changed();}});
        stock.mainList.setListItemTransfer(this);
        stock.close.getController().addOutEventListener(back);
        stock.view.set_opaque(true);
    }
    void open(){
        if(resume==null)menu.open();else menu.restore(resume);
        if(v3!=null)v3.open();else control.open();
        startDiagRefresh();
    }
    /** r48: the Diagnose page shows live values (speed, range, counters): re-read the status files every 2 s while it is open. */
    private void startDiagRefresh(){
        Thread t=new Thread(new Runnable(){public void run(){
            while(attached){
                try{Thread.sleep(2000L);}catch(InterruptedException e){return;}
                if(attached && menu.onDiagnostics())changed();
            }
        }},"MibrDiagRefresh");
        t.setDaemon(true);t.start();
    }
    MibrCarPlayMenuModel.Snapshot snapshot(){return menu.snapshot();}
    MibrPopupEditorModel draftOwner(){return drafts;}
    private static void later(Runnable action){
        de.vw.mib.widgets.internal.ServiceManager.eventDispatcher.invoke(action);
    }
    private void failed(Throwable failure){System.err.println("MIBR_SSM_ROWS_FAILED "+failure);later(leave);}
    public void committed(int index){
        // Native option completion, never focus/pressed.
        if(attached && v3!=null){
            if(index==MibrPopupEditorModel.EXPERT_MODE){
                String wish=drafts.draft(index);drafts.discardDraft(index);
                v3.expertSet(wish);
            }else if(index==MibrPopupEditorModel.ENGINE){
                // r47: the engine type is not a registry key: ask the broker (ENGINE_SET) and drop the local wish.
                String wish=drafts.draft(index);drafts.discardDraft(index);
                if(wish!=null)v3.engineSet(wish);
            }else if(index==MibrPopupEditorModel.MENU_LANGUAGE){
                String wish=drafts.draft(index);drafts.discardDraft(index);
                if(wish!=null)v3.menuLanguageSet(wish);
            }else if(MibrPopupEditorModel.durable(index)!=null){
                String wish=drafts.draft(index);drafts.discardDraft(index);
                if(wish!=null)v3.durableSet(index,wish);
            }else if(index==MibrPopupEditorModel.GPS_DEMO){
                String wish=drafts.draft(index);drafts.discardDraft(index);
                if(wish!=null)v3.gpsDemoSet(wish);
            }else if(MibrPopupEditorModel.isScaling(index)){
                String wish=drafts.draft(index);drafts.discardDraft(index);
                if(wish!=null)v3.scaleSet(index,wish);
            }else if(index>MibrPopupEditorModel.ENGINE&&index<MibrPopupEditorModel.SCALE_MAIN&&MibrPopupEditorModel.isVirtual(index)){
                // r55: the view rows are broker settings of the helper script, not registry keys.
                String wish=drafts.draft(index);drafts.discardDraft(index);
                if(wish!=null)v3.viewSet(MibrViewState.NAMES[index-MibrPopupEditorModel.VIEW_FOLLOW],wish);
            }else v3.commit(index);
        }
    }
    public void changed(){later(new Runnable(){public void run(){
        if(attached)try{
            menu.refresh();
        }catch(Throwable failure){failed(failure);}
    }});}
    private void queueBack(){later(new Runnable(){public void run(){
        if(!attached)return;
        try{
            if(editor.isOpen())editor.close();
            else if(menu.screen()==MibrCarPlayMenuModel.CATEGORIES)leave.run();
            else menu.back();
        }catch(Throwable failure){System.err.println("MIBR_SSM_BACK_FAILED "+failure);leave.run();}
    }});}
    public void show(int screen,String title,String[] rows,String detail){
        if(!attached)return;
        boolean onScalingPage=screen==MibrCarPlayMenuModel.ITEMS&&menu.scalingPageOpen();
        boolean enteredScalingPage=onScalingPage&&!scalingPageVisible;
        scalingPageVisible=onScalingPage;
        if(enteredScalingPage&&v3!=null)v3.scaleRefresh();
        boolean inAdvanced=screen==MibrCarPlayMenuModel.ITEMS && menu.pageHas(MibrPopupEditorModel.GPS_DEMO);
        boolean enteredAdvanced=inAdvanced&&!advancedPageVisible;
        advancedPageVisible=inAdvanced;
        if(enteredAdvanced&&v3!=null)v3.gpsDemoRefresh();
        // A DETAIL state must render actual native stock ListItems, not merely a title.
        // The independent long-text/Scrollbar OEM adapter is a later visual gate.
        if(screen==MibrCarPlayMenuModel.DETAIL)rows=MibrElementDetailRows.lines(detail);
        // Diagnostics has no settings keys: one read-only line with the
        // configuration service state. No write action is offered here.
        if(menu.onDiagnostics()){
            String[] withStatus=new String[rows.length+1];
            System.arraycopy(rows,0,withStatus,0,rows.length);
            withStatus[rows.length]=v3==null?control.status():v3.status();
            rows=withStatus;
            // R2: one read-only line for the CarPlay-Navigation (route guidance in the cockpit).
            String[] withNav=new String[rows.length+1];
            System.arraycopy(rows,0,withNav,0,rows.length);
            withNav[rows.length]=MibrRgiCockpit.statusLine();
            rows=withNav;
            String[] withHealth=new String[rows.length+1];
            System.arraycopy(rows,0,withHealth,0,rows.length);
            withHealth[rows.length]=MibrServiceHealth.statusLine();
            rows=withHealth;
        }
        int count=0;for(int i=0;i<rows.length;i++)if(rows[i]!=null)count++;
        // Readback, broker status or local draft must not tear down a native
        // popup, row clones, listeners, scroll position or focus.
        // Page identity includes group/page/key, not only equal title/count.
        boolean stable=screen!=MibrCarPlayMenuModel.HOME &&
            lastScreen==screen && title.equals(lastTitle) &&
            lastGroup==menu.group() && lastPage==menu.page() &&
            lastSelected==menu.selected() && masters.length==count;
        if(stable){
            labels=rows;
            for(int rank=0;rank<count;rank++)apply(masters[rank],rank);
            // Snapshot updates must not tear down the scrollbar's list reference.
            MibrOemSsmTemplate.syncScrollbar(stock,false);
            return;
        }
        boolean preserve=lastScreen==screen && title.equals(lastTitle) && sameRows(labels,rows);
        int selected=stock.mainList.get_selectedIndex(),focused=stock.mainList.getFocusedIndex();
        int first=stock.mainList.getFirstVisibleIndex();
        epoch++;editor.close();clearMasters();labels=rows;
        lastScreen=screen;lastTitle=title;
        lastGroup=menu.group();lastPage=menu.page();lastSelected=menu.selected();
        stock.title.set_text(title);
        if(screen==MibrCarPlayMenuModel.HOME){leave.run();return;}
        masters=new ListItem[count];WidgetModel[] children=new WidgetModel[count];
        for(int rank=0;rank<count;rank++){
            ListItem template=template(menu.keyForRow(rank));
            ListItem item=(ListItem)handler.createWidgetCloneable(template);
            masters[rank]=item;children[rank]=item;
            item.setListItemControl(new LocalListItemControl(1));
            item.set_visible(true);item.set_enabled(true);
            item.init(stock.view);
            if(stock.view.is_activated())item.activate();
            apply(item,rank);
        }
        MibrHomeList.replaceOwnedSsmItems(stock.mainList,stock.view,children);
        stock.mainList.set_selectedIndex(count==0?-1:preserve && selected>=0 && selected<count?selected:0);
        if(preserve){
            if(focused>=0 && focused<count)stock.mainList.setFocusedIndex(focused);
            if(first>=0 && first<count)stock.mainList.snap(first,0);
        }
        // Bind the stock scrollbar only after count, selection, focus and viewport settled.
        MibrOemSsmTemplate.syncScrollbar(stock,true);
        if(count==0 && detail!=null && detail.length()>0)stock.title.set_text(title+MibrI18n.pick(": keine Live-Werte",": no live values"));
    }
    private static boolean sameRows(String[] a,String[] b){
        if(a.length!=b.length)return false;
        for(int i=0;i<a.length;i++)if(a[i]==null?b[i]!=null:!a[i].equals(b[i]))return false;
        return true;
    }
    private void clearMasters(){
        removeListeners();
        MibrHomeList.replaceOwnedSsmItems(stock.mainList,stock.view,new WidgetModel[0]);
        for(int i=0;i<masters.length;i++)if(masters[i]!=null){
            handler.destroyWidgetCloneable(masters[i]);masters[i]=null;
        }
        masters=new ListItem[0];
    }
    public boolean transferData(ListItemModel item,int unused,int local){
        int rank=item.getAbsoluteIndex();
        if(!attached || rank<0 || rank>=labels.length || labels[rank]==null)return false;
        apply(item,rank);return true;
    }
    private ListItem template(int key){
        if(menu.screen()==MibrCarPlayMenuModel.DETAIL || key<0)return stock.plain;
        if(drafts.directToggle(key))return stock.check;
        return stock.value;
    }
    private static int kind(ListItemModel item){
        int id=item.get_targetId();
        return id==MibrOemSsmTemplate.VALUE_TARGET_ID?VALUE:id==MibrOemSsmTemplate.CHECK_TARGET_ID?CHECK:PLAIN;
    }
    private void apply(ListItemModel item,int rank){
        int key=menu.keyForRow(rank),kind=kind(item);
        boolean scalingNotice=menu.noteRow(rank);
        if(key==MibrPopupEditorModel.EXPERT_MODE)drafts.readback(key,MibrExpert.choice());
        else if(key==MibrPopupEditorModel.ENGINE)drafts.readback(key,MibrEngineState.engine());
        else if(key==MibrPopupEditorModel.MENU_LANGUAGE)drafts.readback(key,MibrI18n.menuOverride());
        else if(key==MibrPopupEditorModel.GPS_DEMO)drafts.readback(key,MibrGpsDemoState.choice());
        else if(key==MibrPopupEditorModel.CARPLAY_NAV)drafts.readback(key,MibrDurableSwitch.CARPLAY_NAV.revision()!=null?
            MibrDurableSwitch.CARPLAY_NAV.value():MibrDurableSwitch.CARPLAY_NAV.persistedOn()?"on":"off");
        else if(key==MibrPopupEditorModel.NAV_DEMO)drafts.readback(key,MibrRgiCockpit.demoRequested()?"on":"off");
        else if(key==MibrPopupEditorModel.CALIB_IMAGE)drafts.readback(key,MibrCalibration.on()?"on":"off");
        else if(MibrPopupEditorModel.durable(key)!=null){
            MibrDurableSwitch sw=MibrPopupEditorModel.durable(key);
            String stored=sw.revision()!=null?sw.value():sw.persistedValue();
            drafts.readback(key,MibrPopupEditorModel.isSafe(key)?
                MibrSafeArea.field(stored,sw.defaultValue(),MibrPopupEditorModel.safeField(key)):stored);
        }
        else if(key>MibrPopupEditorModel.ENGINE&&key<MibrPopupEditorModel.SCALE_MAIN&&MibrPopupEditorModel.isVirtual(key))
            drafts.readback(key,MibrViewState.value(key-MibrPopupEditorModel.VIEW_FOLLOW));
        TextArea text=(TextArea)MibrOemSsmTemplate.target((WidgetModel)item,
            kind==VALUE?MibrOemSsmTemplate.VALUE_LABEL_TARGET_ID:
            kind==CHECK?MibrOemSsmTemplate.CHECK_TEXT_TARGET_ID:MibrOemSsmTemplate.PLAIN_TEXT_TARGET_ID,TextArea.class);
        text.set_text(labels[rank]);
        if(scalingNotice){
            text.set_shorten(false);
            text.set_lineBreakMode(TextAreaModel.LINEBREAKMODE_CHARACTER);
        }
        if(menu.screen()==MibrCarPlayMenuModel.DETAIL){
            text.set_shorten(false);
            text.set_lineBreakMode(TextAreaModel.LINEBREAKMODE_CHARACTER);
        }
        Button button=(Button)MibrOemSsmTemplate.target((WidgetModel)item,
            kind==VALUE?MibrOemSsmTemplate.OPENER_TARGET_ID:
            kind==CHECK?MibrOemSsmTemplate.CHECK_BUTTON_TARGET_ID:MibrOemSsmTemplate.PLAIN_BUTTON_TARGET_ID,Button.class);
        String current=key<0?null:drafts.draft(key);
        if(current==null && key>=0)current=drafts.current(key);
        if(kind==CHECK){
            // Stock ExternalApps checkbox: the OEM row paints the box and the mark
            // itself; only the activated state is set. An unread value shows the
            // empty OEM box like an unchecked row.
            button.set_activated(drafts.checked(key,current));
        }
        if(kind==VALUE){
            TextArea value=(TextArea)MibrOemSsmTemplate.target((WidgetModel)item,
                MibrOemSsmTemplate.VALUE_TEXT_TARGET_ID,TextArea.class);
            String uiMessage=MibrPopupEditorModel.isScaling(key)?MibrScalingState.uiMessage(key):
                key==MibrPopupEditorModel.MENU_LANGUAGE?MibrI18n.menuMessage():
                MibrPopupEditorModel.durable(key)!=null?MibrPopupEditorModel.durable(key).message():
                key==MibrPopupEditorModel.GPS_DEMO?MibrGpsDemoState.message():null;
            value.set_text(uiMessage!=null?uiMessage:(current==null?"":drafts.label(key,current)));
            value.set_shorten(true);
        }
        item.set_visible(true);
        if(scalingNotice){
            // Plain stock text row. Disabled and listener-free: not focusable,
            // not an editor, not a SCALE_SET source.
            item.set_enabled(false);button.set_enabled(false);
            return;
        }
        // carplay.enabled (CHECK) and viewarea.selected (dropdown) are runtime
        // actions, NOT ordinary preferences; native V3 advertises no qualified
        // session/VIEW action owner yet. The view dropdown has no owner at all.
        // r10: the yes/no CHECK rows are saved + applied live through V3; only the
        // two runtime actions stay disabled.
        boolean runtimeActionBlocked=key>=0 && drafts.liveViewGated(key);
        item.set_enabled(!runtimeActionBlocked);
        button.set_enabled(!runtimeActionBlocked);
        // Detail lines contain observations, not clickable actions or live setters.
        if(menu.screen()==MibrCarPlayMenuModel.DETAIL)return;
        for(int i=0;i<listeners.size();i++){RowListener existing=(RowListener)listeners.elementAt(i);
            if(existing.item==item){existing.rank=rank;return;}}
        RowListener listener=new RowListener(item,button,rank,kind==VALUE,epoch);
        listeners.addElement(listener);item.getController().addOutEventListener(listener);
        button.getController().addOutEventListener(listener);
    }
    private final class RowListener extends OutEventAdapter {
        final ListItemModel item;final Button button;int rank;final int version;final boolean value;
        RowListener(ListItemModel item,Button button,int rank,boolean value,int version){
            this.item=item;this.button=button;this.rank=rank;this.value=value;this.version=version;
        }
        public void outHMIEventFired(String event){
            if(attached && version==epoch && value && "pressed".equals(event)){
                int key=menu.keyForRow(rank);
                if(key>=0 && !drafts.liveViewGated(key))try{editor.prepare((DropDownButton)button,key);}
                catch(Throwable failure){System.err.println("MIBR_SSM_POPUP_FAILED "+failure);later(leave);}
            }
        }
        public void outListItemEventFired(String event,int absolute,int a,int b,int c,String sender,long object){
            if(value || !"buttonReleased".equals(event))return;
            later(new Runnable(){public void run(){
                if(!attached || version!=epoch)return;
                try{
                    int key=menu.keyForRow(rank);
                    if(menu.onDiagnostics()||menu.onVersion())return;
                    if(menu.loadRow(rank)){
                        if(v3!=null)v3.menuLoad();
                        return;
                    }
                    if(key==MibrPopupEditorModel.CALIB_IMAGE){
                        if(drafts.toggle(key)){
                            String wish=drafts.draft(key);drafts.discardDraft(key);
                            MibrCalibration.set("on".equals(wish));
                            menu.refresh();
                        }
                    }
                    else if(key==MibrPopupEditorModel.NAV_DEMO){
                        if(drafts.toggle(key)){
                            String wish=drafts.draft(key);drafts.discardDraft(key);
                            MibrRgiCockpit.requestDemo("on".equals(wish));
                            menu.refresh();
                        }
                    }
                    else if(MibrPopupEditorModel.durableCheck(key)){
                        // broker-owned switch; the wish is sent, the row shows the readback.
                        if(!drafts.liveViewGated(key)&&drafts.toggle(key)){
                            String wish=drafts.draft(key);drafts.discardDraft(key);
                            if(v3!=null&&wish!=null)v3.durableSet(key,wish);
                            menu.refresh();
                        }
                    }
                    else if(key>=0 && drafts.directToggle(key)){
                        if(drafts.toggle(key)){
                            if(v3!=null)v3.commit(key);
                            menu.refresh();
                        }
                    }
                    else menu.select(rank);
                }catch(Throwable failure){failed(failure);}
            }});
        }
    }
    private void removeListeners(){
        for(int i=0;i<listeners.size();i++){RowListener listener=(RowListener)listeners.elementAt(i);
            if(listener.item.getController()!=null)listener.item.getController().removeOutEventListener(listener);
            if(listener.button.getController()!=null)listener.button.getController().removeOutEventListener(listener);}
        listeners.removeAllElements();
    }
    /** Called on native onLeave, before the original handler deinitializes. */
    void detach(){
        if(detached)return;
        attached=false;epoch++;control.detach();if(v3!=null)v3.detach();
        MibrCalibration.set(false);
        Throwable failure=null;
        boolean cleanupFailed=false;
        try{editor.detach();}catch(Throwable t){failure=t;}
        try{clearMasters();}catch(Throwable t){cleanupFailed=true;if(failure==null)failure=t;}
        try{stock.mainList.setListItemTransfer(originalTransfer);}catch(Throwable t){cleanupFailed=true;if(failure==null)failure=t;}
        try{MibrHomeList.replaceOwnedSsmItems(stock.mainList,stock.view,original);}catch(Throwable t){cleanupFailed=true;if(failure==null)failure=t;}
        try{stock.close.getController().removeOutEventListener(back);}catch(Throwable t){cleanupFailed=true;if(failure==null)failure=t;}
        drafts.detach();
        // A close warning must not touch deinitialized widgets on a later retry
        // when all ownership restoration and clone cleanup already completed.
        detached=!cleanupFailed;
        if(failure!=null)throw new IllegalStateException("MIBR_SSM_ROWS_DETACH_FAILED "+failure);
    }
}
