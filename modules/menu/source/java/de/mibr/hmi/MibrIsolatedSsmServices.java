package de.mibr.hmi;

import de.vw.mib.app.appadapter.CellValue;
import de.vw.mib.app.framework.AppDefinition;
import de.vw.mib.datapool.*;
import de.vw.mib.datapool.internal.AppAdapterListItemControl;
import de.vw.mib.event.HMIEvent;
import de.vw.mib.event.dispatcher.ViewEventDispatcher;
import de.vw.mib.format.FixFormat;
import de.vw.mib.graphics.Gradient;
import de.vw.mib.graphics.image.Image;
import de.vw.mib.log4mib.LoggerFactory;
import de.vw.mib.properties.values.FixFormatterFieldData;
import de.vw.mib.properties.values.LabeledIconValue;
import de.vw.mib.properties.values.SpellerData;
import de.vw.mib.skin.SkinAnimationPool;
import de.vw.mib.skin.SkinImagePool;
import de.vw.mib.view.internal.*;
import de.vw.mib.view.internal.treebuilder.WidgetTreeBuilder;
import java.util.Hashtable;
import java.util.Vector;
import org.dsi.ifc.global.ResourceLocator;

/** Own local data/list/event domain. Native rendering resources are borrowed read-only. */
final class MibrIsolatedSsmServices implements ViewHandlerServices, ViewHandlerAppServices {
    private final ViewHandlerServices resources;
    private final AppDefinition definition;
    private final LocalData data = new LocalData();
    private final ListControlCache lists = new ListControlCache();
    private final Hashtable dynamicLists = new Hashtable();
    private final ViewEventDispatcher ui;
    private final DynamicListItemControlManager dynamic = new DynamicListItemControlManager() {
        public CellValue getCellValue(CellValue value,int list,int row,int column) { return value; }
        public ExtendedListItemControl getListItemControl(int id) {
            Integer key = new Integer(id);
            ExtendedListItemControl control = (ExtendedListItemControl)dynamicLists.get(key);
            if (control == null) { control = new LocalListItemControl(0); dynamicLists.put(key, control); }
            return control;
        }
    };
    private final AppAdapterListItemControlManager adapters = new AppAdapterListItemControlManager() {
        public AppAdapterListItemControl getListItemControl(int id) { return null; }
    };
    private final ViewEventDispatcher events = new ViewEventDispatcher() {
        public void invoke(Runnable action) { ui.invoke(action); }
        public void createAndSubmitBooleanValueEvent(int id,boolean value) { }
        public void createAndSubmitHMIEvent(int id) { }
        public void createAndSubmitIntegerValueEvent(int id,int value) { }
        public void createAndSubmitListItemEvent(int id,int a,int b,int c,int d,String s,long l) { }
        public void createAndSubmitPointEvent(int id,int a,int b,int c,int d) { }
        public void createAndSubmitSpellerValueEvent(int id,String s,int a,int b,int c) { }
        public void createAndSubmitStringValueEvent(int id,String value) { }
        public void createAndSubmitBooleanValueEvent(AppDefinition a,AppDefinition b,int id,boolean value) { }
        public void createAndSubmitHMIEvent(AppDefinition a,AppDefinition b,int id) { }
        public void createAndSubmitIntegerValueEvent(AppDefinition a,AppDefinition b,int id,int value) { }
        public void createAndSubmitListItemEvent(AppDefinition a,AppDefinition b,int id,int w,int x,int y,int z,String s,long l) { }
        public void createAndSubmitPointEvent(AppDefinition a,AppDefinition b,int id,int w,int x,int y,int z) { }
        public void createAndSubmitSpellerValueEvent(AppDefinition a,AppDefinition b,int id,String s,int x,int y,int z) { }
        public void createAndSubmitStringValueEvent(AppDefinition a,AppDefinition b,int id,String value) { }
        public void submitEvent(HMIEvent event) { }
    };

    MibrIsolatedSsmServices(MibrSsmSourceBinding.Binding source) {
        resources = source.services;
        definition = source.appServices.getAppDefinition();
        ui = de.vw.mib.widgets.internal.ServiceManager.eventDispatcher;
        if (resources == null || definition == null || ui == null)
            throw new IllegalStateException("MIBR_SSM_ISOLATION_UNAVAILABLE");
    }
    public FixFormat getFixFormat() { return resources.getFixFormat(); }
    public GlobalExpressionEvaluator getGlobalExpressionEvaluator() { return resources.getGlobalExpressionEvaluator(); }
    public I18nDatapool getI18nDatapool() { return resources.getI18nDatapool(); }
    public ListControlCache getListControlCache() { return lists; }
    public DynamicListItemControlManager getDynamicListItemControlManager() { return dynamic; }
    public LoggerFactory getLoggerFactory() { return resources.getLoggerFactory(); }
    public ModelDatapool getModelDatapool() { return data; }
    public SkinAnimationPool getSkinAnimationPool() { return resources.getSkinAnimationPool(); }
    public SkinImagePool getSkinImagePool() { return resources.getSkinImagePool(); }
    public WidgetAnimator getWidgetAnimator() { return resources.getWidgetAnimator(); }
    public WidgetTreeBuilder getWidgetTreeBuilder() { return resources.getWidgetTreeBuilder(); }
    public AppDefinition getAppDefinition() { return definition; }
    public AppAdapterListItemControlManager getAppAdapterListItemControlManager() { return adapters; }
    public ViewEventDispatcher getViewEventDispatcher() { return events; }
    void clear() { data.clear(); dynamicLists.clear(); }

