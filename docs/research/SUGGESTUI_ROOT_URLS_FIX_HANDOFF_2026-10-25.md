# Codex Luna handoff — suggestUI ROOT capability fix, 2026-10-25

**State: SOURCE-ONLY DRAFT; unmerged, not on Unit, not in upcoming acceptance image.**

- Code branch: `work/suggestui-root-advertisement-review-20261025` based on `main` (not the owner's unpushed newer acceptance branch).
- Research authority: [CaneTLOTW/M.I.B._Research#129](https://github.com/CaneTLOTW/M.I.B._Research/issues/129), especially comments [root-scope evidence](https://github.com/CaneTLOTW/M.I.B._Research/issues/129#issuecomment-6391479710) and [owner's no-menu/no-auto policy](https://github.com/CaneTLOTW/M.I.B._Research/issues/129#issuecomment-6394796194).
- **Owner's latest request** is to implement the discovered wire fix **in source code** and have Codex Luna review it. This supersedes the earlier research-only restriction **for an isolated code branch only**; it does **not** authorize merging into the current acceptance candidate, uploading binaries to the HU, or implementing automatic UI selection.

## 1. Exact source-backed bug

Before this patch GEN2 called `add_alt_suggest_ui_urls(alt)`, storing an array under `displays[n].altScreenSuggestUIURLs` and logging `GEN2 advertised altScreenSuggestUIURLs count=3`.

The pinned iOS 26.1 decompile `EthanArbuckle/iPhone18-3_26.1_23B85_Restore@90aa0cfe59d9682b4265e1354c8b19ec3c7823ab` shows:
- `System/Library/PrivateFrameworks/CarKit.framework/CarKit/CARSessionConfiguration.mm` near 608: `EndpointInfo["altScreenSuggestUIURLs"]` → `_altScreenSuggestUIURLs` (**ROOT**, not display).
- `CARSession.mm` near 1890–2040: `suggestUI:` reads that list and `clusterSessionURLs`, then calls `CARHandleSuggestUI`.
- `CarKit.mm` near 3917–4024: request/source, iOS/session URL list, and receiver-allowed URLs are intersected; empty root capability can result in `{"urls":[]}`.
- `System/Library/PrivateFrameworks/AirPlaySender.framework/AirPlaySender/AirPlaySender.mm` near 8983–9000: endpoint property `AltScreenSuggestUIURLs` copies `EndpointInfo["altScreenSuggestUIURLs"]`, returning an empty CFArray when missing.
- Existing vehicle archive (2026-10-20) logs **nested** writer count 3, but receives only `suggestUI.urls count=0` in inspected sessions. This correlation supports the candidate defect; it does **not** exclude legitimate withdrawal, app/provider URLs not matching, or a change in the user's exact iOS version.

## 2. What this branch implements (and explicitly does not)

Source: `src/native/altscreen111-gen2/libaltscreen111_gen2.c`.

1. The existing `add_alt_suggest_ui_urls` function now takes the **root** CFMutableDictionary (`info`) and writes the same existing `CFArray<CFString>` there using exactly the key `altScreenSuggestUIURLs`. It checks readback, logs root count/source, and makes failed construction return stock `/info`. The original URL roles and settings precedence remain unchanged.
2. It is called only **after** the synthetic secondary display has been appended and `info["displays"]` has been written, and only when `!compat_profile_exact_reference()`. Classic single-view/strict parity keeps its existing no-advertisement contract.
3. A potentially inherited/misplaced `altScreenSuggestUIURLs` on **synthetic display `alt` only** is removed in the MIBR profile. The stock/Main display and existing `initialURL`, `altScreenURLs`, video streams, UUIDs, ViewAreas, codec pixels and parity data plane are not deliberately altered.
4. Prior `url[192]` parsing scratch was raised to `url[2048]` to avoid silently clipping a configured `urls=...|...|...` list before conversion (still bounded by the underlying `blob[2048]` render and existing max 8 URLs).
5. Original root capability logger checks only **existence, CFType and array count**; it does not newly print raw root URL values. The legacy nested stock-display diagnostics are otherwise untouched.
6. The existing `mibr_platform_control` `suggestUI` path remains exactly **LIVI_NOOP**: stock may return `-6714`, our private Type111 reply may return success, optional D2 scheduling continues. **No storing inbound candidate URLs, no `showUI`, no followSuggestions switch, no new registry key, no HMI changes.**

Tests added: `src/native/altscreen111-gen2/tests/test_suggestui_root_contract.py`. Run:

```sh
python3 -m unittest discover -s src/native/altscreen111-gen2/tests -p 'test_suggestui_root_contract.py' -v
```

**Important:** These are deterministic *static source-contract guards*, not an executed QNX/CFDictionary integration or iOS visual acceptance. In-chat source checks found the relevant 19 invariants true, but no compiled target binary or native vehicle test has been produced.

## 3. Codex Luna independent review assignment

Review this implementation as if you had not designed the patch. Prefer precise source evidence and observable failure states over agreement.

- [ ] Confirm the precise outbound owner: is the actual GEN2 `info` result indeed the iPhone's `EndpointInfo` root in the exact MU1440 protocol path? Does any QNX/Apple intermediary further transform/discard the key before iOS gets it? Compare **active** iPhone build to pinned 26.1 where possible.
- [ ] Verify root vs display dictionary behavior without regressing other root properties, `displays`, `displayPanels`, main stock source, `sourceVersion` or non-strict MIBR compatibility. Review `dict_clone`, old pointer lifetime, CF retain/release and rollback on allocation/copy failure.
- [ ] Check `add_alt_suggest_ui_urls` return paths, count and type of all CFArray elements, max URL size, truncation in other settings stores, empty/duplicate/invalid URLs, escaping, and exact `NSURL.absoluteString` equality with Apple's intersection logic.
- [ ] Inspect alternate profiles: strict classic (no new root key), default mibr (exact three roles when no config), temp/persistent layered `mibr-carplay111-ui-urls.conf` (no accidental partial parsing), disabled MIBR, multiple stock displays and accidental inherited nested values.
- [ ] Evaluate whether `config_line_value` truncation happens further upstream (`settings_scope` snapshot/`alt111_settings` field maximums), even after raising the local scratch buffer. **Do not silently change persistence semantics without proof.**
- [ ] Check logging cost/sensitivity: root diagnostic is shape-only; existing older nested display logger may still print URL strings; propose redaction separately if necessary, preserving acceptance telemetry.
- [ ] Run native host syntax + existing CI/tests and, if toolchain is available, **exact-target** QNX compilation. Add a meaningful CoreFoundation dictionary fixture or isolated native test (one root, one nested case), rather than relying only on text matching; report what could/could not run.
- [ ] Ensure `LIVI_NOOP`/no-menu behavior is unchanged; don't add an automatic switch simply because this root field is now repaired.
- [ ] Reconcile with latest **new/possibly unpushed vehicle acceptance version**, which may include additional changes; don't overwrite deployed or not-yet-pushed source with old public `main` snapshots.

## 4. Bounded acceptance / proof plan

**Do not alter the release scheduled for acceptance.** Only after that release is approved and exact installed identity recorded:

1. Baseline with naturally occurring session: root presence/CFType/count, nested presence/count, active profile, three expected URL strings redacted to safe role labels, exact `initialURL`, same stock Main and appended Type111 count, baseline `suggestUI.urls` at idle, navigation start, active route and withdrawal.
2. Separate authorized reversible candidate A/B: root emission verified in returned `/info` and iOS endpoint property (not merely GEN2 builder log); check non-empty `suggestUI` during active navigation. `suggestUI([])` when the provider withdraws is normal.
3. Observe `stock_rc`, receiver `return_rc`, session ID, chronology `modesChanged` and `VideoConfig/AU/IDR` without duplicating a single command flowing through SessionControl + PlatformControl.
4. Regression: Type110 unchanged, Type111 1010×376, parity and recovery unaffected, preset/stream transitions work, stock fallback on error, no forced UI switch; test app provider and iPhone version explicitly.
5. Only after non-empty suggestions **and** proper URL selection/ownership semantics are demonstrated, ask owner whether a separate opt-in `navigation.followSuggestions` control is desired, default OFF. This parameter is **NOT APPROVED** by the current task.

## 5. Review verdict template

Codex should return:
- **PASS / CHANGES REQUESTED / BLOCKED** (code); exact link/commit.
- Verified root compatibility with iOS [version] and HU [firmware].
- Root-vs-nested fixture outputs; QNX syntax/build/test commands and results.
- List of unverified assumptions and whether every profile restores stock on failure.
- Separate approval decision required before deployment or merging into active acceptance branch.

The present patch is **source-only, not yet demonstrated on vehicle**.
