package de.mibr.hmi;

import de.vw.mib.datapool.LocalListItemControl;
import de.vw.mib.animation.easing.EasingParams;
import de.vw.mib.animation.animations.KeyframeAnimation;
import de.vw.mib.graphics.Insets;
import de.vw.mib.widgets.controller.DefaultListItemController;
import de.vw.mib.widgets.ui.ListItemUI;
import de.vw.mib.widgets.Button;
import de.vw.mib.widgets.ListItem;
import de.vw.mib.widgets.TextArea;
import de.vw.mib.widgets.WidgetList;
import de.vw.mib.widgets.interfaces.WidgetCloneData;
import de.vw.mib.widgets.interfaces.WidgetCloneFactory;
import de.vw.mib.widgets.interfaces.WidgetCloneable;
import de.vw.mib.widgets.list.ListItemTransfer;
import de.vw.mib.widgets.models.AbstractButtonModel;
import de.vw.mib.widgets.models.ContainerModel;
import de.vw.mib.widgets.models.ListItemModel;
import de.vw.mib.widgets.models.TextAreaModel;
import de.vw.mib.widgets.models.ViewModel;
import de.vw.mib.widgets.models.WidgetModel;

/** One owned native grid item. Stock clone and data transfer remain delegated. */
public final class MibrHomeList extends WidgetList {
    private static final int VIEW_ID = 33077553;
    private static final int LIST_ID = 99828432;
    private WidgetModel[] original;
    private final java.util.Vector ownedTiles = new java.util.Vector();
    private MibrHomeAnimationMirror mirror;
    private de.vw.mib.view.internal.AbstractViewHandler mirrorHandler;
    private MibrOemTileLongPress oemLongPress;
    /** Opens the owned CarPlay settings page; shared by our tile and the OEM long press. */
    private static final Runnable OPEN_OWN_PAGE = new Runnable() {
        public void run() {
            // Finish the HOME button stack before entering the separate owned
            // native Ssm through ScreenAreaDude.
            MibrHomeAnimationMirror.ownTransitionStarted();
            de.vw.mib.widgets.internal.ServiceManager.eventDispatcher.invoke(
                new Runnable(){public void run(){
                    if (!MibrOemPageEntry.requestOpen())
                        MibrHomeAnimationMirror.ownTransitionEnded();
                }});
        }
    };
    private WidgetCloneFactory stockFactory;
    private ListItemTransfer stockTransfer;
    private ListItem template;
    private ListItem master;
    private Button style;
    private TextAreaModel textStyle;
    private ViewModel owner;
    private ViewModel settingsOwner;
    private final Hook hook = new Hook();
    private static MibrHomeList active;

    private static final class Data implements WidgetCloneData {
        // Distinct owned identity; no stock CIO/click clone data is inherited.
        Data() { }
    }

    private static void disposeOwnedTree(WidgetModel widget) {
        if (widget instanceof ContainerModel) {
            WidgetModel[] children = ((ContainerModel)widget).getChildren();
            for (int i = 0; children != null && i < children.length; i++) {
                if (children[i] != null) disposeOwnedTree(children[i]);
            }
            ((ContainerModel)widget).setChildren(new WidgetModel[0]);
        }
        try { widget.deInit(); } catch (Throwable ignored) { }
    }

    private static void disposeOwnedChildren(WidgetModel root) {
        if (root instanceof ContainerModel) {
            WidgetModel[] children = ((ContainerModel)root).getChildren();
            for (int i = 0; children != null && i < children.length; i++) {
                if (children[i] != null) disposeOwnedTree(children[i]);
            }
            ((ContainerModel)root).setChildren(new WidgetModel[0]);
        }
    }

    public void init(ViewModel view) {
        super.init(view);
        if(view!=null && view.get_targetId()==MibrOemSsmTemplate.ROOT_TARGET_ID &&
                (get_targetId()==MibrOemSsmTemplate.MAIN_LIST_TARGET_ID ||
                 get_targetId()==MibrOemSsmTemplate.OPTION_LIST_TARGET_ID)) {
            settingsOwner=view;
            return;
        }
        if (view == null || view.get_targetId() != VIEW_ID ||
            !("SimpleGridMenu".equals(view.get_name()) || "Sgm".equals(view.get_name())) ||
            get_targetId() != LIST_ID) return;
        try { attach(view); }
        catch (Throwable t) {
            System.err.println("MIBR_CARPLAY_LIST_ATTACH_FAILED " + t);
            try { detach(); } catch (Throwable ignored) {}
        }
    }

