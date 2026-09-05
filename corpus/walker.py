"""Compatibility wrapper for the packaged TerraDrift history walker.

Use ``python corpus/walker.py --help`` or the higher-level
``terradrift reproduce`` command.
"""

from terradrift.history import main

if __name__ == "__main__":
    main()
