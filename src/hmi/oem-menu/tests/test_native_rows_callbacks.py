"""Execute the production Ssm rows/dropdown callbacks against small OEM doubles.

The ROM widgets cannot run in a desktop JVM. This harness compiles the actual
MibrOwnedSsmRows, MibrNativeDropdownEditor (including StockBinding), and the
three pure menu/draft models unchanged. Only OEM widget/controller/service APIs
and the narrow existing-list replacement seam are doubles. It proves callback
and cleanup ordering, not native rendering or vehicle behavior.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[2]
H = P / "java/de/mibr/hmi"


STUBS = {
    "de/vw/mib/animation/animations/KeyframeAnimation.java": "package de.vw.mib.animation.animations; public class KeyframeAnimation {}",
    "de/vw/mib/animation/easing/EasingParams.java": "package de.vw.mib.animation.easing; public class EasingParams {}",
    "de/vw/mib/graphics/Color.java": "package de.vw.mib.graphics; public class Color { public static final Color WHITE=new Color(); }",
    "de/vw/mib/graphics/Gradient.java": "package de.vw.mib.graphics; public class Gradient {}",
    "de/vw/mib/graphics/Insets.java": "package de.vw.mib.graphics; public class Insets { public int left,right,top,bottom; }",
    "de/vw/mib/graphics/Point.java": "package de.vw.mib.graphics; public class Point {}",
    "de/vw/mib/graphics/Rectangle.java": "package de.vw.mib.graphics; public class Rectangle { public Rectangle(int x,int y,int w,int h){} }",
    "de/vw/mib/graphics/image/Image.java": "package de.vw.mib.graphics.image; public class Image {}",
    "de/vw/mib/datapool/LocalListItemControl.java": "package de.vw.mib.datapool; public class LocalListItemControl { public LocalListItemControl(int n){} }",
    "de/vw/mib/widgets/event/OutEventAdapter.java": """package de.vw.mib.widgets.event;
public class OutEventAdapter { public void outHMIEventFired(String e){} public void outListItemEventFired(String e,int absolute,int a,int b,int c,String sender,long object){} }
""",
    "de/vw/mib/widgets/list/ListItemTransfer.java": "package de.vw.mib.widgets.list; public interface ListItemTransfer { boolean transferData(de.vw.mib.widgets.models.ListItemModel item,int first,int second); }",
    "de/vw/mib/widgets/models/WidgetModel.java": """package de.vw.mib.widgets.models;
public interface WidgetModel { int get_targetId();String get_name();WidgetModel getParent();de.vw.mib.widgets.controller.WidgetController getController();void set_visible(boolean v);void set_enabled(boolean v);boolean is_visible();boolean is_activated();void init(ViewModel v);void activate();void deActivate();void deInit();int get_height();int get_width();int get_y();void set_height(int h);void set_y(int y); }
""",
    "de/vw/mib/widgets/models/ContainerModel.java": "package de.vw.mib.widgets.models; public interface ContainerModel extends WidgetModel { WidgetModel[] getChildren();void setChildren(WidgetModel[] c); }",
    "de/vw/mib/widgets/models/ViewModel.java": "package de.vw.mib.widgets.models; public interface ViewModel extends ContainerModel { boolean is_activated();void set_opaque(boolean b); }",
    "de/vw/mib/widgets/models/AbstractButtonModel.java": "package de.vw.mib.widgets.models; public interface AbstractButtonModel extends WidgetModel {}",
    "de/vw/mib/widgets/models/ListItemModel.java": """package de.vw.mib.widgets.models;
public interface ListItemModel extends ContainerModel { int getAbsoluteIndex();void set_activatedIndex(int i);void setListItemControl(Object c);void set_selectedButtonRefs(AbstractButtonModel[] b);void set_activatedButtonRefs(AbstractButtonModel[] b);WidgetModel[] get_subItemRefs(); }
""",
    "de/vw/mib/widgets/models/TextAreaModel.java": """package de.vw.mib.widgets.models;
public interface TextAreaModel extends WidgetModel { int LINEBREAKMODE_CHARACTER=1;de.vw.mib.widgets.MockFont get_font();de.vw.mib.graphics.Insets get_padding();int get_lineSpacing();void set_text(String s);void set_lineBreakMode(int i);void set_shorten(boolean b);void set_height(int h);void set_y(int y); }
""",
    "de/vw/mib/widgets/controller/WidgetController.java": """package de.vw.mib.widgets.controller;
