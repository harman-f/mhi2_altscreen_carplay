/* Exercise the real GEN2 adapter with no target hooks or live sockets. */
#define ALT111_GEN2_HOST_TEST 1
#include "../src/native/altscreen111-gen2/libaltscreen111_gen2.c"
#include <assert.h>

int main(void)
{
    char root[]="/tmp/alt111-gen2-session-XXXXXX",status[192],log[192];
    struct gen2_settings_scope scope;
    struct mibr_display_config display;
    struct mibr_viewareas_config views;
    char value[96];
    AirPlayReceiverSessionRef session=(void *)(uintptr_t)1;
    assert(mkdtemp(root));
    snprintf(status,sizeof(status),"%s/status",root);g2_status_path=status;
    snprintf(log,sizeof(log),"%s/log",root);g_log_path=log;
    assert(alt111_control_init(&g2_control,1)==ALT111_OK);
    assert(!alt111_settings_defaults(&g_settings_desired,"omonob790"));
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
    g_settings_advertised_session=NULL;
    assert(gen2_control_projection_on(session));
    assert(g2_control.view_count==2 && !g_settings_active_confirmed);
    gen2_control_release();
    unlink(status);unlink(log);assert(!rmdir(root));
    puts("ALT111_GEN2_SETTINGS_SESSION_TEST=PASS");
    return 0;
}
