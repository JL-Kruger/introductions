"""scan.py — filesystem + site.yaml discovery → BuildPlan.

Replaces the BUILDERS dict + content_yamls()/gallery_folders() helpers that
were duplicated in sitebuilder-server.py. Single-source discovery that both
build.py and build_ui.py read from.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

import yaml

# ---------------------------------------------------------------------------
# Slug → output directory map (was hardcoded in contentpage-builder.py; lives
# here now as the canonical copy).
# ---------------------------------------------------------------------------

SLUG_TO_DIR = {
    'WorkHistory':               'Content/Business',
    'SkillsRates':               'Content/Business',
    'CurrentProjects':           'Content/Business',
    'CollaboratorsCommunities':  'Content/Business',
    'ContactPage':               'Content/Business',
    'MyArgument':                'Content/Writings',
}


# ---------------------------------------------------------------------------
# Unit types
# ---------------------------------------------------------------------------

@dataclass
class TokensUnit:
    output: Path

    def label(self) -> str:
        return 'tokens'


@dataclass
class SpriteUnit:
    output: Path

    def label(self) -> str:
        return 'sprite'


@dataclass
class FontsUnit:
    output: Path

    def label(self) -> str:
        return 'fonts'


@dataclass
class PageUnit:
    kind: str   # 'home' | 'hub' | 'placeholder'
    output: Path

    def label(self) -> str:
        return self.kind


@dataclass
class ContentUnit:
    yaml_path: Path
    output: Path
    slug: str

    def label(self) -> str:
        return self.slug


@dataclass
class GalleryUnit:
    folder: Path
    output: Path
    title: str

    def label(self) -> str:
        return self.folder.name


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------

def content_yamls(root: Path) -> List[Path]:
    """Return sorted list of *-content.yaml paths under Toolbox/Python/."""
    return sorted((root / 'Toolbox' / 'Python').glob('*-content.yaml'))


def gallery_folders(root: Path) -> List[Path]:
    """Return sorted list of immediate image subdirectories."""
    images_dir = root / 'Media' / 'Images'
    if not images_dir.is_dir():
        return []
    return sorted(p for p in images_dir.iterdir() if p.is_dir())


def _resolve_content_dest(yaml_path: Path, root: Path):
    """Return (output_path, slug) for a content YAML."""
    with open(yaml_path, encoding='utf-8') as f:
        doc = yaml.safe_load(f)
    meta = doc.get('meta', {})
    if 'dest' in meta:
        return root / meta['dest'], meta.get('slug', yaml_path.stem)
    slug = meta.get('slug', yaml_path.stem)
    folder = SLUG_TO_DIR.get(slug)
    if not folder:
        raise ValueError(
            f'Unknown slug {slug!r} in {yaml_path.name} — add to SLUG_TO_DIR or set meta.dest'
        )
    return root / folder / f'{slug}.html', slug


def _humanise(name: str) -> str:
    name = re.sub(r'[-_]+', ' ', name)
    name = re.sub(r'\s+gallery\s*$', '', name, flags=re.IGNORECASE)
    return name.strip().title()


# ---------------------------------------------------------------------------
# BuildPlan
# ---------------------------------------------------------------------------

def build_plan(root: Path) -> list:
    """Return the ordered list of units representing the full build.

    Emit order per BUILD-ARCH §1:
      tokens → sprite → fonts → home → hub → placeholder → content pages → galleries
    """
    units = []

    units.append(TokensUnit(output=root / 'css' / 'tokens.css'))
    units.append(SpriteUnit(output=root / 'Media' / 'sprite.svg'))
    units.append(FontsUnit(output=root / 'css' / 'fonts.css'))

    units.append(PageUnit(kind='home',        output=root / 'index.html'))
    units.append(PageUnit(kind='hub',         output=root / 'content.html'))
    units.append(PageUnit(kind='placeholder', output=root / '404.html'))

    for yaml_path in content_yamls(root):
        out_path, slug = _resolve_content_dest(yaml_path, root)
        units.append(ContentUnit(yaml_path=yaml_path, output=out_path, slug=slug))

    for folder in gallery_folders(root):
        title = _humanise(folder.name)
        output = folder.parent / f'{folder.name}.html'
        units.append(GalleryUnit(folder=folder, output=output, title=title))

    return units