import java.util.*;import de.vw.mib.widgets.event.OutEventAdapter;import de.vw.mib.widgets.models.WidgetModel;
public class WidgetController { protected WidgetModel widget;private final ArrayList<OutEventAdapter> events=new ArrayList<OutEventAdapter>();public void setWidget(WidgetModel w){widget=w;}public WidgetModel getWidget(){return widget;}public void addOutEventListener(OutEventAdapter e){if(!events.contains(e))events.add(e);}public void removeOutEventListener(OutEventAdapter e){events.remove(e);}public int listenerCount(){return events.size();}public void emitHmi(String e){for(OutEventAdapter x:new ArrayList<OutEventAdapter>(events))x.outHMIEventFired(e);}public void emitList(String e,int i){for(OutEventAdapter x:new ArrayList<OutEventAdapter>(events))x.outListItemEventFired(e,i,0,0,0,"double",0L);} }
""",
    "de/vw/mib/widgets/Widget.java": """package de.vw.mib.widgets;
import de.vw.mib.widgets.models.*;import de.vw.mib.widgets.controller.WidgetController;
public class Widget implements WidgetModel,de.vw.mib.widgets.interfaces.WidgetCloneable {protected int id,x,y,w=640,h=60,absolute=-1;protected String name="";protected boolean visible=true,enabled=true,activated;protected Widget parent;protected WidgetController controller=new WidgetController();public Widget(){controller.setWidget(this);}public int get_targetId(){return id;}public String get_name(){return name;}public WidgetModel getParent(){return parent;}public WidgetController getController(){return controller;}public void setController(WidgetController c){controller=c;c.setWidget(this);}public void set_visible(boolean v){visible=v;}public void set_enabled(boolean v){enabled=v;}public boolean is_visible(){return visible;}public boolean is_activated(){return activated;}public void init(ViewModel v){}public void init(Object...a){}public void activate(){activated=true;}public void deActivate(){activated=false;}public void deInit(){}public int get_height(){return h;}public int get_width(){return w;}public int get_y(){return y;}public void set_height(int a){h=a;}public void set_y(int a){y=a;}public void set_width(int a){w=a;}public void set_name(String n){name=n;}public void set_targetId(int n){id=n;}public void set_position(int a,int b){x=a;y=b;}public void setUI(Object ui){} }
""",
    "de/vw/mib/widgets/Container.java": """package de.vw.mib.widgets;
import de.vw.mib.widgets.models.*;
public class Container extends Widget implements ContainerModel {protected WidgetModel[] children=new WidgetModel[0];public WidgetModel[] getChildren(){return children;}public void setChildren(WidgetModel[] c){children=c==null?new WidgetModel[0]:c;for(WidgetModel m:children)if(m instanceof Widget)((Widget)m).parent=this;} }
""",
    "de/vw/mib/widgets/View.java": """package de.vw.mib.widgets;import de.vw.mib.widgets.models.*;public class View extends Container implements ViewModel {public void set_opaque(boolean b){} }
""",
    "de/vw/mib/widgets/Button.java": """package de.vw.mib.widgets;
import de.vw.mib.widgets.models.*;import de.vw.mib.graphics.image.Image;import de.vw.mib.graphics.Color;
public class Button extends Container implements AbstractButtonModel {public Image[] imagesState;private final StaticImage state=new StaticImage();public StaticImage get_imageStateRef(){return state;}public void set_imagesBackground(Image[] a){}public void set_imagesState(Image[] a){imagesState=a;}public void set_imageStateColors(Color[] a){}public void set_textColors(Color[] a){}public void set_imageStateRef(StaticImage a){}public void set_activated(boolean b){activated=b;}public void set_textAreaRefs(TextAreaModel[] a){}public void set_interactive(boolean b){} }
""",
    "de/vw/mib/widgets/DropDownButton.java": """package de.vw.mib.widgets;import de.vw.mib.widgets.models.*;import de.vw.mib.widgets.controller.DefaultDropDownButtonController;
public class DropDownButton extends Button {private DropDown popup;private InactiveArea inactive;private boolean open;public DropDownButton(){setController(new DefaultDropDownButtonController());}public void set_dropDownRef(DropDown d){popup=d;}public DropDown get_dropDownRef(){return popup;}public void set_inactiveAreaRef(InactiveArea i){inactive=i;}public InactiveArea get_inactiveAreaRef(){return inactive;}public void set_openDropDown(boolean b){open=b;}public boolean is_openDropDown(){return open;} }
""",
    "de/vw/mib/widgets/TextArea.java": """package de.vw.mib.widgets;import de.vw.mib.widgets.models.*;import de.vw.mib.graphics.Insets;
public class TextArea extends Widget implements TextAreaModel {private String text;private int line;private boolean shorten=true;public String text(){return text;}public void set_text(String s){text=s;}public MockFont get_font(){return new MockFont();}public Insets get_padding(){return new Insets();}public int get_lineSpacing(){return 2;}public void set_lineBreakMode(int i){line=i;}public void set_shorten(boolean b){shorten=b;} }
""",
    "de/vw/mib/widgets/MockFont.java": "package de.vw.mib.widgets; public class MockFont {public int getSize(){return 20;}}",
    "de/vw/mib/widgets/ListItem.java": """package de.vw.mib.widgets;import de.vw.mib.widgets.models.*;import de.vw.mib.widgets.controller.DefaultListItemController;import de.vw.mib.widgets.ui.ListItemUI;
