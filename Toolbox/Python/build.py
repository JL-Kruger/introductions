#!/usr/bin/env python3
"""build.py — single-entrypoint site builder.

Scans the project, produces a BuildPlan, and dispatches each unit to its
renderer in the fixed emit order (BUILD-ARCH §1):
  tokens → sprite → fonts → home → hub → placeholder → content pages → galleries

Usage:
  python3 build.py [--root PATH] [--only LABEL] [--list] [--check] [--all]

  --root PATH      Override project root (default: auto-detected from file location)
  --only LABEL     Build only units whose label() matches LABEL (case-insensitive)
                   LABEL can be a kind (home, hub, placeholder, tokens, sprite, fonts),
                   a content slug (WorkHistory, MyArgument, …), or a gallery folder name
  --list           Print the build plan and exit without building
  --check          Validate the scan plan; abort before any file is written
  --all            Build everything (default when --only is omitted)
"""

import argparse
import sys
from pathlib import Path

# Toolbox/Python/ on path so builder_common and builders/ are found
sys.path.insert(0, str(Path(__file__).parent))

from builder_common import project_root
from builders import scan
from builders import tokens, sprite, fonts, homepage, contenthub, placeholder, contentpage, gallery


def _dispatch(unit, root):
    if isinstance(unit, scan.TokensUnit):
        tokens.build(unit, root)
    elif isinstance(unit, scan.SpriteUnit):
        sprite.build(unit, root)
    elif isinstance(unit, scan.FontsUnit):
        fonts.build(unit, root)
    elif isinstance(unit, scan.PageUnit):
        if unit.kind == 'home':
            homepage.build(unit, root)
        elif unit.kind == 'hub':
            contenthub.build(unit, root)
        elif unit.kind == 'placeholder':
            placeholder.build(unit, root)
    elif isinstance(unit, scan.ContentUnit):
        contentpage.build(unit, root)
    elif isinstance(unit, scan.GalleryUnit):
        gallery.build(unit, root)


def main():
    parser = argparse.ArgumentParser(
        description='Build the JL Kruger static site from YAML sources.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--root', default=None,
                        help='Project root override')
    parser.add_argument('--only', default=None, metavar='LABEL',
                        help='Build only units matching this label (kind, slug, or folder name)')
    parser.add_argument('--list', action='store_true', dest='list_units',
                        help='Print build plan and exit')
    parser.add_argument('--check', action='store_true',
                        help='Validate plan; exit without writing any files')
    parser.add_argument('--all', action='store_true', dest='build_all',
                        help='Build everything (default when --only is omitted)')
    args = parser.parse_args()

    root = project_root(args.root)
    plan = scan.build_plan(root)

    if args.list_units:
        print(f'Build plan — {len(plan)} unit(s):')
        for u in plan:
            print(f'  {u.__class__.__name__:<16}  {u.label()}')
        return

    if args.check:
        print(f'Check: {len(plan)} unit(s) in build plan — OK')
        return

    if args.only:
        key = args.only.lower()
        filtered = [u for u in plan
                    if key == u.label().lower()
                    or (isinstance(u, scan.PageUnit) and key == u.kind)]
        if not filtered:
            print(f'ERROR: no unit matching {args.only!r} — run --list to see available labels',
                  file=sys.stderr)
            sys.exit(1)
        plan = filtered

    built = 0
    for unit in plan:
        _dispatch(unit, root)
        built += 1

    print(f'\nDone: {built} unit(s) built.')


if __name__ == '__main__':
    main()
