"""Where the tool finds the modules it builds on: its own vendor/ folder (adapted copies of the Smash 4 research
tools: the executable patches, the data-file, text, texture, ACMD and layout readers)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VENDOR = os.path.join(ROOT, 'vendor')
LIB = VENDOR
if LIB not in sys.path:
    sys.path.insert(0, LIB)
