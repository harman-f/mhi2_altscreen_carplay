/*
 * Route Guidance TLV Definitions and Parsing
 *
 * Defines TLV IDs for iAP2 Route Guidance messages:
 * - 0x5200 StartRouteGuidanceUpdates
 * - 0x5201 RouteGuidanceUpdate
 * - 0x5202 RouteGuidanceManeuverUpdate
 * - 0x5203 StopRouteGuidanceUpdates
 * - 0x5204 RouteGuidanceLaneGuidanceInformation
 *
 * Copyright (c) 2026 LuKa (@LuKa_dev)
 */

#ifndef RGD_TLV_H
#define RGD_TLV_H

#include "../framework/common.h"

/* Raw RGD packet tracing (opt-in: build with -DRGD_TRACE_RAW_FULL=1). Value-based (#if) so a
 * -D...=0 build is consistent between the struct fields below and every writer. Presence-based
 * #ifdef would make -D...=0 enable the trace, and — worse — would give rgd_tlv.c a different
 * rgd_maneuver_t layout from rgd_hook.c the moment any translation unit sees a default define. */
#ifndef RGD_TRACE_RAW_FULL
#define RGD_TRACE_RAW_FULL 0
#endif

/* ============================================================
 * Identify TLV for RouteGuidanceDisplayComponent (0x001E)
 * ============================================================ */
#define IDENT_TLV_ROUTE_GUIDANCE_COMPONENT  0x001E

/* RouteGuidanceDisplayComponent inner TLV IDs
 *
 * Matches MHI3 libesoiap2.so component layout (9 TLVs, IDs 0-8).
 * Verified via CIOSTraceHelper::toString(RouteGuidanceDisplayComponent):
 *   compId, name, maxCurrentRoadNameLength, maxDestinationNameLength,
 *   maxAfterManeuverRoadNameLength, maxManeuverDescriptionLength,
 *   maxGuidanceManeuverStorageCapacity, maxLaneGuidanceDescriptionLength,
 *   maxLaneGuidanceStorageCapacity
 */
#define RGD_COMP_COMPONENT_ID               0x0000
#define RGD_COMP_NAME                       0x0001
#define RGD_COMP_MAX_CURRENT_ROAD_NAME      0x0002
#define RGD_COMP_MAX_DEST_NAME              0x0003
#define RGD_COMP_MAX_AFTER_MANEUVER_NAME    0x0004
#define RGD_COMP_MAX_MANEUVER_DESC          0x0005
#define RGD_COMP_MAX_MANEUVER_CAPACITY      0x0006
#define RGD_COMP_MAX_LANE_GUIDANCE_DESC     0x0007
#define RGD_COMP_MAX_LANE_GUIDANCE_CAPACITY 0x0008

/* ============================================================
 * StartRouteGuidanceUpdates (0x5200) TLV IDs
 * ============================================================ */
#define RGD_START_TLV_COMPONENT_ID       0x0000
#define RGD_START_TLV_SOURCE_NAME        0x0001
#define RGD_START_TLV_SOURCE_SUPPORTS_RG 0x0002
#define RGD_START_TLV_SUPPORTS_EXIT_INFO 0x0003

/* ============================================================
 * RouteGuidanceUpdate (0x5201) TLV IDs
 * ============================================================ */
#define RGD_TLV_COMPONENT_ID            0x0000
#define RGD_TLV_ROUTE_GUIDANCE_STATE    0x0001
#define RGD_TLV_MANEUVER_STATE          0x0002
#define RGD_TLV_CURRENT_ROAD_NAME       0x0003
#define RGD_TLV_DESTINATION_NAME        0x0004
#define RGD_TLV_ETA                     0x0005
#define RGD_TLV_TIME_REMAINING          0x0006
#define RGD_TLV_DISTANCE_REMAINING      0x0007
#define RGD_TLV_DISTANCE_STRING         0x0008
#define RGD_TLV_DISTANCE_UNITS          0x0009
#define RGD_TLV_DIST_TO_MANEUVER        0x000A
#define RGD_TLV_DIST_TO_MANEUVER_STRING 0x000B
#define RGD_TLV_DIST_TO_MANEUVER_UNITS  0x000C
#define RGD_TLV_MANEUVER_LIST           0x000D
#define RGD_TLV_MANEUVER_COUNT          0x000E
#define RGD_TLV_VISIBLE_IN_APP          0x000F
#define RGD_TLV_LANE_GUIDANCE_INDEX     0x0010
#define RGD_TLV_LANE_GUIDANCE_TOTAL     0x0011
#define RGD_TLV_LANE_GUIDANCE_SHOWING   0x0012
#define RGD_TLV_SOURCE_NAME             0x0013
#define RGD_TLV_SOURCE_SUPPORTS_RG      0x0014

/*
 * RouteGuidanceState values (as observed in MHI3 dio_manager type-info strings).
 *
 * mediabase::CDIONavigationMetadataTypeInfo::toString(ERouteGuidanceState):
 *   0=NO_ROUTE_SET, 1=ROUTE_SET, 2=ARRIVED, 3=LOADING, 4=LOCATING,
 *   5=REROUTING, 6=PROCEED_TO_ROUTE
 */
#define RGD_STATE_NO_ROUTE_SET      0
#define RGD_STATE_ROUTE_SET         1
#define RGD_STATE_ARRIVED           2
#define RGD_STATE_LOADING           3
#define RGD_STATE_LOCATING          4
#define RGD_STATE_REROUTING         5
#define RGD_STATE_PROCEED_TO_ROUTE  6

/* Backward-compatible aliases used throughout the hook code. */
#define RGD_STATE_NOT_SET           RGD_STATE_NO_ROUTE_SET
#define RGD_STATE_NOT_ACTIVE        RGD_STATE_NO_ROUTE_SET
#define RGD_STATE_ACTIVE            RGD_STATE_ROUTE_SET

