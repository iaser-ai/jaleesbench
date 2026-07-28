# handoff/ — committed deliverables staging

This directory holds deliverables bound for outside this repo — localized
article sources (`article/<lang>/index.md` + assets), curated GIFs/
screenshots, and translated prompt text for the prompt page — packaged for
the iaser.ai workspace.

Unlike `out/` (gitignored, regenerable build artifacts), everything here
is **committed**: these are curated hand-off products, not build outputs.
Populated by the articles plan phase; the pinned EN article snapshot
(`article/en-reference.md`) lands here too.

Article-package format requirements from the iaser.ai architect
(2026-07-28): include **per-language section headings/slugs** (localized
page anchors), and **explicitly state that videos/GIFs are fully
localized variants with per-language YouTube IDs** (drives their
localized "Watch it in video" line). Their article template is LTR-only
today — RTL page work is scoped on their side.
