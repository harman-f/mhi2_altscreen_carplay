/* Exercise the real GEN2 adapter with no target hooks or live sockets. */
#define ALT111_GEN2_HOST_TEST 1
static char recovery_path[192];
#define ALT111_RECOVERY_PATH recovery_path
#include "../src/native/altscreen111-gen2/libaltscreen111_gen2.c"
#include <assert.h>
static CFTypeRef test_retain(CFTypeRef object){return object;}
static void test_release(CFTypeRef object){(void)object;}

static void test_m1au_time_presence(void)
{
    static const uint8_t config[]={1,0x42,0,31,0xff,0xe1,0,4,0x67,0x42,0,31,1,0,2,0x68,0xce};
    static const uint8_t idr[]={0,0,0,2,0x65,0x88},zero[8]={0};
    struct alt111_video video;struct alt111_output_ticket ticket;
    const uint8_t *bytes;size_t size;uint64_t stream;
    alt111_video_init(&video);stream=alt111_video_begin(&video,1);
    assert(alt111_video_config(&video,stream,config,sizeof(config))==ALT111_OK);
    assert(alt111_video_attach(&video)==ALT111_OK);
    assert(alt111_video_submit_timed(&video,stream,idr,sizeof(idr),1,zero)==ALT111_OK);
    assert(alt111_video_peek(&video,&bytes,&size,&ticket)==ALT111_OK);
    assert(ticket.source_time_present && !memcmp(ticket.source_ts_raw,zero,8));
    m1au_prepare_header_locked(&ticket,size);
    assert((g_tee_frame_header[11]&12u)==12u);
    assert(alt111_video_advance(&video,&ticket,size)==ALT111_OK);
    assert(alt111_video_submit(&video,stream,idr,sizeof(idr),1)==ALT111_OK);
    assert(alt111_video_peek(&video,&bytes,&size,&ticket)==ALT111_OK);
    assert(!ticket.source_time_present && !memcmp(ticket.source_ts_raw,zero,8));
    m1au_prepare_header_locked(&ticket,size);
    assert((g_tee_frame_header[11]&12u)==4u);
    alt111_video_destroy(&video);
}

int main(void)
{
    char root[]="/tmp/alt111-gen2-session-XXXXXX",status[192],log[192];
    struct gen2_settings_scope scope;
    struct mibr_display_config display;
    struct mibr_viewareas_config views;
    char value[96];
    struct alt111_recovery_request request={ALT111_KF_SOURCE_GAP,7,8,9,10,1};
    uint64_t demand;
    AirPlayReceiverSessionRef session=(void *)(uintptr_t)1;
    assert(mkdtemp(root));
    test_m1au_time_presence();
    p_CFRetain=test_retain;p_CFRelease=test_release;
    snprintf(status,sizeof(status),"%s/status",root);g2_status_path=status;
    snprintf(log,sizeof(log),"%s/log",root);g_log_path=log;
    snprintf(recovery_path,sizeof(recovery_path),"%s/recovery",root);
    assert(alt111_control_init(&g2_control,1)==ALT111_OK);
    assert(!alt111_settings_defaults(&g_settings_desired,"classic_single_view"));
    g_settings_have=g_settings_valid=1;
    assert(!gen2_control_projection_on(session)); /* No fabricated advertisement. */
    g_settings_advertised=g_settings_desired;g_settings_have_advertised=1;
    g_settings_advertised_session=(void *)(uintptr_t)2;
    assert(!gen2_control_projection_on(session)); /* Other connection's /info. */
    g_settings_advertised_session=session;
    strcpy(g_settings_advertised_version,"950.7.1");
    assert(gen2_control_projection_on(session));
    assert(g_settings_have_active && g_settings_active_confirmed);
    assert(g2_control.view_count==1);
    assert(!gen2_control_projection_on((void *)(uintptr_t)2));
    assert(g_settings_active_session==session);
    assert(!alt111_settings_defaults(&g_settings_desired,"mibr_dual_view"));
    assert(!alt111_settings_set(&g_settings_desired,ALTSET_DISPLAY_UUID,
                               "11111111-2222-4000-8000-000000000002",ALT111_TEMP));
    g_settings_advertised=g_settings_desired;strcpy(g_settings_advertised_version,"1.2.3");
    assert(gen2_control_projection_on(session)); /* Repeated SETUP keeps active. */
    assert(g2_control.view_count==1);
    memset(&scope,0,sizeof(scope));scope.settings=g_settings_active;scope.valid=1;
    assert(!pthread_setspecific(g_settings_scope_key,&scope));
    load_display_config(&display);load_viewareas_config(&views);
    assert(!strcmp(display.uuid,ALT_UUID_DEFAULT));
    assert(views.count==1 && views.view[0].safe_x==202);
    assert(!strcmp(command_uuid(),ALT_UUID_DEFAULT));
    assert(!read_layered_value(g_source_version_config_name,value,sizeof(value),NULL));
    assert(!strcmp(value,"950.7.1"));
    assert(!strcmp(g_settings_active_version,"950.7.1"));
    assert(!pthread_setspecific(g_settings_scope_key,NULL));
    gen2_control_release();
    assert(!g_settings_have_active && !g_settings_active_confirmed);
    assert(!gen2_control_projection_on(session)); /* Teardown invalidates old /info. */
    g_settings_advertised_session=NULL;
    g_settings_have_advertised=1u; /* New /info after teardown. */
    assert(gen2_control_projection_on(session));
    assert(g2_control.view_count==2 && !g_settings_active_confirmed);
    g2_video.stream=7;g2_video.codec=8;g2_video.consumer=9;g2_video.source_ordinal=10;
    alt111_policy_defaults(&g2_policy.config);g2_policy.config.gap_recovery=0;
    assert(!alt111_recovery_publish(recovery_path,&request));
    request.reasons=ALT111_KF_LIFECYCLE_RESET;request.sequence=2;
    assert(!alt111_recovery_publish(recovery_path,&request)); /* Coalesces both causes. */
    gen2_process_diag_markers();
    assert(g2_control.keyframe_reasons==ALT111_KF_LIFECYCLE_RESET);
    demand=g2_control.keyframe_wanted;
    assert(!alt111_recovery_publish(recovery_path,&request));
    gen2_process_diag_markers();assert(g2_control.keyframe_wanted==demand); /* Replay. */
    request.sequence=3;request.consumer=10;
    assert(!alt111_recovery_publish(recovery_path,&request));
    gen2_process_diag_markers();assert(g2_control.keyframe_wanted==demand); /* Old peer. */
    request.consumer=9;request.ordinal=11;
    assert(!alt111_recovery_publish(recovery_path,&request));
    gen2_process_diag_markers();assert(g2_control.keyframe_wanted==demand); /* Future AU. */
    gen2_control_release();
    strcat(recovery_path,".lock");unlink(recovery_path);
    unlink(status);unlink(log);assert(!rmdir(root));
    puts("ALT111_GEN2_SETTINGS_SESSION_TEST=PASS");
    return 0;
}
