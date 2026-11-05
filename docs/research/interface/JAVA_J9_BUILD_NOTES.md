# MU1440 Java / IBM J9 build notes

> **Research status · 2026-11-05:** **HMI / INPUT RESEARCH REFERENCE.** APIs/build studies do not alone prove installed HMI behavior. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


This project does not redistribute the OEM Java corpus, but the exact reconstruction/build method is
important for anyone working on cluster policy, navigation arbitration or ViewArea state.

Reference firmware:

```text
MHI2_ER_SKG13_P4526_MU1440
```

## Exact stock Java authority

Stock `lsd.jxe`:

```text
size:
55,840,933 bytes

SHA-256:
a55d9cfb69c5756f8202b7f7aa4079d4d5b637ae4c2fd0fe723f1d6816cbeea8
```

One retained reconstruction produced:

```text
reconstructed lsd.jar SHA-256:
57dc5e9313ef8a59403a17b3a6726f0852f6ac68cc72e42ef2a1ca530aba3ae7

compressed lsd.jar.zip SHA-256:
173258a1df2e8b1b0725c6329e6e08240cdee4eab57c612c8dd3baf7dd171285
```

Historical reconstruction tool used for that baseline:

```text
JeniCzech92/lsdtool
commit:
4bf44aac95f03cf3b81985dd9ccd9c81fb1ef63d
```

Newer JXE reconstruction work also uses:

```text
luka-dev/jxe2jar
commit:
3bae6e82177c7084a008c42373042e6eebf5653e
```

**Current comparison authority:** for new internal JXE -> JAR baselines, firmware-to-firmware Java comparisons and revalidation of older findings, use `luka-dev/jxe2jar` by default. `JeniCzech92/lsdtool` remains the historical/known-working licensed route and a useful cross-check, but it is not the preferred internal comparison baseline.

Decompiler:

```text
CFR 0.152
SHA-256:
f686e8f3ded377d7bc87d216a90e9e9512df4156e75b06c655a16648ae8765b2
```

Decompiler output is not bytecode truth. Preserve exact class/JAR hashes and inspect bytecode when a
control-flow or signature question matters.

## The most useful build lesson: use a minimal build island

Do **not** routinely rebuild or ingest the entire decompiled LSD tree.

For a two-class policy patch, use:

```text
exact reconstructed stock lsd.jar
       │
       ├── dependency classpath
       │
patched ChangeDataRate.java
patched ChangeDataRateSequence.java
       │
       └── compile BOTH in one javac invocation
              │
              ▼
        two patched class files
              │
              ▼
          small patch JAR
```

Why both sources must compile together:

If `ChangeDataRate.java` is compiled alone, javac may resolve
`ChangeDataRateSequence` from the **stock** classpath instead of the second patched source.

That can produce errors such as:

```text
cannot find symbol:
constructor ChangeDataRateSequence(int, boolean)

cannot find symbol:
method isDirectMode()
```

The fix is architectural, not "simplify the patch until stock compiles":

> Put both modified source files in the same compilation unit/source root and let the exact stock JAR
> satisfy only the unchanged dependencies.

## Exact stock policy path

The relevant stock Java path is:

```text
Kombi / DSIKOMOGfxStreamSink.ATTR_DATARATE
  -> ChangeDataRate.dsiKOMOGfxStreamSinkUpdateDataRate()
  -> ChangeDataRate
  -> ChangeDataRateSequence
  -> NavigationMap / DisplayManagement behavior
  -> stock map-video producer
```

Raw DSI data-rate states:

```text
0 = OFF
1 = REDUCEDBANDWIDTH
2 = FULL
```

Do not fake/suppress this raw upstream state merely to stop the stock video producer.

The stock map-switch state machine waits for real rate transitions, including states 1/2.

## Correct Direct-VC policy seam

The safer policy is:

```text
requested = latest raw DSI request

if DIRECT policy active:
    effective producer rate = 0
    preserve logical navigation-map / Kombi state
else:
    effective producer rate = requested
```

The principle is:

```text
change producer ownership
not
fake vehicle capability or cluster state
```

This finding eventually led to the simpler native `isoTX2` write-gate approach for the currently
proven path, but the Java policy remains useful for understanding the stock state machine.

## Important stock classes

High-value package family:

```text
de/vw/mib/asl/internal/mostkombi/streamsink/
```

Useful classes include:

```text
usecases/ChangeDataRate.java
usecases/ChangeDataRateSequence.java
usecases/SwitchMapFromABTToKombi.java
usecases/SwitchMapFromABTToKombiSequence.java
usecases/SwitchMapFromKombiToABT.java
usecases/SwitchMapFromKombiToABTSequence.java
usecases/SwitchToPermanentMap.java
usecases/SwitchToPermanentMapSequence.java
states/WaitForServices.java
states/RunningState.java
api/navimap/NavigationMapAdapter.java
api/displaymanagement/DisplayManagementAdapter.java
```

Useful observed service/event relationships include:

- `NavigationMapAdapter.setMapVisible()`
- `NavigationMapAdapter.setMapInvisible()`
- `DisplayManagementAdapter.setDataFrameRate(int)`
- `DisplayManagementAdapter.switchToKombiDisplayContext(int)`

## Static capability is not a runtime switch

The stock state machine checks real vehicle capability such as:

- KOMO graphics stream sink available;
- Kombi display present;
- MOST map capability;
- navigation-map service available.

Do not dynamically spoof those just to enter DIRECT.

They answer:

```text
"does this vehicle have this subsystem?"
```

not:

```text
"which producer owns the already-established map video right now?"
```

## Timer/scheduler lesson

When patching the HMI/J9 stack, prefer the stock MIB timer/thread-switching infrastructure over
creating an arbitrary Java background thread.

That keeps callbacks in the expected execution model and reduces lifecycle surprises.

## Boot loading

Patch JARs can be injected through the IBM J9 boot classpath.

Always verify the **actual running J9 command line** after reboot. Do not assume an installer changed
the process simply because the file edit succeeded.

## NavIgnore separation

Navigation arbitration and video bandwidth/control must remain separable.

A NavIgnore-style patch should not silently own the same class as another rate-control patch unless
the two are intentionally combined.

The public project does not redistribute OEM-derived Java class files. See
`docs/architecture/NAVIGNORE.md`.