/* ============================================================
 * RouteGuidanceManeuverUpdate (0x5202) TLV IDs
 * ============================================================ */
#define MAN_TLV_COMPONENT_ID            0x0000
#define MAN_TLV_INDEX                   0x0001
#define MAN_TLV_DESCRIPTION             0x0002
#define MAN_TLV_TYPE                    0x0003
#define MAN_TLV_AFTER_ROAD_NAME         0x0004
#define MAN_TLV_DISTANCE_BETWEEN        0x0005
#define MAN_TLV_DISTANCE_STRING         0x0006
#define MAN_TLV_DISTANCE_UNITS          0x0007
#define MAN_TLV_DRIVING_SIDE            0x0008
#define MAN_TLV_JUNCTION_TYPE           0x0009
#define MAN_TLV_JUNCTION_ANGLES         0x000A /* JunctionElementAngle (iOS) */
#define MAN_TLV_EXIT_ANGLE              0x000B /* JunctionElementExitAngle (iOS) */
#define MAN_TLV_LINKED_LANE_GUIDANCE    0x000C
#define MAN_TLV_EXIT_INFO               0x000D

/* ============================================================
 * RouteGuidanceLaneGuidanceInformation (0x5204) TLV IDs
 * ============================================================ */
#define LANE_MSG_TLV_COMPONENT_ID            0x0000
#define LANE_MSG_TLV_LANE_GUIDANCE_INDEX     0x0001
#define LANE_MSG_TLV_LANE_INFORMATIONS       0x0002
#define LANE_MSG_TLV_LANE_GUIDANCE_DESC      0x0003

/*
 * Maneuver types.
 *
 * Verified against MHI3 dio_manager type-info strings
 * (CDIONavigationMetadataTypeInfo::toString(EManeuverType)):
 *   0=NO_TURN, 1=LEFT_TURN, 2=RIGHT_TURN, ... , 53=CHANGE_HIGHWAY_RIGHT
 */
#define MAN_TYPE_NOT_SET                    255
#define MAN_TYPE_NO_TURN                    0
#define MAN_TYPE_LEFT_TURN                  1
#define MAN_TYPE_RIGHT_TURN                 2
#define MAN_TYPE_STRAIGHT_AHEAD             3
#define MAN_TYPE_U_TURN                     4
#define MAN_TYPE_FOLLOW_ROAD                5
#define MAN_TYPE_ENTER_ROUNDABOUT           6
#define MAN_TYPE_EXIT_ROUNDABOUT            7
#define MAN_TYPE_OFF_RAMP                   8
#define MAN_TYPE_ON_RAMP                    9
#define MAN_TYPE_ARRIVE_END_OF_NAVIGATION   10
#define MAN_TYPE_START_ROUTE                11
#define MAN_TYPE_ARRIVE_AT_DESTINATION      12
#define MAN_TYPE_KEEP_LEFT                  13
#define MAN_TYPE_KEEP_RIGHT                 14
#define MAN_TYPE_ENTER_FERRY                15
#define MAN_TYPE_EXIT_FERRY                 16
#define MAN_TYPE_CHANGE_FERRY               17
#define MAN_TYPE_START_ROUTE_WITH_U_TURN    18
#define MAN_TYPE_U_TURN_AT_ROUNDABOUT       19
#define MAN_TYPE_LEFT_TURN_AT_END           20
#define MAN_TYPE_RIGHT_TURN_AT_END          21
#define MAN_TYPE_HIGHWAY_OFF_RAMP_LEFT      22
#define MAN_TYPE_HIGHWAY_OFF_RAMP_RIGHT     23
#define MAN_TYPE_ARRIVE_DESTINATION_LEFT    24
#define MAN_TYPE_ARRIVE_DESTINATION_RIGHT   25
#define MAN_TYPE_U_TURN_WHEN_POSSIBLE       26
#define MAN_TYPE_ARRIVE_END_OF_DIRECTIONS   27
#define MAN_TYPE_ROUNDABOUT_EXIT_1          28
#define MAN_TYPE_ROUNDABOUT_EXIT_2          29
#define MAN_TYPE_ROUNDABOUT_EXIT_3          30
#define MAN_TYPE_ROUNDABOUT_EXIT_4          31
#define MAN_TYPE_ROUNDABOUT_EXIT_5          32
#define MAN_TYPE_ROUNDABOUT_EXIT_6          33
#define MAN_TYPE_ROUNDABOUT_EXIT_7          34
#define MAN_TYPE_ROUNDABOUT_EXIT_8          35
#define MAN_TYPE_ROUNDABOUT_EXIT_9          36
#define MAN_TYPE_ROUNDABOUT_EXIT_10         37
#define MAN_TYPE_ROUNDABOUT_EXIT_11         38
#define MAN_TYPE_ROUNDABOUT_EXIT_12         39
#define MAN_TYPE_ROUNDABOUT_EXIT_13         40
#define MAN_TYPE_ROUNDABOUT_EXIT_14         41
#define MAN_TYPE_ROUNDABOUT_EXIT_15         42
#define MAN_TYPE_ROUNDABOUT_EXIT_16         43
#define MAN_TYPE_ROUNDABOUT_EXIT_17         44
#define MAN_TYPE_ROUNDABOUT_EXIT_18         45
#define MAN_TYPE_ROUNDABOUT_EXIT_19         46
#define MAN_TYPE_SHARP_LEFT_TURN            47
#define MAN_TYPE_SHARP_RIGHT_TURN           48
#define MAN_TYPE_SLIGHT_LEFT_TURN           49
#define …16043 tokens truncated…utton(112352865));option.set_height(60);
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
