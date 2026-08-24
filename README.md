# FindWell Directory

A static site. No build tools, no dependencies, no server. Cloudflare Pages
serves it as-is.

## Deploying to Cloudflare (Workers)

Repo layout:

```
wrangler.jsonc     <- tells Cloudflare what to serve
build.py           <- the generator (not published)
README.md          <- this file (not published)
public/            <- the actual website
```

Push all of this to the repo root. `wrangler.jsonc` points the Worker at
`public/`, so only the site is served — `build.py` and this README are not
reachable from the web.

In the Worker's settings, Build command stays **empty** and Deploy command is
`npx wrangler deploy` (Cloudflare's default). Nothing else to configure.

A Worker with no `wrangler.jsonc` has no idea what to serve — that was the
problem. If you would rather use Cloudflare Pages instead, delete the Worker,
create a Pages project from the same repo, and set the build output directory
to `public`.

## The pages

Every page is real HTML at a real URL, so Google indexes each one separately:

| URL | What it is |
|---|---|
| `/` | Home, hero, search console |
| `/directory/` | All listings, filterable |
| `/practice-types/` | The twelve discipline tiles |
| `/practice-types/ayurveda/` etc. | One page per discipline, pre-filtered |
| `/locations/` | State index |
| `/locations/arizona/` etc. | One page per state, pre-filtered |
| `/provider/amitaayurveda/` etc. | One page per practitioner |
| `/join/` | Application form |
| `/about/` | Who we are |
| `/404.html` | Not found |

Also generated: `sitemap.xml` and `robots.txt`. Submit the sitemap in Google
Search Console once the domain is attached.

## Changing listings

Everything comes from `build.py`. Edit the `PROVIDERS` or `DISCIPLINES` list at
the top, then:

```
python3 build.py
```

That regenerates every page, the sitemap, and the cross-links. Commit the
result and Cloudflare redeploys.

Set `SITE` at the top of `build.py` to your live domain before going live —
it feeds the canonical tags, og:url, and the sitemap.

## Search and filtering

The "Where" box on the home page accepts a state name, a state abbreviation,
a city, or a ZIP code, and works out which you meant. The directory rail
filters by state; city remains available as a URL filter
(`/directory/?city=Tucson`) for when a state has enough listings to need it.

Filters run client-side over the already-rendered listings, so results are
instant and the page still works with JavaScript disabled — every listing is
in the HTML. Filter state lives in the query string
(`/directory/?cat=Ayurveda&zip=85716&radius=25`), so a filtered view can be
linked or bookmarked.

Distance uses approximate coordinates entered by hand in `build.py`. Geocode
them properly before relying on radius search — a wrong coordinate silently
drops a practitioner out of nearby results.

## Notes

- The hero and About photographs are hosted locally in `public/assets/img`,
  each in three widths as both WebP and JPEG (the browser picks the smallest
  that fits). To swap either one:
  `python3 make_image.py photo.jpg hero` or `python3 make_image.py photo.jpg about 2.0`,
  then `python3 build.py`.
- The remaining images — logo, discipline tiles, the About photograph, two
  provider logos — still load from the Squarespace CDN and will stop working
  if that subscription lapses. Download them and change the `SS` constant in
  `build.py` when you migrate.
## The application form and one-click publishing

Applications no longer go to a third party. The form posts to a Cloudflare
Worker in `worker/index.js`, which:

1. validates the submission and stores it in a D1 database
2. emails the applicant an acknowledgement
3. emails **you** the full application with **Approve** and **Decline** buttons

Clicking Approve geocodes the address, commits any uploaded logo plus the
listing into `data/listings.json` in this repo, and emails the practitioner to
say their listing is live and that credentials are still being verified. The
commit triggers a Cloudflare rebuild, so the listing is a real page at its own
URL about a minute later.

`build.py` merges `data/listings.json` into `PROVIDERS` at build time. Entries
written by hand in `build.py` win if a slug appears in both. Approved listings
carry `verified: false` until you edit them, which renders a small "not yet
verified" note beside the licensure line — set it to `true` once you have
checked the number against the issuing board.

### Deploying before the backend exists

`wrangler.jsonc` ships with **no bindings**, so it deploys the static site on
its own. The full config lives in `wrangler.api.jsonc` and must not be
deployed until the database and KV namespace exist — Cloudflare fails the
build on the placeholder ids.

Until you switch it on, `/api/apply` returns a 404, the form detects that, and
falls back to opening a pre-filled email. Nothing is lost, it is just manual.

### One-time setup

```
npx wrangler d1 create findwell
npx wrangler d1 execute findwell --remote --file=schema.sql
npx wrangler kv namespace create PENDING
```

Paste the two ids into **`wrangler.api.jsonc`**, then set three secrets:

```
npx wrangler secret put RESEND_API_KEY   # resend.com, verify findwelldirectory.com
npx wrangler secret put GH_TOKEN         # GitHub fine-grained token, Contents: read+write
npx wrangler secret put SIGNING_SECRET   # any long random string
```

Finally, copy `wrangler.api.jsonc` over `wrangler.jsonc` and push. That is the
commit that turns the backend on.

`SIGNING_SECRET` signs the approve links so only your emails can publish.
Anyone with the link can approve, so treat those emails as privileged.

Two admin pages, both behind your signing secret:

- `/api/pending?key=YOUR_SIGNING_SECRET` — applications you have not decided on
- `/api/review?key=YOUR_SIGNING_SECRET` — listings published but not yet checked
  against the issuing board, each with a **Mark verified** button. Clicking it
  flips `verified` to `true` and rebuilds, removing the "not yet verified" note.

Bookmark the review page. You can also edit `data/listings.json` by hand if you
prefer — the button just saves you touching JSON.

### Favicon

The tab icon should be the leaf mark alone — a wordmark is illegible at 16px.
Run this once against the original logo PNG:

```
python3 make_favicon.py findwell-logo-trans.png
```

It trims transparent margins, finds the gap between the mark and the type,
cuts there, squares the result, and writes favicon.png (512), favicon-180.png,
favicon-32.png, favicon.ico and favicon-preview.png. Open the preview to see
how it reads at 16, 32 and 48px before pushing. If the split lands in the wrong
place, pass the fraction of the width to keep, e.g. `python3 make_favicon.py logo.png 0.28`.

`build.py` uses these automatically once they exist, and falls back to the full
logo until then.

### Logos

Applicants upload up to two images. They are held in KV until you approve,
then committed to `public/assets/img/providers/` automatically. Nothing is
kept for declined submissions. To add a logo by hand later, use
`make_logo.py` and set the `logo` field on that listing.

## Notes

- The hero and About photographs are hosted locally in `public/assets/img`,
  each in three widths as both WebP and JPEG (the browser picks the smallest
  that fits). To swap either one:
  `python3 make_image.py photo.jpg hero` or `python3 make_image.py photo.jpg about 2.0`,
  then `python3 build.py`.
- The remaining images — logo, discipline tiles, the About photograph, two
  provider logos — still load from the Squarespace CDN and will stop working
  if that subscription lapses. Download them and change the `SS` constant in
  `build.py` when you migrate.
## The application form

Submissions post to Formspree. Open `build.py`, find `FORMSPREE_ID` near the
top, and paste the code from the end of your endpoint URL — if Formspree gave
you `https://formspree.io/f/abcdwxyz`, the value is `abcdwxyz`. Then run
`python3 build.py` and push.

Until that ID is set, the form still works: it validates, then opens a
pre-filled email instead, so no application is lost. The same fallback runs
if Formspree is unreachable.

### Favicon

The tab icon should be the leaf mark alone — a wordmark is illegible at 16px.
Run this once against the original logo PNG:

```
python3 make_favicon.py findwell-logo-trans.png
```

It trims transparent margins, finds the gap between the mark and the type,
cuts there, squares the result, and writes favicon.png (512), favicon-180.png,
favicon-32.png, favicon.ico and favicon-preview.png. Open the preview to see
how it reads at 16, 32 and 48px before pushing. If the split lands in the wrong
place, pass the fraction of the width to keep, e.g. `python3 make_favicon.py logo.png 0.28`.

`build.py` uses these automatically once they exist, and falls back to the full
logo until then.

### Logos that practitioners upload

Uploaded files go to **Formspree, not to the site**. They appear as a download
link on the submission in your dashboard. To publish one:

1. Download the image from the Formspree submission.
2. `python3 make_logo.py ~/Downloads/their-logo.png provider-slug`
   — pads it to a 400px square without cropping, keeps transparency,
   and writes both PNG and WebP to `public/assets/img/providers/`.
3. In `build.py`, set that practitioner's field to
   `logo="/assets/img/providers/provider-slug.png"`.
4. `python3 build.py` and push.

Practitioners without a logo get a monogram tile built from the practice name,
so a listing never shows a broken image. Don't treat Formspree as permanent
storage — download what you intend to keep.

Field names are human-readable, so Formspree notification emails arrive
labelled ("Practice or business name: …") rather than as field codes. A hidden
honeypot field catches most spam bots. File uploads need a paid Formspree
plan; on the free tier applicants are asked to reply to the confirmation
email with their logo attached.
