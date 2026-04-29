#!/usr/bin/env python3
"""
Geocode DRH traditions from their region strings.

Pipeline:
  1. Load drh_entries_metadata.csv (248 entries, 216 distinct regions)
  2. Apply manual overrides for ambiguous/malformed region strings
  3. Geocode remaining unique regions via Nominatim (1 req/sec)
  4. Save lookup table: data/reference/drh_region_coords.csv
  5. Patch data/processed/feature_matrix.parquet with DRH lat/lon
  6. Regenerate phase7_visualization/data/cultures_metadata.json

Usage:
    python scripts/geocode_drh.py
"""

import json
import time
from pathlib import Path

import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Manual overrides — keyed on exact region string from CSV
# None = genuinely unlocatable (global, unknown, nonsensical)
# ---------------------------------------------------------------------------
MANUAL = {
    # Typos / noise
    "Contemporay Mongolia":                         (46.8625, 103.8467),   # Mongolia centroid
    "Vietnam5":                                     (14.0583, 108.2772),   # Vietnam centroid
    "AncientMediterranean":                         (35.0, 18.0),          # Mediterranean centroid
    "Ancient Mediterranean":                        (35.0, 18.0),
    "Managing":                                     None,                  # nonsensical
    "?":                                            None,                  # unknown

    # Global / multi-continental → None (no meaningful point)
    "Worldwide":                                    None,
    "Africa, Europe, North America, South America, Central America, Europe, Middle East, Asia, Australia, New Zealand": None,
    "The United States (primarily the west coast and the midwest) as well as Australia": (37.09, -95.71),  # US centroid
    "Americas, Europe, Asia":                       None,
    "U.S. and Canada":                              (54.0, -100.0),
    "Europe, the Americas, Australasia":            None,
    "Europe, the Americas, and Australia and New Zealand": None,
    "North Atlantic Spiritualism":                  (50.0, -30.0),         # North Atlantic
    "Global Digital Shinto Communities Network":    None,
    "Unitarian Univeralist Organizations":          (42.0, -71.0),         # Boston (UUA HQ)
    "Countries with significant Muscular Christian presence.": None,
    "Krishna West diaspora":                        None,
    "Primarily North America and Japan":            None,
    "Opus Dei (66 Countries)":                      (40.4168, -3.7038),    # Madrid (Opus Dei HQ)
    "Worldwide Wesleyan/Methodist Populations":     None,
    "The Religious Society of Friends (Quakers)":  (51.5074, -0.1278),    # London (Quaker origins)
    "Locations of the New Prophecy":               (38.7, 29.5),          # Phrygia, Turkey (origin)
    "Origins of Christian Science":                (42.35, -71.06),        # Boston
    "Curious Pastimes LARP sites":                 None,
    "Krishna West":                                (18.5204, 73.8567),    # Pune (ISKCON)

    # Historical regions / polities needing canonical centroid
    "Roman Empire (Greatest Extent)":              (41.9028, 12.4964),    # Rome
    "Eastern Roman Empire (300-600)":              (41.0082, 28.9784),    # Constantinople
    "Latin Empire":                                (41.0082, 28.9784),    # Constantinople
    "Gaul":                                        (46.6034, 1.8883),     # France centroid
    "Phoenicia":                                   (33.8547, 35.8623),    # Beirut area
    "Levant":                                      (33.0, 36.0),
    "Ancient Judah":                               (31.5, 35.0),
    "Edom":                                        (30.5, 35.5),          # Southern Jordan
    "Mittani Empire":                              (36.5, 40.0),          # Northern Syria/Iraq
    "Ur III core region":                          (30.96, 46.10),        # Ur, Iraq
    "Cities integrated in the Assyrian empire":    (36.36, 43.16),        # Nineveh
    "Emar":                                        (36.26, 38.07),        # Meskene, Syria
    "Ur III core region":                          (30.96, 46.10),
    "Kingdom of Nabataea":                         (30.32, 35.44),        # Petra
    "Deir el-Medina":                              (25.73, 32.60),        # Egypt
    "Nubia":                                       (20.0, 30.5),
    "Roman Palestine":                             (31.5, 35.0),
    "AncientMediterranean":                        (35.0, 18.0),
    "Inner NW Syria":                              (36.2, 37.5),
    "al-Andalus and Baghdad":                      (37.0, -4.0),          # Andalusia centroid
    "MENA + Andalusia":                            (27.0, 30.0),          # MENA centroid
    "Alexandria and the Nile, Rome, Antioch and environs, etc.": (30.0, 31.0),  # Alexandria
    "Sanctuaries and Cult Sites of \"Maritime Hera\"": (37.5, 22.0),     # Peloponnese
    "Greece, Magna Graecia":                       (39.0, 22.0),
    "Southern Italy and Greece":                   (39.0, 16.0),
    "Sparta and surrounding territory ('chora')":  (37.07, 22.43),
    "Known Theurgic Neoplatonic Schools":          (36.5, 30.0),          # Eastern Mediterranean
    "Major Yogācāra-driven monasteries during the early Tang period": (34.0, 108.0),  # Chang'an

    # Administrative quirks
    "Great Britain_Political Territory_DRH":       (54.0, -2.0),          # Great Britain centroid
    "Great Britain_Political Territory":           (54.0, -2.0),
    "British Isles: England":                      (52.5, -1.5),
    "British Isles and NW Europe":                 (52.0, 0.0),
    "Northern Britain / Scotland":                 (57.0, -4.0),
    "Iron Age Ireland":                            (53.0, -8.0),
    "Leinster and East Munster":                   (52.5, -7.0),
    "Brittany":                                    (48.0, -3.0),
    "The Russian Empire (2)":                      (55.75, 37.62),        # Moscow
    "Mongolian-speaking region (East and North)":  (47.0, 103.0),
    "Western Zhou (based on Li Feng)":             (34.0, 108.0),
    "Tang China":                                  (34.0, 108.0),
    "Ming and Qing China (combined area)":         (35.0, 105.0),
    "Northern Song Dynasty":                       (34.8, 113.6),         # Kaifeng
    "Southern and Northern Dynasties 440 CE":      (32.0, 118.0),
    "Northern Wei and the Liu-Song":               (40.0, 113.0),
    "Territory of the Taiping Movement":           (23.0, 113.0),         # Guangdong
    "The extent of Dingxiang Wang temples at the end of the Qing": (35.0, 105.0),
    "Luo River, Yellow River Valley, Henan Province": (34.8, 113.6),
    "Erlitou Yanshi,Henan":                        (34.67, 112.95),
    "Zhejiang; Shanxi":                            (29.5, 120.0),
    "Jiangnan Area":                               (31.0, 120.0),
    "Sichuan and surrounding areas":               (30.5, 103.5),
    "Poyang Lake Area":                            (28.8, 116.3),
    "Chang'an, Jiankang, and Sichuan":             (34.3, 108.9),
    "Mount Lu":                                    (29.57, 115.98),
    "Lake Biwa area, Kyōto and Mt Hiei":           (35.0, 135.9),
    "Saru Basin, Hokkaido, Japan":                 (42.5, 142.3),
    "Japanese Empire and Occupied Areas":          (36.2, 138.0),         # Japan centroid
    "Yiguan Dao in Taiwan":                        (23.7, 121.0),
    "Tibet (Tufan) - 669 CE":                      (29.65, 91.17),        # Lhasa
    "Tibet and the Himalayas":                     (29.65, 91.17),
    "Gaddis of the Western Himalayas -- Modern Period": (32.0, 76.5),
    "Greater Kathmandu Valley":                    (27.72, 85.32),
    "Nepal and parts of North India":              (28.0, 83.0),
    "Haryana, Rajasthan, and Eastern Uttar Pradesh, North India": (27.0, 76.0),
    "North India (Rājasthān and Bihār)":           (25.0, 77.0),
    "Ranchi, Jharkhand":                           (23.34, 85.31),
    "Nilgiri Hills, western Tamil Nadu state, India": (11.4, 76.7),
    "Important centers of Ganapatya worship":      (18.5, 74.0),          # Maharashtra
    "Parsis in India":                             (23.0, 72.6),          # Gujarat
    "Mandar River Valley & Polewali":              (-3.35, 119.2),        # Sulawesi
    "Jahai subtribe of northeastern Perak and northwestern Kelantan, Malaysia": (5.5, 101.5),
    "Sarawak, Borneo Island":                      (1.55, 110.36),
    "North Sumatra":                               (3.0, 98.0),
    "Mainland Southeast Asia and China":           (20.0, 103.0),
    "Northwestern Laos":                           (20.5, 102.0),
    "Phú Hòa Đông, Củ Chi, Hồ Chí Minh City":     (10.85, 106.48),
    "Cham H'roi":                                  (13.5, 108.5),         # Central Highlands Vietnam
    "Peripheral Coastal Lowlands":                 (10.0, 107.0),         # S Vietnam coast
    "Tawi-Tawi and adjacent islands":              (5.2, 120.0),          # Philippines
    "Pacific Ocean":                               (0.0, -160.0),         # Central Pacific
    "Nuku Hiva Island, French Polynesia":          (-8.92, -140.1),
    "Island of Tikopia":                           (-12.3, 168.83),
    "Ambunti Sub-Province, Sepik River region, Papua New Guinea": (-4.2, 142.8),
    "Hoskins Peninsula, New Britain.":             (-5.5, 150.3),
    "Bougainville Island":                         (-6.2, 155.3),
    "Melville Island":                             (-11.6, 131.0),        # Australia
    "South-Central Andes":                         (-20.0, -67.0),
    "North Coast of Peru":                         (-8.0, -79.0),
    "Chuchito, Peru":                              (-15.9, -69.8),
    "Jivaro of Ecuador and Peru":                  (-3.0, -77.0),
    "Central Andes":                               (-13.5, -72.0),
    "Tierra del Fuego, Chile":                     (-54.0, -69.0),
    "Rio Cayapas drainage":                        (1.0, -78.8),          # Ecuador
    "Guajira Peninsula":                           (11.7, -72.5),
    "Aztec Imperial Core":                         (19.4, -99.1),         # Mexico City
    "Mexico City, and Aldea de los Reyes in Amecameca (State of Mexico)": (19.2, -98.8),
    "Gulf Coast of Mexico, Southeast Mexico":      (19.0, -96.0),
    "Chiapas":                                     (16.75, -93.1),
    "Town of Chichicastenango":                    (15.12, -91.11),        # Guatemala
    "Huichol Territory, Nayarit and Jalisco, Mexico": (22.0, -104.0),
    "Historic Mescalero Apache Territory":         (33.0, -105.5),        # New Mexico
    "Comanche-occupied southern Great Plains ca. 1870": (34.5, -101.0),
    "Skidi Band Territory":                        (42.0, -99.5),         # Nebraska
    "Fort Belknap Reservation and Gros Ventre lands": (48.3, -108.6),    # Montana
    "Natchez Territory ca. 1718":                  (31.56, -91.4),        # Mississippi
    "Upper division of Alabama":                   (33.5, -86.8),
    "Seneca Reservations (1797)":                  (42.8, -78.7),         # New York
    "New Jersey, New York, Pennsylvania":          (41.0, -75.0),
    "Twana (Southern Coast Salish) Territory ca. 1860": (47.5, -123.0),  # Washington State
    "Havasupai Reservation, 1918":                 (36.2, -112.5),        # Grand Canyon area
    "Hidatsa territory":                           (47.5, -101.5),        # North Dakota
    "Lakota Sioux Reservations as of 1890":        (43.5, -101.0),        # South Dakota
    "Copper River Delta":                          (60.3, -144.8),        # Alaska
    "New France, Atlantic and St. Lawrence Region": (46.5, -72.0),       # Quebec
    "Nunatsiavut and Labrador":                    (56.0, -63.0),
    "Huronia":                                     (44.8, -79.5),         # Ontario
    "Mundurucu Territory ca. 1850":                (-7.0, -56.5),         # Para, Brazil
    "Trumai village of Vanivani, central Mato Grosso State, Brazil": (-12.0, -54.0),
    "Duque de Caxias Reservation, state of Santa Catarina, Brazil ca. 1932": (-26.5, -51.0),
    "Piauí":                                       (-7.7, -43.0),
    "Mirebalais, Haiti":                           (18.83, -72.0),
    "Nation of Islam in American Cities":          (41.85, -87.65),       # Chicago
    "North Atlantic Spiritualism":                 (50.0, -30.0),
    "Reindeer division of the Chukchee, Northeastern Russia": (67.0, 175.0),
    "Upper Liard River":                           (60.0, -129.0),        # Yukon
    "Sápmi (The Sámi Land)":                       (68.0, 25.0),
    "Prehistoric Europe and Southwest Asia":       (45.0, 30.0),          # midpoint
    "Rome":                                        (41.9028, 12.4964),
    "Ile-Ife":                                     (7.47, 4.56),          # Nigeria
    "Oyo":                                         (7.85, 3.93),          # Nigeria
    "Ibadan, Oyo State, Nigeria":                  (7.38, 3.90),
    "Ayetoro, Ilajeland, Ondo State, Southwest Nigeria": (6.66, 4.88),
    "Ori-Oke Iwamimo, Ilaje local government area of Ondo State, Nigeria": (6.55, 5.0),
    "Lagos South-West, Nigeria":                   (6.45, 3.39),
    "Umuahia, Abia State, Southeastern Nigeria":   (5.53, 7.49),
    "Igboland, South East, Nigeria":               (6.0, 7.5),
    "Southeastern Nigeria":                        (5.5, 7.5),
    "Southeast Nigeria":                           (5.5, 7.5),
    "Tiv settlements of Benue province":           (7.5, 9.0),
    "Osun":                                        (7.76, 4.56),          # Osun State
    "Hausaland":                                   (12.0, 8.0),
    "Nigeria, West Africa":                        (9.0, 8.0),            # Nigeria centroid
    "Coastal West Africa":                         (5.0, 0.0),
    "Volta River basin of Northern Ghana":         (10.0, -1.0),
    "Kumasi, Ashanti Region, Ghana, ca. 1895":     (6.69, -1.62),
    "Sub Saharan Africa":                          (0.0, 20.0),
    "Senegal, West Africa":                        (14.5, -14.5),
    "Vicinity of the town of Bo, Sierra Leone":    (7.96, -11.74),
    "Shilluk lands, ca. 1910":                     (10.0, 32.0),          # South Sudan
    "Town and environs of Pare":                   (-4.0, 37.8),          # Tanzania
    "Uluguru Mountains ca. 1925":                  (-7.0, 37.7),          # Tanzania
    "Tsonga lands, Ronga group ca. 1895":          (-25.0, 33.0),         # Mozambique
    "Moria, Limpopo, South Africa":                (-23.9, 29.8),
    "Southern Africa":                             (-30.0, 26.0),
    "Zimbabwe":                                    (-20.0, 30.0),
    "Northern Coastal Plain of Lake Malawi":       (-10.5, 34.3),
    "Nyae Nyae region, Namibia":                   (-19.7, 20.5),
    "Kingdom of Kongo map":                        (-5.0, 15.0),
    "Central Africa/Congo-Brazzaville/Region of Pool": (-4.3, 15.3),
    "North Africa":                                (27.0, 17.0),
    "Ethiopia":                                    (9.0, 40.0),
    "Gaza.":                                       (31.5, 34.47),
    "israel":                                      (31.5, 34.75),
    "Peregrine_Tshitolian":                        (-4.0, 23.0),          # DRC (Tshitolian culture)
    "South-west Asia":                             (32.0, 44.0),
    "Ancestral Caddo Territory":                   (32.0, -94.5),
    "Piauí":                                       (-7.7, -43.0),
    "Emar":                                        (36.26, 38.07),
}


