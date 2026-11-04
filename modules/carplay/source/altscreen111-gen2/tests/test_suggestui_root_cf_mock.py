"""Compile the production suggestUI array writer against a small CF mock."""

from pathlib import Path
import subprocess
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "libaltscreen111_gen2.c"


def extract_function(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for pos in range(brace, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start : pos + 1]
    raise ValueError(f"unterminated function: {signature}")


PRELUDE = r"""
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef long CFIndex;
typedef struct mock_object *CFTypeRef;
typedef struct mock_object *CFStringRef;
typedef struct mock_object *CFMutableArrayRef;
typedef struct mock_object *CFArrayRef;
typedef struct mock_object *CFMutableDictionaryRef;
typedef struct mock_object *CFDictionaryRef;

#define ALT_URL_DEFAULT "maps:/car/instrumentcluster"
#define ALT_URL_MAP "maps:/car/instrumentcluster/map"
#define ALT_URL_INSTRUCTIONCARD "maps:/car/instrumentcluster/instructioncard"

enum { MOCK_STRING = 1, MOCK_ARRAY = 2, MOCK_DICTIONARY = 3 };
struct mock_object {
    int kind;
    unsigned refs;
    char text[256];
    CFTypeRef items[8];
    size_t count;
    struct { CFStringRef key; CFTypeRef value; } entries[8];
};

static const void *p_array_callbacks;
static CFMutableArrayRef (*p_CFArrayCreateMutable)(const void *, CFIndex, const void *);
static void (*p_CFArrayAppendValue)(CFMutableArrayRef, CFTypeRef);
static CFIndex (*p_CFArrayGetCount)(CFArrayRef);
static void (*p_CFRelease)(CFTypeRef);
static void (*p_CFDictionarySetValue)(CFMutableDictionaryRef, CFTypeRef, CFTypeRef);
static CFTypeRef (*p_CFDictionaryGetValue)(CFDictionaryRef, CFTypeRef);
static int fail_string_call;
static int string_calls;
static int fail_array_create;
static int drop_array_append;
static int drop_dictionary_set;
static int layered_status;
static const char *layered_config;
static const char *g_ui_urls_config_name = "mibr-carplay111-ui-urls.conf";

static CFTypeRef retain(CFTypeRef o) { if (o) ++o->refs; return o; }
static CFTypeRef make_object(int kind) {
    CFTypeRef o = calloc(1, sizeof(*o));
    if (o) { o->kind = kind; o->refs = 1; }
    return o;
}
static void mock_release(CFTypeRef o) {
    size_t i;
    if (!o || --o->refs) return;
    if (o->kind == MOCK_ARRAY) {
        for (i = 0; i < o->count; ++i) mock_release(o->items[i]);
    } else if (o->kind == MOCK_DICTIONARY) {
        for (i = 0; i < o->count; ++i) {
            mock_release(o->entries[i].key);
            mock_release(o->entries[i].value);
        }
    }
    free(o);
}
static CFTypeRef mock_string(const char *text) {
    CFTypeRef o;
    ++string_calls;
    if (fail_string_call && string_calls == fail_string_call) return NULL;
    o = make_object(MOCK_STRING);
    if (o) snprintf(o->text, sizeof(o->text), "%s", text);
    return o;
}
static CFMutableArrayRef mock_array_create(const void *allocator, CFIndex capacity, const void *callbacks) {
    (void)allocator; (void)capacity; (void)callbacks;
    return fail_array_create ? NULL : make_object(MOCK_ARRAY);
}
static void mock_array_append(CFMutableArrayRef a, CFTypeRef value) {
    if (!drop_array_append && a && a->kind == MOCK_ARRAY && value && a->count < 8)
        a->items[a->count++] = retain(value);
}
static CFIndex mock_array_count(CFArrayRef a) {
    return a && a->kind == MOCK_ARRAY ? (CFIndex)a->count : -1;
}
static CFTypeRef mock_dictionary_get(CFDictionaryRef d, CFTypeRef key) {
    size_t i;
    if (!d || d->kind != MOCK_DICTIONARY || !key || key->kind != MOCK_STRING) return NULL;
    for (i = 0; i < d->count; ++i)
        if (!strcmp(d->entries[i].key->text, key->text)) return d->entries[i].value;
    return NULL;
}
static void mock_dictionary_set(CFMutableDictionaryRef d, CFTypeRef key, CFTypeRef value) {
    size_t i;
    if (drop_dictionary_set || !d || d->kind != MOCK_DICTIONARY || !key || !value) return;
    for (i = 0; i < d->count; ++i) {
        if (!strcmp(d->entries[i].key->text, key->text)) {
            mock_release(d->entries[i].key); mock_release(d->entries[i].value);
            d->entries[i].key = retain(key); d->entries[i].value = retain(value); return;
        }
    }
    if (d->count < 8) {
        d->entries[d->count].key = retain(key);
        d->entries[d->count].value = retain(value);
        ++d->count;
    }
}
static CFMutableDictionaryRef mock_dictionary_create(void) { return make_object(MOCK_DICTIONARY); }
static int mock_dictionary_has(CFDictionaryRef d, const char *name) {
    CFTypeRef key = mock_string(name), value;
    if (!key) return 0;
    value = mock_dictionary_get(d, key); mock_release(key); return value != NULL;
}
static const char *mock_array_item(CFArrayRef a, size_t i) {
    if (!a || a->kind != MOCK_ARRAY || i >= a->count || !a->items[i] || a->items[i]->kind != MOCK_STRING)
        return NULL;
    return a->items[i]->text;
}
static CFStringRef s_cf(const char *text) { return mock_string(text); }
static int read_layered_value(const char *name, char *out, size_t cap, unsigned *layer) {
    size_t n;
    if (layered_status || !layered_config || strcmp(name, g_ui_urls_config_name)) return -1;
    n = strlen(layered_config);
    if (n >= cap) return -1;
    memcpy(out, layered_config, n + 1); if (layer) *layer = 2u; return 0;
}
static const char *config_layer_name(unsigned layer) { return layer == 2u ? "temp" : "default"; }
static void logf_u2(const char *format, ...) { (void)format; }
static int check(int ok, const char *message) {
    if (ok) return 0;
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}
"""


RUNNER = r"""
int main(void) {
    CFMutableDictionaryRef root, nested, failed;
    CFStringRef key;
    CFArrayRef urls;
    p_CFArrayCreateMutable = mock_array_create;
    p_CFArrayAppendValue = mock_array_append;
    p_CFArrayGetCount = mock_array_count;
    p_CFRelease = mock_release;
    p_CFDictionarySetValue = mock_dictionary_set;
    p_CFDictionaryGetValue = mock_dictionary_get;

    layered_config = "schema=2\nurls=maps:/car/instrumentcluster|maps:/car/instrumentcluster/map|maps:/car/instrumentcluster/instructioncard\n";
    root = mock_dictionary_create(); nested = mock_dictionary_create();
    if (check(add_alt_suggest_ui_urls(root), "configured root list succeeds")) return 1;
    key = s_cf("altScreenSuggestUIURLs");
    urls = (CFArrayRef)mock_dictionary_get(root, key);
    if (check(urls && urls->count == 3, "root has three URL strings")) return 1;
    if (check(!strcmp(mock_array_item(urls, 0), ALT_URL_DEFAULT) &&
              !strcmp(mock_array_item(urls, 1), ALT_URL_MAP) &&
              !strcmp(mock_array_item(urls, 2), ALT_URL_INSTRUCTIONCARD), "root URL order and string values")) return 1;
    if (check(!mock_dictionary_has(nested, "altScreenSuggestUIURLs"), "writer does not put capability under displays[n]")) return 1;
    mock_release(key); mock_release(root); mock_release(nested);

    layered_status = 1; layered_config = NULL;
    root = mock_dictionary_create();
    if (check(add_alt_suggest_ui_urls(root), "defaults used when no list is configured")) return 1;
    key = s_cf("altScreenSuggestUIURLs"); urls = (CFArrayRef)mock_dictionary_get(root, key);
    if (check(urls && urls->count == 3 && !strcmp(mock_array_item(urls, 2), ALT_URL_INSTRUCTIONCARD), "default roles are complete")) return 1;
    mock_release(key); mock_release(root);

    layered_status = 0; layered_config = "schema=2\nurls=maps:/car/instrumentcluster|maps:/car/instrumentcluster/map\n";
    string_calls = 0; fail_string_call = 2;
    root = mock_dictionary_create();
    if (check(!add_alt_suggest_ui_urls(root), "string allocation failure is reported")) return 1;
    if (check(!mock_dictionary_has(root, "altScreenSuggestUIURLs"), "allocation failure leaves root unmodified")) return 1;
    mock_release(root); fail_string_call = 0;

    string_calls = 0; drop_dictionary_set = 1; root = mock_dictionary_create();
    if (check(!add_alt_suggest_ui_urls(root), "failed dictionary readback is reported")) return 1;
    if (check(!mock_dictionary_has(root, "altScreenSuggestUIURLs"), "failed readback leaves root unmodified")) return 1;
    mock_release(root); drop_dictionary_set = 0;

    fail_array_create = 1; failed = mock_dictionary_create();
    if (check(!add_alt_suggest_ui_urls(failed), "array allocation failure is reported")) return 1;
    if (check(!mock_dictionary_has(failed, "altScreenSuggestUIURLs"), "array allocation failure leaves root unmodified")) return 1;
    mock_release(failed); fail_array_create = 0;

    drop_array_append = 1; root = mock_dictionary_create();
    if (check(!add_alt_suggest_ui_urls(root), "silent array append failure is reported")) return 1;
    if (check(!mock_dictionary_has(root, "altScreenSuggestUIURLs"), "append failure leaves root unmodified")) return 1;
    mock_release(root); drop_array_append = 0;

    puts("SUGGESTUI_ROOT_CF_MOCK_PASS"); return 0;
}
"""


def build_and_run() -> str:
    source = SOURCE.read_text(encoding="utf-8")
    writer = extract_function(source, "static int add_alt_suggest_ui_urls(CFMutableDictionaryRef info)")
    parser = extract_function(source, "static int config_line_value(const char *blob, const char *key,")
    with tempfile.TemporaryDirectory(prefix="suggestui-root-cf-") as tmp:
        temp = Path(tmp)
        c_file = temp / "suggestui_root_cf_mock.c"
        executable = temp / "suggestui_root_cf_mock"
        c_file.write_text(PRELUDE + "\n" + parser + "\n" + writer + "\n" + RUNNER, encoding="utf-8")
        subprocess.run(["gcc", "-std=gnu99", "-Wall", "-Wextra", "-Werror", str(c_file), "-o", str(executable)], check=True)
        result = subprocess.run([str(executable)], check=True, capture_output=True, text=True)
        return result.stdout.strip()


class SuggestUIRootCFMockTests(unittest.TestCase):
    def test_compiled_writer_root_scope_and_error_paths(self):
        self.assertEqual(build_and_run(), "SUGGESTUI_ROOT_CF_MOCK_PASS")


if __name__ == "__main__":
    unittest.main()
