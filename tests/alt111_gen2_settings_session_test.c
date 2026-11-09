/* Exercise the real GEN2 adapter with no target hooks or live sockets. */
#define ALT111_GEN2_HOST_TEST 1
static char recovery_path[192];
#define ALT111_RECOVERY_PATH recovery_path
static char safe_path_fmt[160],platform_defaults_path[160];
#define MIBR_GEN2_SAFE_PATH_FMT safe_path_fmt
#define MIBR_GEN2_PLATFORM_DEFAULTS platform_defaults_path
#include "../modules/carplay/source/altscreen111-gen2/libaltscreen111_gen2.c"
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

static void write_file(const char *path,const char *text)
{
    FILE *f=fopen(path,"w");
    assert(f);
    assert(fputs(text,f)>=0);
    assert(!fclose(f));
}

/* Load view 0 safe area with the given registry layer for viewarea.0.safe.x
 * (ALT111_PROFILE = nothing stored) under a fresh scope. */
static void load_safe(unsigned layer,struct mibr_viewareas_config *views)
{
    struct gen2_settings_scope scope;
    struct alt111_settings desired;
    assert(!alt111_settings_defaults(&desired,"mibr_dual_view"));
    if(layer!=ALT111_PROFILE)
        assert(!alt111_settings_set(&desired,alt111_setting_find("viewarea.0.safe.x"),"33",layer));
    memset(&scope,0,sizeof(scope));scope.settings=desired;scope.valid=1;
    assert(!pthread_setspecific(g_settings_scope_key,&scope));
    load_viewareas_config(views);
    assert(!pthread_setspecific(g_settings_scope_key,NULL));
}

static void test_safe_precedence(const char *root)
{
    struct mibr_viewareas_config views;
    char broker[192];
    int profile_x;
    snprintf(safe_path_fmt,sizeof(safe_path_fmt),"%s/%%s.conf",root);
    snprintf(platform_defaults_path,sizeof(platform_defaults_path),"%s/plat.conf",root);
    snprintf(broker,sizeof(broker),"%s/safe-wide.conf",root);
    unlink(broker);unlink(platform_defaults_path);

    /* No files, nothing stored: compiled profile stays. */
    load_safe(ALT111_PROFILE,&views);profile_x=views.view[0].safe_x;
    assert(views.count>=1 && profile_x!=55 && profile_x!=33 && profile_x!=11);

    /* 3: no broker file, only profile layer -> platform default applies. */
    write_file(platform_defaults_path,"safe_voll=1,2,300,200\nsafe_wide=55,66,320,220\n");
    load_safe(ALT111_PROFILE,&views);
    assert(views.view[0].safe_x==55 && views.view[0].safe_y==66 &&
           views.view[0].safe_w==320 && views.view[0].safe_h==220);

    /* 2: stored PERSISTENT or TEMP value is kept; platform default not applied. */
    load_safe(ALT111_PERSISTENT,&views);
    assert(views.view[0].safe_x==33 && views.view[0].safe_w!=320);
    load_safe(ALT111_TEMP,&views);
    assert(views.view[0].safe_x==33 && views.view[0].safe_w!=320);

    /* 1: valid broker file wins over stored value and platform default. */
    write_file(broker,"# mibr\nrevision=3\nvalue=11,22,310,210\n");
    load_safe(ALT111_PERSISTENT,&views);
    assert(views.view[0].safe_x==11 && views.view[0].safe_y==22 &&
           views.view[0].safe_w==310 && views.view[0].safe_h==210);
    load_safe(ALT111_TEMP,&views);assert(views.view[0].safe_x==11);
    load_safe(ALT111_PROFILE,&views);assert(views.view[0].safe_x==11);

    /* 4: a non-empty but corrupt broker file returns early: the configured
     * area stays (stored or profile); the platform default is NOT applied. */
    write_file(broker,"revision=3\nvalue=11,22,310\n");
    load_safe(ALT111_PROFILE,&views);assert(views.view[0].safe_x==profile_x);
    load_safe(ALT111_PERSISTENT,&views);assert(views.view[0].safe_x==33);
    write_file(broker,"revision=3\nvalue=11,22,310,210 junk\n");
    load_safe(ALT111_PROFILE,&views);assert(views.view[0].safe_x==profile_x);
    /* Out-of-range broker value (w<100) is rejected, area unchanged. */
    write_file(broker,"revision=3\nvalue=11,22,50,210\n");
    load_safe(ALT111_PROFILE,&views);assert(views.view[0].safe_x==profile_x);
    /* An empty broker file counts as no choice: falls through like a missing one. */
    write_file(broker,"");
    load_safe(ALT111_PROFILE,&views);assert(views.view[0].safe_x==55);
    load_safe(ALT111_PERSISTENT,&views);assert(views.view[0].safe_x==33);

    unlink(broker);unlink(platform_defaults_path);
    load_safe(ALT111_PROFILE,&views);assert(views.view[0].safe_x==profile_x);
}

static void zoom_cfg_case(const char *path,const char *body,unsigned src,unsigned tag,unsigned win,unsigned au)
{
    FILE *f=fopen(path,"w");
    assert(f);if(body)fputs(body,f);fclose(f);
    gen2_zoom_cfg_load();
    assert(g2_zoom_cfg.source==src && g2_zoom_cfg.tag==tag &&
           g2_zoom_cfg.window_ms==win && g2_zoom_cfg.wheel_auto==au);
}

static void test_zoom_config(const char *root)
{
    snprintf(platform_defaults_path,sizeof(platform_defaults_path),"%s/plat.conf",root);
    unlink(platform_defaults_path);
    gen2_zoom_cfg_load();assert(g2_zoom_cfg.source==40 && g2_zoom_cfg.tag==56 &&
        g2_zoom_cfg.window_ms==40 && g2_zoom_cfg.wheel_auto==0); /* missing file */
    zoom_cfg_case(platform_defaults_path,"safe_voll=1,2,3,4\n",40,56,40,0);
    zoom_cfg_case(platform_defaults_path,"zoom.wheel_source=41\nzoom.tag=57\nzoom.match_window_ms=60\nzoom.wheel_auto=1\n",41,57,60,1);
    zoom_cfg_case(platform_defaults_path,"x=1\nzoom.tag=0\nzoom.wheel_source=65535",65535,0,40,0);
    zoom_cfg_case(platform_defaults_path,"zoom.wheel_source=65536\nzoom.tag=-1\nzoom.match_window_ms=0\nzoom.wheel_auto=2\n",40,56,40,0);
    zoom_cfg_case(platform_defaults_path,"zoom.match_window_ms=501\nzoom.tag=5x\nxzoom.wheel_source=9\n",40,56,40,0);
    zoom_cfg_case(platform_defaults_path,"zoom.match_window_ms=500\nzoom.match_window_ms=1\n",40,56,500,0);
    unlink(platform_defaults_path);
    gen2_zoom_cfg_load();assert(g2_zoom_cfg.window_ms==40); /* back to defaults */
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
    test_zoom_config(root);
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
    test_safe_precedence(root);
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
