package de.mibr.hmi;

/**
 * Holder for the profile bound into this build. One JAR is built per profile,
 * so selection is compile-time: the generated MibrProfileBinding names the
 * adapter class.
 */
public final class MibrOemProfiles {
    private static MibrOemProfile current;

    private MibrOemProfiles() { }

    public static synchronized MibrOemProfile current() {
        if (current == null) current = MibrProfileBinding.create();
        return current;
    }
}
