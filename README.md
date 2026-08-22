# FindWell Directory — working rebuild

One self-contained file: `findwell-directory.html`. No build step, no dependencies, no server. Open it in a browser or drop it on any host.

## What works

- **Search console** — free-text search across name, practitioner, city, ZIP, credentials, training, and blurb.
- **Filter by discipline** — 11 practice types, multi-select, live counts.
- **Filter by location** — city dropdown, ZIP-radius search (5–250 mi), or "Use my location" via browser geolocation. Distance is real haversine math against each listing's coordinates.
- **Telehealth filter** and sort by name / years in practice / distance.
- **Shareable URLs** — every filter combination is encoded in the hash (`#/directory?cat=Ayurveda&near=32.25,-110.92,85716&radius=25`), so results can be linked and the back button behaves correctly.
- **Provider records** — full detail page per listing with credentials, licensure, training, years, fees, payment, insurance, contact, and a map link.
- **Join form** — client-side validation; assembles the submission into an email since there's no backend.
- Responsive to mobile, keyboard-navigable, `prefers-reduced-motion` respected.

## Editing listings

Everything lives in two arrays near the top of the `<script>` block:

- `DISCIPLINES` — the practice-type taxonomy. `key` is used in URLs, `label` is displayed, `note` is the licensure line shown on the discipline index.
- `PROVIDERS` — one object per listing. Required: `id`, `slug`, `name`, `person`, `categories`, `city`, `state`, `lat`, `lng`. Everything else renders as an em-dash if omitted.

`lat`/`lng` drive distance search — a listing without coordinates won't appear in radius results. `ZIPS` is a small lookup table of ZIP centroids; in production replace it with a geocoding call (Google Geocoding, Mapbox, or the free US Census batch geocoder).

## Going live

Static hosting works as-is: Netlify, Cloudflare Pages, GitHub Pages, S3.

To move listings off the page and into something editable by a non-developer, replace the `PROVIDERS` constant with a `fetch()` — Airtable, Google Sheets published as JSON, Sanity, or a Postgres/Supabase table all fit without changing anything else in the rendering code. Point the join form's submit handler at the same backend (or Formspree/Netlify Forms) instead of building a `mailto:`.

## Images

All 16 images from the existing site are carried over and served from the same Squarespace CDN:

- Logo (masthead), hero photograph, and the practitioners photograph in the About block
- All 11 discipline photographs, on the same photo-card layout as the original practice-type page
- Both provider logos, on their listing rows and detail pages

They're referenced through `IMG` and the `img` field on each discipline, with `src()`/`srcset()` building Squarespace's `?format=NNNw` variants — so the browser pulls a 500w file on a phone instead of the full-size original. Everything is lazy-loaded below the fold with explicit aspect ratios, so nothing shifts as images arrive.

The logo now appears in four places: the masthead, the footer (filtered to solid white so it reads on the dark band), the browser tab favicon, and the social-share card when a link is pasted into a message or post.

**Header colour is a one-word switch.** The masthead ships light, which is safe for a dark-ink logo. To flip it to the deep green, change `<header class="masthead">` to `<header class="masthead dark">` — the logo is filtered to white automatically, and the nav colours follow.

Two things to know:

1. **Functional nutrition has no photograph** on the current site, so its tile renders a labelled placeholder frame. Drop an image URL into that discipline's `img` field and it becomes a normal photo card.
2. **These are hotlinks to Squarespace.** They'll keep working while the Squarespace site is live, but if you cancel that subscription the images go with it. Before switching over, download the originals and change the `SS` constant to your own host — that one line updates every image except the masthead logo, which is hardcoded in the HTML so it can preload.

Listings for providers without a logo show a monogram tile built from the practice name, so records never render a broken image.

## Notes

- **Your two live listings are real** — Ananda Ayurveda & Yogalish and AmitaAyurveda, with the details as published on the current site. The other 13 are sample data (fictional practices, `example.org` addresses, `555` numbers), marked with a comment in the array.
- I split the food category into **Local farmers** and **Local grocers** to match your practice-type page, and moved Herbology and Counselors to your labels.
- The footer carries a line clarifying that listings are informational and not a referral or endorsement. Keep something to that effect if this goes live.
