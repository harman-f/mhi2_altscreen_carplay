#define main b0_cli_main
#include "../b0-discovery/mhi2_wcp_b0_discovery.c"
#undef main
#include <assert.h>

int main(int argc, char **argv)
{
    struct b0_state state;
    char content[4096];
    FILE *fp;
    size_t n;
    assert(argc == 2);
    memset(&state, 0, sizeof(state));
    snprintf(state.state_path, sizeof(state.state_path), "%s", argv[1]);
    snprintf(state.ifname, sizeof(state.ifname), "audit0");
    write_state_file(&state, "audit-test");
    fp = fopen(argv[1], "r");
    assert(fp != NULL);
    n = fread(content, 1, sizeof(content) - 1, fp);
    assert(fclose(fp) == 0);
    content[n] = '\0';
    assert(strstr(content, "phase=audit-test\ninterface=audit0\n") != NULL);
    assert(strstr(content, "\\n") == NULL);
    assert(unlink(argv[1]) == 0);
    puts("B0 state newline regression: ok");
    return 0;
}
