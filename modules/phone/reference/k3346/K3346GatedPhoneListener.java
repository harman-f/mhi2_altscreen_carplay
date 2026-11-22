/*
 * K3346 Etap 5.4 - odbierz/rozlacz z karty telefonu VC przy CarPlay.
 *
 * Port luka-dev GatedPhoneListener (wrapper fabrycznego
 * CombiBAPServicePhoneListener). Przy aktywnej bramce K3346GatedPhoneService
 * akcje "Odbierz"/"Odloz" z VC ida do iPhone'a fabryczna droga przycisku
 * sluchawki (K3346CallKeys), a nie do stosu HFP, ktory nie ma rozmowy.
 * Wszystko inne i kazda akcja poza bramka -> stock bez zmian. Java 1.4.
 */
package de.audi.app.combi.bap.app.phone;

import de.audi.atip.interapp.combi.bap.phone.CombiBAPServicePhoneListener;
import de.audi.atip.interapp.combi.bap.phone.data.CombiBAPCallStackEntry;

public class K3346GatedPhoneListener implements CombiBAPServicePhoneListener {
    final CombiBAPServicePhoneListener real;

    private K3346GatedPhoneListener(CombiBAPServicePhoneListener r) {
        this.real = r;
    }

    /** Owija raz; null zostaje null (sluchacz usuniety). */
    public static CombiBAPServicePhoneListener wrap(CombiBAPServicePhoneListener l) {
        if (l == null || l instanceof K3346GatedPhoneListener) return l;
        return new K3346GatedPhoneListener(l);
    }

    public void hangupCall(int i) { if (!K3346GatedPhoneService.onVcAction(K3346GatedPhoneService.ACT_HANGUP)) real.hangupCall(i); }
    public void acceptCall() { if (!K3346GatedPhoneService.onVcAction(K3346GatedPhoneService.ACT_ACCEPT)) real.acceptCall(); }

    /* Etap 6: wybieranie z listy ostatnich przy CarPlay -> iAP2 InitiateCall (hook mm-ipod) */
    public void dialNumber(String s, String s1) { if (!K3346GatedPhoneService.onVcDial(s)) real.dialNumber(s, s1); }
    public void dialNumberFromAdbEntry(String s, String s1, CombiBAPCallStackEntry e) {
        String n = e != null ? e.getTelNumber() : null;
        if (!K3346GatedPhoneService.onVcDial(n != null && n.length() > 0 ? n : s)) real.dialNumberFromAdbEntry(s, s1, e);
    }
    public void dialService(int i) { real.dialService(i); }
    public void confirmEmergencyCall(boolean b) { real.confirmEmergencyCall(b); }
    public void callHold() { real.callHold(); }
    public void resumeCall() { real.resumeCall(); }
    public void setMicMuteState(boolean b) { real.setMicMuteState(b); }
    public void releaseActiveCallAcceptWaitingCall() { real.releaseActiveCallAcceptWaitingCall(); }
    public void swapCalls() { real.swapCalls(); }
    public void callHoldAcceptWaitingCall() { real.callHoldAcceptWaitingCall(); }
    public void releaseAllCallsAcceptWaitingCall() { real.releaseAllCallsAcceptWaitingCall(); }
    public void setWaitingCallOnHold() { real.setWaitingCallOnHold(); }
    public void joinCalls() { real.joinCalls(); }
    public void splitCall(int i) { real.splitCall(i); }
    public void setRingToneMuteState(boolean b) { real.setRingToneMuteState(b); }
    public void setAutomaticRedialActive(boolean b) { real.setAutomaticRedialActive(b); }
    public void resetMissedCallsIndicator() { real.resetMissedCallsIndicator(); }
}
