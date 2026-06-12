"""tokens.py — emit css/tokens.css from variables.yaml.

Thin wrapper around builder_common.write_tokens_css(). Extended token system
(spacing scale, vertical rhythm, fluid type) is a later Opus/Sonnet task
(BUILD-ARCH §4 insertion point 4).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from builder_common import write_tokens_css


def build(unit, root):
    write_tokens_css(root)
