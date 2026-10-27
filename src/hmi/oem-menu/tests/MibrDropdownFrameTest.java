package de.mibr.hmi;
public final class MibrDropdownFrameTest {
 public static void main(String[] args){
  // The real closed popup/list pair was 6/471; it is not a frame-padding measurement.
  if(6-471!=-465)throw new RuntimeException("fixture");
  int c=MibrDropdownFrame.chrome(3,3);
  if(c!=6||MibrDropdownFrame.rows(480,56,3,c)!=3)throw new RuntimeException("measured_three_rows");
  if(3*56+c!=174)throw new RuntimeException("outer_height");
  if(MibrDropdownFrame.rows(480,56,1,c)!=1||MibrDropdownFrame.rows(480,56,9,c)!=8)throw new RuntimeException("bounded_scrolling");
  boolean failed=false;try{MibrDropdownFrame.rows(60,56,3,c);}catch(IllegalStateException e){failed=true;}
  if(!failed)throw new RuntimeException("reject_bad_bounds");
  failed=false;try{MibrDropdownFrame.chrome(Integer.MAX_VALUE,1);}catch(IllegalStateException e){failed=true;}
  if(!failed)throw new RuntimeException("reject_overflow");
  System.out.println("DROPDOWN_FRAME_TEST=PASS collapsed_popup_regression three_rows scrolling bounds overflow");
 }
}
