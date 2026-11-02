package de.mibr.hmi;

import java.util.Hashtable;

/** Compiled finite Settings page graph, including nested Back/focus/scroll state. */
public final class MibrElementTree {
    public static final class Page {
        public final String id,title;
        private final MibrElementSpec[] rows;
        public Page(String id,String title,MibrElementSpec[] rows){
            if(id==null || id.length()==0 || title==null || title.length()==0 ||
               rows==null || rows.length>128)throw new IllegalArgumentException("PAGE_INVALID");
            this.id=id;this.title=title;this.rows=(MibrElementSpec[])rows.clone();
            Hashtable ids=new Hashtable();
            for(int i=0;i<this.rows.length;i++)
                if(this.rows[i]==null || ids.put(this.rows[i].id,Boolean.TRUE)!=null)
                    throw new IllegalArgumentException("PAGE_ROW_DUPLICATE_OR_NULL");
        }
        public int size(){return rows.length;}
        public MibrElementSpec row(int n){return rows[n];}
        public MibrElementSpec[] rows(){return (MibrElementSpec[])rows.clone();}
    }
    private static final class Frame {
        Page page;int focus,first;
        Frame(Page page,int focus,int first){this.page=page;this.focus=focus;this.first=first;}
    }
    private final Hashtable pages=new Hashtable();
    private final Page root;
    private final Frame[] stack=new Frame[16];
    private int depth;
    private boolean detached;
    public MibrElementTree(Page[] all,String rootId){
        if(all==null || all.length==0 || all.length>64)
            throw new IllegalArgumentException("PAGE_COUNT");
        for(int i=0;i<all.length;i++)
            if(all[i]==null || pages.put(all[i].id,all[i])!=null)
                throw new IllegalArgumentException("PAGE_DUPLICATE_OR_NULL");
        root=(Page)pages.get(rootId);
        if(root==null)throw new IllegalArgumentException("PAGE_ROOT_MISSING");
        Hashtable seen=new Hashtable(),active=new Hashtable();
        checkGraph(root,seen,active,0);
        if(seen.size()!=all.length)throw new IllegalArgumentException("PAGE_UNREACHABLE");
        stack[0]=new Frame(root,0,0);
    }
    private void checkGraph(Page page,Hashtable seen,Hashtable active,int depth){
        if(depth>=stack.length)throw new IllegalArgumentException("PAGE_DEPTH_EXCEEDED");
        if(active.containsKey(page.id))throw new IllegalArgumentException("PAGE_CYCLE");
        if(seen.containsKey(page.id))return;
        active.put(page.id,Boolean.TRUE);
        for(int i=0;i<page.size();i++){
            MibrElementSpec s=page.row(i);
            if(s.kind==MibrElementSpec.LINK){
                Page target=(Page)pages.get(s.page);
                if(target==null)throw new IllegalArgumentException("PAGE_LINK_MISSING");
                checkGraph(target,seen,active,depth+1);
            }
        }
        active.remove(page.id);seen.put(page.id,Boolean.TRUE);
    }
    private void live(){if(detached)throw new IllegalStateException("PAGE_TREE_DETACHED");}
    public Page current(){live();return stack[depth].page;}
    public int depth(){live();return depth;}
    public int focus(){live();return stack[depth].focus;}
    public int firstVisible(){live();return stack[depth].first;}
    public void remember(int focused,int first){
        live();Page p=current();
        if(focused < -1 || focused>=p.size() || first<0 ||
           (p.size()==0 && first!=0) || (p.size()>0 && first>=p.size()))
            throw new IllegalArgumentException("PAGE_FOCUS_BOUNDS");
        stack[depth].focus=focused;stack[depth].first=first;
    }
    public boolean open(int row){
        live();Page p=current();if(row<0 || row>=p.size())return false;
        MibrElementSpec s=p.row(row);
        if(s.kind!=MibrElementSpec.LINK)return false;
        if(depth+1>=stack.length)throw new IllegalStateException("PAGE_STACK_FULL");
        Page target=(Page)pages.get(s.page);
        if(target==null)throw new IllegalStateException("PAGE_TARGET_MISSING");
        stack[++depth]=new Frame(target,target.size()==0?-1:0,0);
        return true;
    }
    public boolean back(){
        live();if(depth==0)return false;
        stack[depth--]=null;return true;
    }
    public void reset(){
        live();for(int i=1;i<stack.length;i++)stack[i]=null;
        depth=0;stack[0]=new Frame(root,root.size()==0?-1:0,0);
    }
    public void detach(){
        if(detached)return;
        for(int i=0;i<stack.length;i++)stack[i]=null;
        pages.clear();detached=true;
    }
}
