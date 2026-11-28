"""Where the engine finds the modules it builds on: its own vendor/ folder (the standalone package), else the
repository's tools/ folder it lives in (tools/sm4shclonetool/)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # tools/sm4shclonetool (or the unpacked package)
VENDOR = os.path.join(ROOT, 'vendor')
REPO_TOOLS = os.path.dirname(ROOT)
LIB = VENDOR if os.path.isdir(VENDOR) else REPO_TOOLS
if LIB not in sys.path:
    sys.path.insert(0, LIB)
