package de.mibr.hmi;

import de.vw.mib.desktop.ViewHandlerProvider;
import de.vw.mib.desktop.internal.DesktopManagerImpl;
import de.vw.mib.desktop.internal.ScreenAreaDude;
import de.vw.mib.desktop.internal.common.ServiceManager;
import de.vw.mib.desktop.internal.screenarea.ScreenAreaNode;
import de.vw.mib.desktop.internal.screenarea.ScreenTree;
import de.vw.mib.desktop.internal.screenarea.ViewNode;
import de.vw.mib.desktop.internal.viewhandler.SmartViewHandler;
import de.vw.mib.skin.SkinClassLoader;
import de.vw.mib.view.internal.AbstractViewHandler;
import de.vw.mib.view.internal.ViewHandlerAppServices;
import de.vw.mib.view.internal.ViewHandlerServices;
import de.vw.mib.viewmanager.internal.ViewHandler;
import de.vw.mib.widgets.models.ViewModel;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.List;

/** Exact original MU1440 descriptors, not a replacement OEM factory/handler. */
public final class MibrSsmSourceBinding {
    private MibrSsmSourceBinding() { }

    public static final class Binding {
        final DesktopManagerImpl desktop;
        final ScreenTree tree;
        final ScreenAreaDude area;
        final String path;
        final SmartViewHandler home;
        final AbstractViewHandler handler;
        final ViewHandlerProvider provider;
        final ViewHandlerServices services;
        final ViewHandlerAppServices appServices;
        final SkinClassLoader loader;
        private final Method nativeEnter;

        private Binding(Scan scan, AbstractViewHandler actual) throws Exception {
            desktop = ServiceManager.desktopManager;
            tree = ServiceManager.screenAreaTree;
            path = scan.path;
            home = scan.match;
            handler = actual;
            provider = home.getViewHandlerProvider();
            loader = ServiceManager.skinClassLoader;
            if (desktop == null || tree == null || provider == null || loader == null ||
                    path == null || path.length() == 0 || desktop.isSkinChanging())
                throw new IllegalStateException("MIBR_SSM_SOURCE_SERVICES_UNAVAILABLE");
            services = (ViewHandlerServices)readExact("services", ViewHandlerServices.class, actual);
            appServices = (ViewHandlerAppServices)readExact("appServices", ViewHandlerAppServices.class, actual);
            if (services == null || appServices == null || appServices.getAppDefinition() == null ||
                    de.vw.mib.widgets.internal.ServiceManager.eventDispatcher == null)
                throw new IllegalStateException("MIBR_SSM_SOURCE_SERVICES_NULL");
            // getScreenAreaDude can create unknown areas. Prove this existing area first.
            if (tree.getScreenAreaNode(path) != scan.node ||
                    desktop.getDominantViewHandlerOfScreenArea(path) != home)
                throw new IllegalStateException("MIBR_SSM_SOURCE_FOREGROUND_CHANGED");
            area = desktop.getScreenAreaDude(path);
            if (area == null || area.getCurrentViewHandler() != home)
                throw new IllegalStateException("MIBR_SSM_SOURCE_TRANSITION_PENDING");
            // Exact package-private OEM seam. It performs native ScreenTree registration
            // and lifecycle without inserting this owned handler into the global LRU.
            nativeEnter = ScreenAreaDude.class.getDeclaredMethod("enterView",
                new Class[] {SmartViewHandler.class});
            if (nativeEnter.getReturnType() != Void.TYPE)
                throw new IllegalStateException("MIBR_SSM_ENTER_DESCRIPTOR_CHANGED");
            nativeEnter.setAccessible(true);
        }

        void enter(SmartViewHandler expected, SmartViewHandler next) throws Exception {
            if (next == null || ServiceManager.desktopManager != desktop ||
                    ServiceManager.screenAreaTree != tree || desktop.isSkinChanging() ||
                    tree.getScreenAreaNode(path) == null ||
                    desktop.getDominantViewHandlerOfScreenArea(path) != expected)
                throw new IllegalStateException("MIBR_SSM_FOREGROUND_OWNER_CHANGED");
            try { nativeEnter.invoke(area, new Object[] {next}); }
            catch (InvocationTargetException failure) {
                Throwable cause = failure.getTargetException();
                if (cause instanceof Exception) throw (Exception)cause;
                if (cause instanceof Error) throw (Error)cause;
                throw new IllegalStateException("MIBR_SSM_ENTER_FAILED");
            }
        }

