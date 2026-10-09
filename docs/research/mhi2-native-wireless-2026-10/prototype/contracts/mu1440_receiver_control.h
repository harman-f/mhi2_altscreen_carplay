/* PRIVATE-RESEARCH: reconstructed control ABI, not a deployed adapter.
 * Evidence: analysis/MU1440_RECEIVER_DIO_CONTRACT_2026-10-07.md.
 * Native ARM32 / QNX ABI build and live tests remain required.
 * Do not copy MH2P object offsets or replace the stock delegate context.
 */
#ifndef MHI2_MU1440_RECEIVER_CONTROL_H
#define MHI2_MU1440_RECEIVER_CONTROL_H

#include <stddef.h>
#include <stdint.h>

#define MHI2_MU1440_AIRPLAY_SHA256 \
    "193a4fd9101ec2aa05e7159cfa307b96500810d379ca74a194f172adc13a46b5"
#define MHI2_MU1440_DIO_SHA256 \
    "4d6867bdd4c99a032d3c634299f36f88dc72aa54e333589a24af4497a96aee02"

typedef struct mhi2_mu1440_session_private *mhi2_mu1440_session_ref;
typedef struct mhi2_mu1440_cfl_string *mhi2_mu1440_string_ref;
typedef struct mhi2_mu1440_cfl_dictionary *mhi2_mu1440_dictionary_ref;
typedef struct mhi2_mu1440_cfl_object *mhi2_mu1440_object_ref;
struct mhi2_mu1440_mode_state; /* Media/resource layout is still opaque. */
typedef int32_t mhi2_mu1440_status;

typedef mhi2_mu1440_status (*mhi2_mu1440_control_fn)(
    mhi2_mu1440_session_ref session, mhi2_mu1440_string_ref command,
    const void *qualifier, mhi2_mu1440_dictionary_ref params,
    mhi2_mu1440_dictionary_ref *response, void *context);

/* Completion response is borrowed: retain/copy before deferred processing.
 * The receiver releases its session retain after invoking this callback.
 */
typedef void (*mhi2_mu1440_send_completion_fn)(
    mhi2_mu1440_status status, mhi2_mu1440_dictionary_ref response, void *context);

typedef struct mhi2_mu1440_session_delegate {
    void *context;                                  /* slot 0 */
    uintptr_t reserved_word1;                        /* stock zero, unknown role */
    uintptr_t reserved_word2;                        /* stock zero, unknown role */
    void (*finalized)(mhi2_mu1440_session_ref, void *);
    mhi2_mu1440_control_fn control;
    mhi2_mu1440_object_ref (*copy_property)(mhi2_mu1440_session_ref,
        mhi2_mu1440_string_ref, const void *, mhi2_mu1440_status *, void *);
    uintptr_t reserved_word6;                        /* stock zero, unknown role */
    mhi2_mu1440_status (*notify_property)(mhi2_mu1440_session_ref,
        mhi2_mu1440_string_ref, const void *, void *);
    void (*modes_changed)(mhi2_mu1440_session_ref,
        const struct mhi2_mu1440_mode_state *, void *);
    void (*request_ui)(mhi2_mu1440_session_ref, void *);
    void (*duck_audio)(mhi2_mu1440_session_ref, double, double, void *);
    void (*unduck_audio)(mhi2_mu1440_session_ref, double, void *);
    void (*audio_torn_down)(void *);                  /* stock conditional */
    void (*airplay_error)(int32_t);                  /* no context parameter */
} mhi2_mu1440_session_delegate;

/* Symbol binding and exact-input startup gates are not implemented here.
 * send_command requires a live session event client and receiver queue owner.
 */
typedef struct mhi2_mu1440_control_api {
    void (*set_delegate)(mhi2_mu1440_session_ref,
                         const mhi2_mu1440_session_delegate *);
    mhi2_mu1440_status (*session_control)(mhi2_mu1440_session_ref, uint32_t,
        mhi2_mu1440_string_ref, const void *, mhi2_mu1440_dictionary_ref,
        mhi2_mu1440_dictionary_ref *);
    mhi2_mu1440_status (*send_command)(mhi2_mu1440_session_ref,
        mhi2_mu1440_dictionary_ref, mhi2_mu1440_send_completion_fn, void *);
} mhi2_mu1440_control_api;

/* Intentionally fail for a 64-bit host or incompatible ABI. C99-compatible. */
#define MHI2_MU_ABI_ASSERT(name, expr) typedef char name[(expr) ? 1 : -1]
MHI2_MU_ABI_ASSERT(mhi2_mu_pointer_width, sizeof(void *) == 4);
MHI2_MU_ABI_ASSERT(mhi2_mu_callback_width, sizeof(mhi2_mu1440_control_fn) == 4);
MHI2_MU_ABI_ASSERT(mhi2_mu_delegate_width, sizeof(mhi2_mu1440_session_delegate) == 0x38);
#define MHI2_MU_SLOT(field, word) \
    MHI2_MU_ABI_ASSERT(mhi2_mu_offset_##field, \
                      offsetof(mhi2_mu1440_session_delegate, field) == (word) * 4)
MHI2_MU_SLOT(context, 0);
MHI2_MU_SLOT(reserved_word1, 1);
MHI2_MU_SLOT(reserved_word2, 2);
MHI2_MU_SLOT(finalized, 3);
MHI2_MU_SLOT(control, 4);
MHI2_MU_SLOT(copy_property, 5);
MHI2_MU_SLOT(reserved_word6, 6);
MHI2_MU_SLOT(notify_property, 7);
MHI2_MU_SLOT(modes_changed, 8);
MHI2_MU_SLOT(request_ui, 9);
MHI2_MU_SLOT(duck_audio, 10);
MHI2_MU_SLOT(unduck_audio, 11);
MHI2_MU_SLOT(audio_torn_down, 12);
MHI2_MU_SLOT(airplay_error, 13);
#undef MHI2_MU_SLOT
#undef MHI2_MU_ABI_ASSERT
#endif
