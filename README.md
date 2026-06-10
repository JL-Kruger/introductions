# Introductions

WELCOME TO THE REPO FOR MY SITE BRO! - You _must_ be a curious cat.

anyhoodle - I got an llm to generate the rest of the words that you read here. Figured I would put my stamp up here to say, hey I read it and adjusted what I didn't approve.

---

## What this is

- **Live:** https://jlkruger.exopraxist.org/
- **GitHub mirror:** https://jl-kruger.github.io/introductions
- **Repo:** https://github.com/JL-Kruger/introductions

The source for **JL Kruger's** personal site — an introduction of sorts. Multimedia maker, community builder, and assembler of words that occasionally argue with each other.

A hand-built static website. No framework, no build server, no runtime — just HTML, CSS, and a sprinkle of vanilla JavaScript for the glow and the doodads. Open `index.html` in a browser and the whole thing works.

The pages are generated locally from YAML source files by a set of Python `*-builder.py` scripts (kept out of the repo, see below). What lands here is the rendered output: ready-to-serve HTML.

## Structure

```
introductions
│
├─ index.html            Home page
├─ content.html          Hub for all content pages
├─ downloads.html        Hub for download links
├─ 404.html              Placeholder / maintenance page
│
├─ css/                  Stylesheets
│  ├─ styles.css           homepage
│  ├─ content.css          hub pages
│  ├─ content-page.css     content pages
│  └─ tokens.css           design tokens
│
├─ js/                   Vanilla JS
│  ├─ shimmer.js           the glow
│  ├─ pretext-engine.js    text shenaniganery
│  └─ svg-assets.js        critters, separators, doodads
│
├─ Content/
│  ├─ Writings/          essays and arguments
│  ├─ Business/          skills, rates, contact, work history, projects
│  └─ Legal/             terms, privacy, licenses
│
└─ Media/
   ├─ Images/            page images, galleries, responsive webp
   ├─ Files/             downloadable bits (catalogued in downloads.html)
   └─ SVG-Assets/        site decor
```

A fuller annotated tree lives in [`SITEMAP.md`](SITEMAP.md).

## Building

Pages are authored as YAML and rendered to HTML by Python builder scripts that live in a local-only `Toolbox/` directory (not tracked here). The committed `.html` files are the build output, so the site stands on its own without the toolchain.

## License

See the documents under [`Content/Legal/`](Content/Legal/) for terms, privacy, and content licensing. Content © JL Kruger unless noted otherwise.