    private static Button button(WidgetModel node) {
        if (node instanceof Button) return (Button)node;
        if (node instanceof ContainerModel) {
            WidgetModel[] children = ((ContainerModel)node).getChildren();
            for (int i = 0; children != null && i < children.length; i++) {
                Button found = button(children[i]);
                if (found != null) return found;
            }
        }
        return null;
    }

    private static TextAreaModel text(WidgetModel node) {
        if (node instanceof TextAreaModel) return (TextAreaModel)node;
        if (node instanceof ContainerModel) {
            WidgetModel[] children = ((ContainerModel)node).getChildren();
            for (int i = 0; children != null && i < children.length; i++) {
                TextAreaModel found = text(children[i]);
                if (found != null) return found;
            }
        }
        return null;
    }

    private void attach(ViewModel view) {
        if (original != null) return;
        WidgetModel[] children = getChildren();
        WidgetCloneFactory factory = getWidgetCloneFactory();
        ListItemTransfer transfer = getListItemTransfer();
        if (children == null || factory == null || transfer == null) return;
        ListItem seed = null;
        for (int i = 0; i < children.length; i++) {
            if (children[i] instanceof ListItem &&
                children[i].get_width() > 0 && children[i].get_height() > 0) {
                seed = (ListItem)children[i];
                break;
            }
        }
        if (seed == null) return;
        Button stockButton = button(seed);
        TextAreaModel stockText = text(seed);
        if (stockButton == null || stockText == null) return;
        original = children;
        stockFactory = factory;
        stockTransfer = transfer;
        template = seed;
        style = stockButton;
        textStyle = stockText;
        owner = view;
        master = createTile();
        scheduleMirror();
        master.setListItemControl(new LocalListItemControl(1));
        WidgetModel[] appended = new WidgetModel[children.length + 1];
        System.arraycopy(children, 0, appended, 0, children.length);
        appended[children.length] = master;
        setWidgetCloneFactory(hook);
        setListItemTransfer(hook);
        master.init(view);
        replaceItems(appended);
        if (is_activated()) master.activate();
        active = this;
        MibrSsmNativePage.captureHome(view,this);
        System.out.println("MIBR_CARPLAY_LIST_ATTACHED stock=" + children.length);
    }

