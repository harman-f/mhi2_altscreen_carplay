# Acknowledgements

This project exists because a lot of useful MIB2/MHI2 work was published before it.

## Luka / luka-dev

Special thanks to **Luka (`luka-dev`)** for substantial public groundwork around CarPlay/RGI,
MIB2 Java/JXE work and the QNX 6.5 ARMv7 toolchain.

Public projects used directly or as architectural references include:

- https://github.com/luka-dev/mib2q-carplay-rgi
- https://github.com/luka-dev/qnx65-armv7-toolchain
- https://github.com/luka-dev/jxe2jar

Several project decisions became much easier once those pieces were available publicly:

- treating route-guidance metadata separately from full-screen video;
- using small, focused native hooks rather than replacing more of the stack than necessary;
- reconstructing IBM J9/JXE Java in a reproducible way;
- building project-owned QNX/ARM components with a public toolchain.

## OneB1t

Thanks to **OneB1t** and contributors to:

https://github.com/OneB1t/VcMOSTRenderMqb

That work provided important public evidence and implementation context for the MQB Virtual Cockpit /
MOST rendering path.

## Public MHI2Q AltScreen / mirror work

The following public projects have been useful comparators:

- https://github.com/Lanye-z/MHI2Q-CarPlay-MMI-Mirror
- [yuedizhibo/MHI2Q-CarPlay-AltScreen](https://github.com/yuedizhibo/MHI2Q-CarPlay-AltScreen) — owner: yuedizhibo; separate Audi MHI2Q comparison

Their value here is primarily architectural and comparative: control-plane vocabulary, hook roles,
recovery structure and secondary-display behavior.

This project does not claim those implementations as its own and does not copy proprietary payloads
from commercial solutions.


## omonob/MHI2-Carplay-Maps (owner: omonob/QCDWJ) MU1440 AltScreen work

Thanks to the public [omonob/MHI2-Carplay-Maps](https://github.com/omonob/MHI2-Carplay-Maps) project.

Its MU1440/790/791 work has been a useful behavioral comparator for:

- secondary-display negotiation/profile choices;
- complete-AU/source-timestamp handling;
- keyframe request policy;
- MPEG-TS/MOST transport structure;
- routing/session lifecycle.

The project uses those observations as comparative evidence and reimplements behavior independently rather than
redistributing opaque/proprietary payloads.

## Steering-wheel and HMI prior art

Thanks to [y-batsianouski/mib2-voicecontrol-button-patch](https://github.com/y-batsianouski/mib2-voicecontrol-button-patch)
for a public MIB2 hardkey/listener implementation that provided a strong lead for the exact MU1440 ASL input audit.

Thanks also to [jilleb/mib2-toolbox](https://github.com/jilleb/mib2-toolbox) and other public MIB2 HMI work for
useful Java/bootclasspath/menu/runtime precedent. Exact-target MU1440 claims in this repository remain independently
gated and are not inferred solely from those projects.

## Wider MIB community

Additional public MIB2/JXE/HMI work from projects such as:

- `chefranov/mhi2-au37x-carplay`
- `JeniCzech92/lsdtool`
- `grajen3/mib2-lsd-patching`
- `adi961/mib2-android-auto-vc`

has helped reduce duplicated reverse engineering.

## AI-assisted engineering

AI-assisted tooling, including ChatGPT, has been used for:

- reverse-engineering hypothesis generation;
- source/binary comparison;
- code review;
- build/debug workflow design;
- test-plan construction;
- documentation.

AI output is not treated as evidence by itself. Claims in this repository are expected to trace back
to vehicle observations, binary evidence, reproducible builds or clearly identified prior art.

## Input-map contributors welcome

The [public physical key/encoder table](docs/testing/MU1440_MFW_RAW_KEY_MAPPING.md) credits previous public implementation leads separately from our reference-vehicle observations and invites compatible-platform owners to share missing VIEW/Assist and head-unit button mappings. Upstream names here refer only to identified public repositories; this is not a list of private research sources, commercial payload suppliers or implied endorsements.

## Future contributors

If you provide a useful trace, target hash, patch, reverse-engineering finding or test result, please
add enough provenance that future maintainers can understand where it came from.

The goal is for credit and technical lineage to remain visible rather than disappearing into a
binary package.