def geocode_region(geolocator: Nominatim, region: str) -> tuple[float, float] | None:
    """Query Nominatim for a region string; return (lat, lon) or None."""
    try:
        loc = geolocator.geocode(region, timeout=10)
        if loc:
            return (round(loc.latitude, 4), round(loc.longitude, 4))
        return None
    except (GeocoderTimedOut, GeocoderServiceError):
        return None


def main() -> None:
    meta_path = ROOT / "data/raw/drh/drh_entries_metadata.csv"
    feature_matrix_path = ROOT / "data/processed/feature_matrix.parquet"
    ref_out = ROOT / "data/reference/drh_region_coords.csv"
    cultures_json = ROOT / "phase7_visualization/data/cultures_metadata.json"

    df = pd.read_csv(meta_path)
    print(f"Loaded {len(df)} DRH entries, {df['region'].nunique()} distinct regions")

    geolocator = Nominatim(user_agent="shs2-drh-geocoder/1.0")

    # Build region → (lat, lon) lookup
    lookup: dict[str, tuple[float, float] | None] = {}

    distinct_regions = df["region"].unique()
    print(f"\nGeocoding {len(distinct_regions)} unique regions…")

    for i, region in enumerate(distinct_regions):
        if region in MANUAL:
            lookup[region] = MANUAL[region]
            status = "manual"
        else:
            coords = geocode_region(geolocator, region)
            lookup[region] = coords
            status = "geocoded" if coords else "FAILED"
            time.sleep(1.1)  # Nominatim rate limit: 1 req/sec

        lat, lon = lookup[region] if lookup[region] else (None, None)
        print(f"  [{i+1:3d}/{len(distinct_regions)}] {status:8s} | {region[:60]:<60} → {lat}, {lon}")

    # Save reference lookup
    ref_out.parent.mkdir(parents=True, exist_ok=True)
    ref_rows = [{"region": r, "lat": v[0] if v else None, "lon": v[1] if v else None}
                for r, v in lookup.items()]
    pd.DataFrame(ref_rows).to_csv(ref_out, index=False)
    print(f"\nSaved region lookup → {ref_out}")

    # Patch drh_entries_metadata.csv
    df["lat"] = df["region"].map(lambda r: lookup.get(r, (None, None))[0] if lookup.get(r) else None)
    df["lon"] = df["region"].map(lambda r: lookup.get(r, (None, None))[1] if lookup.get(r) else None)
    df.to_csv(meta_path, index=False)
    print(f"Patched {meta_path.name}: "
          f"{df['lat'].notna().sum()}/{len(df)} entries now have coordinates")

    # Patch feature_matrix.parquet
    fm = pd.read_parquet(feature_matrix_path)
    print(f"\nFeature matrix: {len(fm)} rows; DRH rows: {(fm['source'] == 'drh').sum()}")

    # Build drh_id → (lat, lon) from metadata (using int_id as key matching DRH_N)
    id_to_coords: dict[str, tuple[float, float] | None] = {}
    for _, row in df.iterrows():
        # culture_id in feature_matrix is "DRH_{index}" — we match by name
        pass  # We'll merge on culture_name

    # culture_name in feature_matrix matches name in metadata
    # Build coord_map handling duplicate names — keep first non-null lat/lon per name
    coord_map: dict[str, dict] = {}
    for _, row in df.iterrows():
        name = row["name"]
        if name not in coord_map or (coord_map[name]["lat"] is None and pd.notna(row["lat"])):
            coord_map[name] = {"lat": row["lat"] if pd.notna(row["lat"]) else None,
                               "lon": row["lon"] if pd.notna(row["lon"]) else None}

    drh_mask = fm["source"] == "drh"
    updated = 0
    for idx in fm[drh_mask].index:
        name = fm.at[idx, "culture_name"]
        if name in coord_map:
            fm.at[idx, "lat"] = coord_map[name]["lat"]
            fm.at[idx, "lon"] = coord_map[name]["lon"]
            updated += 1

    fm.to_parquet(feature_matrix_path, index=False)
    drh_with_coords = fm[drh_mask]["lat"].notna().sum()
    print(f"Patched feature_matrix.parquet: {drh_with_coords}/{drh_mask.sum()} DRH rows now have lat/lon")

    # Patch cultures_metadata.json
    with open(cultures_json) as f:
        viz = json.load(f)
    cultures = viz["cultures"]

    patched_viz = 0
    for c in cultures:
        if c.get("source") == "drh" and c.get("lat") is None:
            name = c.get("name", "")
            if name in coord_map:
                lat = coord_map[name]["lat"]
                lon = coord_map[name]["lon"]
                if lat is not None:
                    c["lat"] = lat
                    c["lon"] = lon
                    patched_viz += 1

    with open(cultures_json, "w") as f:
        json.dump(viz, f, separators=(",", ":"))
    print(f"Patched cultures_metadata.json: {patched_viz} DRH entries now have lat/lon")

    # Summary
    total = len(distinct_regions)
    resolved = sum(1 for v in lookup.values() if v is not None)
    print(f"\n--- Summary ---")
    print(f"Regions geocoded:  {resolved}/{total} ({100*resolved/total:.1f}%)")
    print(f"Regions unresolved (will remain NaN): {total - resolved}")
    unresolved = [r for r, v in lookup.items() if v is None]
    if unresolved:
        print("Unresolved regions:")
        for r in unresolved:
            print(f"  - {r}")


if __name__ == "__main__":
    main()
