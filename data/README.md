# Data

All data was downloaded before the hackathon (17 October – 11 November 2026). Area: Albania.

| Folder | What | Source | Covers |
|---|---|---|---|
| `modis/` | Active fire hotspots, MODIS Collection 6.1 (Terra and Aqua, 1 km) | NASA FIRMS | Nov 2000 – 6 Nov 2026 |
| `viirs_snpp/` | Active fire hotspots, VIIRS S-NPP (375 m) | NASA FIRMS | Jan 2012 – 31 Oct 2026 (end of satellite data) |
| `viirs_noaa20/` | Active fire hotspots, VIIRS NOAA-20 (375 m) | NASA FIRMS | Apr 2018 – 7 Nov 2026 |
| `viirs_noaa21/` | Active fire hotspots, VIIRS NOAA-21 (375 m) | NASA FIRMS | Mar 2023 – 10 Nov 2026 |
| `effis/` | Burnt area perimeters (fires of about 30 ha or more) | EFFIS, European Commission (Copernicus EMS) | 2001 – Nov 2026 |
| `boundaries/` | Albania borders: country (ADM0), counties (ADM1), municipalities (ADM2), units (ADM3) | geoBoundaries | – |

## Notes

- FIRMS files: yearly files (`*_Albania.csv`) and request files (`fire_archive_*` = final data, `fire_nrt_*` = near real-time). Some dates overlap; duplicates are removed in the code.
- Column names differ a little between MODIS and VIIRS files (for example `brightness` and `bright_ti4`).
- EFFIS maps mainly larger fires (about 30 ha or more). Some perimeters are partly based on MODIS data.

## Credits and licences

- **NASA FIRMS** – NASA's Fire Information for Resource Management System. NASA data is open; please credit the source. https://firms.modaps.eosdis.nasa.gov
- **EFFIS** – © European Union. Reuse is allowed if the source is acknowledged. See `effis/effis_readme_and_licence.txt`. https://forest-fire.emergency.copernicus.eu
- **geoBoundaries** – CC BY 4.0. See `boundaries/CITATION-AND-USE-geoBoundaries.txt`. https://www.geoboundaries.org
