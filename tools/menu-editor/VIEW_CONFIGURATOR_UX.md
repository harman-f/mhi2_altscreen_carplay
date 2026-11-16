# View configurator P0.9.9: OEM overlays measured on rectified photos

The three calibration photos (Voll, Wide, Center; calibration clip with 100x50 labelled grid) were rectified into stream-111 pixels with a homography from grid points (residual about 1 stream pixel). Result: the AID10 display shows the whole 1010x376 stream in every view; the views differ only by the OEM chrome on top.

Changes:
- All three cockpit SVGs are now 1:1 with stream pixels: no bezel inset, no side scales (those are outside the display).
- Measured geometry (`AID10_CLUSTER_GEOMETRY_P099.json`, about 3 px): top bar to y 38 (clock tab to y 51), bottom bar from y 335; Voll corners from y 276 (x 160 / 871, sloping to 250 / 782); Wide panel edges 162->231 and 847->777; Center dials r 186 at (182,186) and (822,186).
- Shared top/bottom (compass, clock, temperature, road text, distance, ETA, footer) at the measured positions and sizes.
- Grid patterns now 10 px / 100x50 like the calibration clip.
- Safe Area editor: masks and edge shell from the measured geometry; new display modes "Foto vom Auto (entzerrt)" and "Foto + Maske".
- Cockpit preview: checkbox "Foto vom Auto überlagern" (editor only, not stored in the project).
- The rectified photos are embedded once as JPEG (`AID10_PHOTOS`).

## Online use and working folder (P0.9.10)

- Public copy: `https://harman-f.github.io/mhi2_altscreen_carplay/configurator/` (deployed from the develop tip by `cluster-atlas-pages.yml` on main; `configurator-pages-refresh.yml` re-runs it after each configurator change on develop). Nothing is uploaded: the page runs entirely in the browser.
- The same single HTML file works offline (save the page or download it from the repo and open it locally).
- Chrome/Edge: "Arbeitsordner wählen" picks a local folder once. The project is then written automatically to `<folder>/mibr-project.json` after every change and loaded from there on the next start. The browser keeps the folder handle (IndexedDB); depending on the browser it may ask once per session to allow access again ("Arbeitsordner verbinden").
- Firefox/Safari: no folder access API. The browser backup (localStorage) stays active, "Projekt speichern" downloads `mibr-project.json` (normally into Downloads) and "Projekt laden" imports it again.
- "Auf SD-Karte exportieren" is unchanged (writes `/mibr-menu/mibr-menu.txt` or offers a ZIP).
