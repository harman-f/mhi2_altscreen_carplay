package de.mibr.hmi;
/** Native PushUp frame geometry: content plus LayoutAttribs vertical insets. */
final class MibrDropdownFrame {
 private MibrDropdownFrame(){}
 static int chrome(int top,int bottom){
  if(top<0||bottom<0||top>Integer.MAX_VALUE-bottom)throw new IllegalStateException("MIBR_SSM_OPTION_VIEW_BOUNDS insets");
  return top+bottom;
 }
 static int rows(int viewHeight,int rowHeight,int count,int chrome){
  if(viewHeight<=24||rowHeight<=0||count<=0||chrome<0||chrome>viewHeight-24)
   throw new IllegalStateException("MIBR_SSM_OPTION_VIEW_BOUNDS dimensions");
  int available=viewHeight-24-chrome;
  if(available<rowHeight)throw new IllegalStateException("MIBR_SSM_OPTION_VIEW_BOUNDS row_fit");
  return Math.min(count,available/rowHeight);
 }
}
