
import os
import sys


if os.name == "nt":
    for _entry in list(sys.path):
        if os.path.isabs(_entry) and "site-packages" in _entry.lower() and not _entry.startswith("\\\\?\\"):
            _extended = "\\\\?\\" + os.path.abspath(_entry)
            if _extended not in sys.path:
                sys.path.insert(0, _extended)
