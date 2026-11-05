"""Frozen copy of the pre-profile OEM source patcher (Skoda MU1440 behaviour).

Used only by test_profiles.py to prove the data-driven Skoda anchor set yields
byte-identical output. Do not edit.
"""

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
        "import org.osgi.framework.BundleContext;",
        "import org.osgi.framework.BundleContext;\nimport org.osgi.framework.InvalidSyntaxException;",
        "ACTIVATOR_INVALID_SYNTAX_IMPORT",
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
    text = replace_once(
        text,
        "this.bundleContext.addServiceListener(this, string);\n"
        "        ServiceReference[] serviceReferenceArray = this.bundleContext.getServiceReferences(null, string);",
        "ServiceReference[] serviceReferenceArray;\n"
        "        try {\n"
        "            this.bundleContext.addServiceListener(this, string);\n"
        "            serviceReferenceArray = this.bundleContext.getServiceReferences(null, string);\n"
        "        } catch (InvalidSyntaxException invalidSyntaxException) {\n"
        "            throw new IllegalArgumentException(\"Invalid CIO service filter: \" + invalidSyntaxException.toString());\n"
        "        }",
        "ACTIVATOR_SERVICE_FILTER_CHECKED_EXCEPTION",
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
