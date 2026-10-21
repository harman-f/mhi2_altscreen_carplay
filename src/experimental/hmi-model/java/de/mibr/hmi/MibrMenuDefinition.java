/* Generated from menu-definition.json schema 2. UI navigation metadata only. */
package de.mibr.hmi;
public final class MibrMenuDefinition {
 private MibrMenuDefinition() {}
 public static final String TITLE_DE="CarPlay-Einstellungen";
 public static final String TITLE_EN="CarPlay settings";
 public static String title(){return MibrI18n.german()?TITLE_DE:TITLE_EN;}
 public static final String[] ROOT_KEYS={
  "navigation.surface",
  "navigation.ETA",
  "navigation.speedLimit",
  "navigation.compass",
  "navigation.maneuver",
  "viewarea.selected"
 };
 public static final String[] GROUP_IDS={
  "advanced"
 };
 public static final String[] GROUP_NAMES_DE={
  "Erweitert"
 };
 public static final String[] GROUP_NAMES_EN={
  "Advanced"
 };
 public static String[] groupNames(){return MibrI18n.german()?GROUP_NAMES_DE:GROUP_NAMES_EN;}
 public static final String[][] GROUP_KEYS={
  {"carplay.enabled", "maxFPS", "sourceVersion"}
 };
 /** Every HMI-visible key: main list first, then submenus in order. */
 public static final String[] VISIBLE_KEYS={
  "navigation.surface",
  "navigation.ETA",
  "navigation.speedLimit",
  "navigation.compass",
  "navigation.maneuver",
  "viewarea.selected",
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
