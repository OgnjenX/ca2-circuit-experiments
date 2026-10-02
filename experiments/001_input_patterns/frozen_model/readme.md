# Frozen native sources

These are byte-for-byte copies of the model sources used in experiment 001,
before the readability cleanup. They retain the recorded SHA-256 checksums.
The experiment's source map points here. Use these files to inspect the exact
historical implementation; edit `models/ca2_carlsim/` for further development.

The original release assets and frozen runtime layout are unchanged. A formatted
source has a different file hash even when its C++ token sequence is identical.

A local `.clang-format` disables formatting in this directory to protect the
historical copies when formatting the working project.
