#!/usr/bin/env python
"""Phase 1 Data Ingestion & Coverage Analysis Script"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

# Styling
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (14, 6)
plt.rcParams['font.size'] = 10

print("=" * 70)
print("PHASE 1: DATA INGESTION & COVERAGE ANALYSIS")
print("=" * 70)

# Import parsers
from src.ingest.dplace import parse_dplace
from src.ingest.seshat import parse_seshat
from src.ingest.drh import parse_drh

# Load data
print("\nLoading data sources...")
dplace_df = parse_dplace(
    societies_path=Path("data/raw/dplace/societies.csv"),
    variables_path=Path("data/raw/dplace/variables.csv"),
    data_path=Path("data/raw/dplace/data.csv"),
)
print(f"  ✓ D-PLACE: {len(dplace_df):,} records")

seshat_df = parse_seshat()
print(f"  ✓ Seshat: {len(seshat_df):,} records (mock fallback)")

drh_df = parse_drh(source_path=Path("data/raw/drh/drh_sample.csv"))
print(f"  ✓ DRH: {len(drh_df):,} records")

# Combine
combined_df = pd.concat([dplace_df, seshat_df, drh_df], ignore_index=True)
print(f"\n✓ COMBINED: {len(combined_df):,} total records")

# ==========================
# Overall Statistics
# ==========================
print("\n" + "=" * 70)
print("OVERALL STATISTICS")
print("=" * 70)

print(f"\nTotal Records: {len(combined_df):,}")
print(f"Unique Cultures: {combined_df['culture_id'].nunique():,}")
print(f"Unique Variables: {combined_df['variable_name'].nunique()}")

print(f"\nSources:")
for source in combined_df['source'].unique():
    count = len(combined_df[combined_df['source'] == source])
    cultures = combined_df[combined_df['source'] == source]['culture_id'].nunique()
    print(f"  {source.upper():10} {count:6,} records  {cultures:4,} cultures")

# ==========================
# Geographic Coverage
# ==========================
print("\n" + "=" * 70)
print("GEOGRAPHIC COVERAGE")
print("=" * 70)

gdf = combined_df[combined_df['lat'].notna() & combined_df['lon'].notna()]
print(f"\nRecords with coordinates: {len(gdf):,} / {len(combined_df):,} ({100*len(gdf)/len(combined_df):.1f}%)")
print(f"Latitude range: {gdf['lat'].min():.1f}° to {gdf['lat'].max():.1f}°")
print(f"Longitude range: {gdf['lon'].min():.1f}° to {gdf['lon'].max():.1f}°")

# ==========================
# Geographic Visualization
# ==========================
print("\nGenerating geographic visualizations...")
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

for idx, source in enumerate(['dplace', 'seshat', 'drh']):
    source_gdf = gdf[gdf['source'] == source]
    if len(source_gdf) > 0:
        ax = axes[idx]
        scatter = ax.scatter(source_gdf['lon'], source_gdf['lat'], 
                            alpha=0.5, s=50, c=source_gdf['lat'], 
                            cmap='viridis')
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.set_title(f'{source.upper()}\n{len(source_gdf):,} records')
        ax.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax, label='Latitude')

plt.tight_layout()
plt.savefig('data/visualizations/01_geographic_distribution.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✓ Saved: 01_geographic_distribution.png")

# ==========================
# Temporal Coverage
# ==========================
print("\n" + "=" * 70)
print("TEMPORAL COVERAGE")
print("=" * 70)

tdf = combined_df[combined_df['time_start'].notna()]
print(f"\nRecords with time: {len(tdf):,} / {len(combined_df):,} ({100*len(tdf)/len(combined_df):.1f}%)")

print(f"\nTemporal range by source:")
for source in combined_df['source'].unique():
    source_df = combined_df[combined_df['source'] == source]
    source_tdf = source_df[source_df['time_start'].notna()]
    if len(source_tdf) > 0:
        print(f"  {source.upper():10} {source_tdf['time_start'].min():.0f} to {source_tdf['time_start'].max():.0f} ({source_tdf['time_start'].max() - source_tdf['time_start'].min():.0f} years)")

# Timeline visualization
print("\nGenerating temporal visualization...")
fig, ax = plt.subplots(figsize=(14, 6))

colors = {'dplace': '#1f77b4', 'seshat': '#ff7f0e', 'drh': '#2ca02c'}

for source in combined_df['source'].unique():
    source_tdf = tdf[tdf['source'] == source]
    if len(source_tdf) > 0:
        ax.scatter(source_tdf['time_start'], [source]*len(source_tdf), 
                  alpha=0.6, s=100, label=source.upper(), color=colors.get(source, '#d62728'))

ax.set_xlabel('Year (BCE negative, CE positive)')
ax.set_ylabel('Data Source')
ax.set_title('Temporal Distribution of Shamanism Data')
ax.legend(loc='best')
ax.grid(True, alpha=0.3, axis='x')
plt.tight_layout()
plt.savefig('data/visualizations/02_temporal_distribution.png', dpi=150, bbox_inches='tight')
plt.close()
print("  ✓ Saved: 02_temporal_distribution.png")

# ==========================
# Variable Coverage
# ==========================
print("\n" + "=" * 70)
print("VARIABLE COVERAGE")
print("=" * 70)

print(f"\nTotal unique variables: {combined_df['variable_name'].nunique()}")
print(f"\nTop 15 most frequent variables:")
var_counts = combined_df['variable_name'].value_counts().head(15)
for var, count in var_counts.items():
    print(f"  {var:35} {count:6,}")

print(f"\nVariables by source:")
for source in combined_df['source'].unique():
    source_df = combined_df[combined_df['source'] == source]
    nvars = source_df['variable_name'].nunique()
    print(f"  {source.upper():10} {nvars:3} variables")

# ==========================
# Data Completeness
# ==========================
print("\n" + "=" * 70)
print("DATA COMPLETENESS")
print("=" * 70)

print(f"\nMissing values:")
missing = combined_df.isnull().sum()
for col in combined_df.columns:
    count = missing[col]
    pct = 100 * count / len(combined_df)
    if count > 0:
        print(f"  {col:20} {count:6,} ({pct:5.1f}%)")

null_vals = combined_df['variable_value'].isnull().sum()
print(f"\nValue completeness: {len(combined_df) - null_vals:,} valid values ({100*(len(combined_df)-null_vals)/len(combined_df):.1f}%)")

# ==========================
# Cross-Source Overlap
# ==========================
print("\n" + "=" * 70)
print("CROSS-SOURCE OVERLAP ANALYSIS")
print("=" * 70)

dplace_cultures = set(dplace_df['culture_id'].unique())
seshat_cultures = set(seshat_df['culture_id'].unique())
drh_cultures = set(drh_df['culture_id'].unique())

print(f"\nCultures by source:")
print(f"  D-PLACE: {len(dplace_cultures):,}")
print(f"  Seshat:  {len(seshat_cultures):,}")
print(f"  DRH:     {len(drh_cultures):,}")
print(f"  Total unique: {len(dplace_cultures | seshat_cultures | drh_cultures):,}")

overlap_dp_sh = len(dplace_cultures & seshat_cultures)
overlap_dp_dr = len(dplace_cultures & drh_cultures)
overlap_sh_dr = len(seshat_cultures & drh_cultures)
overlap_all = len(dplace_cultures & seshat_cultures & drh_cultures)

print(f"\nCulture overlaps:")
print(f"  D-PLACE ∩ Seshat: {overlap_dp_sh}")
print(f"  D-PLACE ∩ DRH:    {overlap_dp_dr}")
print(f"  Seshat ∩ DRH:     {overlap_sh_dr}")
print(f"  All three:        {overlap_all}")

# ==========================
# Phase 2 Priorities
# ==========================
print("\n" + "=" * 70)
print("PHASE 2 DATA COLLECTION PRIORITIES")
print("=" * 70)

records_no_geo = len(combined_df) - len(gdf)
records_no_time = len(combined_df) - len(tdf)

print(f"\n1. GEOGRAPHIC GAPS:")
print(f"   Current coverage: {len(gdf):,} / {len(combined_df):,} ({100*len(gdf)/len(combined_df):.1f}%)")
print(f"   Priority: Add coordinates for {records_no_geo:,} records")

print(f"\n2. TEMPORAL GAPS:")
print(f"   Current coverage: {len(tdf):,} / {len(combined_df):,} ({100*len(tdf)/len(combined_df):.1f}%)")
print(f"   Priority: Extend temporal data for {records_no_time:,} records")

print(f"\n3. VARIABLE STANDARDIZATION:")
print(f"   Current unique variables: 75")
print(f"   Priority: Harmonize definitions across sources")

print(f"\n4. SESHAT REAL DATA:")
print(f"   Current: Mock data (3 polities)")
print(f"   Priority: Obtain credentials or full public release")

missing_dplace = (dplace_df['variable_value'] == 99).sum()
missing_drh = (drh_df['variable_value'].isnull()).sum()

print(f"\n5. DATA QUALITY:")
print(f"   D-PLACE missing values (code 99): {missing_dplace:,}")
print(f"   DRH missing values: {missing_drh:,}")

print("\n" + "=" * 70)
print("✓ ANALYSIS COMPLETE")
print("=" * 70)
print("\nGenerated visualizations saved to data/visualizations/")
