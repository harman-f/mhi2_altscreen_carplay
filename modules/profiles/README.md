# Three firmware profiles — one common beta release

**Owner decision (2026-11-03):** The Škoda MU1440 P4526 and SEAT MU1409 P4708 and MU1447 P4709 profiles are equally required for the ordinary beta installation bundle. The repository structure is treated as accepted for further development; extensive software-level work is the current baseline. Final end-to-end system testing remains pending **for the beta as a whole**, not as a special SEAT approval process.

| Profile | Firmware | Original `lsd.jxe` SHA-256 | Java |
| --- | --- | --- | --- |
| `skoda-mu1440-p4526` | `MHI2_ER_SKG13_P4526_MU1440` | `a55d9cfb69c5756f8202b7f7aa4079d4d5b637ae4c2fd0fe723f1d6816cbeea8` | R57 reference source |
| `seat-mu1409-p4708` | `MHI2_ER_SEG11_P4708_MU1409` | exact digest still missing; P4708_1 must be compared separately | OEM Java work can continue |
| `seat-mu1447-p4709` | `MHI2_ER_SEG11_P4709_MU1447` | `945586fbede2fe53b5b41d7c10490641ff71fcc9581fb237cf40328f450cb22e` | OEM Java work can continue |

The P4709 digest is taken from the existing exact JXE corpus matrix. For the MU1409 contributor, the reported **55,712,590-byte** original JXE is *not* a hash. P4709 was 55,712,574 bytes. Do not fabricate a digest or treat these as the same file.

Each of the three profile directories has exactly the same `hmi/`, `icons/`, `display/`, `input/` and `integration/` groups. Shared CarPlay, Broker, Menu and Navigation code is published once, with one settings registry and one broker. Java adapter repairs and optimization happen in their target profile without forking shared menu/business logic.

Host-side `python3 tools/release/plan_multi_profile_beta.py --self-test` emits the mandatory three-profile release input. **Missing exact original firmware hashes and compiled Java adapter payloads do not exclude the target from the beta source/build plan, but must be supplied before a genuinely working auto-install ZIP for that firmware is distributed.** All three obey the same package integrity, QNX shell, reversible installation and fingerprint-selection requirements. Final physical vehicle acceptance is not a special prerequisite to building beta test packages.

This integration does not claim a complete new R3 ZIP or newly measured vehicle tests.
