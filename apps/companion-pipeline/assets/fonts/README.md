# Vendored card fonts

Checked in so card rendering is **machine-independent**. Before this, the
pipeline named font families and hoped the host had them: Chrome
substitutes a missing family silently, so `ur` cards rendered correctly
only because macOS happens to ship `NotoNastaliq.ttc`, and `ar` cards had
been rendering in the Geeza Pro fallback all along — nobody had ever seen
an `ar` card in the face its config named. Cards now load these files by
path, so every machine produces the same pixels, and the faces match the
ones iaser.ai self-hosts on the web surfaces.

| File | Family | Coverage |
|---|---|---|
| `NotoNaskhArabic-arabic.woff2` | Noto Naskh Arabic | Arabic |
| `NotoNaskhArabic-latin.woff2` | Noto Naskh Arabic | Latin |
| `NotoNastaliqUrdu-arabic.woff2` | Noto Nastaliq Urdu | Arabic |
| `NotoNastaliqUrdu-latin.woff2` | Noto Nastaliq Urdu | Latin |

Two subsets per family because cards mix scripts — product names and
`s.iaser.ai/prompt` are Latin inside otherwise-RTL text. Both weights (400
and 700; `h1` is 700) come from the same file: these are variable fonts,
and Google serves one file per subset for both weights.

## Provenance

Google Fonts, 2026-07-31 — Noto Naskh Arabic v44, Noto Nastaliq Urdu v23,
the same `fonts.gstatic.com` subsets a browser would fetch from the CSS2
API. Verified `wOF2` magic bytes on all four.

To refresh, re-request the CSS2 API with a modern-Chrome UA (the UA
decides whether you are served woff2 or an older format), take the
`arabic` and `latin` `@font-face` URLs for each family, and re-download.

## License

SIL Open Font License 1.1 — OFL text per family is included alongside the
files, as the license requires. The fonts are redistributable, including
in a public repo, under those terms; they are not to be sold on their own,
and the reserved font names must not be used on modified versions.
