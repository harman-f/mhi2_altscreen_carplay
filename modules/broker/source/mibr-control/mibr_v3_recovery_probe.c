/* SPDX-License-Identifier: GPL-3.0-or-later
 * HOST/QNX offline read-only diagnostic. No service, profile write or repair.
 */
#include "mibr_v3_recovery_gate.h"
#include <stdio.h>
int main(int argc,char **argv){
    int status=argc==2?mibr_v3_recovery_check(argv[1]):-1;
    puts(status?"MIBR_V3_RECOVERY=STOCK_ONLY_RECONCILE":"MIBR_V3_RECOVERY=STRUCTURAL_CLEAN_BOOT_REPLAY_REQUIRED");
    return status?2:0;
}
