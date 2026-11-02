/* MIBR-owned menu language preference, independent of OEM locale. */
#ifndef MIBR_MENU_LANGUAGE_H
#define MIBR_MENU_LANGUAGE_H
#include <stdint.h>
#include <stddef.h>
struct mibr_menu_language {char value[5];uint64_t revision;int stored;};
struct mibr_menu_language_guard {
    int (*enter_rw)(void *);
    int (*restore_ro)(void *);
    void *context;
};
int mibr_menu_language_valid(const char *);
int mibr_menu_language_load(const char *,struct mibr_menu_language *,char *,size_t);
int mibr_menu_language_set(const char *,const struct mibr_menu_language *,
 const char *,uint64_t,const struct mibr_menu_language_guard *,char *,size_t);
#endif
