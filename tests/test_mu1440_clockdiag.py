#!/usr/bin/env python3
"""Clock diagnostic host gate: real native C self-test and unchanged TS contract."""
from pathlib import Path
import re
import subprocess
import sys

writer = Path("src/native/direct-ts-parity/direct_ts_parity.c").read_text()
binary = sys.argv[1]
res = subprocess.run([binary, "--self-test"], capture_output=True, text=True, timeout=8)
assert res.returncode == 0, (res.returncode, res.stderr, res.stdout)
assert "PARITY_SELFTEST=PASS" in res.stdout
for needle in (
    "#define TRANSPORT_BPS 12288000u",
    "#define TRANSPORT_TICKS_NUM 705u",
    "#define PCR_INTERVAL_PACKETS 327u",
    "#define MOST_BLOCK_PACKETS 64u",
    "c->transport_pcr90k = TRANSPORT_PCR_BASE +",
    "if((blocks_now & 127u)==0u)publish_status_throttled",
    "publish_status_throttled(&stats,&clock,&queue,\"running\");",
    "publish_status(&stats,&clock,&queue,rc==0?",
    "diag_note_au(&stats,monotonic_us()",
    "diag_clock_accepted_model_ppm=",
    "diag_last_arrival_age_us=",
    "diag_source_rewinds=",
    "diag_input_fps_x100=",
    "now-g_status_last_us>=1000000ull",
    "state!=g_status_last_state",
):
    assert needle in writer, needle
assert writer.count("diag_note_au(&stats,monotonic_us()") == 1
assert "0x4ccccccdu,364001u" in writer, "C self-test must validate 1s no-frame gap"
assert "diag_source_rewinds!=1u" in writer
assert "dt.diag_gap50!=3u" in writer
assert "dt.diag_gap100!=2u" in writer
assert "dt.diag_gap250!=1u" in writer
assert "status_publish_allowed(1500000ull,1)" in writer

for name in ("MU1440_CLOCKDIAG_SWAP.sh", "MU1440_CLOCKDIAG_LIVE.sh",
             "MU1440_CLOCKDIAG_FIXTURE.sh"):
    path = Path("deployment/mu1440-fixture-replay-v1") / name
    out = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
    assert out.returncode == 0, (path, out.stderr)
# bash -n accepts 'hash(){}', but the original QNX /bin/ksh rejects that
# built-in name with 'syntax error: (' unexpected'. Guard actual on-car parse.
for name in ("MU1440_CLOCKDIAG_SWAP.sh", "MU1440_CLOCKDIAG_LIVE.sh",
             "MU1440_CLOCKDIAG_FIXTURE.sh"):
    qnx_script = (Path("deployment/mu1440-fixture-replay-v1") / name).read_text()
    assert not re.search(r"(?m)^hash\s*\(\)\s*\{", qnx_script), name
    assert not re.search(r"\$\(hash\s", qnx_script), name
    assert "hashfile(){" in qnx_script, name

swap = Path("deployment/mu1440-fixture-replay-v1/MU1440_CLOCKDIAG_SWAP.sh").read_text()
for needle in ("__NEW_BRIDGE_HASH__", "__NEW_OWNER_HASH__", "CI295_B=", "CI305_B=",
               "CLOCKDIAG_SWAP=AUTORESTORE_PASS", "checkidle", "ORIGINAL"):
    if needle == "ORIGINAL":
        assert 'original.sha256' in swap
    else:
        assert needle in swap, needle
live = Path("deployment/mu1440-fixture-replay-v1/MU1440_CLOCKDIAG_LIVE.sh").read_text()
assert "parity_session.sh\" 150" in live
assert "status-snapshots.log" in live
assert "exec \"$OWNER\" --stop" in live
# Correlated but low-overhead source-side evidence: no GEN2 binary change.
# The vehicle sampler reads the existing 1Hz GEN2 status alongside the writer
# every 3s and only removes markers created for this particular run.
for needle in (
    "SOURCE_TIMING_ENABLE=/tmp/mibr-alt111-source-timing.enabled",
    "SOURCE_TIMING_INTERVAL=/tmp/mibr-alt111-source-timing-interval-ms",
    "SOURCE_TIMING_STATUS=/tmp/mibr-alt111-source-timing.status",
    "GEN2_STATUS=/tmp/mibr-alt111-gen2.status",
    "TIMING_ENABLE_OWNED=0",
    "TIMING_INTERVAL_OWNED=0",
    "echo '--- stream111 ---'",
    "echo '--- gen2-source-timing ---'",
    "echo '--- gen2 ---'",
    "echo '--- parity ---'",
    'if [ ! -e "$SOURCE_TIMING_INTERVAL" ]; then',
    'if [ ! -e "$SOURCE_TIMING_ENABLE" ]; then',
    'if [ "$TIMING_ENABLE_OWNED" -eq 1 ]; then',
    'if [ "$TIMING_INTERVAL_OWNED" -eq 1 ]; then',
    'source_timing_capture=present',
    'source_timing_capture=missing',
    'gen2-source-final.status',
    'gen2-final.status',
):
    assert needle in live, needle