    private ListItem createTile() {
        // Build a NEW native item. Cloning the stock Tuner/Radio seed retains
        // its native parent-level event map, even after replacing child widgets.
        ListItem item = new ListItem();
        Insets zero = new Insets();
        // Same tap/zoom choreography as the neighbouring stock tile: reuse the
        // seed's native easing and keyframe arrays instead of empty ones, which
        // left the tile standing while the other tiles receded.
        EasingParams[] easing = template.get_easing();
        KeyframeAnimation[] keyframes = template.get_keyframeAnimations();
        if (easing == null) easing = new EasingParams[0];
        if (keyframes == null) keyframes = new KeyframeAnimation[0];
        System.out.println("MIBR_HOME_TILE_ANIMATION_SEED easing=" + easing.length
            + " keyframes=" + keyframes.length);
        item.init(true, new AbstractButtonModel[0], -1, 255, null, false, 0.0f,
            true, zero, 0, 0, false, zero, 0, null, 0, 0, zero, null,
            easing, new WidgetModel[0], true, new boolean[0],
            template.get_height(), keyframes, true, null,
            -1, true, "MibrCarPlayTile", null, null, 0L,
            0.0f, 0.0f, 0.0f, 10000.0f, 60.0f, 1.0f,
            0, 255, null, 0, false, 0.0f, 0.0f, 0.0f,
            1.0f, 1.0f, 1.0f, true, new AbstractButtonModel[0],
            new ListItemModel[0], -8800, zero, true, template.get_width(), 0, 0, 0);
        item.setController(new DefaultListItemController());
        item.setUI(new ListItemUI());
        int width = template.get_width();
        int height = template.get_height();
        int iconWidth = Math.min(235, Math.max(0, width - 60));
        int iconHeight = Math.min(154, Math.max(0, height - 80));
        int iconX = (width - iconWidth) / 2;
        int iconY = Math.min(30, Math.max(0, height - iconHeight - 50));
        int labelWidth = Math.min(235, Math.max(0, width - 60));
        int labelHeight = Math.min(37, height);
        int labelX = (width - labelWidth) / 2;
        int labelY = Math.max(0, height - labelHeight - 1);
        TextArea label = MibrOwnedWidgets.createLabel(null, textStyle,
            MibrI18n.pick("CarPlay-Menü", "CarPlay menu"), "MibrCarPlayTileText", -8802,
            labelX, labelY, labelWidth, labelHeight);
        Button touch = MibrOwnedWidgets.createTouchButton(null,
            new MibrOwnedWidgets.ActionSink() {
                public void onReleased() { OPEN_OWN_PAGE.run(); }
            }, "MibrCarPlayTileButton", -8801, 0, 0, width, height);
        // r27: the stock tile art (flat pressed bitmap) must not show behind our own four-state icon.
        de.vw.mib.graphics.image.Image[] stockArt = style.get_imagesBackground();
        de.vw.mib.graphics.image.Image[] blankArt =
            new de.vw.mib.graphics.image.Image[stockArt == null ? 0 : stockArt.length];
        for (int i = 0; i < blankArt.length; i++) blankArt[i] = new de.vw.mib.graphics.image.Image();
        touch.set_imagesBackground(blankArt);
        touch.set_colorsBackground(style.get_colorsBackground());
        touch.set_textColors(style.get_textColors());
        WidgetModel icon = null;
        if (iconWidth > 0 && iconHeight > 0) {
            icon = MibrOwnedWidgets.createFourStateIcon(null, touch,
                    "MibrCarPlayTileIcon", -8803,
                    iconX, iconY, iconWidth, iconHeight);
        }
        if (icon != null && touch instanceof MibrOwnedWidgets.TouchButton) {
            final WidgetModel art = icon;
            ((MibrOwnedWidgets.TouchButton)touch).setStateListener(
                new Runnable() { public void run() { art.repaint(); } });
        }
        touch.setChildren(icon == null ? new WidgetModel[] {label}
                : new WidgetModel[] {icon, label});
        item.setChildren(new WidgetModel[] {touch});
        item.set_selectedButtonRefs(new AbstractButtonModel[] {touch});
        item.set_activatedButtonRefs(new AbstractButtonModel[] {touch});
        item.setCloneData(new Data());
        item.set_name("MibrCarPlayTile");
        ownedTiles.addElement(item);
        return item;
    }


    private void replaceItems(WidgetModel[] items) {
        removeListItemChangedHandler(getChildren());
        setChildren(items);
        registerListItemChangedHandler(items);
        initListLUT();
        validateListImmediately(8194);
        invalidateList();
    }

    /** Existing factory55 subclass; used only by the separately owned Ssm. */
    static void replaceOwnedSsmItems(WidgetList list,ViewModel view,WidgetModel[] items) {
        if(!(list instanceof MibrHomeList))
            throw new IllegalStateException("MIBR_SSM_LIST_CLASS_UNAVAILABLE");
        MibrHomeList own=(MibrHomeList)list;
        if(own.settingsOwner!=view || view==null ||
                view.get_targetId()!=MibrOemSsmTemplate.ROOT_TARGET_ID)
            throw new IllegalStateException("MIBR_SSM_LIST_OWNER_MISMATCH");
        WidgetModel[] old=own.getChildren();
        int count=0;
        for(int i=0;old!=null && i<old.length;i++)if(old[i] instanceof ListItemModel)count++;
        ListItemModel[] masters=new ListItemModel[count];count=0;
        for(int i=0;old!=null && i<old.length;i++)if(old[i] instanceof ListItemModel){
            ListItemModel master=(ListItemModel)old[i];
            if(master.get_subItemRefs()!=null && master.get_subItemRefs().length!=0)
                throw new IllegalStateException("MIBR_SSM_UNEXPECTED_SUBITEMS");
            masters[count++]=master;
        }
        // Same original destroyClones contract as AbstractTemplateList.deInit.
        // Destroy the old LUT before replacing it; no abandoned native pool.
        own.listLUT.destroyClones(own.getWidgetCloneFactory(),masters);
        own.replaceItems(items);
    }

