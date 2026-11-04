# Vehicle configuration entry point

Vehicle-specific metadata has one canonical home under
[`modules/profiles/`](../../modules/profiles/). Each profile directory owns its
`profile.json` and the HMI, icons, display, input and integration groups for
that firmware target. The directories here intentionally contain no copies of
those files.

| Vehicle profile | Canonical profile |
| --- | --- |
| Škoda MU1440 P4526 | [`skoda-mu1440-p4526/profile.json`](../../modules/profiles/skoda-mu1440-p4526/profile.json) |
| SEAT MU1409 P4708 | [`seat-mu1409-p4708/profile.json`](../../modules/profiles/seat-mu1409-p4708/profile.json) |
| SEAT MU1447 P4709 | [`seat-mu1447-p4709/profile.json`](../../modules/profiles/seat-mu1447-p4709/profile.json) |

The machine-readable [module index](../../modules/module-index.json) is the
shared profile inventory used by release planning. Exact firmware fingerprints
and target-specific outputs remain subject to the status recorded by each
profile and build evidence. Do not infer vehicle support from a profile
directory's presence.