public class ListItem extends Container implements ListItemModel {private int index=-1,activatedIndex=-1;private Object control;public ListItem(){setController(new DefaultListItemController());}public void setAbsoluteIndex(int n){index=n;}public int getAbsoluteIndex(){return index;}public void set_activatedIndex(int i){activatedIndex=i;}public int get_activatedIndex(){return activatedIndex;}public void setListItemControl(Object c){control=c;}public void set_selectedButtonRefs(AbstractButtonModel[] b){}public void set_activatedButtonRefs(AbstractButtonModel[] b){}public WidgetModel[] get_subItemRefs(){return new WidgetModel[0];} }
""",
    "de/vw/mib/widgets/WidgetList.java": """package de.vw.mib.widgets;import de.vw.mib.widgets.models.*;import de.vw.mib.widgets.list.ListItemTransfer;import de.vw.mib.widgets.controller.DefaultWidgetListController;
public class WidgetList extends Container {private ListItemTransfer transfer;private int selected=-1,focused=-1,first=-1;public WidgetList(){setController(new DefaultWidgetListController());}public void setListItemTransfer(ListItemTransfer t){transfer=t;}public ListItemTransfer getListItemTransfer(){return transfer;}public void set_selectedIndex(int i){selected=i;}public int get_selectedIndex(){return selected;}public void setFocusedIndex(int i){focused=i;}public int getFocusedIndex(){return focused;}public int getFirstVisibleIndex(){return first;}public void snap(int i,int mode){first=i;}public int get_itemCount(){return children.length;}public void init(Object...a){}public void init(ViewModel v){}public void setChildren(WidgetModel[] c){super.setChildren(c);for(int i=0;i<children.length;i++)if(children[i] instanceof ListItem)((ListItem)children[i]).setAbsoluteIndex(i);} }
""",
    "de/vw/mib/widgets/DropDown.java": "package de.vw.mib.widgets; public class DropDown extends WidgetList {public void init(Object...a){} }",
    "de/vw/mib/widgets/InactiveArea.java": "package de.vw.mib.widgets;import de.vw.mib.graphics.Rectangle;public class InactiveArea extends Container {public void init(Object...a){}public void set_exclusionArea(Rectangle r){} }",
    "de/vw/mib/widgets/StaticImage.java": "package de.vw.mib.widgets;import de.vw.mib.graphics.*;import de.vw.mib.animation.easing.EasingParams;import de.vw.mib.widgets.ui.StaticImageUI;public class StaticImage extends Widget {public void init(Object...a){}public void setUI(StaticImageUI u){} }",
    "de/vw/mib/widgets/controller/DefaultPushButtonController.java": "package de.vw.mib.widgets.controller;public class DefaultPushButtonController extends WidgetController {}",
    "de/vw/mib/widgets/controller/DefaultListItemController.java": "package de.vw.mib.widgets.controller;public class DefaultListItemController extends WidgetController {}",
    "de/vw/mib/widgets/controller/DefaultWidgetListController.java": "package de.vw.mib.widgets.controller;public class DefaultWidgetListController extends WidgetController {}",
    "de/vw/mib/widgets/controller/DefaultInactiveAreaController.java": "package de.vw.mib.widgets.controller;public class DefaultInactiveAreaController extends WidgetController {}",
    "de/vw/mib/widgets/controller/DefaultDropDownButtonController.java": """package de.vw.mib.widgets.controller;
import de.vw.mib.widgets.*;
public class DefaultDropDownButtonController extends DefaultPushButtonController {public boolean throwClose;public void fire_closeDropDown(){if(throwClose)throw new IllegalStateException("test-close");DropDownButton b=(DropDownButton)getWidget();boolean was=b.is_openDropDown();b.set_openDropDown(false);if(was)emitHmi("dropDownClosed");}}
""",
    "de/vw/mib/widgets/ui/DropDownButtonUI.java": "package de.vw.mib.widgets.ui;public class DropDownButtonUI {}",
    "de/vw/mib/widgets/ui/DropDownUI.java": "package de.vw.mib.widgets.ui;public class DropDownUI {}",
    "de/vw/mib/widgets/ui/ContainerUI.java": "package de.vw.mib.widgets.ui;public class ContainerUI {}",
    "de/vw/mib/widgets/ui/ListItemUI.java": "package de.vw.mib.widgets.ui;public class ListItemUI {}",
    "de/vw/mib/widgets/ui/StaticImageUI.java": "package de.vw.mib.widgets.ui;public class StaticImageUI {}",
    "de/vw/mib/widgets/ui/WidgetListUI.java": "package de.vw.mib.widgets.ui;public class WidgetListUI {}",
    "de/vw/mib/widgets/internal/ServiceManager.java": "package de.vw.mib.widgets.internal;public class ServiceManager {public static Dispatcher eventDispatcher;public static class Dispatcher {public void invoke(Runnable r){de.mibr.hmi.Harness.enqueue(r);}}public static ServiceManager instance;}",
    "de/vw/mib/view/internal/AbstractViewHandler.java": """package de.vw.mib.view.internal;import de.vw.mib.widgets.*;import de.vw.mib.widgets.models.*;import de.vw.mib.widgets.interfaces.WidgetCloneable;