    private static final class LocalData implements ModelDatapool {
        private final Hashtable values = new Hashtable(), observers = new Hashtable();
        private final Vector updates = new Vector();
        private Object get(int id) { return values.get(new Integer(id)); }
        private void put(int id,Object value) {
            Integer key = new Integer(id);
            if (value == null) values.remove(key); else values.put(key,value);
        }
        void clear() { values.clear(); observers.clear(); updates.removeAllElements(); }
        public boolean getBoolean(int id) { return Boolean.TRUE.equals(get(id)); }
        public int getInteger(int id) { Object v=get(id); return v instanceof Integer?((Integer)v).intValue():0; }
        public long getLong(int id) { Object v=get(id); return v instanceof Long?((Long)v).longValue():0L; }
        public float getFloat(int id) { Object v=get(id); return v instanceof Float?((Float)v).floatValue():0.0f; }
        public String getString(int id) { Object v=get(id); return v instanceof String?(String)v:""; }
        public Object getRawObject(int id) { return get(id); }
        public boolean[] getFlagVector(int id) { Object v=get(id); return v instanceof boolean[]?(boolean[])v:new boolean[0]; }
        public int[] getIntegerArray(int id) { Object v=get(id); return v instanceof int[]?(int[])v:new int[0]; }
        public int[] getIntegerVector(int id) { return getIntegerArray(id); }
        public String[] getStringVector(int id) { Object v=get(id); return v instanceof String[]?(String[])v:new String[0]; }
        public Image[] getImageVector(int id) { Object v=get(id); return v instanceof Image[]?(Image[])v:new Image[0]; }
        public Gradient getGradient(int id) { return (Gradient)get(id); }
        public Gradient[] getGradientVector(int id) { Object v=get(id); return v instanceof Gradient[]?(Gradient[])v:new Gradient[0]; }
        public FixFormatterFieldData getFixFormatterFieldData(int id) { return (FixFormatterFieldData)get(id); }
        public LabeledIconValue getLabeledIconValue(int id) { return (LabeledIconValue)get(id); }
        public ResourceLocator getResourceLocator(int id) { return (ResourceLocator)get(id); }
        public SpellerData getSpellerData(int id) { return (SpellerData)get(id); }
        public void setBoolean(int id,boolean v) { put(id,v?Boolean.TRUE:Boolean.FALSE); }
        public void setInteger(int id,int v) { put(id,new Integer(v)); }
        public void setLong(int id,long v) { put(id,new Long(v)); }
        public void setFloat(int id,float v) { put(id,new Float(v)); }
        public void setString(int id,String v) { put(id,v); }
        public void setRawObject(int id,Object v) { put(id,v); }
        public void setFlagVector(int id,boolean[] v) { put(id,v); }
        public void setIntegerArray(int id,int[] v) { put(id,v); }
        public void setIntegerVector(int id,int[] v) { put(id,v); }
        public void setStringVector(int id,String[] v) { put(id,v); }
        public void setImageVector(int id,Image[] v) { put(id,v); }
        public void setGradient(int id,Gradient v) { put(id,v); }
        public void setGradientVector(int id,Gradient[] v) { put(id,v); }
        public void setFixFormatterFieldData(int id,FixFormatterFieldData v) { put(id,v); }
        public void setLabeledIconValue(int id,LabeledIconValue v) { put(id,v); }
        public void setResourceLocator(int id,ResourceLocator v) { put(id,v); }
        public void setSpellerData(int id,SpellerData v) { put(id,v); }
        public void registerDatapoolUpdate(ModelDatapoolObserver observer) {
            if(observer!=null && !updates.contains(observer)) updates.addElement(observer);
        }
        public void registerObserver(int id,ModelDatapoolObserver observer) { registerObserver(id,observer,false); }
        public void registerObserver(int id,ModelDatapoolObserver observer,boolean immediate) {
            if(observer==null)return;
            Integer key=new Integer(id); Vector list=(Vector)observers.get(key);
            if(list==null){list=new Vector();observers.put(key,list);}
            if(!list.contains(observer))list.addElement(observer);
            // Registration is isolated; it never registers at the original datapool.
            if(immediate)observer.datapoolValueChanged(id);
        }
        public void unregisterObserver(int id,ModelDatapoolObserver observer) {
            Integer key=new Integer(id); Vector list=(Vector)observers.get(key);
            if(list!=null){list.removeElement(observer);if(list.isEmpty())observers.remove(key);}
        }
    }
}