    private final class Hook implements WidgetCloneFactory, ListItemTransfer {
        public WidgetCloneable createWidgetCloneable(WidgetCloneable source) {
            return source.getCloneData() instanceof Data ? createTile()
                : stockFactory.createWidgetCloneable(source);
        }
        public void destroyWidgetCloneable(WidgetCloneable clone) {
            if (clone.getCloneData() instanceof Data) {
                ownedTiles.removeElement(clone);
                // Owned items never enter the Sgm factory's destroy path.
                disposeOwnedChildren((WidgetModel)clone);
                ((WidgetModel)clone).deInit();
                return;
            }
            stockFactory.destroyWidgetCloneable(clone);
        }
        public boolean transferData(ListItemModel item, int first, int second) {
            return item.getCloneData() instanceof Data || stockTransfer.transferData(item, first, second);
        }
    }

    private void scheduleMirror() {
        de.vw.mib.widgets.internal.ServiceManager.eventDispatcher.invoke(new Runnable() {
            public void run() { installMirror(); }
        });
    }

    /** Pass-through Sgm animation adapter so the owned tile follows the OEM HOME choreography. */
    private void installMirror() {
        if (original == null || mirror != null || owner == null) return;
        try {
            de.vw.mib.view.internal.AbstractViewHandler handler = MibrSsmSourceBinding.findHandler(owner);
            if (handler == null) return; // retried on activate()
            mirror = MibrHomeAnimationMirror.install(handler, new MibrHomeAnimationMirror.Targets() {
                public WidgetModel[] ownedTiles() {
                    WidgetModel[] tiles = new WidgetModel[ownedTiles.size()];
                    ownedTiles.copyInto(tiles);
                    return tiles;
                }
            });
            if (mirror != null) mirrorHandler = handler;
            System.out.println("MIBR_HOME_ANIMATION_MIRROR " + (mirror != null ? "INSTALLED" : "TABLE_MISMATCH"));
            installOemLongPress(handler);
        } catch (Throwable t) {
            mirror = null; mirrorHandler = null;
            System.err.println("MIBR_HOME_ANIMATION_MIRROR_FAILED " + t);
        }
    }

    /** Long press on the stock SmartLink/CarPlay/AA tile; independent of the mirror. */
    private void installOemLongPress(de.vw.mib.view.internal.AbstractViewHandler handler) {
        if (oemLongPress != null || handler == null) return;
        try {
            oemLongPress = MibrOemTileLongPress.install(handler, OPEN_OWN_PAGE);
            System.out.println("MIBR_OEM_LONGPRESS " + (oemLongPress != null ? "INSTALLED" : "LAYOUT_MISMATCH"));
        } catch (Throwable t) {
            oemLongPress = null;
            System.err.println("MIBR_OEM_LONGPRESS_FAILED " + t);
        }
    }

    public void activate() {
        super.activate();
        if (original != null && mirror == null) scheduleMirror();
        if (oemLongPress != null) {
            try { oemLongPress.refresh(); }
            catch (Throwable t) { System.err.println("MIBR_OEM_LONGPRESS_REFRESH_FAILED " + t); }
        }
    }

    private void detach() {
        if (original == null) return;
        if (mirror != null) {
            try { mirror.restore(mirrorHandler); }
            catch (Throwable t) { System.err.println("MIBR_HOME_ANIMATION_RESTORE_FAILED " + t); }
            mirror = null; mirrorHandler = null;
        }
        if (oemLongPress != null) { oemLongPress.restore(); oemLongPress = null; }
        ownedTiles.removeAllElements();
        MibrSsmNativePage.releaseHome(owner,this);
        WidgetModel[] saved = original;
        try {
            if (master != null) master.set_visible(false);
            replaceItems(saved);
            if (master != null) {
                master.deActivate();
                disposeOwnedChildren(master);
                master.deInit();
            }
        } finally {
            setWidgetCloneFactory(stockFactory);
            setListItemTransfer(stockTransfer);
            original = null; stockFactory = null; stockTransfer = null;
            template = null; master = null; style = null; textStyle = null; owner = null;
            if (active == this) active = null;
        }
    }

    public static synchronized void detachOwnedList() {
        if (active != null) active.detach();
    }

    public void deInit() {
        try { detach(); } catch (Throwable t) { System.err.println("MIBR_CARPLAY_LIST_DETACH_FAILED " + t); }
        try { super.deInit(); } finally { settingsOwner=null; }
    }

    protected void reset() {
        try { detach(); } catch (Throwable t) { System.err.println("MIBR_CARPLAY_LIST_RESET_FAILED " + t); }
        super.reset();
        settingsOwner=null;
    }
}