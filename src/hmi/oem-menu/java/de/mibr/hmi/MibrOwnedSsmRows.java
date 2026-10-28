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
    private int epoch;
    private int lastScreen=-1;
    private int lastGroup=-2,lastPage=-1,lastSelected=-2;
    private String lastTitle;
    private String[] labels=new String[0];

    private static final int PLAIN=0,VALUE=1,CHECK=2;
    private static final int DIAGNOSTICS_GROUP=group("diagnostics");
    private static int group(String id){
        for(int i=0;i<MibrMenuDefinition.GROUP_IDS.length;i++)
            if(id.equals(MibrMenuDefinition.GROUP_IDS[i]))return i;
        return -1;
    }
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
                if(attached && menu.screen()==MibrCarPlayMenuModel.ITEMS && menu.group()==DIAGNOSTICS_GROUP)changed();
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
            if(index==MibrPopupEditorModel.ENGINE){
                // r47: the engine type is not a registry key: ask the broker (ENGINE_SET) and drop the local wish.
                String wish=drafts.draft(index);drafts.discardDraft(index);
                if(wish!=null)v3.engineSet(wish);
            }else if(index>MibrPopupEditorModel.ENGINE&&MibrPopupEditorModel.isVirtual(index)){
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
        // A DETAIL state must render actual native stock ListItems, not merely a title.
        // The independent long-text/Scrollbar OEM adapter is a later visual gate.
        if(screen==MibrCarPlayMenuModel.DETAIL)rows=MibrElementDetailRows.lines(detail);
        // Diagnostics has no settings keys: one read-only line with the
        // configuration service state. No write action is offered here.
        if(screen==MibrCarPlayMenuModel.ITEMS && menu.group()==DIAGNOSTICS_GROUP){
            String[] withStatus=new String[rows.length+1];
            System.arraycopy(rows,0,withStatus,0,rows.length);
            withStatus[rows.length]=v3==null?control.status():v3.status();
            rows=withStatus;
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
        if(count==0 && detail!=null && detail.length()>0)stock.title.set_text(title+": keine Live-Werte");
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
        if(key==MibrPopupEditorModel.ENGINE)drafts.readback(key,MibrEngineState.engine());
        else if(key>MibrPopupEditorModel.ENGINE&&MibrPopupEditorModel.isVirtual(key))
            drafts.readback(key,MibrViewState.value(key-MibrPopupEditorModel.VIEW_FOLLOW));
        MibrElementSpec spec=key<0||key>=MibrSettingsCatalog.KEYS.length?null:MibrCanonicalElementMenu.describeVisible(MibrSettingsCatalog.KEYS[key]);
        TextArea text=(TextArea)MibrOemSsmTemplate.target((WidgetModel)item,
            kind==VALUE?MibrOemSsmTemplate.VALUE_LABEL_TARGET_ID:
            kind==CHECK?MibrOemSsmTemplate.CHECK_TEXT_TARGET_ID:MibrOemSsmTemplate.PLAIN_TEXT_TARGET_ID,TextArea.class);
        text.set_text(spec!=null?spec.label:labels[rank]);
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
            value.set_text(current==null?"":drafts.label(key,current));
            value.set_shorten(true);
        }
        item.set_visible(true);
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
                    if(menu.screen()==MibrCarPlayMenuModel.ITEMS && menu.group()==DIAGNOSTICS_GROUP)return;
                    if(key>=0 && drafts.directToggle(key)){
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
        Throwable failure=null;
        boolean cleanupFailed=false;
        try{editor.detach();}catch(Throwable t){failure=t;}
        try{if(stock.indicator!=null){stock.indicator.detach();stock.indicator=null;}}
        catch(Throwable t){cleanupFailed=true;if(failure==null)failure=t;}
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
