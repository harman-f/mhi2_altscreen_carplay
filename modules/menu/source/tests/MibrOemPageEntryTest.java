package de.mibr.hmi;
/** Host state test ONLY: no view, render or vehicle acceptance. */
public final class MibrOemPageEntryTest {
    private static final class Fake implements MibrOemPageEntry.NativePage {
        int opens,closes; boolean succeed=true,throwOnOpen=false;
        public boolean open() {
            opens++;
            if(throwOnOpen)throw new IllegalStateException("synthetic");
            return succeed;
        }
        public void close() { closes++; }
    }
    private static void check(boolean b,String s) { if(!b)throw new AssertionError(s); }
    public static void main(String[] x) {
        MibrOemPageEntry.detach();
        check(!MibrOemPageEntry.requestOpen(),"no service: fail closed");
        Fake f=new Fake();
        check(MibrOemPageEntry.bind(f),"first binding");
        check(!MibrOemPageEntry.bind(new Fake()),"duplicate binding blocked");
        check(MibrOemPageEntry.requestOpen(),"open");
        check(MibrOemPageEntry.requestOpen() && f.opens==1,"double event coalesced");
        MibrOemPageEntry.back(); MibrOemPageEntry.back();
        check(f.closes==1 && !MibrOemPageEntry.isOpen(),"Back idempotent");
        check(MibrOemPageEntry.requestOpen() && f.opens==2,"reopen");
        MibrOemPageEntry.detach();
        check(f.closes==2 && !MibrOemPageEntry.requestOpen(),"detach");
        Fake fail=new Fake(); fail.succeed=false;
        check(MibrOemPageEntry.bind(fail),"bind failure");
        check(!MibrOemPageEntry.requestOpen() && fail.closes==1,"false cleanup");
        MibrOemPageEntry.detach();
        check(fail.closes==1,"already handled failed entry is not closed twice");
        Fake bad=new Fake(); bad.throwOnOpen=true;
        check(MibrOemPageEntry.bind(bad),"bind throwing");
        check(!MibrOemPageEntry.requestOpen() && bad.closes==1,"exception cleanup");
        MibrOemPageEntry.detach();
        // Scoped Back: first step returns from owned child to still-open Ssm.
        Fake nested=new Fake();
        check(MibrOemPageEntry.bind(nested),"nested binding");
        check(MibrOemPageEntry.requestOpen(),"nested open");
        final int[] steps=new int[1];
        MibrOemPageEntry.setChildBack(nested,new MibrOemPageEntry.ChildBack(){
            public boolean backChild(){if(steps[0]++==0)return true;return false;}
        });
        MibrOemPageEntry.back();
        check(nested.closes==0 && MibrOemPageEntry.isOpen() && steps[0]==1,
              "first Back remains inside top-level Ssm");
        MibrOemPageEntry.back();
        check(nested.closes==1 && !MibrOemPageEntry.isOpen(),"second Back closes top-level");
        check(MibrOemPageEntry.requestOpen(),"nested reopened");
        MibrOemPageEntry.detach();
        check(nested.closes==2 && !MibrOemPageEntry.isOpen(),
              "detach closes entire owner irrespective of child Back");
        Fake generic=new Fake();
        MibrElementSpec info=MibrElementSpec.info("test.info","Approved local page");
        MibrElementEngine engine=new MibrElementEngine(new MibrElementSpec[]{info});
        check(!MibrOemPageEntry.requestTypedChild(info,engine,"verified local",null),
              "generic page admission absent outside opened owner");
        check(MibrOemPageEntry.bind(generic),"typed owner binding");
        final int[] admitted=new int[1];
        MibrOemPageEntry.setTypedChild(generic,new MibrOemPageEntry.TypedChild(){
            public boolean open(MibrElementSpec spec,MibrElementEngine e,String text,
                                MibrOemPageEntry.LocalSink sink){
                if(spec!=info || e!=engine || !"verified local".equals(text))return false;
                admitted[0]++;return true;
            }
        });
        check(!MibrOemPageEntry.requestTypedChild(info,engine,"verified local",null),
              "typed child must not open HOME by itself");
        check(MibrOemPageEntry.requestOpen() &&
              MibrOemPageEntry.requestTypedChild(info,engine,"verified local",null) &&
              admitted[0]==1,"owner-scoped exact typed-page entry");
        MibrOemPageEntry.detach();
        check(!MibrOemPageEntry.requestTypedChild(info,engine,"verified local",null) &&
              generic.closes==1,"typed entry cleared after full detach");
        engine.detach();
        System.out.println("MIBR_OEM_PAGE_ENTRY_HOST_PASS nested_back=PASS typed_child=PASS");
    }
}
