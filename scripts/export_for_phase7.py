#!/usr/bin/env python3
"""
Export Phase 6 outputs to JSON format for Phase 7 interactive visualization.

This script converts:
1. Cluster assignments + culture metadata → cultures_metadata.json
2. Phase 6 statistical analysis results → analysis_results.json
3. Phylogenetic information (stub for now) → phylo_tree.json

Output: phase7_visualization/data/*.json
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def export_cultures_metadata():
    """
    Create cultures_metadata.json with all culture attributes.
    
    Structure:
    {
      "cultures": [
        {
          "id": "CARNEIRO4_001",
          "name": "Ancient Egyptians",
          "lat": 25.0,
          "lon": 30.0,
          "cluster": 0,
          "language_family": "unknown",
          "features": [...],
          "source": "dplace"
        },
        ...
      ]
    }
    """
    print("Loading data...")
    
    # Load main data
    dplace = pd.read_parquet('data/processed/dplace_real.parquet')
    clusters = pd.read_csv('data/processed/clusters/culture_cluster_membership.csv')
    
    # Pivot features into matrix (one row per culture)
    features_pivot = dplace.pivot_table(
        index='culture_id',
        columns='variable_name',
        values='variable_value',
        aggfunc='first'
    )
    
    # Get culture metadata (one row per culture)
    culture_meta = dplace.drop_duplicates(
        subset=['culture_id'],
        keep='first'
    )[['culture_id', 'culture_name', 'lat', 'lon', 'source']].copy()
    
    # Merge with cluster assignments
    culture_meta = culture_meta.merge(
        clusters,
        left_on='culture_id',
        right_on='culture_id',
        how='left'
    )
    
    # Merge with features
    culture_meta = culture_meta.merge(
        features_pivot,
        left_on='culture_id',
        right_index=True,
        how='left'
    )
    
    # Build cultures array
    cultures = []
    for _, row in culture_meta.iterrows():
        # Extract features (all columns except metadata)
        metadata_cols = ['culture_id', 'culture_name', 'lat', 'lon', 'source', 'cluster_id', 'method']
        feature_cols = [col for col in row.index if col not in metadata_cols]
        
        culture = {
            "id": str(row['culture_id']),
            "name": str(row['culture_name']),
            "lat": float(row['lat']) if pd.notna(row['lat']) else None,
            "lon": float(row['lon']) if pd.notna(row['lon']) else None,
            "cluster": int(row['cluster_id']) if pd.notna(row['cluster_id']) else None,
            "language_family": "unknown",  # TODO: Link from phylogenetic data
            "source": str(row['source']),
            "features": {}
        }
        
        # Add features
        for col in feature_cols:
            val = row[col]
            if pd.notna(val):
                culture["features"][col] = int(val) if isinstance(val, (int, float)) and not pd.isna(val) else val
        
        cultures.append(culture)
    
    output = {
        "metadata": {
            "total_cultures": len(cultures),
            "total_clusters": int(culture_meta['cluster_id'].max()) + 1 if culture_meta['cluster_id'].max() >= 0 else 0,
            "sources": list(culture_meta['source'].unique()),
            "generated_from": "Phase 6 analysis"
        },
        "cultures": cultures
    }
    
    # Save
    output_path = Path('phase7_visualization/data/cultures_metadata.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✓ Exported {len(cultures)} cultures to {output_path}")
    return len(cultures)


def export_analysis_results():
    """
    Create analysis_results.json with Phase 6 statistical outputs.
    
    Structure:
    {
      "morans_i": [...],
      "mantel_results": {...},
      "phylogenetic_signal": [...],
      "distance_decay": [...]
    }
    """
    print("Exporting analysis results...")
    
    analysis_results = {}
    
    # Load spatial analysis CSVs
    phase6_path = Path('data/processed/spatial_analysis_phase6')
    
    # Moran's I
    if (phase6_path / 'morans_i_per_feature.csv').exists():
        morans_i_df = pd.read_csv(phase6_path / 'morans_i_per_feature.csv')
        analysis_results['morans_i'] = morans_i_df.to_dict('records')
        print(f"  - Loaded {len(morans_i_df)} Moran's I results")
    
    # Mantel results
    if (phase6_path / 'mantel_results.csv').exists():
        mantel_df = pd.read_csv(phase6_path / 'mantel_results.csv')
        analysis_results['mantel'] = mantel_df.to_dict('records')
        print(f"  - Loaded Mantel test results")
    
    # Phylogenetic signal
    if (phase6_path / 'phylogenetic_signal.csv').exists():
        phylo_df = pd.read_csv(phase6_path / 'phylogenetic_signal.csv')
        analysis_results['phylogenetic_signal'] = phylo_df.to_dict('records')
        print(f"  - Loaded {len(phylo_df)} phylogenetic signal results")
    
    # Distance decay
    if (phase6_path / 'distance_decay_analysis.csv').exists():
        decay_df = pd.read_csv(phase6_path / 'distance_decay_analysis.csv')
        analysis_results['distance_decay'] = decay_df.to_dict('records')
        print(f"  - Loaded distance decay analysis")
    
    # Hypothesis synthesis
    if (phase6_path / 'hypothesis_synthesis.json').exists():
        with open(phase6_path / 'hypothesis_synthesis.json', 'r') as f:
            analysis_results['hypothesis_synthesis'] = json.load(f)
        print(f"  - Loaded hypothesis synthesis")
    
    # Save
    output_path = Path('phase7_visualization/data/analysis_results.json')
    with open(output_path, 'w') as f:
        json.dump(analysis_results, f, indent=2)
    
    print(f"✓ Exported analysis results to {output_path}")


def export_cluster_profiles():
    """
    Create cluster_profiles.json with cluster characteristics.
    """
    print("Exporting cluster profiles...")
    
    cluster_path = Path('data/processed/clusters')
    
    profiles = {}
    
    # Load cluster profiles
    if (cluster_path / 'cluster_profiles.csv').exists():
        profiles_df = pd.read_csv(cluster_path / 'cluster_profiles.csv')
        profiles = profiles_df.to_dict('records')
    
    # Load robustness analysis
    robustness = {}
    if (cluster_path / 'robustness_analysis.json').exists():
        with open(cluster_path / 'robustness_analysis.json', 'r') as f:
            robustness = json.load(f)
    
    output = {
        "profiles": profiles,
        "robustness_analysis": robustness
    }
    
    output_path = Path('phase7_visualization/data/cluster_profiles.json')
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✓ Exported cluster profiles to {output_path}")


def export_phylo_tree_stub():
    """
    Create phylo_tree.json with phylogenetic structure (stub for now).
    
    Real implementation requires parsing D-PLACE/Glottolog phylogenetic tree.
    For Phase 7 Sprint 1, this is a placeholder.
    """
    print("Creating phylogenetic tree stub...")
    
    # Load cultures to get language families
    dplace = pd.read_parquet('data/processed/dplace_real.parquet')
    culture_meta = dplace.drop_duplicates(subset=['culture_id'], keep='first')
    
    # Create a simple tree structure (stub)
    tree = {
        "name": "World Languages",
        "children": [
            {
                "name": "Language Family 1",
                "id": "LF_1",
                "cultures": [],
                "cluster_composition": {}
            },
            # TODO: Populate with real language family data
        ]
    }
    
    output_path = Path('phase7_visualization/data/phylo_tree.json')
    with open(output_path, 'w') as f:
        json.dump(tree, f, indent=2)
    
    print(f"✓ Created phylogenetic tree stub at {output_path}")


def export_distance_matrices_stub():
    """
    Create distance_matrices.json with precomputed distance matrices (stub).
    
    Real implementation computes:
    - Geographic distances (pairwise)
    - Phylogenetic distances (pairwise)
    - Feature distances (Jaccard)
    
    For Phase 7 Sprint 1, this is a placeholder with empty structure.
    """
    print("Creating distance matrices stub...")
    
    matrices = {
        "geographic": {
            "description": "Geographic distances (km) between cultures",
            "shape": [1257, 1257],
            "data": []  # TODO: Populate with actual matrix
        },
        "phylogenetic": {
            "description": "Phylogenetic distances between cultures",
            "shape": [1257, 1257],
            "data": []
        },
        "feature": {
            "description": "Jaccard distances between feature vectors",
            "shape": [1257, 1257],
            "data": []
        }
    }
    
    output_path = Path('phase7_visualization/data/distance_matrices.json')
    with open(output_path, 'w') as f:
        json.dump(matrices, f, indent=2)
    
    print(f"✓ Created distance matrices stub at {output_path}")


def main():
    print("\n" + "="*60)
    print("PHASE 7 DATA EXPORT")
    print("="*60 + "\n")
    
    try:
        n_cultures = export_cultures_metadata()
        export_analysis_results()
        export_cluster_profiles()
        export_phylo_tree_stub()
        export_distance_matrices_stub()
        
        print("\n" + "="*60)
        print("✓ EXPORT COMPLETE")
        print(f"  - {n_cultures} cultures exported")
        print(f"  - 5 JSON files generated in phase7_visualization/data/")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
