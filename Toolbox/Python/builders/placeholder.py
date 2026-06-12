"""placeholder.py — render /404.html from site.yaml › placeholder.

New in this refactor (BUILD-ARCH §0 gap: 404.html was orphaned — no builder
consumed site.yaml › placeholder). Reuses contenthub's bento-grid renderer.
Not included in the parity byte-diff gate (no prior baseline exists).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from builder_common import load_yaml, set_rel_prefix

from builders.contenthub import render


def build(unit, root):
    set_rel_prefix(unit.output, root)
    data = load_yaml('Toolbox/Python/site.yaml')
    render(data, 'placeholder', 'Page Not Found — JL Kruger', unit.output, root)
