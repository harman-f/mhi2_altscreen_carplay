#!/usr/bin/env python3
"""Construct one minimal, guarded patch of the exact retained CIO OSGi Activator.
Never patch the OEM binary, Sgm.jxe, or the skin. Fail on any upstream drift.
"""
import pathlib
import subprocess
import sys
import re
ROOT = pathlib.Path(__file__).resolve().parents[5]
PROJECT = ROOT / "projects/mhi2-hmi-control-plane/implementation/mibr-carplay-settings-home"
REV = "refs/remotes/origin/IGNORE"
STOCK = "projects/mhi2-au37x-carplay-skoda-mu1440/derived/skoda-mu1440-lsd/java/de/vw/mib/cio/internal/Activator.java"
expected_blob = "fae47c206c5e4eb06e937445633b4c8cc64c3ce9"
blob = subprocess.check_output(["git", "rev-parse", REV + ":" + STOCK], cwd=ROOT, text=True).strip()
if blob != expected_blob:
    raise SystemExit("REFUSE: exact MU1440 Activator blob mismatch: " + blob)
source = subprocess.check_output(["git", "show", REV + ":" + STOCK], cwd=ROOT, text=True)
source = re.sub(r"/\*\n \* Decompiled with CFR 0\.152\.\n \*/\n", "", source, count=1)
source = re.sub(r"\n\s*@Override", "", source)
def replace_once(old, new):
    global source
    if source.count(old) != 1:
        raise SystemExit("REFUSE: expected single source anchor: " + old)
    source = source.replace(old, new, 1)
replace_once(
    "public void start(BundleContext bundleContext) {\n        this.bundleContext = bundleContext;",
    "public void start(BundleContext bundleContext) {\n" +
    "        de.mibr.hmi.MibrHomeCio.activatorStarted();\n" +
    "        this.bundleContext = bundleContext;"
)
replace_once(
    "public void stop(BundleContext bundleContext) {\n    }",
    "public void stop(BundleContext bundleContext) {\n" +
    "        de.mibr.hmi.MibrHomeCio.deactivate();\n" +
    "    }"
)
replace_once(
    "throw new NoClassDefFoundError().initCause(classNotFoundException);",
    "NoClassDefFoundError err = new NoClassDefFoundError(); err.initCause(classNotFoundException); throw err;"
)
replace_once(
    "this.factory = new Factory(this.logger, configurationManager, this.dictionary, this.idService);",
    "this.factory = new Factory(this.logger, configurationManager, this.dictionary, this.idService);\n" +
    "        de.mibr.hmi.MibrHomeCio.bind(this.factory, this.dictionary, dispatcher, this.idService);"
)
replace_once(
    "this.factory.setScriptWidgetService(this.scriptWidgetCioService);",
    "this.factory.setScriptWidgetService(this.scriptWidgetCioService);\n" +
    "        de.mibr.hmi.MibrHomeCio.activate(this.cioVisualizationService);"
)
replace_once(
    "this.cioVisualizationService = (CioVisualizationService)object;",
    "this.cioVisualizationService = new de.mibr.hmi.MibrVisualizationService((CioVisualizationService)object);"
)
replace_once(
    "this.bundleContext.addServiceListener(this, string);\n" +
    "        ServiceReference[] serviceReferenceArray = this.bundleContext.getServiceReferences(null, string);\n" +
    "        for (int i2 = 0; serviceReferenceArray != null && i2 < serviceReferenceArray.length; ++i2) {\n" +
    "            this.serviceChanged(new ServiceEvent(1, serviceReferenceArray[i2]));\n" +
    "        }",
    "try {\n" +
    "            this.bundleContext.addServiceListener(this, string);\n" +
    "            ServiceReference[] serviceReferenceArray = this.bundleContext.getServiceReferences(null, string);\n" +
    "            for (int i2 = 0; serviceReferenceArray != null && i2 < serviceReferenceArray.length; ++i2) {\n" +
    "                this.serviceChanged(new ServiceEvent(1, serviceReferenceArray[i2]));\n" +
    "            }\n" +
    "        } catch (org.osgi.framework.InvalidSyntaxException exception) {\n" +
    "            throw new IllegalStateException(\"invalid fixed CIO service filter\");\n" +
    "        }"
)
path = PROJECT / "generated-src/de/vw/mib/cio/internal/Activator.java"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(source, encoding="utf-8", newline="\n")
print("PREPARE=PASS OEM_ACTIVATOR_BLOB=" + blob)
print("CARPLAY_HOME_ACTIVATOR_PATCH=PASS guarded startup, native-list entry and detach hooks")
