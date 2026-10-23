#!/usr/bin/env python3
"""Patch two caller-supplied OEM source files in a private build directory.

The inputs are not distributed. Each patch is guarded by exact unique anchors;
source drift fails closed instead of producing a partial replacement.
"""
import argparse
from pathlib import Path


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise ValueError(label + "_ANCHOR_COUNT=" + str(count))
    return text.replace(old, new, 1)


def patch_activator(text):
    if "de.mibr.hmi.MibrHomeCio" in text or "new de.mibr.hmi.MibrVisualizationService" in text:
        raise ValueError("ACTIVATOR_ALREADY_PATCHED")
    text = replace_once(
        text,
        "public void start(BundleContext bundleContext) {\n        this.bundleContext = bundleContext;",
        "public void start(BundleContext bundleContext) {\n"
        "        de.mibr.hmi.MibrHomeCio.activatorStarted();\n"
        "        this.bundleContext = bundleContext;",
        "ACTIVATOR_START",
    )
    text = replace_once(
        text,
        "public void stop(BundleContext bundleContext) {\n    }",
        "public void stop(BundleContext bundleContext) {\n"
        "        de.mibr.hmi.MibrHomeCio.deactivate();\n"
        "    }",
        "ACTIVATOR_STOP",
    )
    text = replace_once(
        text,
        "throw new NoClassDefFoundError().initCause(classNotFoundException);",
        "NoClassDefFoundError err = new NoClassDefFoundError(); "
        "err.initCause(classNotFoundException); throw err;",
        "ACTIVATOR_JAVA12_CAUSE",
    )
    text = replace_once(
        text,
        "this.factory = new Factory(this.logger, configurationManager, this.dictionary, this.idService);",
        "this.factory = new Factory(this.logger, configurationManager, this.dictionary, this.idService);\n"
        "        de.mibr.hmi.MibrHomeCio.bind(this.factory, this.dictionary, dispatcher, this.idService);",
        "ACTIVATOR_BIND",
    )
    text = replace_once(
        text,
        "this.factory.setScriptWidgetService(this.scriptWidgetCioService);",
        "this.factory.setScriptWidgetService(this.scriptWidgetCioService);\n"
        "        de.mibr.hmi.MibrHomeCio.activate(this.cioVisualizationService);",
        "ACTIVATOR_ACTIVATE",
    )
    return replace_once(
        text,
        "this.cioVisualizationService = (CioVisualizationService)object;",
        "this.cioVisualizationService = new de.mibr.hmi.MibrVisualizationService((CioVisualizationService)object);",
        "ACTIVATOR_VISUALIZATION",
    )


def patch_widget_factory(text):
    if "import de.mibr.hmi.MibrHomeList;" in text or "return new MibrHomeList();" in text:
        raise ValueError("WIDGET_FACTORY_ALREADY_PATCHED")
    text = replace_once(
        text,
        "import de.vw.mib.view.internal.treebuilder.WidgetFactory;",
        "import de.vw.mib.view.internal.treebuilder.WidgetFactory;\nimport de.mibr.hmi.MibrHomeList;",
        "WIDGET_FACTORY_IMPORT",
    )
    return replace_once(
        text,
        "case 55: {\n                return new WidgetList();\n            }",
        "case 55: {\n                return new MibrHomeList();\n            }",
        "WIDGET_FACTORY_SLOT_55",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activator", required=True, type=Path,
                        help="local source for the target CIO Activator")
    parser.add_argument("--widget-factory", required=True, type=Path,
                        help="local source for the target WidgetFactoryImpl")
    parser.add_argument("--out-dir", required=True, type=Path,
                        help="private generated-source directory")
    args = parser.parse_args()
    try:
        activator = args.activator.read_text(encoding="utf-8").replace("\r\n", "\n")
        widget = args.widget_factory.read_text(encoding="utf-8").replace("\r\n", "\n")
        activator = patch_activator(activator)
        widget = patch_widget_factory(widget)
        a_path = args.out_dir / "de/vw/mib/cio/internal/Activator.java"
        w_path = args.out_dir / "generated/de/vw/mib/global/view/internal/WidgetFactoryImpl.java"
        a_path.parent.mkdir(parents=True, exist_ok=True)
        w_path.parent.mkdir(parents=True, exist_ok=True)
        a_path.write_text(activator, encoding="utf-8", newline="\n")
        w_path.write_text(widget, encoding="utf-8", newline="\n")
        print("OEM_SOURCE_PATCH=PASS inputs=2 outputs=private-build-only")
        return 0
    except (OSError, UnicodeError, ValueError) as error:
        raise SystemExit(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
