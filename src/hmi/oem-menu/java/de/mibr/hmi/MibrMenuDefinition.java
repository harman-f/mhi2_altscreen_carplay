/* Generated from menu-definition.json schema 3. UI navigation metadata only. */
package de.mibr.hmi;
public final class MibrMenuDefinition {
 private MibrMenuDefinition() {}
 public static final String TITLE_DE="CarPlay-Einstellungen";
 public static final String TITLE_EN="CarPlay settings";
 public static String title(){return MibrI18n.german()?TITLE_DE:TITLE_EN;}
 public static final String[] ROOT_KEYS={
  "viewarea.selected",
  "navigation.surface",
  "navigation.ETA",
  "navigation.speedLimit",
  "navigation.compass",
  "navigation.maneuver"
 };
 public static final String[] GROUP_IDS={
  "nav_hints",
  "views",
  "safe_voll",
  "safe_wide",
  "safe_center",
  "advanced",
  "diagnostics",
  "version"
 };
 public static final String[] GROUP_NAMES_DE={
  "Pfeile im Cockpit",
  "Ansichten",
  "Safe Area Voll",
  "Safe Area Wide",
  "Safe Area Center",
  "Erweitert",
  "Diagnose",
  "Version"
 };
 public static final String[] GROUP_NAMES_EN={
  "Cockpit arrows",
  "Views",
  "Safe area full",
  "Safe area wide",
  "Safe area center",
  "Advanced",
  "Diagnostics",
  "Version"
 };
 public static String[] groupNames(){return MibrI18n.german()?GROUP_NAMES_DE:GROUP_NAMES_EN;}
 public static final String[] VIRTUAL_PAGE_IDS={
  "scaling"
 };
 public static final String[] VIRTUAL_PAGE_PARENTS={
  "advanced"
 };
 public static final String[] VIRTUAL_PAGE_NAMES_DE={
  "Scaling"
 };
 public static final String[] VIRTUAL_PAGE_NAMES_EN={
  "Scaling"
 };
 public static String virtualPageName(int page){return MibrI18n.german()?VIRTUAL_PAGE_NAMES_DE[page]:VIRTUAL_PAGE_NAMES_EN[page];}
 public static final String[] VIRTUAL_PAGE_NOTICES_DE={
  "\u00c4nderungen werden bei der n\u00e4chsten CarPlay-Verbindung \u00fcbertragen."
 };
 public static final String[] VIRTUAL_PAGE_NOTICES_EN={
  "Changes are sent on the next CarPlay connection."
 };
 public static String virtualPageNotice(int page){return MibrI18n.german()?VIRTUAL_PAGE_NOTICES_DE[page]:VIRTUAL_PAGE_NOTICES_EN[page];}
 public static final String[][] VIRTUAL_CONTROL_IDS={
  {"scaling.main.zoomFactor", "scaling.cluster.zoomFactor", "scaling.cluster.physicalSize", "scaling.main.physicalSize"}
 };
 public static final String[][][] VIRTUAL_CONTROL_OPTIONS={
  {{"AUTO", "70", "85", "100", "125", "150"}, {"AUTO", "70", "85", "100", "125", "150"}, {"BASE", "P20", "P30", "P50"}, {"BASE", "P20", "P30", "P50"}}
 };
 public static final String[][] VIRTUAL_CONTROL_LABELS_DE={
  {"Zoomfaktor Hauptdisplay", "Zoomfaktor Virtual Cockpit", "Physische Displaygr\u00f6\u00dfe Virtual Cockpit", "Physische Displaygr\u00f6\u00dfe Hauptdisplay"}
 };
 public static final String[][] VIRTUAL_CONTROL_LABELS_EN={
  {"Main display zoom factor", "Virtual Cockpit zoom factor", "Virtual Cockpit physical size", "Main display physical size"}
 };
 public static String virtualControlLabel(int page,int row){return MibrI18n.german()?VIRTUAL_CONTROL_LABELS_DE[page][row]:VIRTUAL_CONTROL_LABELS_EN[page][row];}
 public static final String[][] GROUP_KEYS={
  {},
  {},
  {},
  {},
  {},
  {"carplay.enabled", "maxFPS", "sourceVersion"},
  {},
  {}
 };
 /** Every HMI-visible key: main list first, then submenus in order. */
 public static final String[] VISIBLE_KEYS={
  "viewarea.selected",
  "navigation.surface",
  "navigation.ETA",
  "navigation.speedLimit",
  "navigation.compass",
  "navigation.maneuver",
  "carplay.enabled",
  "maxFPS",
  "sourceVersion"
 };
 /** Exact native MIBR/3 SNAPSHOT scope=ui row order; includes HMI-hidden keys. */
 public static final String[] NATIVE_UI_KEYS={
  "carplay.enabled",
  "viewarea.selected",
  "navigation.surface",
  "navigation.ETA",
  "navigation.speedLimit",
  "navigation.compass",
  "navigation.maneuver",
  "navigation.url",
  "preset.id",
  "maxFPS",
  "sourceVersion"
 };
}
