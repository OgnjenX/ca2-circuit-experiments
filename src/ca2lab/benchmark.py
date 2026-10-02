"""Coverage and numerical gates for prospectively scored benchmark setups."""
import math

def require_coverage(rows, expected, key):
    actual=[key(row) for row in rows]
    if len(actual)!=len(set(actual)) or set(actual)!=set(expected):
        raise ValueError('Missing, duplicate or unexpected assay coverage')

def setup_pass(rows, primary_frequencies, numerical_pass):
    frequencies=[row['frequency_Hz'] for row in rows]
    complete=(len(frequencies)==len(set(frequencies)) and set(frequencies)==set(primary_frequencies))
    return bool(numerical_pass and complete and all(
        row['eligible_all_seeds'] and row['inside_compatibility_band']
        and math.isfinite(row['model_mean_ratio']) for row in rows))
