# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import subprocess
import os,tempfile,shutil
r=Path(__file__).resolve().parents[1]
tmp=tempfile.TemporaryDirectory()
p=Path(tmp.name);work=p/'host-model';work.mkdir()
files={
'de/vw/mib/widgets/models/WidgetModel.java':'''package de.vw.mib.widgets.models;public interface WidgetModel {int get_x();int get_y();int get_width();int get_height();int get_targetId();WidgetModel getParent();boolean is_activated();}''',
'de/vw/mib/widgets/models/ContainerModel.java':'''package de.vw.mib.widgets.models;public interface ContainerModel extends WidgetModel {WidgetModel[] getChildren();void setChildren(WidgetModel[] a);}''',
'de/vw/mib/widgets/models/ViewModel.java':'''package de.vw.mib.widgets.models;public interface ViewModel extends WidgetModel {}''',
'de/vw/mib/widgets/interfaces/Adjustable.java':'''package de.vw.mib.widgets.interfaces;import de.vw.mib.widgets.event.AdjustmentListener;public interface Adjustable {int getMinimum();int getMaximum();int getValue();int getBlockIncrement();void addAdjustmentListener(AdjustmentListener l);void removeAdjustmentListener(AdjustmentListener l);}''',
'de/vw/mib/widgets/event/AdjustmentListener.java':'''package de.vw.mib.widgets.event;import de.vw.mib.widgets.interfaces.Adjustable;public interface AdjustmentListener {void adjustmentValueChanged(Adjustable a,int n);}''',
'de/vw/mib/widgets/Widget.java':'''package de.vw.mib.widgets;import de.vw.mib.widgets.models.*;public class Widget implements WidgetModel {public int x,y,w=800,h=356,id,disposed;public boolean visible,active;public WidgetModel parent;public int get_x(){return x;}public int get_y(){return y;}public int get_width(){return w;}public int get_height(){return h;}public int get_targetId(){return id;}public WidgetModel getParent(){return parent;}public boolean is_activated(){return active;}public void set_x(int v){x=v;}public void set_y(int v){y=v;}public void set_width(int v){w=v;}public void set_height(int v){h=v;}public void set_visible(boolean v){visible=v;}public void repaint(){}public void activate(){active=true;}public void deActivate(){active=false;}public void deInit(){disposed++;}}''',
'de/vw/mib/widgets/WidgetList.java':'''package de.vw.mib.widgets;import de.vw.mib.widgets.interfaces.Adjustable;import de.vw.mib.widgets.event.AdjustmentListener;import java.util.Vector;public class WidgetList extends Widget implements Adjustable {public int max=1000,value,min;public Vector<AdjustmentListener> listeners=new Vector<AdjustmentListener>();public int getMinimum(){return min;}public int getMaximum(){return max;}public int getValue(){return value;}public int getBlockIncrement(){return h;}public int get_itemCount(){return 20;}public void addAdjustmentListener(AdjustmentListener l){if(!listeners.contains(l))listeners.add(l);l.adjustmentValueChanged(this,0);}public void removeAdjustmentListener(AdjustmentListener l){listeners.remove(l);}public void notifyChange(){for(AdjustmentListener l:listeners)l.adjustmentValueChanged(this,0);}}''',
'de/mibr/hmi/MibrOwnedStaticImage.java':'''package de.mibr.hmi;import de.vw.mib.widgets.Widget;import de.vw.mib.widgets.models.ViewModel;public class MibrOwnedStaticImage extends Widget {public String path;public MibrOwnedStaticImage(String p){path=p;}public void init(Object... args){for(int i=0;i<args.length-1;i++)if(args[i] instanceof String)id=((Integer)args[i+1]).intValue();}public void init(ViewModel v){}public void setUI(Object ui){}}''',
'de/mibr/hmi/MibrScrollBarUI.java':'''package de.mibr.hmi;public class MibrScrollBarUI {}''',
'de/mibr/hmi/MibrOemSsmTemplate.java':'''package de.mibr.hmi;public class MibrOemSsmTemplate {static void diag(String s){}}''',
'de/mibr/hmi/IndicatorTest.java':'''package de.mibr.hmi;
import de.vw.mib.widgets.*;import de.vw.mib.widgets.models.*;
public class IndicatorTest {
 static class Node extends Widget implements ContainerModel,ViewModel {WidgetModel[] a;public WidgetModel[] getChildren(){return a;}public void setChildren(WidgetModel[] b){a=b;}}
 static void check(boolean b){if(!b)throw new RuntimeException("INDICATOR_TEST_FAILED");}
 static Widget child(Node p,int id){for(WidgetModel w:p.a)if(w.get_targetId()==id)return (Widget)w;throw new RuntimeException("missing child");}
 public static void main(String[] args){
  System.setProperty("mibr.hmi.scrollbar.theme","seat_red");
  Node parent=new Node();parent.active=true;WidgetList l=new WidgetList();l.parent=parent;parent.a=new WidgetModel[]{l};
  MibrScrollIndicator i=MibrScrollIndicator.attach(l,parent);check(i!=null&&parent.a.length==3&&l.listeners.size()==1);
  Widget t=child(parent,-8812),track=child(parent,-8811);check(((MibrOwnedStaticImage)t).path.equals("/icons/mibr_scroll_thumb_seat_red.png"));check(t.visible&&track.visible&&t.h>=36&&t.h<=l.h&&t.y==l.y);
  check(MibrScrollIndicator.attach(l,parent)==null&&parent.a.length==3&&l.listeners.size()==1);
  l.value=l.max;l.notifyChange();check(t.y+t.h==l.y+l.h);
  l.value=-100;l.notifyChange();check(t.y==l.y);
  l.value=l.max+100;l.notifyChange();check(t.y+t.h==l.y+l.h);
  l.max=0;l.notifyChange();check(!t.visible&&!track.visible);
  l.max=1200;l.value=250;l.h=240;l.notifyChange();check(t.visible&&t.y>=l.y&&t.y+t.h<=l.y+l.h);
  i.detach();check(parent.a.length==1&&parent.a[0]==l&&l.listeners.isEmpty()&&t.disposed==1&&track.disposed==1);
  i.detach();i.update();check(t.disposed==1&&parent.a.length==1);
  i=MibrScrollIndicator.attach(l,parent);check(i!=null&&l.listeners.size()==1&&parent.a.length==3);i.detach();
  System.clearProperty("mibr.hmi.scrollbar.theme");i=MibrScrollIndicator.attach(l,parent);
  check(i!=null&&((MibrOwnedStaticImage)child(parent,-8812)).path.equals("/icons/mibr_scroll_thumb_v2.png"));i.detach();
  l.parent=new Widget();check(MibrScrollIndicator.attach(l,parent)==null&&l.listeners.isEmpty());
  System.out.println("INDICATOR_HOST=PASS attach scroll clamp resize hide detach idempotence reentry duplicate_guard bad_parent");
 }
}'''}
for pkg,cls in [('graphics','Gradient'),('graphics','Insets'),('graphics/image','Image'),('animation/easing','EasingParams')]:
 files['de/vw/mib/'+pkg+'/'+cls+'.java']='package de.vw.mib.'+pkg.replace('/','.')+';public class '+cls+' {}'
