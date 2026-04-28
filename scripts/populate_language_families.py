#!/usr/bin/env python3
"""
Language Family Population Script for Phase 7 Visualization

Extracts language family information from multiple sources:
1. D-PLACE glottocodes via Glottolog API
2. Geographic region-based classification for unmapped cultures
3. Manual cultural knowledge for known societies

Updates cultures_metadata.json with language_family field.
"""

import json
import csv
import requests
from typing import Dict, Optional, Tuple

# Global language family mappings based on culture names and regions
CULTURAL_LANGUAGE_FAMILIES = {
    # European historical societies
    "Ancient Romans": "Indo-European",
    "Assyrian Empire": "Afro-Asiatic",
    "Kingdom of León": "Indo-European",
    "Vikings": "Indo-European",
    "Ancient Egyptians": "Afro-Asiatic",
    
    # African societies
    "Fon": "Niger-Congo",
    "Ashanti": "Niger-Congo",
    "Yoruba": "Niger-Congo",
    "Zulu": "Niger-Congo",
    "Maasai": "Nilo-Saharan",
    "San": "Khoisan",
    
    # Asian historical societies
    "China (Han Dynasty)": "Sino-Tibetan",
    "Japanese": "Japonic",
    "Korean": "Koreanic",
    "Persian": "Indo-European",
    
    # American societies
    "Aztec": "Oto-Manguean",
    "Inca": "Quechuan",
    "Maya": "Mayan",
    
    # Oceanic
    "Aboriginal Australian": "Australian",
    "Polynesian": "Austronesian",
    "Melanesian": "Austronesian",
}

# Region-based language family defaults
REGION_FAMILIES = {
    "Southern Africa": "Niger-Congo",
    "East Africa": "Nilo-Saharan",
    "West Africa": "Niger-Congo",
    "North Africa": "Afro-Asiatic",
    "Southern Europe": "Indo-European",
    "Northern Europe": "Indo-European",
    "Eastern Europe": "Indo-European",
    "East Asia": "Sino-Tibetan",
    "Southeast Asia": "Austroasiatic",
    "South Asia": "Indo-European",
    "Middle East": "Afro-Asiatic",
    "Oceania": "Austronesian",
    "North America": "Indigenous American",
    "Central America": "Mayan",
    "South America": "Indigenous American",
}

def get_glottolog_family(glottocode: str) -> Optional[str]:
    """
    Query Glottolog API to get language family from glottocode.
    
    Args:
        glottocode: Glottocode string (e.g., "juho1239")
    
    Returns:
        Language family name or None if not found
    """
    if not glottocode or glottocode.strip() == "":
        return None
    
    try:
        # Query Glottolog JSON API
        url = f"https://glottolog.org/api/v3/languoid/{glottocode}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            # Get the top-level family
            if 'family' in data:
                family_name = data['family'].get('name')
                if family_name:
                    return family_name
            
            # Fallback to looking at lineage
            if 'lineage' in data:
                # lineage contains the family hierarchy
                lineage = data['lineage']
                if lineage and len(lineage) > 0:
                    # Last item in lineage is usually the top-level family
                    return lineage[0][0]
        
        return None
    except Exception as e:
        print(f"  ⚠ Error querying Glottolog for {glottocode}: {str(e)}")
        return None

def load_dplace_mapping() -> Dict[str, Dict]:
    """Load D-PLACE societies data for reference."""
    dplace_data = {}
    try:
        with open('data/raw/dplace/societies.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                dplace_data[row['Name'].lower()] = row
    except Exception as e:
        print(f"Warning: Could not load D-PLACE data: {e}")
    
    return dplace_data

def assign_language_family(culture: Dict, dplace_mapping: Dict) -> str:
    """
    Assign language family to a culture using multiple strategies.
    
    Strategy order:
    1. Direct cultural knowledge mapping
    2. D-PLACE glottocode lookup via Glottolog API
    3. Region-based default
    4. Return "unknown"
    """
    name = culture['name']
    
    # Strategy 1: Direct cultural knowledge
    if name in CULTURAL_LANGUAGE_FAMILIES:
        return CULTURAL_LANGUAGE_FAMILIES[name]
    
    # Strategy 2: Try D-PLACE glottocode lookup
    name_lower = name.lower()
    if name_lower in dplace_mapping:
        dplace_row = dplace_mapping[name_lower]
        glottocode = dplace_row.get('Glottocode', '').strip()
        
        if glottocode:
            family = get_glottolog_family(glottocode)
            if family:
                return family
    
    # Strategy 3: Region-based default
    # Try to infer from culture characteristics
    # For historical societies, use geographic region
    if 'lat' in culture and 'lon' in culture:
        lat = culture['lat']
        lon = culture['lon']
        
        # Simple geographic region classification
        if lat < -20:  # Southern Africa/Oceania
            if lon > 100:
                return "Austronesian"
            else:
                return "Niger-Congo"
        elif lat < 0:  # Equatorial Africa/South America
            if lon < -30:  # South America
                return "Indigenous American"
            elif lon < 50:  # Central/West Africa
                return "Niger-Congo"
            else:  # East Africa
                return "Nilo-Saharan"
        elif lat < 20:  # North Africa/Middle East/Central America
            if lon < -60:  # Central America
                return "Mayan"
            elif lon < 50:  # North Africa/Middle East
                return "Afro-Asiatic"
            else:  # Asia
                return "Indo-European"
        elif lat < 50:  # Southern Europe/South Asia
            if lon < 30:  # Europe/North Africa
                return "Indo-European"
            elif lon < 140:  # South/East Asia
                return "Sino-Tibetan"
            else:  # Pacific
                return "Austronesian"
        else:  # Northern regions
            return "Indo-European"
    
    # Fallback
    return "unknown"

def main():
    """Main script execution."""
    print("=" * 70)
    print("Language Family Population Script")
    print("=" * 70)
    
    # Load D-PLACE data
    print("\n1. Loading D-PLACE data...")
    dplace_mapping = load_dplace_mapping()
    print(f"   ✓ Loaded {len(dplace_mapping)} D-PLACE societies")
    
    # Load cultures metadata
    print("\n2. Loading cultures_metadata.json...")
    with open('phase7_visualization/data/cultures_metadata.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cultures = data['cultures']
    print(f"   ✓ Loaded {len(cultures)} cultures")
    
    # Assign language families
    print("\n3. Assigning language families...")
    updated_count = 0
    family_counts = {}
    
    for i, culture in enumerate(cultures):
        if i % 200 == 0:
            print(f"   Processing {i}/{len(cultures)}...")
        
        old_family = culture.get('language_family', 'unknown')
        new_family = assign_language_family(culture, dplace_mapping)
        
        if old_family != new_family or old_family == 'unknown':
            culture['language_family'] = new_family
            updated_count += 1
        
        # Track counts
        family_counts[new_family] = family_counts.get(new_family, 0) + 1
    
    print(f"   ✓ Updated {updated_count} cultures")
    
    # Save updated data
    print("\n4. Saving updated cultures_metadata.json...")
    with open('phase7_visualization/data/cultures_metadata.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("   ✓ Saved successfully")
    
    # Print summary
    print("\n5. Language Family Distribution:")
    print("-" * 70)
    for family, count in sorted(family_counts.items(), key=lambda x: -x[1]):
        pct = (count / len(cultures)) * 100
        print(f"   {family:30s} {count:4d} ({pct:5.1f}%)")
    
    print("\n" + "=" * 70)
    print("✓ Language family population complete!")
    print("=" * 70)

if __name__ == '__main__':
    main()
