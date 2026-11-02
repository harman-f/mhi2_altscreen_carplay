package de.mibr.hmi;

/**
 * Expert mode: entries marked expert only appear while it is on. "Until restart" lives here in RAM; "permanent" is the
 * broker switch expert_mode.
 */
final class MibrExpert {
    private MibrExpert(){}
    private static boolean session;

    private static boolean permanent(){
        MibrDurableSwitch sw=MibrDurableSwitch.EXPERT_MODE;
        return "on".equals(sw.revision()!=null?sw.value():sw.persistedValue());
    }
    static synchronized boolean on(){return session||permanent();}
    /** Dropdown value: off, session, on. */
    static synchronized String choice(){return permanent()?"on":session?"session":"off";}
    static synchronized void session(boolean value){session=value;}
}
