package de.vw.mib.extstartup.spi;
public interface ExtendedStartupSPI {
  void addBootResumeListener(StartupResumeListener listener);
  boolean isResumeFromSnapshotBoot();
  boolean isSnapshotBoot();
  boolean providesExtendedBootSupport();
  void readyToMakeSnaphot();
  void setSnapshotCorrupted();
}