        void unregisterDetached(SmartViewHandler owned) {
            if(owned.isLinked() || desktop.getDominantViewHandlerOfScreenArea(path)==owned)
                throw new IllegalStateException("MIBR_SSM_STILL_FOREGROUND");
            ScreenAreaNode node=tree.getScreenAreaNode(path);
            List entries=node==null?null:node.getChildren();
            for(int i=0;entries!=null && i<entries.size();i++){
                Object entry=entries.get(i);
                if(entry instanceof ViewNode && ((ViewNode)entry).getViewHandler()==owned){
                    tree.unregisterViewHandler(path,owned);return;
                }
            }
        }
    }

    static int lifecycle(AbstractViewHandler handler) throws Exception {
        Field field=AbstractViewHandler.class.getDeclaredField("lifeCycle");
        if(field.getType()!=Integer.TYPE)throw new IllegalStateException("MIBR_SSM_LIFECYCLE_DESCRIPTOR");
        field.setAccessible(true);return field.getInt(handler);
    }

    private static Object readExact(String name, Class type, AbstractViewHandler source) throws Exception {
        Field field = AbstractViewHandler.class.getDeclaredField(name);
        if (field.getType() != type)
            throw new IllegalStateException("MIBR_SSM_FIELD_DESCRIPTOR_CHANGED " + name);
        field.setAccessible(true);
        return field.get(source);
    }

    private static final class Scan {
        SmartViewHandler match;
        ScreenAreaNode node;
        String path;
        int hits, nodes;
    }

    /** Resolves at the actual click, after HOME's init/enter/activate completed. */
    public static Binding capture(ViewModel owner) throws Exception {
        if (owner == null || owner.get_targetId() != 33077553 ||
                !("SimpleGridMenu".equals(owner.get_name()) || "Sgm".equals(owner.get_name())) ||
                ServiceManager.screenAreaTree == null)
            throw new IllegalStateException("MIBR_SSM_HOME_NOT_READY");
        Scan scan = new Scan();
        scan(ServiceManager.screenAreaTree.getScreenAreaNode(""), owner, scan, 0);
        if (scan.hits != 1 || scan.match == null || !scan.node.isActive() ||
                !scan.match.isLinked() || !scan.match.isActive())
            throw new IllegalStateException("MIBR_SSM_HOME_IDENTITY_NOT_UNIQUE_ACTIVE");
        ViewHandler source = scan.match.getViewHandler();
        if (!(source instanceof AbstractViewHandler) || source.getView() != owner ||
                !((AbstractViewHandler)source).isActivated())
            throw new IllegalStateException("MIBR_SSM_HOME_HANDLER_NOT_INITIALIZED");
        // Exact MMX ScreenAreaDude hero path requires original H_69BD plus
        // ScreenAreaAnimation. Probe the original short-name only; leave the
        // original animation area unmodified and explicitly unverified.
        System.out.println("MIBR_HOME_HERO_SOURCE short="+
            scan.match.getShortViewHandlerName()+
            " animationArea=UNVERIFIED nativeEnter=ScreenAreaDude");
        return new Binding(scan, (AbstractViewHandler)source);
    }

    /** The original HOME handler owning {@code owner}, or null while it is not (uniquely) registered. */
    static AbstractViewHandler findHandler(ViewModel owner) {
        if (owner == null || ServiceManager.screenAreaTree == null) return null;
        Scan scan = new Scan();
        scan(ServiceManager.screenAreaTree.getScreenAreaNode(""), owner, scan, 0);
        if (scan.hits != 1 || scan.match == null) return null;
        ViewHandler source = scan.match.getViewHandler();
        return source instanceof AbstractViewHandler && source.getView() == owner
            ? (AbstractViewHandler)source : null;
    }

    private static void scan(ScreenAreaNode area, ViewModel owner, Scan result, int depth) {
        if (area == null || depth > 16 || ++result.nodes > 256)
            throw new IllegalStateException("MIBR_SSM_SCREEN_TREE_BOUNDS");
        List views = area.getChildren();
        for (int i = 0; views != null && i < views.size(); i++) {
            Object entry = views.get(i);
            if (!(entry instanceof ViewNode)) throw new IllegalStateException("MIBR_SSM_SCREEN_VIEW_TYPE");
            ViewNode node = (ViewNode)entry;
            SmartViewHandler smart = node.getViewHandler();
            if (smart != null && smart.getView() == owner) {
                result.hits++; result.match = smart; result.node = area; result.path = area.getScreenAreaPath();
            }
            List children = node.getChildren();
            for (int j = 0; children != null && j < children.size(); j++) {
                Object child = children.get(j);
                if (!(child instanceof ScreenAreaNode)) throw new IllegalStateException("MIBR_SSM_SCREEN_AREA_TYPE");
                scan((ScreenAreaNode)child, owner, result, depth + 1);
            }
        }
    }
}