# Preflight must remain read-only: no temporary marker creation until after
# pair/source/gate checks, the start-mode early exit, and SD log preparation.
assert live.index('echo CLOCKDIAG_LIVE=PREFLIGHT_PASS') < live.index('TIMING_ENABLE_OWNED=1')
assert live.index('[ "$MODE" = start ] || exit 0') < live.index('TIMING_ENABLE_OWNED=1')
assert live.index('TIMING_ENABLE_OWNED=1') < live.index('MARK=$RUN/.recording')
assert live.index('echo \'--- gen2-source-timing ---\'') < live.index('echo \'--- parity ---\'')
assert live.index('if [ "$TIMING_ENABLE_OWNED" -eq 1 ]; then') < live.index('mount -ur "$SD"')
assert live.count('snapshot "$2" "$N"') == 1
print("MU1440_CLOCKDIAG_HOST=PASS 1Hz status, variable fps gaps, matched swap and no PCR mutation")

# Experimental EAGAIN readiness wakeups: default unchanged and fail-safe fallback.
for needle in (
    '#include <poll.h>', 'MIBR_PARITY_EAGAIN_WAIT',
    '!strcmp(opt,"poll")', 'g_poll_wait_enabled=!fixture_mode',
    'poll_wait_should_disable(', 'writer_poll_fallbacks=',
    'writer_poll_disabled=', 'wait_state->poll_ready_pending',
    'wait_state->false_ready>=3u', 'wait_state->disabled=1',
    'WRITE_TIMEOUT_US 500000u', 'usleep(1000);',
):
    assert needle in writer, needle
assert writer.count('poll(&pfd,1,timeout_ms)') == 1
for name in ("MU1440_CLOCKDIAG_SWAP.sh", "MU1440_CLOCKDIAG_LIVE.sh", "MU1440_CLOCKDIAG_FIXTURE.sh"):
    assert "MIBR_PARITY_EAGAIN_WAIT" not in (
        Path("deployment/mu1440-fixture-replay-v1") / name
    ).read_text()
print("MU1440_POLL_PROTO_HOST=PASS C selftest plus disabled-by-default policy")

# Idealized discrete-event test: readiness-capable vs unsupported poll.
# This is a policy model, not physical isoTX2 validation.
def replay_poll_policy(mode, notify, blocks=1000, service_us=7833):
    now = 0
    fallback = False
    for block in range(blocks):
        ready = block * service_us
        while now < ready:
            if mode == "poll" and not fallback:
                if notify:
                    now = ready
                else:
                    fallback = True
            else:
                now += 2000  # observed effective QNX 1ms usleep
    return now, fallback

legacy, _ = replay_poll_policy("legacy", False)
ideal, ideal_fallback = replay_poll_policy("poll", True)
unsupported, fallback = replay_poll_policy("poll", False)
assert ideal <= legacy
assert not ideal_fallback
assert fallback
assert unsupported <= legacy + 2000
print("MU1440_POLL_SIMULATION=PASS coarse-timer model; no hardware claim")

# Independent experimental SD package must never reuse clockdiag-v1 backup.
poll_dir = Path("deployment/mu1440-fixture-replay-v1")
poll_swap = (poll_dir / "MU1440_POLL_SWAP.sh").read_text()
poll_live = (poll_dir / "MU1440_POLL_LIVE.sh").read_text()
poll_fixture = (poll_dir / "MU1440_POLL_FIXTURE.sh").read_text()
for script in ("MU1440_POLL_SWAP.sh","MU1440_POLL_LIVE.sh","MU1440_POLL_FIXTURE.sh"):
    sh = poll_dir / script
    assert subprocess.run(["bash","-n",str(sh)],capture_output=True).returncode == 0
    assert "hash(){" not in sh.read_text()
    assert "/omonob-clock-test/pollwait-v1" in sh.read_text()
    assert "clockdiag-v1" not in sh.read_text()
assert "mibr-pollwait-v1-backup" in poll_swap
assert "mibr-clockdiag-v1-backup" not in poll_swap
assert "CI314_B=74c39c205bdab2f5e894cf35e644bf7d9fe9c9b46dc71a27e26bb5c2b237f3e2" in poll_swap
assert "CI314_O=c513ca1f7fb52df2d6ebb4e65b7bddc7b0aa3c1e455a2d1d614c63972794e370" in poll_swap
assert 'fail current_pair_not_qualified' in poll_swap
assert 'fail gate_not_stock' in poll_swap
assert 'fail owner_lock' in poll_swap
assert 'fail parity_running' in poll_swap
assert 'MIBR_PARITY_EAGAIN_WAIT' in poll_live
assert 'requested_eagain_wait=' in poll_live
assert 'MIBR_PARITY_EAGAIN_WAIT' not in poll_fixture
assert "owner_rc=" in poll_live
assert (poll_dir/"POLLWAIT_README.md").is_file()
print("MU1440_POLL_PAIRING=PASS separate CI314-aware swap, exact rollback, no autostart")
