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
| `/locations/` | City index |
| `/locations/tucson-az/` etc. | One page per city, pre-filtered |
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

Filters run client-side over the already-rendered listings, so results are
instant and the page still works with JavaScript disabled — every listing is
in the HTML. Filter state lives in the query string
(`/directory/?cat=Ayurveda&zip=85716&radius=25`), so a filtered view can be
linked or bookmarked.

Distance uses approximate coordinates entered by hand in `build.py`. Geocode
them properly before relying on radius search — a wrong coordinate silently
drops a practitioner out of nearby results.

## Notes

- All images still load from the Squarespace CDN. They will stop working if
  that subscription lapses. Download the originals and change the `SS`
  constant in `build.py` when you migrate.
- The join form has no backend; it assembles a mailto. Point it at a form
  service to collect submissions directly.
