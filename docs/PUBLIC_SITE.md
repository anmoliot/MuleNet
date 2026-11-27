# Public Website

The user approved the image-first MuleNet direction before implementation.
The public landing page is a separate Vite entry under `frontend/website/`.
It does not import the legacy app, read private environment variables, expose
an API proxy, collect visitor data, or connect to scoring and case services.
This is not completion of the investigator-UI migration or production acceptance.

## Local Commands

```sh
cd frontend
npm ci
npm run build:site
npm run dev:site
```

The local development URL is `http://127.0.0.1:5174/`. An already-running static
preview may occupy that port; stop that specific preview before starting another
server, or explicitly choose a different port. The existing app retains its
original Vite entry and commands.

```sh
node scripts/render-site-evidence.mjs --check
npx eslint --config eslint.site.config.js website scripts/*.mjs *.site.config.js tests/site.spec.js
npm run test:site
node scripts/package-site.mjs
```

Browser tests expect a running preview of `dist-site/`. Windows verification used
`SITE_BROWSER_CHANNEL=msedge` in isolated headless profiles; Linux CI installs
Playwright Chromium explicitly. `SITE_BASE_URL` selects another test origin.
No existing personal browser profile or authentication state is read.

## Evidence And Assets

`render-site-evidence.mjs` projects measured metrics from the PaySim and local
account-simulator reports into `reports/site-evidence.json` and the public
`evidence.json`. The page reads this file and never supplies fallback numbers.
Generation fails if required measured values are missing. Source hashes are
included. PaySim and account tasks remain explicitly distinct; no customer,
recovery, commercial-price or real watchlist-access claims are introduced.

The connected-account bitmap was generated with the built-in image tool and
refined to use transparency. It is explicitly an illustration, not a captured
application or live model result. The brand sheet and approved opening remain
design references, not code or measured evidence. IBM Plex fonts are self-hosted
from pinned Fontsource packages; their OFL notices ship with the static site.

Final asset: `frontend/website/public/evidence-graph-alpha.png`. The built-in
image-generation workflow produced the account graph, then applied this final
edit prompt: remove only the pale-yellow background to true transparency;
preserve all account labels, nodes, positions, connections, arrowheads, coral
review edges, off-white node interiors and the review check; add no new titles,
labels, texture, shadows or background. The original brand/opening previews are
not substituted for a working page. The modal retains a readable graph scale
with keyboard/touch scrolling; its HTML explanation identifies the same path.

Browser receipts are generated in `reports/site-browser-tests.json`, pairing
measurements in `reports/site-contrast/`, and screenshots under
`.tools/site-browser/`. WCAG relative-luminance ratios and APCA are separate
instruments. Flat-background HTML text is measured across recorded states;
raster text is inspected visually. These checks are not a full accessibility
certification, assistive-technology audit or security certification.

## Deployment Boundary

The Vercel target is the separate `mulenet-public` project in the connected
owner's team. Deployment packages only the allowlisted files in `dist-site/`,
using `package-site.mjs`; symlinks, unexpected directories and non-public files
fail closed. `reports/site-build.json` records the exact published-file hashes.
No model artifact, raw dataset, service credential, `.env`, backend source or
private investigator entry is included. The deployment has static security
headers and a self-only content policy, with no API rewrite or server functions.

Default Vercel deployment protection is retained. The provider assigned the new
project's first deployment to its production target despite an omitted target
in the request; the verified receipt records that actual target, not preview.
This publishes only the static research website, not a production release of
the fraud platform. Hosted CI results are not claimed from local receipts.
Existing platform security findings remain open.
