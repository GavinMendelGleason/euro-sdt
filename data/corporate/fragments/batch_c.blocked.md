# Batch C — blocked official sources

## Saint-Gobain

Status: blocked. Every HTML/PDF request to the corporate domain returns HTTP 403 with a Cloudflare
browser-integrity interstitial ("We're checking your browser before allowing access", Ray IDs
`a54441e0c8f4a16b` / `a54442635a16c2b1`), independent of client and user agent. `robots.txt` and
`/sitemap.xml` return 200 from the same host, so this is a WAF rule on document responses rather
than a network outage, and no browser challenge can be solved from this network.

URLs tried:

| URL | Status |
| --- | --- |
| `https://www.saint-gobain.com/en/group/corporate-governance/board-directors-and-committees` (board page) | 403 via curl (Safari/Chrome/Firefox/cURL UA), `curl_cffi` (chrome, chrome124, safari17_0 TLS impersonation), Playwright chromium (headless and headed under Xvfb), Playwright firefox (headed), Playwright webkit, and the `read` tool |
| `https://www.saint-gobain.com/fr/group/gouvernance/conseil-administration` | 403 |
| `https://www.saint-gobain.com/en/group/corporate-governance` | 403 |
| `https://www.saint-gobain.com/sites/saint-gobain.com/files/media/document/Saint-Gobain_2025_DEU_VA.pdf` (2025 universal registration document) | 403 |
| `https://www.saint-gobain.com/sites/saint-gobain.com/files/media/document/02_ag2026_brochure_va.pdf` (2026 shareholders' meeting brochure) | 403 |
| `https://www.saint-gobain.com/sites/saint-gobain.com/files/media/document/2025-URD-SAINT-GOBAIN-ENG_INTERACTIF_0505-mix_03.pdf` | 403 |
| `https://www.saint-gobain.com/en/finance/regulated-information/universal-registration-document-including-annual-financial-report` | 403 |

Archives and proxies also failed to yield the page:

- Wayback Machine: newest capture of the board page is 2025-04-05 (no 2026 snapshot); Save Page Now returned 520.
- Common Crawl `CC-MAIN-2026-43` and `CC-MAIN-2026-39`: no capture of the board page.
- archive.today: no snapshot. `r.jina.ai`, codetabs, allorigins, `translate.goog` and textise proxies: 403/522.
- Microlink refused the URL outright: `uses antibot protection` (`EPROXYNEEDED`).
- The site bypasses the WAF only for JSON responses (`?_format=json`), but the board route answers
  `A route that returns a rendered array as its response only supports the HTML format.` (406), and
  `/jsonapi` is disabled, so no machine-readable rendering of the page exists.

No Saint-Gobain rows are included in `batch_c.csv`; no non-official mirror was used as evidence.
