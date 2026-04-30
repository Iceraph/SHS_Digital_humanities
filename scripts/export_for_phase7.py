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
import re

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

def export_cultures_metadata():
    """
    Create cultures_metadata.json with all culture attributes.

    Uses the multisource feature matrix (D-PLACE + Seshat + DRH) and the
    multisource cluster assignments (data/processed/clusters/multisource/).

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
          "features": {...},
          "source": "dplace"
        },
        ...
      ]
    }
    """
    print("Loading data...")

    # Canonical multisource feature matrix (2,452 cultures × 21 features + metadata)
    feature_matrix = pd.read_parquet('data/processed/feature_matrix.parquet')

    # Multisource cluster assignments (1,160 cultures: 755 dplace + 400 seshat + 5 drh)
    clusters = pd.read_csv('data/processed/clusters/multisource/culture_cluster_membership_k8.csv')

    # Feature columns: everything that isn't metadata
    metadata_cols = {'culture_id', 'culture_name', 'source', 'unit_type', 'temporal_mode',
                     'lat', 'lon', 'time_start', 'time_end', 'language_family', 'glottocode'}
    feature_cols = [c for c in feature_matrix.columns if c not in metadata_cols]

    # Keep ALL cultures; cluster_id = NaN for phylogenetically-filtered-out cultures
    # (those without cluster assignments render as gray "unclustered" points in the viz)
    culture_meta = feature_matrix.merge(
        clusters[['culture_id', 'cluster_id']],
        on='culture_id',
        how='left'
    )

    # Build cultures array
    cultures = []
    for _, row in culture_meta.iterrows():
        culture = {
            "id": str(row['culture_id']),
            "name": str(row['culture_name']),
            "lat": float(row['lat']) if pd.notna(row['lat']) else None,
            "lon": float(row['lon']) if pd.notna(row['lon']) else None,
            "cluster": int(row['cluster_id']) if pd.notna(row['cluster_id']) else None,
            "language_family": (
                str(row['language_family'])
                if pd.notna(row.get('language_family')) and not str(row.get('language_family', '')).startswith('seshat:')
                else 'unknown'
            ),
            "source": str(row['source']),
            "features": {}
        }

        for col in feature_cols:
            val = row[col]
            if pd.notna(val):
                culture["features"][col] = int(val) if isinstance(val, (int, float)) else val

        cultures.append(culture)

    output = {
        "metadata": {
            "total_cultures": len(cultures),
            "total_clusters": int(culture_meta['cluster_id'].max()) + 1 if len(culture_meta) > 0 else 0,
            "sources": sorted(culture_meta['source'].unique().tolist()),
            "generated_from": "Multisource Phase 3-4 (D-PLACE + Seshat + DRH, commit 3432cae)"
        },
        "cultures": cultures
    }

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
    multisource_path = cluster_path / 'multisource'

    profiles = {}

    # Prefer multisource cluster profiles; fall back to baseline
    profiles_file = multisource_path / 'cluster_profiles.csv'
    if not profiles_file.exists():
        profiles_file = cluster_path / 'cluster_profiles.csv'
    if profiles_file.exists():
        profiles_df = pd.read_csv(profiles_file)
        profiles = profiles_df.to_dict('records')
        print(f"  - Loaded cluster profiles from {profiles_file}")

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


def _extract_newick_from_nexus(nexus_text: str) -> str | None:
    match = re.search(r"TREE\s+summary\s*=\s*(?:\[&R\]\s*)?(.*?);", nexus_text, re.S)
    if not match:
        return None
    newick = match.group(1).strip()
    newick = re.sub(r"\[.*?\]", "", newick)
    return newick


