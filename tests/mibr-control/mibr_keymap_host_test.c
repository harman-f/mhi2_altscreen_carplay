/* Host test of the pure keymap parser (mibr_keymap.h). */
#include "mibr_keymap.h"
#include <assert.h>
#include <string.h>

static int logs;
static void lg(const char *m){(void)m;logs++;}
static void expect(const struct mibr_keymap *m,int i,int kbd,int key){assert(m->kbd[i]==kbd&&m->key[i]==key);}

int main(void){
    struct mibr_keymap m;
    char d[160];
    FILE *f;
    int n;
    mibr_keymap_defaults(&m);                 /* compiled defaults = Skoda MU1440 */
    expect(&m,MIBR_KM_VIEW_STEP,4,40);expect(&m,MIBR_KM_VIEW_RESYNC_LONG,4,40);
    expect(&m,MIBR_KM_CARPLAY_SWITCH_LONG,4,44);
    /* every shipped platform-defaults file parses to exactly the defaults, without a log line */
    {static const char *const files[]={"modules/navigation/source/platform-defaults/skoda-mu1440.conf",
        "modules/navigation/source/platform-defaults/seat-mu1409.conf","modules/navigation/source/platform-defaults/seat-mu1447.conf"};
     int i;
     for(i=0;i<3;i++){
        mibr_keymap_defaults(&m);logs=0;
        f=fopen(files[i],"r");assert(f);
        {char b[4097];size_t r=fread(b,1,4096,f);fclose(f);assert(r<4096);b[r]=0;
         assert(mibr_keymap_parse(&m,b,lg)==3&&!logs);}
        expect(&m,0,4,40);expect(&m,1,4,40);expect(&m,2,4,44);}}
    /* override, spaces, comments, CRLF, partial file */
    mibr_keymap_defaults(&m);
    n=mibr_keymap_parse(&m,"# c\r\n  key.carplay_switch_long = 13/116 # trailing\r\n\nkey.view_resync_long=5/7",lg);
    assert(n==2&&!logs);
    expect(&m,MIBR_KM_CARPLAY_SWITCH_LONG,13,116);expect(&m,MIBR_KM_VIEW_RESYNC_LONG,5,7);
    expect(&m,MIBR_KM_VIEW_STEP,4,40);        /* untouched entry keeps its default */
    /* other lines (safe_*, zoom.*, key.menu, unknown key.*) are ignored silently, malformed key.* values
     * are ignored with a log line, values unchanged */
    mibr_keymap_defaults(&m);logs=0;
    n=mibr_keymap_parse(&m,"safe_wide=1,2,3,4\nzoom.tag=56\nkey.menu=16\nkey.future=1/2\nview_step=9/9\n"
        "key.view_step\nkey.view_step=4\nkey.view_step=a/b\nkey.view_step=4/\n"
        "key.view_step=4/40/1\nkey.view_step=-1/3\nkey.view_step=4/70000\nkey.view_step=4/40x\nkey.=3/3\n",lg);
    assert(n==0);assert(logs==8);              /* "key.=3/3" has an empty (unknown) name: no log */
    expect(&m,MIBR_KM_VIEW_STEP,4,40);
    /* too-long line is malformed, later lines still apply */
    {char big[400];memset(big,'x',sizeof(big)-1);big[sizeof(big)-1]=0;
     memcpy(big,"key.view_step=",14);
     mibr_keymap_defaults(&m);logs=0;
     {char t[600];strcpy(t,big);strcat(t,"\nkey.carplay_switch_long=6/9\n");
      n=mibr_keymap_parse(&m,t,lg);assert(n==1&&logs==1);expect(&m,MIBR_KM_CARPLAY_SWITCH_LONG,6,9);}}
    /* missing file: defaults, -1 */
    mibr_keymap_defaults(&m);m.key[0]=99;
    assert(mibr_keymap_load(&m,"/nonexistent/defaults.conf",lg)==-1);expect(&m,0,4,40);
    /* oversized file: defaults + log */
    f=fopen("keymap_big.tmp","w");
    {int i;for(i=0;i<300;i++)fputs("# padding padding padding\n",f);fputs("key.view_step=9/9\n",f);}
    fclose(f);logs=0;
    assert(mibr_keymap_load(&m,"keymap_big.tmp",lg)==0&&logs==1);expect(&m,0,4,40);
    remove("keymap_big.tmp");
    /* load from a real file */
    f=fopen("keymap_ok.tmp","w");fputs("key.view_resync_long=4/41\n",f);fclose(f);
    assert(mibr_keymap_load(&m,"keymap_ok.tmp",lg)==1);expect(&m,MIBR_KM_VIEW_RESYNC_LONG,4,41);
    remove("keymap_ok.tmp");
    mibr_keymap_describe(&m,d,sizeof(d));
    assert(!strcmp(d,"key.view_step=4/40 key.view_resync_long=4/41 key.carplay_switch_long=4/44"));
    mibr_keymap_describe(&m,d,8);assert(strlen(d)<8);
    puts("mibr_keymap host PASS");
    return 0;
}
