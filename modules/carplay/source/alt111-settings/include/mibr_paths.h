/* SPDX-License-Identifier: GPL-3.0-or-later */
/*
 * Single MIB Runtime root (M1). Every native consumer builds its persistent
 * paths from this one constant; nothing else may spell the absolute root.
 * Layout contract: docs/architecture/FIRMWARE_PROFILES_AND_CONFIGURATION.md 2.4.
 * Location only: file names, formats and polarity are unchanged by M1.
 * Host tests may override the root with -DMIBR_ROOT_DIR=\"/tmp/...\".
 */
#ifndef MIBR_PATHS_H
#define MIBR_PATHS_H

#ifndef MIBR_ROOT_DIR
#define MIBR_ROOT_DIR "/mnt/app/root/mibr"
#endif
#define MIBR_BIN_DIR      MIBR_ROOT_DIR "/bin"
#define MIBR_SCRIPTS_DIR  MIBR_ROOT_DIR "/scripts"
#define MIBR_CONFIG_DIR   MIBR_ROOT_DIR "/config"
#define MIBR_STATE_DIR    MIBR_ROOT_DIR "/state"
#define MIBR_VERSION_DIR  MIBR_ROOT_DIR "/version"
#define MIBR_LOGS_DIR     MIBR_ROOT_DIR "/logs"
/* Group files of the registry persistence layer (config/carplay/<name>). */
#define MIBR_CARPLAY_CONFIG_DIR MIBR_CONFIG_DIR "/carplay"

#endif