def _parse_newick(newick: str) -> dict | None:
    if not newick:
        return None

    root = None
    current = None
    stack: list[dict] = []
    i = 0
    length = len(newick)

    while i < length:
        ch = newick[i]

        if ch in " \t\n\r":
            i += 1
            continue

        if ch == "(":
            node = {"name": None, "children": []}
            if current is not None:
                current["children"].append(node)
                stack.append(current)
            current = node
            if root is None:
                root = node
            i += 1
            continue

        if ch == ",":
            if stack:
                parent = stack[-1]
                node = {"name": None, "children": []}
                parent["children"].append(node)
                current = node
            i += 1
            continue

        if ch == ")":
            if stack:
                current = stack.pop()
            i += 1
            continue

        if ch == ":":
            i += 1
            while i < length and newick[i] not in ",);":
                i += 1
            continue

        if ch in "'\"":
            quote = ch
            i += 1
            start = i
            while i < length and newick[i] != quote:
                i += 1
            name = newick[start:i].strip()
            if current is not None and name:
                current["name"] = name
            i += 1
            continue

        if ch == ";":
            break

        start = i
        while i < length and newick[i] not in ":,);":
            i += 1
        name = newick[start:i].strip()
        if current is not None and name:
            current["name"] = name

    return root


def _prune_tree(node: dict | None, keep: set[str]) -> dict | None:
    if node is None:
        return None

    children = node.get("children") or []
    if children:
        pruned_children = []
        for child in children:
            pruned = _prune_tree(child, keep)
            if pruned is not None:
                pruned_children.append(pruned)
        node["children"] = pruned_children

    if node.get("children"):
        return node

    name = node.get("name")
    if name in keep:
        return node
    return None


def _add_cluster_composition(node: dict, cluster_map: dict[str, list[int]]) -> dict[int, int]:
    children = node.get("children") or []
    if not children:
        clusters = cluster_map.get(node.get("name"), [])
        counts: dict[int, int] = {}
        for cluster in clusters:
            if cluster is None or (isinstance(cluster, float) and np.isnan(cluster)):
                continue
            counts[int(cluster)] = counts.get(int(cluster), 0) + 1
        node["cluster_composition"] = counts
        return counts

    totals: dict[int, int] = {}
    for child in children:
        child_counts = _add_cluster_composition(child, cluster_map)
        for cluster, count in child_counts.items():
            totals[cluster] = totals.get(cluster, 0) + count
    node["cluster_composition"] = totals
    return totals


def _assign_node_ids(node: dict, prefix: str, counter: list[int]) -> None:
    if node.get("name"):
        node["id"] = node["name"]
    else:
        counter[0] += 1
        node["id"] = f"{prefix}_{counter[0]}"

    for child in node.get("children") or []:
        _assign_node_ids(child, prefix, counter)


def export_phylo_tree():
    """
    Create phylo_tree.json by parsing D-PLACE Glottolog trees.
    """
    print("Creating phylogenetic tree...")

    feature_matrix = pd.read_parquet('data/processed/feature_matrix.parquet')
    clusters = pd.read_csv('data/processed/clusters/multisource/culture_cluster_membership_k8.csv')

    culture_meta = feature_matrix.merge(
        clusters[['culture_id', 'cluster_id']],
        on='culture_id',
        how='left'
    )

    dplace = culture_meta[(culture_meta['source'] == 'dplace') & culture_meta['glottocode'].notna()]
    glottocode_clusters: dict[str, list[int]] = {}
    for _, row in dplace.iterrows():
        code = str(row['glottocode'])
        cluster = row['cluster_id'] if pd.notna(row['cluster_id']) else None
        glottocode_clusters.setdefault(code, []).append(cluster)

    keep = set(glottocode_clusters.keys())
    trees_dir = Path('data/raw/dplace_repo/cldf/trees')
    children = []

    for tree_path in sorted(trees_dir.glob('*.trees')):
        try:
            text = tree_path.read_text()
        except Exception:
            continue

        newick = _extract_newick_from_nexus(text)
        if not newick:
            continue

        parsed = _parse_newick(newick)
        pruned = _prune_tree(parsed, keep)
        if not pruned:
            continue

        if not pruned.get('name'):
            pruned['name'] = tree_path.stem
        pruned['id'] = tree_path.stem
        _add_cluster_composition(pruned, glottocode_clusters)
        _assign_node_ids(pruned, tree_path.stem, [0])

        children.append(pruned)

    tree = {
        "name": "World Languages",
        "id": "world_languages",
        "children": children
    }
    _add_cluster_composition(tree, glottocode_clusters)
    _assign_node_ids(tree, "world", [0])

    output_path = Path('phase7_visualization/data/phylo_tree.json')
    with open(output_path, 'w') as f:
        json.dump(tree, f, indent=2)

    print(f"✓ Created phylogenetic tree at {output_path}")


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
        export_phylo_tree()
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
