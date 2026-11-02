# Upstream component notice

`routeguidance/rgd_tlv.c` and `routeguidance/rgd_tlv.h` are copied verbatim from
[`luka-dev/mib2q-carplay-rgi`](https://github.com/luka-dev/mib2q-carplay-rgi), commit
`df73e061a29c4d996550716987f42a9243daa09a` (2026-10-29). Their Git blob IDs at that
commit are `bc1c4841d4e2f75adc7cece10b81fd1eaa891f0e` and
`c945cb0f66c4e4b735375a927701bdfebf86649e` respectively. The three headers under
`framework/` are the exact upstream build dependencies at the same commit:
`common.h` (`37203e40694d97f86808548c33c6b0e3defd218b`), `logging.h`
(`f0d2236686e9ec07e732a16a347efce591409981`), and `ap_status.h`
(`b7d5040ba8fca6c68813935a312a1a5896309063`). Each retains its upstream copyright
notice.

The upstream repository is licensed under GPL version 3. The upstream `LICENSE` is
included beside these files. No other upstream module is included. The vendored parser
is compiled with logging disabled; `ENABLE_LOGGING=0` is a build option, not a source
modification.
