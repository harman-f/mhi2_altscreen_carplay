#!/usr/bin/env python3
"""menu-editor/function-catalog.json -> MibrMenuCatalog.java and the standard menu file."""
import json
import pathlib
import zlib

HERE = pathlib.Path(__file__).resolve().parent
CATALOG = HERE / "menu-editor" / "function-catalog.json"
JAVA = HERE / "java" / "de" / "mibr" / "hmi" / "MibrMenuCatalog.java"
STANDARD = HERE / "menu-editor" / "standard-menu.txt"


def java_string(value):
    return json.dumps(value, ensure_ascii=False)


def array(name, values):
    return " static final String[] %s={\n  %s\n };\n" % (name, ",\n  ".join(java_string(v) for v in values))


def order(functions):
    """Parents before children, keeps the catalog order within a parent."""
    out = []

    def walk(parent):
        for f in functions:
            if f["parent"] == parent:
                out.append(f)
                walk(f["id"])

    walk("root")
    return out


def standard_file(catalog):
    lines = ["MIBR_MENU/1", "catalog=%d" % catalog["catalog"], "brand=skoda", "name=Standard"]
    for f in order(catalog["functions"]):
        flags = "x" if f.get("expert") else "-"
        lines.append("\t".join((f["id"], f["parent"], flags, "", "")))
    body = "\n".join(lines) + "\n"
    return body + "crc32=%08x\n" % (zlib.crc32(body.encode("utf-8")) & 0xffffffff)


def basic_file(catalog):
    """The fallback inside the JAR: only what it takes to load a menu."""
    lines = ["MIBR_MENU/1", "catalog=%d" % catalog["catalog"], "brand=skoda", "name=Basic"]
    lines += ["version\troot\t-\t\t", "advanced\troot\t-\t\t", "menu.load\tadvanced\t-\t\t"]
    body = "\n".join(lines) + "\n"
    return body + "crc32=%08x\n" % (zlib.crc32(body.encode("utf-8")) & 0xffffffff)


def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    functions = order(catalog["functions"])
    if len(functions) != len(catalog["functions"]):
        raise SystemExit("catalog entry with unknown parent")
    standard = standard_file(catalog)
    STANDARD.write_bytes(standard.encode("utf-8"))
    java = ["/* Generated from menu-editor/function-catalog.json. */\n", "package de.mibr.hmi;\n",
            "final class MibrMenuCatalog {\n", " private MibrMenuCatalog(){}\n",
            " static final int CATALOG=%d;\n" % catalog["catalog"],
            array("IDS", [f["id"] for f in functions]),
            array("KINDS", [f["kind"] for f in functions]),
            array("DE", [f["de"] for f in functions]),
            array("EN", [f["en"] for f in functions]),
            " static final int[] SINCE={%s};\n" % ",".join(str(f.get("since", 1)) for f in functions),
            " static final String BASIC=%s;\n" % java_string(basic_file(catalog)),
            "}\n"]
    JAVA.write_bytes("".join(java).encode("utf-8"))


if __name__ == "__main__":
    main()
