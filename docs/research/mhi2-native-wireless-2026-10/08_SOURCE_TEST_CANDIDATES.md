# 08. Prospective original source and test contribution (not yet exported)

**Public status: metadata only.** There is currently no new Wireless source tree in this staged public contribution; the original code exists in a separate **private** archive and is subject to a file-level authorship, copyright, license, privacy and firmware-derived-expression audit before anyone may publish it. A list of names/hashes is not redistribution permission.

## Highest-value coherent sets

| Prospective code family | What it covers | Current caveats |
|---|---|---|
| Native servicegraph adapter + owner hook | iAP `0x4000` registration within target Bluetooth owner | Firmware-specific insertion, attach/detach and lifecycle not proven on vehicle |
| RFCOMM provider: C, header and **all six included implementation units** | SDP/RFCOMM bytes, callback lifetimes, generation, QNX endpoint | Whole dependency set required; do not publish only the small wrapper |
| Stock-compatible Type-3 transport adapter | Stock `mm-ipod`/iAP2 bridge without replacing MFi authorization | Target interface/ABI review and rights check required |
| A3 credential parser and network preflight | WLAN request/response and active AP inspection | **Known Protocol=2/WEP misclassification and stale-field risk**; needs fix and negative test |
| B0 DNS-SD read-only observer | Service browse, resolve and address lookup | **Not** a trusted controller owner; identity, Add/Remove and IPv6 scope issues |
| Unit, mock and QNX-specific tests | Lifecycle, provider events, QNX notify/write/dispatch, recovery models | These establish *offline/host* behavior only |

The provider's six included units are named `prelude`, `setup`, `lifecycle`, `streams`, `events` and `qnx`; the C wrapper includes each one directly. The existing `Makefile` generates three `build/qnx_*.inc` **test fixtures** from the QNX implementation as part of the test prerequisites. These generated fixtures need not be copied as separate checked-in source files, but a complete source transfer must retain the Makefile extraction rules and original input source.

## Secondary or excluded sets

- Volatile process wrappers, overlays, stock-launch/stop scripts: **secondary historical diagnostic material** requiring safety review and explicit nonproduction labeling. Not suitable for a generic vehicle installer.
- Exact-target reconstructed delegate headers: potentially useful as **conceptual ABI descriptions**, not automatically approved copyable source; do not assume firmware-derived header contents are cleared.
- Raw firmware images, decompiler outputs, MFi/certificate/key material, protected code, OEM patches, real AP credentials, partner product files or personal logs: **exclude from the outbound distribution**.

## Minimum source publication gate

1. Identify creator(s), source commit, copied third-party portions, outbound license and mandatory notices for **each** file.
2. Compare code expressions against copyrighted original implementations and avoid directly redistributing protected function bodies.
3. Review every actual exported file for keys/certificates, tokens, SSIDs/PSKs, MAC/VIN, private paths, company/account identifiers and third-party solution names. Manual review is needed in addition to regex checks.
4. Export a dependency-complete C/header/include/tests set, compile with the applicable host and QNX tools and run the *actual exported bytes* through regression tests.
5. Create `SOURCE_MANIFEST.tsv` recording final exported SHA-256, author, origin, license, redaction and test level. Source Git-object SHA-1 from a private snapshot is not the same thing as an exported SHA-256.
6. Publish through a new clean public research-only branch and PR **only after deliberate authorization and reviewed diff**. No auto-merge or current vehicle instructions.

A dated internal candidate index and test inventory are held separately from these public docs for maintainers performing clearance.
