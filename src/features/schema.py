"""
Feature schema for the shamanism spatio-temporal analysis.

Defines the 21 canonical binary/ordinal features that form the cross-source
feature matrix.  Every feature name here must match the ``feature_name`` values
produced by the Phase 2 harmonisation crosswalk.
"""

# Ordered list of canonical feature names — matches CLUSTERING_FEATURES in
# src/analysis/config.py and is the column order for feature_matrix.parquet.
CANONICAL_FEATURES: list[str] = [
    "ancestor_mediation",
    "animal_transformation",
    "chanting_singing",
    "dedicated_specialist",
    "divination",
    "entheogen_use",
    "healing_function",
    "hereditary_transmission",
    "initiatory_crisis",
    "initiatory_ordeal",
    "layered_cosmology",
    "moralizing_supernatural",
    "nature_spirits",
    "possession_crisis",
    "public_performance",
    "rhythmic_percussion",
    "ritual_performance",
    "soul_flight",
    "specialist_presence",
    "spirit_possession",
    "trance_induction",
    "unmapped_shamanic_indicators",
]

# Metadata columns that accompany every row in the feature matrix.
METADATA_COLS: list[str] = [
    "culture_id",
    "culture_name",
    "source",
    "unit_type",
    "temporal_mode",
    "lat",
    "lon",
    "time_start",
    "time_end",
    "language_family",
    "glottocode",
]

# Which features each source can contribute.  A source can only ever have
# non-NA values for features in its own set; everything else stays NaN.
SOURCE_FEATURE_COVERAGE: dict[str, list[str]] = {
    "dplace": [
        "ancestor_mediation",
        "animal_transformation",
        "chanting_singing",
        "divination",
        "entheogen_use",
        "hereditary_transmission",
        "initiatory_crisis",
        "initiatory_ordeal",
        "layered_cosmology",
        "nature_spirits",
        "possession_crisis",
        "public_performance",
        "rhythmic_percussion",
        "ritual_performance",
        "soul_flight",
        "specialist_presence",
        "spirit_possession",
        "trance_induction",
        "unmapped_shamanic_indicators",
    ],
    "drh": [
        "ancestor_mediation",
        "divination",
        "healing_function",
        "trance_induction",
    ],
    "seshat": [
        "dedicated_specialist",
        "moralizing_supernatural",
    ],
}

# Human-readable descriptions for each feature.
FEATURE_DESCRIPTIONS: dict[str, str] = {
    "ancestor_mediation":          "Communication with or channelling of deceased ancestors",
    "animal_transformation":       "Practitioner becomes or merges with an animal spirit",
    "chanting_singing":            "Vocal techniques (icaros, throat singing, chanting) central to practice",
    "dedicated_specialist":        "Recognised social role (0=none, 1=part-time, 2=full-time)",
    "divination":                  "Foretelling future or discovering hidden knowledge",
    "entheogen_use":               "Psychoactive substances used ritually for altered states",
    "healing_function":            "Primary purpose is curing illness or removing affliction",
    "hereditary_transmission":     "Role passed within family or lineage",
    "initiatory_crisis":           "Illness, death-rebirth, or ordeal required before becoming specialist",
    "initiatory_ordeal":           "Physical ordeal as part of initiation",
    "layered_cosmology":           "Belief in upper/lower/middle worlds or axis mundi",
    "nature_spirits":              "Interaction with spirits of natural features",
    "possession_crisis":           "Involuntary spirit possession triggering a crisis",
    "public_performance":          "Ritual performed before a community audience",
    "rhythmic_percussion":         "Drumming or rattling central to trance induction",
    "ritual_performance":          "Formalised ritual performance context",
    "soul_flight":                 "Soul travels to other realms while body remains",
    "specialist_presence":         "Any specialised ritual practitioner role present",
    "spirit_possession":           "Spirit enters and controls the practitioner's body",
    "trance_induction":            "Practitioner deliberately enters a non-ordinary mental state",
    "moralizing_supernatural":      "Supernatural agents enforce moral norms (Seshat moralizing_supernatural / moralizing_agentic)",
    "unmapped_shamanic_indicators": "Other shamanic indicators not mapped to named features",
}
