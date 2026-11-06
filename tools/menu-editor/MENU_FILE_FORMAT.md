# MIBR menu file

The file the editor saves and the unit loads. `function-catalog.json` lists the function IDs of a build.

- SD card: `/mibr-menu/mibr-menu.txt`. On the unit after loading: `/mnt/app/root/mibr/config/menu/layout.conf`.
- UTF-8, LF line ends, at most 16384 bytes.

```text
MIBR_MENU/1
catalog=1
brand=skoda
name=Free text
viewarea.selected<TAB>root<TAB>-<TAB><TAB>
nav_hints<TAB>root<TAB>-<TAB>Pfeile<TAB>Arrows
nav_source<TAB>nav_hints<TAB>x<TAB><TAB>
page.1<TAB>root<TAB>-<TAB>Neue Ebene<TAB>New level
hint.1<TAB>page.1<TAB>-<TAB>Text<TAB>Text
crc32=1a2b3c4d
```

Header lines in this order: `MIBR_MENU/1`, `catalog=<number>`, `brand=<skoda|vw|seat|audi>`, `name=<text>`.

Entry lines have five tab-separated fields: `id`, `parent`, `flags`, `de`, `en`.

- `id`: a catalog ID, `page.<n>` for a new level, `hint.<n>` for a free note. Characters `A-Za-z0-9_.`.
- `parent`: `root`, or the ID of a page listed earlier in the file. A `fixedpage` takes no children.
- `flags`: `-`, or `x` for expert only. Expert status applies to everything below a page. `menu.load` and `version` must not be expert only, not even through a page above them.
- `de`, `en`: titles, at most 60 characters, no tabs. Empty means the standard title of the catalog ID. `page.<n>` and `hint.<n>` need both.
- The optional line `root<TAB>-<TAB>-<TAB>de<TAB>en` renames the menu itself.
- File order is display order within a parent. IDs must be unique. Depth below root at most 5.
- A catalog ID that is not in the file is unused and does not appear. `menu.load` and `version` must be in the file; the unit adds them if they are missing, and `expert.mode` when the file has expert entries.

Last line: `crc32=<8 lower-case hex digits>`, CRC-32 (IEEE, as in zip) of all bytes before that line, including the LF before it. Nothing may follow it except one LF.

The unit refuses a file with a wrong checksum, wrong magic or broken structure and keeps the stored one. It skips unknown IDs and reports how many. Catalog functions added in a later catalog than the file names are appended under `advanced`.

`standard-menu.txt` is the full menu an installation ships as `config/mibr-menu.conf`. The JAR holds only a basic menu (Version, Erweitert > Menü laden) for a missing or damaged file.
