# Configuration source map

Configuration has one shared source set and one platform-specific profile set.
This directory is a navigation layer; the canonical files remain in their
existing owners and are linked below rather than copied here.

| Scope | Canonical source | What it defines |
| --- | --- | --- |
| Shared CarPlay settings | [`settings/registry.json`](../settings/registry.json) | Keys, presets, defaults, validation metadata and runtime bindings. |
| Shared broker defaults | [`modules/broker/source/mibr-control/mibr_durable_switch.c`](../modules/broker/source/mibr-control/mibr_durable_switch.c) | Compiled defaults and durable switch behavior. |
| Per-platform profile | [`config/vehicles/`](vehicles/README.md) → [`modules/profiles/`](../modules/profiles/) | Firmware identity and only the platform-specific integration groups. |
| Human-readable defaults | [`DEFAULT_CONFIGURATION_MATRIX.md`](../docs/configuration/DEFAULT_CONFIGURATION_MATRIX.md) | Derived inventory of shared defaults and menu-only controls; not a second editable registry. |

The deployed `mibr-platform-defaults.conf` is a runtime override consumed by
the broker. It is distinct from the checked-in compiled defaults and from
vehicle identity/profile metadata. A profile field is effective only when a
consumer implements it; declarative metadata alone does not change runtime
behavior.