files['de/vw/mib/graphics/Color.java']='package de.vw.mib.graphics;public class Color {public Color(int a){}}'
for n,s in files.items():
 f=work/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s)
files['de/mibr/hmi/MibrIconState.java']='package de.mibr.hmi;public class MibrIconState {static final String ROOT="/icons/";}'
f=work/'de/mibr/hmi/MibrIconState.java';f.write_text(files['de/mibr/hmi/MibrIconState.java'])
out=p/'test-classes';out.mkdir()
javac=os.environ.get('JAVAC','javac');java=os.environ.get('JAVA','java')
subprocess.run([javac,'-d',str(out)]+[str(work/n) for n in files]+[str(r/'src/hmi/oem-menu/java/de/mibr/hmi/MibrScrollIndicator.java')],check=True)
subprocess.run([java,'-cp',str(out),'de.mibr.hmi.IndicatorTest'],check=True)

# Verify generated first-party RGBA artwork without external imaging libraries.
import struct,zlib
spec=__import__('importlib.util',fromlist=['']).spec_from_file_location('seat_art',r/'tools/generate_seat_scroll_thumb.py')
art=__import__('importlib.util',fromlist=['']).module_from_spec(spec);spec.loader.exec_module(art)
png=art.png();assert png[:8]==b'\x89PNG\r\n\x1a\n'
pos=8;compressed=b''
while pos<len(png):
    n=struct.unpack('>I',png[pos:pos+4])[0];kind=png[pos+4:pos+8];data=png[pos+8:pos+8+n]
    assert zlib.crc32(kind+data)&0xffffffff==struct.unpack('>I',png[pos+8+n:pos+12+n])[0]
    if kind==b'IDAT':compressed+=data
    pos+=12+n
assert zlib.decompress(compressed)==(b'\0'+bytes((220,35,55,255))*8)*32
print('SEAT_RED_ARTWORK=PASS generated uniform RGBA; no OEM pixels')