public class AbstractViewHandler {public int created,destroyed,failCreate=-1;public WidgetCloneable createWidgetCloneable(WidgetCloneable w){if(created==failCreate)throw new IllegalStateException("partial-clone");created++;return de.mibr.hmi.Harness.cloneRow((ListItem)w);}public void destroyWidgetCloneable(WidgetCloneable w){destroyed++;((WidgetModel)w).deInit();}}
""",
    "de/vw/mib/widgets/interfaces/WidgetCloneable.java": "package de.vw.mib.widgets.interfaces;public interface WidgetCloneable {}",
    "de/vw/mib/widgets/list/Unused.java": "package de.vw.mib.widgets.list;public class Unused {}",
    "de/mibr/hmi/MibrHomeList.java": """package de.mibr.hmi;import de.vw.mib.widgets.*;import de.vw.mib.widgets.models.*;
public final class MibrHomeList {public static int replacements;public static void replaceOwnedSsmItems(WidgetList list,ViewModel view,WidgetModel[] items){list.setChildren(items);replacements++;}}
""",
    "de/mibr/hmi/MibrOemDropdownStyle.java": """package de.mibr.hmi;import de.vw.mib.graphics.*;import de.vw.mib.graphics.image.Image;import de.vw.mib.widgets.Button;
final class MibrOemDropdownStyle {final Image[] background=new Image[1];static MibrOemDropdownStyle resolve(){return new MibrOemDropdownStyle();}void bind(Button b,boolean option){}}
""",
    "de/mibr/hmi/MibrOwnedWidgets.java": """package de.mibr.hmi;import de.vw.mib.widgets.*;import de.vw.mib.widgets.models.*;
final class MibrOwnedWidgets {static Button createTouchButton(Object a,Object b,String n,int id,int x,int y,int w,int h){Button b0=new Button();b0.set_name(n);b0.set_targetId(id);b0.set_width(w);b0.set_height(h);b0.set_position(x,y);return b0;}static TextArea createLabel(Object a,TextAreaModel s,String t,String n,int id,int x,int y,int w,int h){TextArea t0=new TextArea();t0.set_name(n);t0.set_targetId(id);t0.set_text(t);t0.set_width(w);t0.set_height(h);t0.set_position(x,y);return t0;}}
""",
    "de/mibr/hmi/MibrOemSsmTemplate.java": """package de.mibr.hmi;import de.vw.mib.widgets.*;import de.vw.mib.widgets.models.*;
