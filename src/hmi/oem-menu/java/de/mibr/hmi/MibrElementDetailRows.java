package de.mibr.hmi;
import java.util.Vector;

/**
 * Read-only native WidgetList row source for existing owned Ssm detail pages.
 * Each output is a separate stock plain ListItem, not a HOME freehand overlay.
 * It does not fabricate backend values or claim ScrollableText equivalence.
 */
public final class MibrElementDetailRows {
    private static final int MAX_ROWS=24, MAX_LABEL=52, MAX_TEXT=8192;
    private MibrElementDetailRows(){}
    public static String[] lines(String text){
        if(text==null || text.length()==0)return new String[]{MibrI18n.pick("Keine Detailinformationen", "No detail information")};
        if(text.length()>MAX_TEXT)throw new IllegalArgumentException("DETAIL_TEXT_TOO_LONG");
        Vector list=new Vector();
        int start=0;
        for(int i=0;i<=text.length();i++){
            if(i<text.length() && text.charAt(i)!='\n')continue;
            String item=text.substring(start,i);
            if(item.endsWith("\r"))item=item.substring(0,item.length()-1);
            for(int n=0;n<item.length();n++)
                if(Character.isISOControl(item.charAt(n)) && item.charAt(n)!='\t')
                    throw new IllegalArgumentException("DETAIL_CONTROL_CHARACTER");
            item=item.replace('\t',' ').trim();
            if(item.length()==0)add(list," ");
            while(item.length()>MAX_LABEL){
                int split=MAX_LABEL;
                for(int p=MAX_LABEL;p>=MAX_LABEL/2;p--){
                    if(item.charAt(p)==' '){split=p;break;}
                }
                add(list,item.substring(0,split).trim());
                item=item.substring(split).trim();
            }
            if(item.length()>0)add(list,item);
            start=i+1;
        }
        String[] result=new String[list.size()];
        list.copyInto(result);
        return result;
    }
    private static void add(Vector rows,String line){
        if(rows.size()>=MAX_ROWS)throw new IllegalArgumentException("DETAIL_ROW_LIMIT");
        rows.addElement(line);
    }
}
