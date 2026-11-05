"""Host stubs that let tests compile core classes which consult MibrOemProfiles.

The real MibrOemProfile and MibrOemProfiles are compiled unchanged. The generated
MibrProfileBinding is replaced by a binding to a plain test profile whose
listenersClearedOnDeInit() follows -Dmibr.test.reregister=true.
"""
from pathlib import Path

H = Path(__file__).resolve().parents[1] / "java/de/mibr/hmi"

REAL_SOURCES = [H / "MibrOemProfile.java", H / "MibrOemProfiles.java"]

STUBS = {
    "de/mibr/hmi/MibrTileRenderer.java":
        "package de.mibr.hmi; public interface MibrTileRenderer {}",
    "de/mibr/hmi/MibrProfileBinding.java": """package de.mibr.hmi;
final class MibrProfileBinding {
    static MibrOemProfile create() { return new TestProfile(); }
    static final class TestProfile implements MibrOemProfile {
        public String id() { return "test"; }
        public int internalViewId() { return 982; }
        public int[] homeTileGeometry(int w, int h) { return new int[] {0, 0, w, h, w}; }
        public MibrTileRenderer createTileRenderer() { return null; }
        public int nativeDropdownStrategy() { return DROPDOWN_LIVE_OEM_WIDGETS; }
        public int[][] passThroughAnimationTable() {
            return Boolean.getBoolean("mibr.test.passthrough") ? new int[][] {{1, 2, 3}} : null;
        }
        public int imageIndexOffset() { return 0; }
        public boolean listenersClearedOnDeInit() { return Boolean.getBoolean("mibr.test.reregister"); }
    }
}
""",
}
