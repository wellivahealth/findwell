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
| `/articles/` | Article index (empty until you add one) |
| `/articles/<slug>/` | One page per article |
| `/advertise/` | Advertising and partnerships |
| `/about/` | Who we are |
| `/404.html` | Not found |

Also generated: `sitemap.xml` and `robots.txt`. Submit the sitemap in Google
Search Console once the domain is attached.

## Marking a listing as board-confirmed

Use the review page — no code editing:

```
findwelldirectory.com/api/review?key=YOUR_SIGNING_SECRET
```

Every listing still published "as reported" appears with a link straight to the
right board for its discipline and state, and a form already filled in with the
credential text, the board's name and today's date. Open the board in a new tab,
check the number, come back, press **Mark confirmed**. The listing updates and
is live in about a minute.

The source field is required. A confirmation with no named source is refused —
that is the whole point of the statement.

Listings written by hand in `PROVIDERS` inside `build.py` are not editable from
that page; give them a `verification` field directly:

```python
verification={"what": "License AZ LAC-010717 confirmed",
              "source": "the Arizona Acupuncture Board of Examiners",
              "date": "25 Aug 2026"},
```

To add boards for new states or disciplines, edit `BOARDS` at the top of
`worker/index.js`.

## Never overwrite data/listings.json

`data/listings.json` holds every listing published through the Approve button.
It lives only in the repo — it is the live database.

**Update zips do not contain it, on purpose.** If a zip included it, copying the
files in would wipe listings that were approved since the zip was made. When
updating, replace `public/`, `worker/`, `build.py` and `wrangler.jsonc`, and
leave `data/` alone.

If the file is ever missing, `build.py` carries on without it and the site
shows only the listings written by hand in `PROVIDERS`.

## Writing an article

Add an entry to the `ARTICLES` list in `build.py`, newest first:

```python
dict(slug="choosing-an-acupuncturist",
     title="How to choose an acupuncturist",
     date="2026-09-01", author="Amita Nathwani",
     summary="What to ask before a first appointment.",
     body="<p>First paragraph.</p><h2>A heading</h2><p>More.</p>")
```

`body` is raw HTML — `<p>`, `<h2>`, `<ul>`, `<blockquote>` are all styled. Run
`build.py` and the index page, the article page and the sitemap all update. The
index shows an empty state until the first entry exists.

## Integrative & functional medicine

This category is gated on licensure: MD, DO, NP or PA. "Functional medicine"
is a method rather than a licence class, so admitting it as its own category
would put a physician and a weekend-certified coach side by side. Keeping the
gate on the licence and publishing the training separately avoids that.

Listings in this category carry an extra record line, **Integrative training**.
If the applicant reports none, the line reads "None reported" rather than being
hidden — the absence is the information. The field is `integrative_training`
on the listing.

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

### How requests are routed

`run_worker_first: ["/api/*"]` in `wrangler.jsonc` is load-bearing. Without it,
Cloudflare's asset router answers GET requests before the Worker runs, so every
`/api/` link — approve, decline, review, verify, selftest — returns the 404
page. POST requests still reach the Worker, which makes the symptom confusing:
the form errors while the email buttons silently 404.

### The build command (required for publishing to work)

Cloudflare must run the site generator on every deploy, otherwise approving a
listing writes `data/listings.json` and nothing regenerates the HTML.

Cloudflare dashboard -> Workers & Pages -> findwell -> Settings -> Build:

- **Build command:** `python3 build.py`
- **Deploy command:** `npx wrangler deploy` (the default)

`build.py` uses only the Python standard library, so nothing needs installing.

### Turning it on — three secrets, no database

```
npx wrangler secret put RESEND_API_KEY   # resend.com; verify findwelldirectory.com for sending
npx wrangler secret put GH_TOKEN         # GitHub fine-grained token, Contents: read + write
npx wrangler secret put SIGNING_SECRET   # any long random string you invent
```

Then push. `wrangler.jsonc` already points at `worker/index.js`, so the
backend comes up with the deploy.

If a secret is missing the Worker still deploys — the form just falls back to
opening a pre-filled email, and `/api/selftest?key=YOUR_SIGNING_SECRET` will
tell you which piece is missing.

There is nothing else to create — no database, no namespace, no ids to paste.
The Worker keeps everything in this repo through the GitHub API: a submission
lands in `data/pending/`, approving moves it into `data/listings.json` and the
logo into `public/assets/img/providers/`. Each action is a single commit, so
Cloudflare rebuilds once per decision.

`SIGNING_SECRET` signs the approve links so only your emails can publish.
Anyone holding a link can approve, so treat those emails as privileged.

Admin pages, both behind that secret:

- `/api/pending?key=YOUR_SIGNING_SECRET` — applications awaiting a decision
- `/api/review?key=YOUR_SIGNING_SECRET` — published listings not yet credential-checked
- `/api/selftest?key=YOUR_SIGNING_SECRET` — checks every dependency and names
  whatever is broken; also sends a test email to ADMIN_EMAIL

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

### Discipline tile images

Tiles are 4:3. To add or replace one:

```
python3 make_tile.py photo.jpg integrative 0.72 0.61 0.70
```

The three numbers are the centre of interest as fractions of width and height,
and a zoom factor (1.0 is the widest possible crop, lower crops in tighter).
Wide stock photographs usually need both — the default centre crop leaves the
subject off to one side with dead space beside it.

It writes 500/750/1000px JPEG and WebP to `public/assets/img/disciplines/`.
Then set that discipline's `img` to the stem, without a width or extension:

```python
img="/assets/img/disciplines/integrative"
```

Disciplines with `img=None` render a labelled placeholder frame instead.

### Social share card

The image shown when a link is pasted into Slack, iMessage, LinkedIn or X.
1200x630, built from the hero photograph and the logo:

```
python3 make_card.py
```

Writes `public/assets/img/share-card.jpg`. Re-run it after changing the hero
image or the logo, then `build.py`. Every page uses the same card; if you ever
want per-listing cards, the same script can be extended.

Twitter/X is set to `summary_large_image`, so the card renders full width
rather than as a thumbnail.

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
