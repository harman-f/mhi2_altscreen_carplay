#ifndef MIBR_ALT111_ZOOM_ADAPTER_H
#define MIBR_ALT111_ZOOM_ADAPTER_H
#include <stdint.h>
/*
 * Integration API in the existing libaltscreen111 process.
 * NOTE: This is not cross-process DSI IPC. The Java service/VC-focus source
 * still needs to be independently verified, built and wired for MU1440.
 * Do not call bind_verified until real page/focus and DIRECT ownership have
 * been observed. Negotiated 111 alone is insufficient.
 * session must match the current gen2 control generation.
 * positive_is_in: +1 if positive encoder detent means zoom in;
 *                 -1 if positive detent means zoom out;
 *                  0 means unknown and disables every zoom submission.
 * OEM listener fan-out is the caller's separate unmodified responsibility.
 */
int mibr_alt111_zoom_bind_verified(uint64_t session, unsigned vc_map_focus,
                                   unsigned direct_owner, int positive_is_in);
int mibr_alt111_zoom_observe_encoder2(uint64_t session, int keyboard,
                                      int encoder_id, int signed_steps,
                                      int extra, int effective_validity);
#endif
