# Vehicle-profile menu binaries

These three profile-specific MIBR-CarPlay.jar files are the exact artifacts from
the 1.5.0-beta.11 r11b test package. They contain adapted OEM classes and are
included under the repository owner's explicit authorization. Do not add the
original OEM firmware, original JARs, decompiled OEM sources, or J9 SDK.

| Profile | SHA-256 |
| --- | --- |
| SEAT MU1409 | `4877e37eabea093f765cd81775728fcad088c981ce541ec61350f5d9cdcdeb6a` |
| SEAT MU1447 | `4f7786d3aa3f6c70f3b2b93858569081634ed7aeb3e3e9c0c50ab60ed8a8e177` |
| Skoda MU1440 | `5f63fcddfa267bc7dd134b3c548a9a0e300d57a625aac3fbf472164706884a39` |

The public menu Java/firmware-profile/registry inputs were reconciled with the
reference JARs at source baseline `420fc46c63594a1a0274ddf6a3da7fb19c33b294`.
`tools/release/stage_prebuilt_menu.py` refuses package reuse if those inputs have
changed. This baseline identifies the reviewed public source snapshot; it is
not a claim that these ZIP archives were rebuilt byte-for-byte by public CI.
Never update the baseline without a newly reviewed locally built set of JARs,
source/API hashes and class-version verification. The separately built extender
is not part of these three prebuilt menu JARs.

The owner reports that the Skoda package was installed and its uninstall and
reinstall exercised on the unit. SEAT has not been vehicle-tested. These bytes
are a historical reference; a new build is not automatically vehicle-qualified.
