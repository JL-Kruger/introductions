# SITEMAP for JL Kruger Introductions Website

---

SiteURL: https://jlkruger.exopraxist.org/
GitHubMirrorURL: https://jl-kruger.github.io/introductions
SiteRepoURL: https://github.com/JL-Kruger/introductions

---

## Repository Structure

introductions
|
|_/css                  <--- it's all for the style points, darling
| |_ styles.css         <--- homepage style sheet
| |_ content.css        <--- hub pages style sheet
| |_ content-page.css   <--- content pages style sheet
| |_ *.css              <--- special style sheets for special pages
|
|_/js                   <--- the fancy shit
| |_ shimmer.js         <--- make the glow go oh
| |_ pretext-engine.js  <--- texticle shenaniganery
| |_ svg-assets.js      <--- critters and separators and other such doodads
| |_ *.js               <--- fancy shit that I haven't thought up yet
|
|_/Content
| |_/Writings
| | |_ MyArgument.html  <--- a cover letter of sorts.
| | |_ *.html           <--- other writings
| |
| |_/Business
| | |_ SkillsRates.html                 <--- what I can do and what it costs
| | |_ ContactPage.html                 <--- the many and varied ways to reach me
| | |_ WorkHistory.html                 <--- a record of professional adventures.
| | |_ CollaboratorsCommunities.html    <--- a collection of conspirators
| | |_ CurrentProjects.html             <--- my current preoccupations
| | |_ *.html                           <--- more business more page
| |
| |_/Legal
|   |_ JLKruger-WebsiteTerms.html       <--- them's the rules biches
|   |_ JLKruger-PrivacyPolicy.html      <--- I track my projects, not my visitors
|   |_ *-license.html                   <--- keeping certain things certain
|   |_ *-SLA.html                       <--- service level agreements
|
|_/Media
| |_/Images
| | |_/*-gallery        <--- page-scoped image collections
| | | |_ *.jpg
| | | |_ *.png
| | | |_ *.svg
| | | |_ *.webp
| | | 
| | |_/responsive
| | | |_ *.webp
| | |
| | |_ *.jpg
| | |_ *.png
| | |_ *.svg
| | |_ *.webp
| | |_ *-gallery.html   <--- gallery-builder.py outputs
| |
| |_/Files              <--- bucket for files (curated catalogue in downloads.html)
| | |_ *.*
| |
| |_/SVG-Assets         <--- decor for the site.
|   |_ *.svg
|
|_ index.html           <--- home page
|_ content.html         <--- hub page for all content pages
|_ downloads.html       <--- hub page for download links
|_ 404.html             <--- placeholder/under construction/maintenance page
|_ README.md            <--- info for the github repo.
|_ SITEMAP.md           <--- this document.

|---local-only----------

|_/Toolbox
| |_/Python
| | |_/.venv                    <--- virtual environment for python scripts.
| | | 
| | |_ variables.yaml           <--- place for *-builder.py variables to live.
| | |_ site.yaml                <--- source data for core site pages.
| | |_ gallery-builder.py       <--- builds *-gallery.html files from folders
| | |_ contentpage-builder.py   <--- ingests *-content.yaml and outputs *.html
| | |_ contenthub-builder.py    <--- builds content.html
| | |_ homepage-builder.py      <--- builds index.html
| | |_ *-content.yaml           <--- content source files
| | |_ *-page.yaml              <--- special source files
| | |_ *-builder.py             <--- page build scripts
| | |_ *-ui.html                <--- interfaces
| |
| |_/Agent-Contextuals          <--- knowledge and other usefuls
| | |_/*
| | | |_ *.*
| | |_ *.md
| |
| |_/Agent-Skills               <--- agent skills library
|   |_/*
|   | |_ *.*
|   |_ *.md
|
|_ DESIGN.md            <--- Design specifications
|_ AGENTS.md            <--- Agent-specific instructions.

