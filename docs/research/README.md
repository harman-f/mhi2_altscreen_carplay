# Research library — MIB Runtime

[Documentation home](../README.md) · [Feature and vehicle evidence](../status/FEATURE_STATUS.md) · [Packages and releases](../packages/README.md) · [Research rules](AGENTS.md)

The research library retains **dated technical evidence, competing implementations, reverse engineering, failed approaches and open hypotheses**. It is not a second product manual. To see what the **current public source**, **a released package**, or **an actual vehicle run** proves, start with the links above.

## Browse by topic

| Research area | What you will find | Start here |
| --- | --- | --- |
| **[CarPlay / protocol](carplay/README.md)** | Stream 111, iOS sender, cluster settings, ViewArea, PlatformControl | [Stream-111 protocol](carplay/STREAM111_PROTOCOL.md) |
| **[Media / MOST](media/README.md)** | Producer comparisons, GEN2 hooks, frame rate, decoder and keyframe hypotheses | [Comparator findings](media/COMPARATOR_FINDINGS.md) |
| **[Firmware and cluster](firmware/README.md)** | Exact MHI2 baselines, portability, AID/FPK and OEM source comparison | [Firmware profile map](firmware/MHI2_FIRMWARE_PROFILE_MAP_2026-09-28.md) |
| **[Hardware, boot and clocks](hardware/README.md)** | MMX Tegra/QNX, NOR, RCC Jacinto5, safe read-only diagnostics | [Consolidated hardware study](hardware/MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md) |
| **[HMI and input](interface/README.md)** | J9 build interface, buttons, media/Now Playing, native input | [Key and encoder studies](keypanel/README.md) |
| **[Wireless CarPlay](mhi2-native-wireless-2026-10/README.md)** | Independent Bluetooth/iAP2/Wi-Fi research, prototypes, blockers | [Wireless end-to-end architecture](mhi2-native-wireless-2026-10/09_END_TO_END_ARCHITECTURE.md) |
| **[Historical / superseded summaries](archive/README.md)** | Older summaries replaced as current navigation, retained for provenance | [5 October preview](archive/CURRENT_RESEARCH_PREVIEW_2026-10-05.md) |

The existing [AltScreen Cluster Atlas](../index.html) is a separate, cross-project comparison view. [Public references and attribution](PUBLIC_REFERENCES.md) · [Research method](../RESEARCH_METHOD.md).

## What does the status on a research page mean?

| Classification | Meaning | How to use it |
| --- | --- | --- |
| **REFERENCE / EVIDENCE** | Original analysis, static proof, repeatable observation, or dated experimental record | Reusable **within its documented exact target and evidence limits**; it is not automatically the latest runtime |
| **OPEN RESEARCH / PROPOSAL** | Design, untested hypothesis or experiment with unclosed validation gates | Investigate; do not equate it with a ready-made feature |
| **HISTORICAL SNAPSHOT** | A faithful record of an earlier point in the project | Useful for chronology and regression reasoning, not current release instructions |
| **SUPERSEDED OVERVIEW** | A newer canonical status or architecture page replaced the *summary's role* | Follow the replacement for current conclusions; preserve original evidence and attribution |
| **SOURCE INTEGRATED** | A separately cited PR/commit includes a particular implementation | Source presence does not demonstrate package, unit or vehicle acceptance |

**A newer result supersedes a specific conclusion, not necessarily an entire study.** For example, one previously unknown input key can be resolved while the same report still provides valid measured packet data. Do not reclassify a whole document without linking the exact later evidence.

## From research to implementation

Research notes belong here. Current interfaces, source and ownership belong in [modules](../../modules/), [architecture](../architecture/README.md) and [configuration](../configuration/DEFAULT_CONFIGURATION_MATRIX.md). Package details and vehicle claims belong in [package status](../packages/README.md) and [feature/evidence status](../status/FEATURE_STATUS.md), respectively.

When a research line becomes integrated, **add a short pointer to its canonical current owner and keep the original dated study**. When an approach is abandoned, mark the decision and its later evidence explicitly rather than deleting the failed experiment. Preserve real-world negative results and safety constraints.

[Documentation and archival policy](../DOCUMENTATION_POLICY.md) · [Instructions for documentation agents](../AGENTS.md) · [Research-specific agent rules](AGENTS.md).
