package de.mibr.hmi;

import de.vw.mib.datapool.LocalListItemControl;
import de.vw.mib.view.internal.AbstractViewHandler;
import de.vw.mib.widgets.Button;
import de.vw.mib.widgets.DropDownButton;
import de.vw.mib.widgets.ListItem;
import de.vw.mib.widgets.Slider;
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
    /** r15: masters cloned from the Tsmv slider source (destroyed through it), parallel to masters. */
    private MibrSafeSliderSource.Row[] sliderRows=new MibrSafeSliderSource.Row[0];
    /** r15h: owned header (Tsmv Item) masters, parallel to masters; disposed as owned trees. */
    private ListItem[] itemRows=new ListItem[0];
    private final Vector itemListeners=new Vector();
    private MibrSafeSliderSource sliders;
    private final Vector sliderListeners=new Vector();
    private boolean attached=true;
    private boolean detached;
    private boolean scalingPageVisible;
    private boolean advancedPageVisible;
    private int epoch;
    private int lastScreen=-1;
    private int lastGroup=-2,lastPage=-1,lastSelected=-2;
    private String lastTitle;
    private String[] labels=new String[0];

    private static final int PLAIN=0,VALUE=1,CHECK=2,SLIDER=3,ITEM=4;
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
    /** r15: native OEM slider rows for the safe-area edges (resolved lazily on the first edge page). */
    private de.vw.mib.widgets.interfaces.WidgetCloneFactory stockFactory;
    private int safeRefreshedGroup=-2;
    static{
        MibrSafeArea.diag=new MibrSafeArea.Diag(){public void line(String text){MibrOemSsmTemplate.diag(text);}};
    }
    /** r15e: owned OEM slider rows; the list clones them through the source's factory (stock items unchanged). */
    void sliders(MibrSafeSliderSource source){
        sliders=source;
        if(source!=null&&stockFactory==null){
            stockFactory=stock.mainList.getWidgetCloneFactory();
            if(stockFactory!=null)stock.mainList.setWidgetCloneFactory(source.factory(stockFactory));
        }
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
    private void failed(Throwable failure){
        String text=failure.getClass().getName()+": "+failure.getMessage();
        // r15d: a failure while slider rows are laid out never closes the menu: pre-r15 rows instead (once).
        boolean involved=MibrSafeArea.slidersShown()||sliderMastersPresent()||sliderListeners.size()>0;
        if(MibrSafeArea.onLayoutFailure(involved)==MibrSafeArea.FAIL_FALLBACK){
            MibrOemSsmTemplate.diag("MIBR_SAFE_SLIDER_ROWS_SKIPPED reason=LAYOUT_FAILED "+text);
            MibrOemSsmTemplate.diagTrace("MIBR_SAFE_SLIDER_LAYOUT_TRACE",failure);
            try{
                if(sliders!=null)sliders.fail("LAYOUT_FAILED");
                try{clearMasters();}catch(Throwable cleanup){
                    MibrOemSsmTemplate.diag("MIBR_SAFE_SLIDER_CLEANUP_FAILED "+cleanup);
                    for(int i=0;i<sliderRows.length;i++)if(sliderRows[i]!=null){
                        MibrSafeSliderSource.dispose(sliderRows[i].item);sliderRows[i]=null;}
                    for(int i=0;i<itemRows.length;i++)if(itemRows[i]!=null){
                        MibrSafeSliderSource.dispose(itemRows[i]);itemRows[i]=null;}
                }
                lastScreen=-1;lastTitle=null; // force a full rebuild
                menu.refresh();
                MibrOemSsmTemplate.diag("MIBR_SAFE_SLIDER_FALLBACK_RENDERED");
                return;
            }catch(Throwable again){
                text=again.getClass().getName()+": "+again.getMessage();
            }
        }
        MibrOemSsmTemplate.diag("MIBR_SSM_ROWS_FAILED "+text);
        MibrOemSsmTemplate.diagTrace("MIBR_SSM_ROWS_FAILED_TRACE",failure);
        System.err.println("MIBR_SSM_ROWS_FAILED "+text);
        later(leave);
    }
    private boolean sliderMastersPresent(){
        for(int i=0;i<sliderRows.length;i++)if(sliderRows[i]!=null)return true;
        for(int i=0;i<itemRows.length;i++)if(itemRows[i]!=null)return true;
        return false;
    }
    public void committed(int index){
        // Native option completion, never focus/pressed.
        if(attached && index==MibrPopupEditorModel.CALIB_IMAGE){
            // local RAM marker, no broker: the chosen pattern id is the marker content
            String wish=drafts.draft(index);drafts.discardDraft(index);
            if(wish!=null)MibrCalibration.set(wish);
            changed(); // no broker callback for a local marker: refresh the readback ourselves
            return;
        }
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
        boolean toggled=menu.consumeToggle();
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
        // r15c: resolve before the first layout of an edge page, then render once more through the model so the
        // very first layout of the page already has the slider rows (no deferred second layout that can be lost).
        boolean edgePage=screen==MibrCarPlayMenuModel.ITEMS&&menu.safeEdgePage();
        // r15f: entering a safe-area page reads its value+revision, so the first SET carries the current CAS revision.
        if(edgePage&&menu.group()!=safeRefreshedGroup&&v3!=null){
            safeRefreshedGroup=menu.group();
            for(int i=0;i<menu.rowCount();i++){
                int k=menu.keyForRow(i);
                if(k>=0&&MibrPopupEditorModel.isSafe(k)){v3.safeRefresh(k);break;}
            }
        }else if(!edgePage)safeRefreshedGroup=-2;
        // r15i: the cockpit zoom page uses the same owned slider rows (resolve before its first layout too)
        boolean sliderPage=screen==MibrCarPlayMenuModel.ITEMS&&menu.sliderPage();
        int plan=MibrSafeArea.sliderPlan(sliderPage,sliders==null?-1:sliders.state(),hasSliderRows());
        if(plan==MibrSafeArea.PLAN_RESOLVE){
            sliders.resolve(stock.value.get_width(),handler.getClass().getClassLoader());
            plan=MibrSafeArea.sliderPlan(sliderPage,sliders.state(),hasSliderRows());
        }
        if(plan==MibrSafeArea.PLAN_RERENDER){menu.refresh();return;}
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
        // r15i polish: an expand/collapse tap keeps the page where it was and reveals the expanded header + slider
        boolean reveal=toggled&&lastScreen==screen&&title.equals(lastTitle);
        int visible=reveal?stock.mainList.getLastFullyVisibleIndex()-stock.mainList.getFirstFullyVisibleIndex()+1:0;
        epoch++;editor.close();clearMasters();labels=rows;
        lastScreen=screen;lastTitle=title;
        lastGroup=menu.group();lastPage=menu.page();lastSelected=menu.selected();
        stock.title.set_text(title);
        if(screen==MibrCarPlayMenuModel.HOME){leave.run();return;}
        masters=new ListItem[count];WidgetModel[] children=new WidgetModel[count];
        sliderRows=new MibrSafeSliderSource.Row[count];itemRows=new ListItem[count];
        boolean sliderLost=false;
        for(int rank=0;rank<count;rank++){
            ListItem item=null;
            if(menu.sliderKeyForRow(rank)>=0){
                MibrSafeSliderSource.Row row=sliders==null?null:sliders.create();
                if(row!=null){sliderRows[rank]=row;item=row.item;}
                else sliderLost=true; // fail closed: an empty stock row now, no slider rows on the next render
            }else if(sliders!=null&&menu.safeToggleRow(rank)){
                // r15h: the edge header is the stock Tsmv Item look (label + preview, value when expanded)
                MibrSafeSliderSource.Item header=sliders.createItem();
                if(header!=null){itemRows[rank]=header.item;item=header.item;}
                else sliderLost=true;
            }
            if(item==null){
                ListItem template=template(menu.keyForRow(rank));
                item=(ListItem)handler.createWidgetCloneable(template);
            }
            masters[rank]=item;children[rank]=item;
            item.setListItemControl(new LocalListItemControl(1));
            item.set_visible(true);item.set_enabled(true);
            item.init(stock.view);
            if(stock.view.is_activated())item.activate();
            apply(item,rank);
        }
        MibrHomeList.replaceOwnedSsmItems(stock.mainList,stock.view,children);
        int header=reveal?menu.expandedRow():-1;
        if(reveal){
            int at=header>=0?header:Math.max(0,Math.min(count-1,selected));
            int top=MibrSafeArea.revealFirst(first,visible,header,count);
            stock.mainList.set_selectedIndex(count==0?-1:at);
            if(count>0)stock.mainList.setFocusedIndex(at);
            if(top>=0&&top<count)stock.mainList.snap(top,0);
            MibrOemSsmTemplate.diag("MIBR_SLIDER_REVEAL header="+header+" first="+first+" visible="+visible+" top="+top+" count="+count);
        }else{
            stock.mainList.set_selectedIndex(count==0?-1:preserve && selected>=0 && selected<count?selected:0);
            if(preserve){
                if(focused>=0 && focused<count)stock.mainList.setFocusedIndex(focused);
                if(first>=0 && first<count)stock.mainList.snap(first,0);
            }
        }
        // Bind the stock scrollbar only after count, selection, focus and viewport settled.
        MibrOemSsmTemplate.syncScrollbar(stock,true);
        if(count==0 && detail!=null && detail.length()>0)stock.title.set_text(title+MibrI18n.pick(": keine Live-Werte",": no live values"));
        if(sliderPage){
            int n=0,h=0;for(int i=0;i<sliderRows.length;i++){if(sliderRows[i]!=null)n++;if(itemRows[i]!=null)h++;}
            if(n>0||h>0)MibrOemSsmTemplate.diag("MIBR_SAFE_SLIDER_ROWS rows="+n+" items="+h+" total="+count+
                " expanded="+menu.expandedSafe()+" kind=owned");
            else MibrOemSsmTemplate.diag("MIBR_SAFE_SLIDER_ROWS_SKIPPED reason="+(sliders==null?"NO_SOURCE":
                sliderLost?"CLONE_FAILED":sliders.state()==MibrSafeSliderSource.FAILED?"SOURCE_FAILED":"NOT_READY"));
        }
        if(sliderLost)changed();
    }
    private boolean hasSliderRows(){return menu.builtWithSliders();}
    private static boolean sameRows(String[] a,String[] b){
        if(a.length!=b.length)return false;
        for(int i=0;i<a.length;i++)if(a[i]==null?b[i]!=null:!a[i].equals(b[i]))return false;
        return true;
    }
    private void clearMasters(){
        removeListeners();
        MibrHomeList.replaceOwnedSsmItems(stock.mainList,stock.view,new WidgetModel[0]);
        for(int i=0;i<masters.length;i++)if(masters[i]!=null){
            if(i<itemRows.length&&itemRows[i]!=null){
                MibrSafeSliderSource.dispose(masters[i]);itemRows[i]=null;
            }else if(i<sliderRows.length&&sliderRows[i]!=null){
                MibrSafeSliderSource.dispose(masters[i]);
                sliderRows[i]=null;
            }else handler.destroyWidgetCloneable(masters[i]);
            masters[i]=null;
        }
        masters=new ListItem[0];sliderRows=new MibrSafeSliderSource.Row[0];itemRows=new ListItem[0];
    }
    public boolean transferData(ListItemModel item,int unused,int local){
        int rank=item.getAbsoluteIndex();
        if(!attached || rank<0 || rank>=labels.length || labels[rank]==null)return false;
        apply(item,rank);return true;
    }
    private ListItem template(int key){
        if(menu.screen()==MibrCarPlayMenuModel.DETAIL || key<0)return stock.plain;
        if(drafts.directToggle(key))return stock.check;
        // r15g: with slider rows an edge row is a plain collapsed row (label + value), no dropdown
        if(MibrSafeArea.slidersShown()&&MibrPopupEditorModel.isSafe(key)&&
           MibrPopupEditorModel.safeField(key)<MibrSafeArea.RESET_FIELD)return stock.plain;
        return stock.value;
    }
    private static int kind(ListItemModel item){
        int id=item.get_targetId();
        return id==MibrOemSsmTemplate.VALUE_TARGET_ID?VALUE:id==MibrOemSsmTemplate.CHECK_TARGET_ID?CHECK:
            id==MibrSafeSliderSource.ROW?SLIDER:id==MibrSafeSliderSource.ITEM_ROW?ITEM:PLAIN;
    }
    private MibrSafeSliderSource.Row sliderRow(ListItemModel item){
        for(int i=0;i<sliderRows.length;i++)if(sliderRows[i]!=null&&sliderRows[i].item==item)return sliderRows[i];
        return null;
    }
    /**
     * r15 slider row: OEM Tsmv SubItem clone. Range 0..1010 (Links/Rechts) or 0..376 (Oben/Unten), step 10 px;
     * its own -/+ buttons move the edge by 1 px. The value is the shown edge (live wish, else broker readback).
     */
    private void applySlider(ListItemModel item,int rank){
        // The list shows LUT clones of the masters (cloned by the Tsmv handler): resolve the parts in THIS item.
        int key=menu.sliderKeyForRow(rank);
        if(key<0||!(item instanceof ListItem))return;
        MibrSafeSliderSource.Row row=sliderRow(item);
        if(row==null)row=MibrSafeSliderSource.parts((ListItem)item);
        boolean zoom=MibrScalingState.zoomSlider(key);
        // r15i: cockpit zoom = 6 discrete positions 0..5 (step 1; -/+ one position); edges = stream px (step 10, -/+ 1 px)
        MibrDurableSwitch sw=zoom?null:MibrPopupEditorModel.durable(key);
        int field=zoom?-1:MibrPopupEditorModel.safeField(key);
        int edge=zoom?Math.max(0,MibrScalingState.zoomPosition(MibrScalingState.shown(key))):
            MibrSafeArea.edgeValue(MibrSafeArea.shown(sw),sw.defaultValue(),field);
        int max=zoom?MibrScalingState.ZOOM.length-1:MibrSafeArea.span(field),step=zoom?1:MibrSafeArea.SLIDER_STEP;
        SliderListener listener=null;
        for(int i=0;i<sliderListeners.size();i++){SliderListener l=(SliderListener)sliderListeners.elementAt(i);
            if(l.row.item==item){listener=l;break;}}
        Slider slider=row.slider;
        if(slider.get_valueMin()!=0)slider.set_valueMin(0);
        if(slider.get_valueMax()!=max)slider.set_valueMax(max);
        if(slider.get_step()!=step)slider.set_step(step);
        if(slider.is_valueChangeOnlyOnRelease())slider.set_valueChangeOnlyOnRelease(false);
        // Never pull the thumb under the finger: a value from the slider itself is not written back for 1 s.
        boolean touched=listener!=null&&System.currentTimeMillis()-listener.touched<1000L;
        if(!touched&&slider.get_value()!=edge)slider.set_value(edge);
        // A save in flight is not a reason to freeze the slider (the newest wish is sent after the reply).
        // r15g: always enabled and interactive (like the owned HOME tile button); a refused save is logged, not hidden
        item.set_visible(true);item.set_enabled(true);slider.set_enabled(true);slider.set_interactive(true);
        row.decrease.set_enabled(true);row.decrease.set_interactive(true);
        row.increase.set_enabled(true);row.increase.set_interactive(true);
        if(listener==null){
            row.slider.getController().setOutEventMapping("valueChanged",-1);
            row.decrease.getController().setOutEventMapping("pressed",-1);
            row.increase.getController().setOutEventMapping("pressed",-1);
            listener=new SliderListener(row,epoch);
            sliderListeners.addElement(listener);listener.add();
            if(zoom)MibrOemSsmTemplate.diag("MIBR_ZOOM_SLIDER_ATTACH rank="+rank+" listeners="+sliderListeners.size()+
                " enabled="+slider.is_enabled()+" interactive="+slider.is_interactive()+" position="+edge+
                " writable="+MibrScalingState.writable(key)+" rev="+MibrScalingState.revision(key)+" v3="+(v3!=null));
            else MibrOemSsmTemplate.diag("MIBR_SAFE_SLIDER_ATTACH edge="+field+" rank="+rank+" listeners="+sliderListeners.size()+
                " enabled="+slider.is_enabled()+" interactive="+slider.is_interactive()+" visible="+slider.is_visible()+
                " ctrl="+(slider.getController()!=null)+" master="+(row==sliderRow(item))+" available="+sw.available+
                " writable="+sw.writable()+" rev="+sw.revision()+" v3="+(v3!=null));
        }
        listener.rank=rank;
    }
    /**
     * r15h: edge header = stock Tsmv Item: label left; collapsed shows the mini-slider preview (9 stock steps) of the
     * current edge, expanded shows the numeric value right-aligned (as the stock sound menu). Tap toggles.
     */
    private void applyItem(ListItemModel item,int rank){
        int key=menu.keyForRow(rank);
        if(key<0||!(item instanceof ListItem)||sliders==null)return;
        MibrSafeSliderSource.Item parts=MibrSafeSliderSource.itemParts((ListItem)item);
        boolean zoom=MibrScalingState.zoomSlider(key);
        int field=zoom?-1:MibrPopupEditorModel.safeField(key);
        String valueText;int previewStep;
        if(zoom){
            // r15i: "Auto" or the number; an unread value shows the read/failure message instead
            String shown=MibrScalingState.shown(key);
            String message=shown==null?MibrScalingState.uiMessage(key):null;
            valueText=message!=null?message:MibrScalingState.zoomLabel(shown);
            previewStep=MibrScalingState.zoomPreviewStep(Math.max(0,MibrScalingState.zoomPosition(shown)));
        }else{
            MibrDurableSwitch sw=MibrPopupEditorModel.durable(key);
            int edge=MibrSafeArea.edgeValue(MibrSafeArea.shown(sw),sw.defaultValue(),field);
            valueText=String.valueOf(edge);
            previewStep=MibrSafeArea.previewStep(edge,MibrSafeArea.span(field));
        }
        boolean expanded=menu.expandedSafe()==key;
        parts.label.set_text(labels[rank]);
        parts.value.set_text(valueText);
        parts.value.set_visible(expanded);
        parts.preview.set_visible(!expanded);
        try{parts.button.set_imagesState(sliders.previewImages(previewStep));}
        catch(Throwable missing){MibrOemSsmTemplate.diag("MIBR_SAFE_SLIDER_PREVIEW_FAILED "+missing);}
        item.set_visible(true);item.set_enabled(true);
        parts.button.set_enabled(true);parts.button.set_interactive(true);
        for(int i=0;i<itemListeners.size();i++){ItemListener l=(ItemListener)itemListeners.elementAt(i);
            if(l.parts.item==item){l.rank=rank;return;}}
        parts.button.getController().setOutEventMapping("released",-1);
        parts.button.getController().setOutEventMapping("pressed",-1);
        ItemListener l=new ItemListener(parts,rank,epoch);
        itemListeners.addElement(l);parts.button.getController().addOutEventListener(l);
        MibrOemSsmTemplate.diag("MIBR_SAFE_SLIDER_ATTACH kind=item edge="+field+" rank="+rank+" enabled="+parts.button.is_enabled()+
            " interactive="+parts.button.is_interactive()+" ctrl="+(parts.button.getController()!=null));
    }
    private final class ItemListener extends OutEventAdapter {
        final MibrSafeSliderSource.Item parts;final int version;int rank;
        ItemListener(MibrSafeSliderSource.Item parts,int rank,int version){this.parts=parts;this.rank=rank;this.version=version;}
        public void outHMIEventFired(String event){
            if(!"released".equals(event))return;
            MibrOemSsmTemplate.diag("MIBR_SAFE_SLIDER_EVT kind=expand rank="+rank+" live="+(attached&&version==epoch));
            if(!attached||version!=epoch)return;
            later(new Runnable(){public void run(){
                if(!attached||version!=epoch)return;
                try{menu.toggleSafe(rank);}catch(Throwable failure){failed(failure);}
            }});
        }
    }
    private final class SliderListener extends OutEventAdapter {
        final MibrSafeSliderSource.Row row;final int version;int rank;long touched;
        private final OutEventAdapter minus=new OutEventAdapter(){
            public void outHMIEventFired(String event){if("pressed".equals(event))nudge(-1);}
        };
        private final OutEventAdapter plus=new OutEventAdapter(){
            public void outHMIEventFired(String event){if("pressed".equals(event))nudge(1);}
        };
        SliderListener(MibrSafeSliderSource.Row row,int version){this.row=row;this.version=version;}
        void add(){
            row.slider.getController().addOutEventListener(this);
            row.decrease.getController().addOutEventListener(minus);
            row.increase.getController().addOutEventListener(plus);
        }
        void remove(){
            if(row.slider.getController()!=null)row.slider.getController().removeOutEventListener(this);
            if(row.decrease.getController()!=null)row.decrease.getController().removeOutEventListener(minus);
            if(row.increase.getController()!=null)row.increase.getController().removeOutEventListener(plus);
        }
        private boolean live(){return attached&&version==epoch&&v3!=null;}
        /** Native DefaultSliderController.fire_valueChanged -> fireIntegerEvent("valueChanged",value) -> listeners. */
        public void outIntegerEventFired(String name,final int value){
            int k=menu.sliderKeyForRow(rank);
            MibrOemSsmTemplate.diag("MIBR_SAFE_SLIDER_EVT kind="+name+" value="+value+(MibrScalingState.zoomSlider(k)?" zoom=1":" edge="+
                MibrPopupEditorModel.safeField(Math.max(MibrPopupEditorModel.SAFE_FIRST,k)))+" live="+live());
            if(!"valueChanged".equals(name)||!live())return;
            touched=System.currentTimeMillis();
            final int key=menu.sliderKeyForRow(rank);
            if(key<0)return;
            later(new Runnable(){public void run(){
                if(!live())return;
                try{
                    if(MibrScalingState.zoomSlider(key))v3.zoomSlide(key,value);
                    else v3.safeEdge(key,value);
                }catch(Throwable failure){failed(failure);}
            }});
        }
        private void nudge(final int delta){
            MibrOemSsmTemplate.diag("MIBR_SAFE_SLIDER_EVT kind=pressed value="+delta+" rank="+rank+" live="+live());
            if(!live())return;
            final int key=menu.sliderKeyForRow(rank);
            if(key<0)return;
            later(new Runnable(){public void run(){
                if(!live())return;
                try{
                    if(MibrScalingState.zoomSlider(key))v3.zoomNudge(key,delta);
                    else v3.safeNudge(key,delta);
                }catch(Throwable failure){failed(failure);}
            }});
        }
    }
    private void apply(ListItemModel item,int rank){
        int key=menu.keyForRow(rank),kind=kind(item);
        if(kind==SLIDER){applySlider(item,rank);return;}
        if(kind==ITEM){applyItem(item,rank);return;}
        boolean scalingNotice=menu.noteRow(rank);
        if(key==MibrPopupEditorModel.EXPERT_MODE)drafts.readback(key,MibrExpert.choice());
        else if(key==MibrPopupEditorModel.ENGINE)drafts.readback(key,MibrEngineState.engine());
        else if(key==MibrPopupEditorModel.MENU_LANGUAGE)drafts.readback(key,MibrI18n.menuOverride());
        else if(key==MibrPopupEditorModel.GPS_DEMO)drafts.readback(key,MibrGpsDemoState.choice());
        else if(key==MibrPopupEditorModel.CARPLAY_NAV)drafts.readback(key,MibrDurableSwitch.CARPLAY_NAV.revision()!=null?
            MibrDurableSwitch.CARPLAY_NAV.value():MibrDurableSwitch.CARPLAY_NAV.persistedOn()?"on":"off");
        else if(key==MibrPopupEditorModel.NAV_DEMO)drafts.readback(key,MibrRgiCockpit.demoRequested()?"on":"off");
        else if(key==MibrPopupEditorModel.CALIB_IMAGE)drafts.readback(key,MibrCalibration.get());
        else if(MibrPopupEditorModel.durable(key)!=null){
            MibrDurableSwitch sw=MibrPopupEditorModel.durable(key);
            String stored=MibrPopupEditorModel.isSafe(key)?MibrSafeArea.shown(sw):sw.revision()!=null?sw.value():sw.persistedValue();
            drafts.readback(key,MibrPopupEditorModel.isSafe(key)?
                MibrSafeArea.field(stored,sw.defaultValue(),MibrPopupEditorModel.safeField(key)):stored);
        }
        else if(key>MibrPopupEditorModel.ENGINE&&key<MibrPopupEditorModel.SCALE_MAIN&&MibrPopupEditorModel.isVirtual(key))
            drafts.readback(key,MibrViewState.value(key-MibrPopupEditorModel.VIEW_FOLLOW));
        TextArea text=(TextArea)MibrOemSsmTemplate.target((WidgetModel)item,
            kind==VALUE?MibrOemSsmTemplate.VALUE_LABEL_TARGET_ID:
            kind==CHECK?MibrOemSsmTemplate.CHECK_TEXT_TARGET_ID:MibrOemSsmTemplate.PLAIN_TEXT_TARGET_ID,TextArea.class);
        if(kind==PLAIN&&key>=0&&menu.safeToggleRow(rank)){
            MibrDurableSwitch esw=MibrPopupEditorModel.durable(key);
            int edge=MibrSafeArea.edgeValue(MibrSafeArea.shown(esw),esw.defaultValue(),MibrPopupEditorModel.safeField(key));
            text.set_text(labels[rank]+": "+edge+" px");
        }else text.set_text(labels[rank]);
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
                    if(key==MibrPopupEditorModel.NAV_DEMO){
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
                    else if(menu.safeToggleRow(rank)){
                        MibrOemSsmTemplate.diag("MIBR_SAFE_SLIDER_EVT kind=expand key="+key);
                        menu.toggleSafe(rank);
                    }
                    else menu.select(rank);
                }catch(Throwable failure){failed(failure);}
            }});
        }
    }
    private void removeListeners(){
        for(int i=0;i<itemListeners.size();i++)try{ItemListener l=(ItemListener)itemListeners.elementAt(i);
            if(l.parts.button.getController()!=null)l.parts.button.getController().removeOutEventListener(l);}
            catch(Throwable failure){System.err.println("MIBR_SSM_ITEM_LISTENER_REMOVE_FAILED "+failure);}
        itemListeners.removeAllElements();
        for(int i=0;i<sliderListeners.size();i++)try{((SliderListener)sliderListeners.elementAt(i)).remove();}
            catch(Throwable failure){System.err.println("MIBR_SSM_SLIDER_LISTENER_REMOVE_FAILED "+failure);}
        sliderListeners.removeAllElements();
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
        if(stockFactory!=null)try{stock.mainList.setWidgetCloneFactory(stockFactory);stockFactory=null;}
            catch(Throwable t){cleanupFailed=true;if(failure==null)failure=t;}
        try{MibrHomeList.replaceOwnedSsmItems(stock.mainList,stock.view,original);}catch(Throwable t){cleanupFailed=true;if(failure==null)failure=t;}
        try{stock.close.getController().removeOutEventListener(back);}catch(Throwable t){cleanupFailed=true;if(failure==null)failure=t;}
        drafts.detach();
        // A close warning must not touch deinitialized widgets on a later retry
        // when all ownership restoration and clone cleanup already completed.
        detached=!cleanupFailed;
        if(failure!=null)throw new IllegalStateException("MIBR_SSM_ROWS_DETACH_FAILED "+failure);
    }
}
