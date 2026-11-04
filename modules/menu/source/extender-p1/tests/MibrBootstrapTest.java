import de.mibr.extender.MibrStartupHook;
public final class MibrBootstrapTest {
    public static void main(String[] args) {
        MibrStartupHook hook = new MibrStartupHook();
        new MibrStartupHook();
        check(!hook.providesExtendedBootSupport(), "unexpected boot support");
        check(!hook.isResumeFromSnapshotBoot(), "unexpected resume");
        check(!hook.isSnapshotBoot(), "unexpected snapshot");
        check(!hook.isSnapshotBoot(), "unexpected repeat snapshot");
        hook.addBootResumeListener(null);
        hook.readyToMakeSnaphot();
        hook.setSnapshotCorrupted();
        System.out.println("P1_HOST_TEST_PASS");
    }
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
