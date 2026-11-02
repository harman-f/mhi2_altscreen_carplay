#!/usr/bin/env python3
"""Read-only static proof of the original MU1440 DIO GPS send seam.

No patching, process control, device mutation, iAP2 sends or dependencies.
Addresses/hash refer *only* to the pinned original SKG13/P4526 DIO ELF.
A PASS is proof of the static call instruction, NOT of loader/session authority.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

DIO_SHA = "4d6867bdd4c99a032d3c634299f36f88dc72aa54e333589a24af4497a96aee02"
CLIENT_SHA = "c33021b21c5656886e64964efcf806fddb4259027c3c1ed396522e7a44adfdea"
DRIVER_SHA = "7149a3e75b1b19e89021841759f420a6eced456b6c697a3dd1f0e436abea0b8c"
DIO_CALL = 0x1793B8
DIO_PLT = 0x1121E8
DIO_JOB_TAIL = 0x179580
DIO_SENDER = 0x179324


class PreflightError(ValueError):
    pass


def arm_branch_target(word, address, link=None):
    """Decode only an unconditional ARM A32 B/BL instruction."""
    if (word >> 28) != 0xE or (word & 0x0E000000) != 0x0A000000:
        raise PreflightError("EXPECTED_UNCONDITIONAL_ARM_BRANCH")
    if link is not None and bool(word & 0x01000000) != bool(link):
        raise PreflightError("EXPECTED_BRANCH_LINK_MISMATCH")
    offset = word & 0x00FFFFFF
    if offset & 0x800000:
        offset -= 0x1000000
    return (address + 8 + (offset << 2)) & 0xFFFFFFFF


def elf32_load_segments(data, require_executable=False):
    if len(data) < 52 or data[:4] != b"\x7fELF" or data[4:6] != b"\x01\x01":
        raise PreflightError("EXPECTED_ELF32_LITTLE_ENDIAN")
    kind, machine = struct.unpack_from("<HH", data, 16)
    if machine != 40 or (require_executable and kind != 2):
        raise PreflightError("EXPECTED_ARM_ET_EXEC")
    phoff = struct.unpack_from("<I", data, 28)[0]
    entsize, count = struct.unpack_from("<HH", data, 42)
    if entsize < 32 or not count or count > 100 or phoff + entsize * count > len(data):
        raise PreflightError("INVALID_ELF_PROGRAM_HEADERS")
    segments = []
    for i in range(count):
        t, off, va, _pa, fsize, memsize, _flags, _align = struct.unpack_from(
            "<IIIIIIII", data, phoff + entsize * i
        )
        if t == 1:
            if off > len(data) or fsize > len(data) - off or fsize > memsize:
                raise PreflightError("INVALID_LOAD_SEGMENT")
            segments.append((va, va + fsize, off))
    if not segments:
        raise PreflightError("NO_LOAD_SEGMENTS")
    return segments


def read_word_at_va(data, segments, va):
    for start, end, offset in segments:
        if start <= va and va + 4 <= end:
            return struct.unpack_from("<I", data, offset + va - start)[0]
    raise PreflightError("CALLSITE_UNMAPPED")


def sha(path, expected):
    file = Path(path)
    data = file.read_bytes()
    result = hashlib.sha256(data).hexdigest()
    if result != expected:
        raise PreflightError("SHA_MISMATCH:" + file.name + ":actual=" + result)
    return data


def check(dio, client=None, driver=None):
    raw = sha(dio, DIO_SHA)
    segments = elf32_load_segments(raw, True)
    send_insn = read_word_at_va(raw, segments, DIO_CALL)
    job_insn = read_word_at_va(raw, segments, DIO_JOB_TAIL)
    if arm_branch_target(send_insn, DIO_CALL, True) != DIO_PLT:
        raise PreflightError("DIO_VENDOR_CALL_TARGET_CHANGED")
    if arm_branch_target(job_insn, DIO_JOB_TAIL, False) != DIO_SENDER:
        raise PreflightError("DIO_JOB_TAIL_TARGET_CHANGED")
    if client is not None:
        elf32_load_segments(sha(client, CLIENT_SHA))
    if driver is not None:
        elf32_load_segments(sha(driver, DRIVER_SHA))
    return {
        "status": "PINNED_ORIGINAL_DIO_CALLSITE_VERIFIED",
        "dio_sha256": DIO_SHA,
        "vendor_call_va": hex(DIO_CALL),
        "vendor_plt_va": hex(DIO_PLT),
        "onjob_branch_va": hex(DIO_JOB_TAIL),
        "sender_va": hex(DIO_SENDER),
        "client_sha_verified": client is not None,
        "driver_sha_verified": driver is not None,
        "qnx_loader_interposition": "NOT_TESTED_ON_TARGET",
        "real_session_epoch": "NOT_PROVEN",
        "ordered_location_start_stop": "NOT_PROVEN",
        "qualified_speed": "NOT_PROVEN",
        "status_for_install": "BLOCK",
    }


def selftest():
    # A32 immediate branch, positive and negative displacement, and invalid op.
    def op(frm, to, linked):
        delta = to - (frm + 8)
        assert delta % 4 == 0 and -(1 << 25) <= delta < (1 << 25)
        return 0xEA000000 | (0x01000000 if linked else 0) | ((delta >> 2) & 0xFFFFFF)
    assert arm_branch_target(op(DIO_CALL, DIO_PLT, True), DIO_CALL, True) == DIO_PLT
    assert arm_branch_target(op(DIO_JOB_TAIL, DIO_SENDER, False), DIO_JOB_TAIL, False) == DIO_SENDER
    try:
        arm_branch_target(0xE1A00000, DIO_CALL)
    except PreflightError:
        pass
    else:
        raise AssertionError("NON_BRANCH_ACCEPTED")
    print("GPS_DIO_SEAM_DECODE_SELFTEST_PASS")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dio", type=Path)
    ap.add_argument("--client", type=Path)
    ap.add_argument("--driver", type=Path)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    if not args.dio:
        ap.error("--dio is required unless --selftest")
    try:
        print(json.dumps(check(args.dio, args.client, args.driver), indent=2, sort_keys=True))
    except (PreflightError, OSError) as error:
        print(json.dumps({"status": "BLOCK", "reason": str(error)}, sort_keys=True))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
