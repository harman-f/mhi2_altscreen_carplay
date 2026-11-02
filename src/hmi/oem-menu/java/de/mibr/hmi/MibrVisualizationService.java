package de.mibr.hmi;

import de.vw.mib.cio.CioIntentVisualizationImpl;
import de.vw.mib.cio.framework.CioIdService;
import de.vw.mib.cio.framework.CioIntentVisualization;
import de.vw.mib.cio.framework.CioVisualizationService;

/** Reuses a live stock grid tile's visuals and substitutes ONLY our own title. */
public final class MibrVisualizationService implements CioVisualizationService {
    private final CioVisualizationService stock;
    private long fallback;
    public MibrVisualizationService(CioVisualizationService stock) {
        this.stock = stock;
    }
    public void load(CioIdService ids) { stock.load(ids); }
    public void loadDone() { stock.loadDone(); }
    public CioIntentVisualization getStockVisualization(long id) {
        return stock.getVisualization(id);
    }
    public void setFallback(long id) { fallback = id; }
    public CioIntentVisualization getVisualization(long id) {
        if (id != MibrHomeCio.visualizationId()) {
            return stock.getVisualization(id);
        }
        try {
            MibrHomeCio.stage("HOME_TILE_VIS_REQUESTED");
            CioIntentVisualization donor = stock.getVisualization(fallback);
            if (donor == null) {
                MibrHomeCio.stage("FAIL_TILE_VIS_FALLBACK");
                return stock.getVisualization(0L);
            }
            MibrHomeCio.stage("HOME_TILE_VIS_RETURNED");
            return new CioIntentVisualizationImpl(donor.getContextColors(),
                donor.getIcons(), donor.getIconColors(), donor.getIconGlowColors(),
                "CarPlay-Einstellungen", donor.getTextColors(), donor.getTextGlowColors());
        } catch (Throwable ignored) {
            MibrHomeCio.stage("FAIL_TILE_VIS_FALLBACK");
            try { return stock.getVisualization(fallback); }
            catch (Throwable ignoredAgain) {
                try { return stock.getVisualization(0L); }
                catch (Throwable ignoredLast) { return null; }
            }
        }
    }
}