final class MibrOemSsmTemplate {static boolean syncScrollbar(Binding b,boolean replaced){return true;}static final int VALUE_TARGET_ID=53708779,VALUE_LABEL_TARGET_ID=64398879,PLAIN_TEXT_TARGET_ID=101603979,OPENER_TARGET_ID=40267630,PLAIN_BUTTON_TARGET_ID=4894361,VALUE_TEXT_TARGET_ID=70740890,OPTION_TEXT_TARGET_ID=47818560,CHECK_TARGET_ID=19737792,CHECK_BUTTON_TARGET_ID=103710118,CHECK_TEXT_TARGET_ID=119782300;
static WidgetModel target(WidgetModel root,int id,Class type){WidgetModel got=find(root,id,type);if(got==null)throw new IllegalStateException("target:"+id);return got;}static WidgetModel find(WidgetModel root,int id,Class type){if(root==null)return null;if(type.isInstance(root)&&root.get_targetId()==id)return root;if(root instanceof ContainerModel){WidgetModel[] c=((ContainerModel)root).getChildren();for(WidgetModel w:c){WidgetModel got=find(w,id,type);if(got!=null)return got;}}return null;}
static final class Binding {final ViewModel view;final ListItem plain,value,check,option;final DropDownButton opener;final DropDown popup;final WidgetList mainList,options;final TextArea title;final Button close;Binding(ViewModel v,ListItem p,ListItem x,ListItem k,DropDownButton b,DropDown d,WidgetList l,TextArea t,Button c,WidgetList o,ListItem i){view=v;plain=p;value=x;check=k;opener=b;popup=d;mainList=l;title=t;close=c;options=o;option=i;}}
}
""",
    "de/mibr/hmi/MibrRgiCockpit.java": "package de.mibr.hmi;final class MibrRgiCockpit {static String statusLine(){return \"\";}static boolean demoRequested(){return false;}static void requestDemo(boolean enabled){}}",
    "de/mibr/hmi/MibrServiceHealth.java": "package de.mibr.hmi;final class MibrServiceHealth {static String statusLine(){return \"\";}}",
    "de/mibr/hmi/MibrCalibration.java": "package de.mibr.hmi;final class MibrCalibration {static boolean on(){return false;}static void set(boolean enabled){}}",
}


HARNESS = r'''package de.mibr.hmi;
import de.vw.mib.widgets.*;import de.vw.mib.widgets.models.*;import de.vw.mib.widgets.controller.*;import de.vw.mib.widgets.event.*;import de.vw.mib.widgets.list.*;import de.vw.mib.view.internal.AbstractViewHandler;
import java.util.*;
public final class Harness {
 static final ArrayList<Runnable> queue=new ArrayList<Runnable>();static MibrOemSsmTemplate.Binding activeStock;
 public static void enqueue(Runnable r){queue.add(r);}
 static void check(boolean b,String s){if(!b)throw new AssertionError(s);}
 static void drain(){int n=0;while(!queue.isEmpty()){if(++n>100)throw new AssertionError("queue loop");queue.remove(0).run();}}
 static TextArea text(int id,int width){TextArea t=new TextArea();t.set_targetId(id);t.set_width(width);return t;}
 static Button button(int id){Button b=new Button();b.set_targetId(id);b.set_width(id==MibrOemSsmTemplate.PLAIN_BUTTON_TARGET_ID?1139:500);b.set_height(id==MibrOemSsmTemplate.PLAIN_BUTTON_TARGET_ID?94:60);return b;}
 static DropDownButton opener(){DropDownButton b=new DropDownButton();b.set_targetId(MibrOemSsmTemplate.OPENER_TARGET_ID);b.set_y(100);return b;}
 static ListItem row(int id,WidgetModel...children){ListItem l=new ListItem();l.set_targetId(id);l.setChildren(children);return l;}
 public static ListItem cloneRow(ListItem src){WidgetModel[] c=src.getChildren();WidgetModel[] copy=new WidgetModel[c.length];for(int i=0;i<c.length;i++){WidgetModel w=c[i];if(w instanceof TextArea){TextArea t=text(w.get_targetId(),w.get_width());copy[i]=t;}else if(w instanceof DropDownButton){DropDownButton d=opener();d.set_width(w.get_width());if(activeStock!=null){d.set_dropDownRef(activeStock.popup);d.set_inactiveAreaRef(activeStock.opener.get_inactiveAreaRef());}copy[i]=d;}else if(w instanceof Button){copy[i]=button(w.get_targetId());}}return row(src.get_targetId(),copy);}
 static MibrOemSsmTemplate.Binding stock(){
  View view=new View();view.set_height(480);view.set_width(800);view.set_targetId(24786208);
  TextArea title=text(1,600);Button back=button(2);
  WidgetList main=new WidgetList();ListItem plain=row(110,text(MibrOemSsmTemplate.PLAIN_TEXT_TARGET_ID,500),button(MibrOemSsmTemplate.PLAIN_BUTTON_TARGET_ID));
  ListItem value=row(MibrOemSsmTemplate.VALUE_TARGET_ID,text(MibrOemSsmTemplate.VALUE_LABEL_TARGET_ID,300),text(MibrOemSsmTemplate.VALUE_TEXT_TARGET_ID,200),opener());
  ListItem checkRow=row(MibrOemSsmTemplate.CHECK_TARGET_ID,button(MibrOemSsmTemplate.CHECK_BUTTON_TARGET_ID),text(MibrOemSsmTemplate.CHECK_TEXT_TARGET_ID,500));
  main.setChildren(new WidgetModel[]{plain,value,checkRow});ListItem option=row(37984426,text(MibrOemSsmTemplate.OPTION_TEXT_TARGET_ID,460),button(112352865));option.set_height(60);
  WidgetList opts=new WidgetList();opts.setChildren(new WidgetModel[]{option});opts.set_height(120);DropDown popup=new DropDown();popup.set_width(600);popup.set_height(180);InactiveArea inactive=new InactiveArea();opener().set_dropDownRef(popup);
  DropDownButton open=(DropDownButton)value.getChildren()[2];open.set_dropDownRef(popup);open.set_inactiveAreaRef(inactive);open.set_width(500);
  view.setChildren(new WidgetModel[]{main,value,popup});
  activeStock=new MibrOemSsmTemplate.Binding(view,plain,value,checkRow,open,popup,main,title,back,opts,option);return activeStock;
 }
 static void popupCallbacks(){
  MibrOemSsmTemplate.Binding s=stock();ListItemTransfer original=new ListItemTransfer(){public boolean transferData(ListItemModel i,int a,int b){return false;}};s.options.setListItemTransfer(original);
  MibrPopupEditorModel model=new MibrPopupEditorModel();final int[] changed={0};MibrNativeDropdownEditor.StockBinding binding=new MibrNativeDropdownEditor.StockBinding(s,model,new MibrNativeDropdownEditor.Sink(){public void changed(){changed[0]++;}public void committed(int i){}});
  check(!model.directToggle(1) && !model.liveViewGated(1) && model.open(1),"r14 view dropdown (Voll/Wide) opens as a popup");model.cancel();
  binding.prepare(s.opener,3);check(model.opened()==3,"surface choice popup prepared");check(s.option.get_height()==60 && s.popup.get_height()==240 && s.options.get_height()==180,"OEM option height is fixed; three rows fit inside the stock frame padding");
  check(s.option.getChildren().length==2 && s.option.getChildren()[1].get_targetId()==112352865,"fixture option children");check(MibrOemSsmTemplate.target(s.option,112352865,Button.class)!=null,"fixture nested option button");s.option.setAbsoluteIndex(1);check(binding.transferData(s.option,0,0),"row transfer");check(s.option.get_height()==60 && s.option.getChildren()[1].get_height()==60,"native option and Button geometry unchanged");DefaultDropDownButtonController ctl=(DefaultDropDownButtonController)s.opener.getController();
  int old=model.operationToken();ctl.emitHmi("dropDownClosed");check(model.opened()==3,"close is deferred");
  s.option.getController().emitList("buttonReleased",0);check("map".equals(model.draft(3)),"surface choice committed after earlier native close callback");
  drain();check(model.opened()==-1 && s.popup.get_height()==180 && s.options.get_height()==120,"old close callback harmless and OEM popup height restored");
  binding.prepare(s.opener,3);ctl.emitHmi("dropDownClosed");binding.prepare(s.opener,7);int newer=model.operationToken();check(newer!=old && model.opened()==7,"reopen has distinct operation token");drain();check(model.opened()==7,"stale queued close must not cancel reopened popup");
  ctl.emitHmi("dropDownClosed");drain();check(model.opened()==-1,"outside close cancels current operation");
  for(int i=0;i<8;i++){binding.prepare(s.opener,3);binding.close();check(!binding.isOpen(),"cycle closed");}
  binding.prepare(s.opener,3);ctl.throwClose=true;boolean threw=false;try{binding.detach();}catch(Throwable expected){threw=true;}check(threw,"injected close exception surfaced");
  check(s.options.getListItemTransfer()==original,"detach restores transfer even when close throws");
 }
 static void rowRefreshAndPartialClone(){
  MibrOemSsmTemplate.Binding s=stock();AbstractViewHandler handler=new AbstractViewHandler();final int[] leaves={0};WidgetModel[] original=s.mainList.getChildren();ListItemTransfer originalTransfer=new ListItemTransfer(){public boolean transferData(ListItemModel i,int a,int b){return false;}};s.mainList.setListItemTransfer(originalTransfer);MibrOwnedSsmRows rows=new MibrOwnedSsmRows(handler,s,new Runnable(){public void run(){leaves[0]++;}},new MibrPopupEditorModel(),null);
  rows.open();check(s.mainList.get_itemCount()==8 && s.mainList.get_selectedIndex()==0,"main list expected 8 rows and selected=0; got count="+s.mainList.get_itemCount()+" selected="+s.mainList.get_selectedIndex());
  int[] kinds={MibrOemSsmTemplate.VALUE_TARGET_ID,MibrOemSsmTemplate.VALUE_TARGET_ID,MibrOemSsmTemplate.CHECK_TARGET_ID,MibrOemSsmTemplate.CHECK_TARGET_ID,MibrOemSsmTemplate.CHECK_TARGET_ID,MibrOemSsmTemplate.VALUE_TARGET_ID,110,110};
  for(int r=0;r<8;r++)check(s.mainList.getChildren()[r].get_targetId()==kinds[r],"main row "+r+" stock template");
  TextArea viewLabel=(TextArea)MibrOemSsmTemplate.target(s.mainList.getChildren()[0],MibrOemSsmTemplate.VALUE_LABEL_TARGET_ID,TextArea.class);
  check("Ansicht".equals(viewLabel.text()),"view dropdown row label");
  TextArea viewsLink=(TextArea)MibrOemSsmTemplate.target(s.mainList.getChildren()[6],MibrOemSsmTemplate.PLAIN_TEXT_TARGET_ID,TextArea.class);
  check("Ansichten".equals(viewsLink.text()),"Ansichten link label");
  ((ListItemModel)s.mainList.getChildren()[6]).getController().emitList("buttonReleased",6);drain();
  check(s.mainList.get_itemCount()==7,"Ansichten: seven view rows");
  s.close.getController().emitHmi("released");drain();
  check(s.mainList.get_itemCount()==8,"Ansichten Back restores the main list");
  TextArea link=(TextArea)MibrOemSsmTemplate.target(s.mainList.getChildren()[7],MibrOemSsmTemplate.PLAIN_TEXT_TARGET_ID,TextArea.class);
  check("Erweitert".equals(link.text()),"Erweitert link label");
  ((ListItemModel)s.mainList.getChildren()[7]).getController().emitList("buttonReleased",7);drain();
  check(s.mainList.get_itemCount()==6,"Erweitert: 3 settings, Motorart, Scaling, Diagnose");
  ((ListItemModel)s.mainList.getChildren()[4]).getController().emitList("buttonReleased",4);drain();
  check(s.mainList.get_itemCount()==2,"Scaling page has exactly two dropdowns");
  TextArea mainScale=(TextArea)MibrOemSsmTemplate.target(s.mainList.getChildren()[0],MibrOemSsmTemplate.VALUE_LABEL_TARGET_ID,TextArea.class);
  TextArea clusterScale=(TextArea)MibrOemSsmTemplate.target(s.mainList.getChildren()[1],MibrOemSsmTemplate.VALUE_LABEL_TARGET_ID,TextArea.class);
  check("Zoomfaktor Hauptdisplay".equals(mainScale.text()) && "Zoomfaktor Virtual Cockpit".equals(clusterScale.text()),"scaling row labels");
  s.close.getController().emitHmi("released");drain();
  check(s.mainList.get_itemCount()==6,"Scaling Back returns to Erweitert");
  ((ListItemModel)s.mainList.getChildren()[5]).getController().emitList("buttonReleased",5);drain();
  check(s.mainList.get_itemCount()==8,"Diagnostics: seven vehicle-data lines plus the read-only service state");
  TextArea state=(TextArea)MibrOemSsmTemplate.target(s.mainList.getChildren()[7],MibrOemSsmTemplate.PLAIN_TEXT_TARGET_ID,TextArea.class);
  check("Dienst nicht verbunden".equals(state.text()),"service state text");
  ((ListItemModel)s.mainList.getChildren()[0]).getController().emitList("buttonReleased",0);drain();
  check(s.mainList.get_itemCount()==8,"service state row is not an action");
  s.close.getController().emitHmi("released");drain();
  check(s.mainList.get_itemCount()==6,"Diagnose Back returns to Erweitert");
  s.close.getController().emitHmi("released");drain();
  check(s.mainList.get_itemCount()==8,"Erweitert Back restores the main list");
  TextArea eta=(TextArea)MibrOemSsmTemplate.target(s.mainList.getChildren()[2],MibrOemSsmTemplate.CHECK_TEXT_TARGET_ID,TextArea.class);
  Button unknownButton=(Button)MibrOemSsmTemplate.target(s.mainList.getChildren()[2],MibrOemSsmTemplate.CHECK_BUTTON_TARGET_ID,Button.class);check("Ankunftszeit".equals(eta.text()) && unknownButton.imagesState==null && unknownButton.get_imageStateRef().is_visible() && !unknownButton.is_activated(),"stock CHECK row; unknown shows the empty OEM box");
  ((ListItemModel)s.mainList.getChildren()[2]).getController().emitList("buttonReleased",2);drain();
  Button draftedButton=(Button)MibrOemSsmTemplate.target(s.mainList.getChildren()[2],MibrOemSsmTemplate.CHECK_BUTTON_TARGET_ID,Button.class);check(draftedButton.get_imageStateRef().is_visible() && draftedButton.is_activated() && draftedButton.imagesState==null,"checkbox toggles to yes without image graft");
  TextArea surface=(TextArea)MibrOemSsmTemplate.target(s.mainList.getChildren()[1],MibrOemSsmTemplate.VALUE_TEXT_TARGET_ID,TextArea.class);
  check("".equals(surface.text()),"unknown choice shows no developer marker");
  s.mainList.set_selectedIndex(2);s.mainList.setFocusedIndex(1);s.mainList.snap(1,0);
  int made=handler.created,disposed=handler.destroyed,updates=MibrHomeList.replacements;
  WidgetModel kept=s.mainList.getChildren()[1];rows.changed();drain();
  check(s.mainList.get_selectedIndex()==2 && s.mainList.getFocusedIndex()==1 && s.mainList.getFirstVisibleIndex()==1,"same-page refresh preserves selection, focus, and viewport");
  check(handler.created==made && handler.destroyed==disposed && MibrHomeList.replacements==updates && s.mainList.getChildren()[1]==kept,"same-page update retains OEM row identity without widget-list replacement");
  rows.changed();drain();check(handler.created==made && handler.destroyed==disposed,"repeat snapshot refresh has zero clone churn");
  rows.detach();check(s.mainList.getChildren()==original,"detach restores original children");check(s.mainList.getListItemTransfer()==originalTransfer,"detach restores original transfer");check(handler.created==handler.destroyed,"all allocated rows disposed exactly once");
  MibrOemSsmTemplate.Binding failing=stock();ListItemTransfer saved=new ListItemTransfer(){public boolean transferData(ListItemModel i,int a,int b){return false;}};failing.mainList.setListItemTransfer(saved);AbstractViewHandler fh=new AbstractViewHandler();MibrOwnedSsmRows fr=new MibrOwnedSsmRows(fh,failing,new Runnable(){public void run(){}});fr.open();((ListItemModel)failing.mainList.getChildren()[0]).getController().emitList("buttonReleased",0);drain();WidgetModel popupRow=failing.mainList.getChildren()[2]; // the first TWO canonical rows are native binary controlsButton popupButton=(Button)MibrOemSsmTemplate.target(popupRow,MibrOemSsmTemplate.OPENER_TARGET_ID,Button.class);popupButton.getController().emitHmi("pressed");DefaultDropDownButtonController popupController=(DefaultDropDownButtonController)popupButton.getController();popupController.throwClose=true;boolean closeThrew=false;try{fr.detach();}catch(Throwable expected){closeThrew=true;}check(closeThrew,"rows detach reports injected native close failure");check(failing.mainList.getChildren().length==2 && failing.mainList.getListItemTransfer()==saved,"rows detach continues restoring OEM children and transfer after close exception");check(fh.created==fh.destroyed,"rows detach still destroys all masters after close exception");fr.detach();check(fh.created==fh.destroyed,"retry after failure does not double-destroy masters");
  AbstractViewHandler partial=new AbstractViewHandler();partial.failCreate=1;MibrOemSsmTemplate.Binding p=stock();MibrOwnedSsmRows r=new MibrOwnedSsmRows(partial,p,new Runnable(){public void run(){}});boolean threw=false;try{r.open();}catch(Throwable expected){threw=true;}check(threw,"partial clone fault injected");r.detach();check(partial.created==1 && partial.destroyed==1,"partial clone released on detach");
 }
 public static void main(String[] args){MibrI18n.forced="de_DE";MibrMenuLayout.storedPath=System.getProperty("mibr.menu.standard");de.vw.mib.widgets.internal.ServiceManager.eventDispatcher=new de.vw.mib.widgets.internal.ServiceManager.Dispatcher();popupCallbacks();drain();if(!"popup".equals(System.getProperty("mibr.test.scenario"))){rowRefreshAndPartialClone();drain();}System.out.println("NATIVE_ROWS_CALLBACKS_PASS");}
}'''


class NativeRowsCallbacks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="mibr-native-rows-callbacks-"))
        configured = os.environ.get("MIBR_TEST_JAVA_HOME")
        cls.javac = str(Path(configured) / "bin/javac") if configured else shutil.which("javac")
        cls.java = str(Path(configured) / "bin/java") if configured else shutil.which("java")
        if os.name == "nt" and configured:
            cls.javac += ".exe"
            cls.java += ".exe"
        if not cls.javac or not cls.java:
            raise RuntimeError("Existing JDK required; set MIBR_TEST_JAVA_HOME (no installation/setup)")
        sources = []
        for relative, body in STUBS.items():
            path = cls.tmp / "src" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
            sources.append(str(path))
        harness = cls.tmp / "src/de/mibr/hmi/Harness.java"
        harness.parent.mkdir(parents=True, exist_ok=True)
        harness.write_text(HARNESS, encoding="utf-8")
        sources.append(str(harness))
        for name in ("MibrControlProtocol", "MibrControlClient", "MibrControlSession", "MibrOwnedSsmRows", "MibrOemPageEntry", "MibrElementDetailRows", "MibrNativeDropdownEditor",
                     "MibrElementSpec", "MibrElementEngine", "MibrElementTree", "MibrCanonicalElementMenu", "MibrPopupEditorModel",
                     "MibrDraftChoiceModel", "MibrScalingState", "MibrCarPlayMenuModel", "MibrVdataDiag", "MibrEngineState", "MibrViewState", "MibrMenuDefinition", "MibrI18n",
                     "MibrDurableSwitch", "MibrPlatformDefaults", "MibrSafeArea", "MibrGpsDemoState", "MibrVersionInfo",
                     "MibrMenuCatalog", "MibrMenuFunctions", "MibrMenuLayout", "MibrExpert",
                     "MibrV3Protocol", "MibrV3Client", "MibrV3Session",
                     "MibrSettingsCatalog"):
            sources.append(str(H / (name + ".java")))
        cls.out = cls.tmp / "classes"
        cls.out.mkdir()
        run = subprocess.run([cls.javac, "-encoding", "UTF-8", "-source", "8", "-target", "8", "-d", str(cls.out)] + sources,
                             capture_output=True, text=True)
        if run.returncode:
            raise AssertionError(run.stdout + run.stderr)

    def test_native_rows_popup_callbacks_and_cleanup(self):
        run = subprocess.run([self.java, "-Dmibr.test.scenario=popup",
                              "-Dmibr.menu.standard=" + str(ROOT / "tools/menu-editor/standard-menu.txt"),
                              "-cp", str(self.out), "de.mibr.hmi.Harness"],
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("NATIVE_ROWS_CALLBACKS_PASS", run.stdout)

    def test_legacy_r56_row_refresh_fixture(self):
        self.skipTest("legacy R56 row-refresh fixture is not retained in the public source tree; current popup callbacks are tested separately")


if __name__ == "__main__":
    unittest.main()
