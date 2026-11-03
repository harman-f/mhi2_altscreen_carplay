/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MIBR_V3_RECOVERY_GATE_H
#define MIBR_V3_RECOVERY_GATE_H
/* Read-only on-media inspection: 0=clean profile and optional valid lastgood;
 * nonzero=STOCK_ONLY/manual reconciliation. Never repairs or removes artifacts.
 * Original core still validates cross-key combinations on synchronous boot replay. */
int mibr_v3_recovery_check(const char *profile_path);
#endif
