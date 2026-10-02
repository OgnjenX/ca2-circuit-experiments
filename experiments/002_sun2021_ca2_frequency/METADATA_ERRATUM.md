# Run metadata adapter

The prospectively frozen controller records STP/static `release` in every run
configuration and uses the correct executable, but omits that categorical field
from the measurement rows consumed by the frozen analysis. `finalize_metadata.py`
adds the label from each checksum-verified configuration and checks it against
the frozen executable identity. It preserves the original batch separately and
changes no numerical measurements, raw monitors, model settings or analysis.
This software adapter was added after train testing began. The original scientific
freeze and all of its integrity checks remain unchanged.
