/**
 * FindWell Directory — application intake and one-click publishing.
 *
 * POST /api/apply     the join form posts here
 * GET  /api/approve   the button in your notification email
 * GET  /api/decline   the other button
 * GET  /api/pending   applications still waiting on you
 * GET  /api/review    published listings not yet credential-checked
 * GET  /api/verify    marks one of those verified
 *
 * Everything else falls through to the static site in /public.
 *
 * There is no database. A submission is committed to data/pending/ in the
 * repo; approving moves it into data/listings.json and moves any logo into
 * public/assets/img/providers/. Each action is one commit, so Cloudflare
 * rebuilds once and the listing is live in about a minute.
 *
 * That keeps the setup to three secrets — no D1, no KV, no binding ids.
 */

const SCOPE_TO_KEY = {
  'Ayurveda': 'Ayurveda',
  'Acupuncture': 'Acupuncture',
  'Traditional Chinese Medicine': 'TCM',
  'Naturopathic Medicine': 'Naturopathy',
  'Chiropractic': 'Chiropractic',
  'Body Work': 'Bodywork',
  'Energy Work': 'EnergyMedicine',
  'Integrative / Functional Medicine': 'IntegrativeMedicine',
  'Counseling': 'Counseling',
  'Health & Wellness Coaching': 'Coaching',
  'Herbalism': 'Herbalism',
  'Farmer': 'Farms',
  'Grocer': 'Grocers',
};

// ---------------------------------------------------------------- helpers

const esc = (s) => String(s ?? '').replace(/[&<>"']/g,
  (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function slugify(s) {
  return String(s || '').toLowerCase().normalize('NFKD')
    .replace(/[^\w\s-]/g, '').trim().replace(/\s+/g, '-').replace(/-+/g, '-').slice(0, 60);
}

async function hmac(secret, message) {
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(message));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

function safeEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}

/**
 * Compare a ?key= value against SIGNING_SECRET.
 * Base64 secrets contain "+", and a "+" in a query string decodes to a space,
 * so it is put back. Whitespace at either end is ignored — a trailing newline
 * pasted into the dashboard is otherwise invisible and breaks every check.
 */
function keyOk(url, env) {
  const provided = (url.searchParams.get('key') || '').trim().replace(/ /g, '+');
  const expected = (env.SIGNING_SECRET || '').trim();
  return { ok: !!expected && safeEqual(provided, expected),
           got: provided.length, want: expected.length };
}

const json = (data, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { 'content-type': 'application/json' },
});

function page(title, body, status = 200) {
  return new Response(`<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title>
<style>body{font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
background:#f7fafa;color:#17302f;display:grid;place-items:center;min-height:100vh;margin:0;padding:2rem}
.card{background:#fff;border:1px solid #dbe3e3;border-radius:10px;padding:2rem;max-width:34rem}
h1{font-size:1.4rem;margin:0 0 .6rem}p{margin:0 0 .8rem;color:#4a5f5f}a{color:#2e5f5c}
ul{padding-left:0;list-style:none}</style></head><body><div class="card">${body}</div></body></html>`,
    { status, headers: { 'content-type': 'text/html; charset=utf-8' } });
}

const b64 = (str) => {
  const bytes = new TextEncoder().encode(str);
  let bin = '';
  bytes.forEach((b) => { bin += String.fromCharCode(b); });
  return btoa(bin);
};

const b64bytes = (buf) => {
  const bytes = new Uint8Array(buf);
  let bin = '';
  for (let i = 0; i < bytes.length; i += 8192) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 8192));
  }
  return btoa(bin);
};

const fromB64 = (s) => new TextDecoder().decode(
  Uint8Array.from(atob(String(s).replace(/\n/g, '')), (c) => c.charCodeAt(0)));

// ---------------------------------------------------------------- github

function gh(env, path, init = {}) {
  return fetch(`https://api.github.com${path}`, {
    ...init,
    headers: {
      authorization: `Bearer ${env.GH_TOKEN}`,
      accept: 'application/vnd.github+json',
      'user-agent': 'findwell-worker',
      ...(init.body ? { 'content-type': 'application/json' } : {}),
      ...(init.headers || {}),
    },
  });
}

async function ghJson(env, path, init) {
  const res = await gh(env, path, init);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`GitHub ${path} ${res.status}: ${(await res.text()).slice(0, 300)}`);
  return res.json();
}

async function readFile(env, path) {
  const branch = env.GH_BRANCH || 'main';
  return ghJson(env, `/repos/${env.GH_REPO}/contents/${encodeURI(path)}?ref=${branch}`);
}

/**
 * Write and delete several files in one commit, so Cloudflare rebuilds once.
 * files: [{ path, contentBase64 }] or [{ path, remove: true }]
 */
async function commitFiles(env, message, files) {
  const repo = env.GH_REPO;
  const branch = env.GH_BRANCH || 'main';

  const ref = await ghJson(env, `/repos/${repo}/git/ref/heads/${branch}`);
  const headSha = ref.object.sha;
  const head = await ghJson(env, `/repos/${repo}/git/commits/${headSha}`);

  const tree = [];
  for (const f of files) {
    if (f.remove) {
      tree.push({ path: f.path, mode: '100644', type: 'blob', sha: null });
      continue;
    }
    const blob = await ghJson(env, `/repos/${repo}/git/blobs`, {
      method: 'POST',
      body: JSON.stringify({ content: f.contentBase64, encoding: 'base64' }),
    });
    tree.push({ path: f.path, mode: '100644', type: 'blob', sha: blob.sha });
  }

  const newTree = await ghJson(env, `/repos/${repo}/git/trees`, {
    method: 'POST',
    body: JSON.stringify({ base_tree: head.tree.sha, tree }),
  });
  const commit = await ghJson(env, `/repos/${repo}/git/commits`, {
    method: 'POST',
    body: JSON.stringify({ message, tree: newTree.sha, parents: [headSha] }),
  });
  await ghJson(env, `/repos/${repo}/git/refs/heads/${branch}`, {
    method: 'PATCH',
    body: JSON.stringify({ sha: commit.sha }),
  });
  return commit.sha;
}

// ---------------------------------------------------------------- email

async function sendEmail(env, { to, subject, html, replyTo }) {
  if (!env.RESEND_API_KEY || !to) return { skipped: true };
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      authorization: `Bearer ${env.RESEND_API_KEY}`,
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      from: env.MAIL_FROM || 'FindWell Directory <noreply@findwelldirectory.com>',
      to: [to], subject, html,
      // Always replyable: MAIL_FROM may be a noreply address, so point
      // replies at a mailbox someone actually reads.
      reply_to: replyTo || env.ADMIN_EMAIL || undefined,
    }),
  });
  return { ok: res.ok, status: res.status };
}

const shell = (inner) => `<div style="font:16px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#17302f;max-width:36rem">
${inner}
<p style="margin-top:2rem;padding-top:1rem;border-top:1px solid #dbe3e3;font-size:13px;color:#5f7473">
FindWell Directory — a network of holistic health care providers<br>
<a href="https://findwelldirectory.com" style="color:#2e5f5c">findwelldirectory.com</a></p></div>`;

const receivedEmail = (s) => shell(`<h2 style="font-size:20px;margin:0 0 12px">We have your application</h2>
<p>Thank you for applying to the FindWell Directory. We have your details for <strong>${esc(s.practice)}</strong>.</p>
<p>We review each application and check credentials and license numbers against the issuing board before publishing. We will email you as soon as your listing is live, and will only be in touch before then if we have a question.</p>
<p>If anything you sent needs correcting, just reply to this email.</p>`);

const publishedEmail = (s, url) => shell(`<h2 style="font-size:20px;margin:0 0 12px">Your listing is live</h2>
<p>Thank you for joining the FindWell Directory. Your listing for <strong>${esc(s.practice)}</strong> is now published:</p>
<p><a href="${esc(url)}" style="display:inline-block;background:#c23a4b;color:#fff;text-decoration:none;padding:10px 18px;border-radius:6px;font-weight:600">View your listing</a></p>
<p>One more step on our side: we verify credentials and license numbers against the issuing board before a listing is considered confirmed. That is usually quick, and we will contact you only if we have questions or need something clarified.</p>
<p>If anything on your listing needs correcting, reply to this email and we will fix it.</p>`);

function adminEmail(s, approveUrl, declineUrl) {
  const row = (k, v) => v
    ? `<tr><td style="padding:4px 12px 4px 0;color:#5f7473;vertical-align:top;white-space:nowrap">${esc(k)}</td><td style="padding:4px 0">${esc(v)}</td></tr>`
    : '';
  return shell(`<h2 style="font-size:20px;margin:0 0 4px">New application — ${esc(s.practice)}</h2>
<p style="margin:0 0 16px;color:#5f7473">${esc(s.first)} ${esc(s.last)} · ${esc(s.city)}, ${esc(s.state)}</p>
<p style="margin:0 0 20px">
<a href="${esc(approveUrl)}" style="display:inline-block;background:#2e5f5c;color:#fff;text-decoration:none;padding:11px 20px;border-radius:6px;font-weight:600;margin-right:8px">Approve &amp; publish</a>
<a href="${esc(declineUrl)}" style="display:inline-block;background:#fff;color:#c23a4b;border:1px solid #c23a4b;text-decoration:none;padding:10px 19px;border-radius:6px;font-weight:600">Decline</a></p>
<table style="border-collapse:collapse;font-size:14px">
${row('Scope', s.scope.join(', '))}
${row('Licensed', s.licensed)}${row('License no.', s.license)}
${row('Certifications', s.certs)}${row('Years', s.years)}
${row('Training', s.training)}
${row('Integrative training', s.integrative || 'none reported')}
${row('Telehealth', s.telehealth)}${row('Physical location', s.physical)}
${row('Address', s.address)}
${row('Email', s.email)}${row('Phone', s.phone)}${row('Website', s.website)}
${row('Social', s.social)}
${row('Payments', s.payments.join(', '))}${row('Pricing', s.pricing)}
${row('Short description', s.short)}${row('Description', s.long)}
${row('Logo uploaded', s.logo_name || 'none')}
${row('Attested accurate', s.attestation ? 'Yes' : 'NOT TICKED')}
</table>
<p style="margin-top:20px;padding:12px;background:#eff4f4;border-radius:6px;font-size:14px">
<strong>Internal — not published</strong><br>
Desired size: ${esc(s.size) || '—'}<br>
Open to insurance: ${esc(s.openins) || '—'}<br>
Uses an EHR: ${esc(s.ehr) || '—'}</p>
<p style="font-size:13px;color:#5f7473">Approving publishes the listing and rebuilds the site — live in about a minute.</p>`);
}

// ---------------------------------------------------------------- geocode

async function geocode(address) {
  if (!address) return {};
  try {
    const url = 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress'
      + `?address=${encodeURIComponent(address)}&benchmark=Public_AR_Current&format=json`;
    const res = await fetch(url, { signal: AbortSignal.timeout(6000) });
    if (!res.ok) return {};
    const m = (await res.json())?.result?.addressMatches?.[0]?.coordinates;
    return m ? { lat: Number(m.y), lng: Number(m.x) } : {};
  } catch { return {}; }
}

// ---------------------------------------------------------------- intake

function readForm(form) {
  const g = (k) => (form.get(k) || '').toString().trim();
  const split = (k) => g(k).split(',').map((s) => s.trim()).filter(Boolean);
  const s = {
    first: g('First name'), last: g('Last name'), practice: g('Practice or business name'),
    email: g('email'), phone: g('Phone'), website: g('Website'), social: g('Social media'),
    physical: g('physical'), country: g('Country'),
    addr1: g('Address line 1'), addr2: g('Address line 2'),
    city: g('City'), state: g('State').toUpperCase().slice(0, 2), zip: g('ZIP code'),
    scope: split('Scope of practice'), short: g('Describe your practice'),
    licensed: g('licensed'), license: g('State(s) and license number(s)'),
    certs: g('Certificates or affiliations'), years: g('Years in practice'),
    training: g('Primary training and education'), integrative: g('Integrative training'),
    payments: split('Payment methods'), pricing: g('Pricing structure'),
    telehealth: g('telehealth'), long: g('Listing description'),
    size: g('Desired size of practice'), openins: g('openins'), ehr: g('ehr'),
    attestation: g('Attestation'),
    honeypot: g('_gotcha'),
  };
  s.address = s.physical === 'Yes'
    ? [s.addr1, s.addr2, `${s.city}, ${s.state} ${s.zip}`.trim()].filter(Boolean).join(', ')
    : '';
  return s;
}

function validate(s) {
  const missing = [];
  for (const [k, label] of [['first', 'first name'], ['last', 'last name'],
    ['practice', 'practice name'], ['email', 'email'], ['city', 'city'], ['state', 'state']]) {
    if (!s[k]) missing.push(label);
  }
  if (s.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(s.email)) missing.push('a valid email');
  if (!s.scope.length) missing.push('scope of practice');
  return missing;
}

function toListing(s, coords, logoPath) {
  const year = new Date().getFullYear();
  const years = parseInt(s.years, 10);
  return {
    slug: slugify(s.practice),
    name: s.practice,
    person: `${s.first} ${s.last}`.trim(),
    logo: logoPath || null,
    categories: s.scope.map((x) => SCOPE_TO_KEY[x]).filter(Boolean),
    city: s.city, state: s.state, zip: s.zip, address: s.address,
    lat: coords.lat ?? null, lng: coords.lng ?? null,
    telehealth: s.telehealth === 'Yes',
    phone: s.phone, email: s.email, website: s.website,
    social: s.social.split(/[\s,]+/).filter((u) => /^https?:/.test(u)),
    credentials: s.certs || '',
    licensure: s.licensed === 'Yes'
      ? (s.license || 'State licensed — number pending verification')
      : 'No state licensure exists for this discipline',
    training: s.training || '',
    integrative_training: s.integrative || '',
    since: Number.isFinite(years) && years > 0 && years < 90 ? year - years : null,
    affiliations: s.certs || '—',
    pricing: s.pricing || '—',
    payments: s.payments.join(', ') || '—',
    insurance: s.payments.includes('Insurance')
      ? 'Accepted — verify your plan with the practice' : 'Not accepted',
    blurb: s.short || '',
    long: s.long || '',
    verified: false,
  };
}

// ---------------------------------------------------------------- routes

async function handleApply(request, env) {
  const form = await request.formData();
  const s = readForm(form);
  if (s.honeypot) return json({ ok: true });              // bot: accept, store nothing

  const missing = validate(s);
  if (missing.length) return json({ ok: false, error: `Missing ${missing.join(', ')}.` }, 400);

  const id = `${new Date().toISOString().slice(0, 10)}-${slugify(s.practice) || 'application'}`;
  const files = [];

  const file = form.get('Logo or headshot');
  if (file && typeof file === 'object' && file.size > 0 && file.size <= 10 * 1024 * 1024
      && /^image\/(png|jpeg|webp)$/.test(file.type)) {
    const ext = file.type.includes('png') ? 'png' : file.type.includes('webp') ? 'webp' : 'jpg';
    s.logo_name = file.name || `logo.${ext}`;
    s.logo_ext = ext;
    files.push({
      path: `data/pending/${id}-logo.${ext}`,
      contentBase64: b64bytes(await file.arrayBuffer()),
    });
  }

  s.received_at = new Date().toISOString();
  files.push({ path: `data/pending/${id}.json`, contentBase64: b64(JSON.stringify(s, null, 2)) });

  await commitFiles(env, `Application: ${s.practice}`, files);

  const sig = await hmac((env.SIGNING_SECRET || '').trim(), id);
  const base = env.SITE_URL || 'https://findwelldirectory.com';
  await Promise.all([
    sendEmail(env, {
      to: env.ADMIN_EMAIL, replyTo: s.email,
      subject: `New application — ${s.practice}`,
      html: adminEmail(s,
        `${base}/api/approve?id=${encodeURIComponent(id)}&sig=${sig}`,
        `${base}/api/decline?id=${encodeURIComponent(id)}&sig=${sig}`),
    }),
    sendEmail(env, {
      to: s.email,
      subject: 'We have your FindWell Directory application',
      html: receivedEmail(s),
    }),
  ]);

  return json({ ok: true });
}

async function handleApprove(request, env) {
  const url = new URL(request.url);
  const id = url.searchParams.get('id') || '';
  if (!safeEqual((url.searchParams.get('sig') || '').trim(), await hmac((env.SIGNING_SECRET || '').trim(), id))) {
    return page('Invalid link',
      '<h1>That link is not valid</h1><p>Open the original email and press the button again.</p>', 403);
  }

  const pending = await readFile(env, `data/pending/${id}.json`);
  if (!pending) {
    return page('Already handled',
      '<h1>Nothing to do</h1><p>This application has already been approved or declined.</p>');
  }
  const s = JSON.parse(fromB64(pending.content));
  const slug = slugify(s.practice);
  const files = [];

  let logoPath = null;
  if (s.logo_ext) {
    const src = await readFile(env, `data/pending/${id}-logo.${s.logo_ext}`);
    if (src) {
      logoPath = `/assets/img/providers/${slug}.${s.logo_ext}`;
      files.push({
        path: `public/assets/img/providers/${slug}.${s.logo_ext}`,
        contentBase64: src.content.replace(/\n/g, ''),
      });
      files.push({ path: `data/pending/${id}-logo.${s.logo_ext}`, remove: true });
    }
  }

  const coords = await geocode(s.address || `${s.city}, ${s.state} ${s.zip}`);

  const current = await readFile(env, 'data/listings.json');
  const listings = current ? JSON.parse(fromB64(current.content)) : [];
  const listing = toListing(s, coords, logoPath);
  const idx = listings.findIndex((l) => l.slug === listing.slug);
  if (idx > -1) listings[idx] = listing; else listings.push(listing);

  files.push({
    path: 'data/listings.json',
    contentBase64: b64(JSON.stringify(listings, null, 2) + '\n'),
  });
  files.push({ path: `data/pending/${id}.json`, remove: true });

  await commitFiles(env, `Publish listing: ${s.practice}`, files);

  const base = env.SITE_URL || 'https://findwelldirectory.com';
  const listingUrl = `${base}/provider/${listing.slug}/`;
  await sendEmail(env, {
    to: s.email,
    subject: 'Your FindWell Directory listing is live',
    html: publishedEmail(s, listingUrl),
  });

  return page('Published', `<h1>Published</h1>
<p><strong>${esc(s.practice)}</strong> has been added and the site is rebuilding. It will be live at
<a href="${esc(listingUrl)}">${esc(listingUrl)}</a> in about a minute.</p>
<p>${esc(s.first)} has been emailed to say the listing is live and that credentials are still being verified.</p>
${logoPath ? '<p>Their logo was published with it.</p>' : ''}
${coords.lat ? '' : '<p style="color:#c23a4b">The address could not be geocoded, so this listing will not appear in distance searches until coordinates are added by hand.</p>'}
<p style="font-size:14px"><a href="${base}/api/review?key=${encodeURIComponent(env.SIGNING_SECRET)}">Mark it verified</a> once you have checked the licence number.</p>`);
}

async function handleDecline(request, env) {
  const url = new URL(request.url);
  const id = url.searchParams.get('id') || '';
  if (!safeEqual((url.searchParams.get('sig') || '').trim(), await hmac((env.SIGNING_SECRET || '').trim(), id))) {
    return page('Invalid link', '<h1>That link is not valid</h1>', 403);
  }
  const pending = await readFile(env, `data/pending/${id}.json`);
  if (!pending) return page('Already handled', '<h1>Nothing to do</h1><p>Already approved or declined.</p>');
  const s = JSON.parse(fromB64(pending.content));

  const files = [{ path: `data/pending/${id}.json`, remove: true }];
  if (s.logo_ext) files.push({ path: `data/pending/${id}-logo.${s.logo_ext}`, remove: true });
  await commitFiles(env, `Decline application: ${s.practice}`, files);

  return page('Declined',
    '<h1>Declined</h1><p>Nothing was published and no email was sent to the applicant.</p>');
}

async function handlePending(request, env) {
  const url = new URL(request.url);
  if (!keyOk(url, env).ok) return page('Not authorised', '<h1>Not authorised</h1>', 403);
  const dir = await readFile(env, 'data/pending');
  const files = Array.isArray(dir) ? dir.filter((f) => f.name.endsWith('.json')) : [];
  const base = env.SITE_URL || 'https://findwelldirectory.com';
  const rows = await Promise.all(files.map(async (f) => {
    const id = f.name.replace(/\.json$/, '');
    const sig = await hmac((env.SIGNING_SECRET || '').trim(), id);
    return `<li style="padding:10px 0;border-top:1px solid #dbe3e3">${esc(id)}
      &nbsp;<a href="${base}/api/approve?id=${encodeURIComponent(id)}&sig=${sig}">approve</a>
      &nbsp;<a href="${base}/api/decline?id=${encodeURIComponent(id)}&sig=${sig}">decline</a></li>`;
  }));
  return page('Pending applications',
    `<h1>Pending applications</h1><ul>${rows.join('') || '<li>Nothing waiting.</li>'}</ul>`);
}

async function handleReview(request, env) {
  const url = new URL(request.url);
  if (!keyOk(url, env).ok) return page('Not authorised', '<h1>Not authorised</h1>', 403);
  const current = await readFile(env, 'data/listings.json');
  const listings = current ? JSON.parse(fromB64(current.content)) : [];
  const waiting = listings.filter((l) => l.verified === false);
  const base = env.SITE_URL || 'https://findwelldirectory.com';
  const rows = await Promise.all(waiting.map(async (l) => {
    const sig = await hmac((env.SIGNING_SECRET || '').trim(), 'verify:' + l.slug);
    return `<li style="padding:12px 0;border-top:1px solid #dbe3e3">
      <strong>${esc(l.name)}</strong> — ${esc(l.person)}<br>
      <span style="color:#5f7473;font-size:14px">${esc(l.licensure)}</span><br>
      <a href="${base}/provider/${esc(l.slug)}/" style="font-size:14px">view listing</a> ·
      <a href="${base}/api/verify?slug=${encodeURIComponent(l.slug)}&sig=${sig}"
         style="display:inline-block;background:#2e5f5c;color:#fff;text-decoration:none;padding:5px 12px;border-radius:5px;font-size:14px;font-weight:600">Mark verified</a></li>`;
  }));
  return page('Awaiting verification', `<h1>Awaiting verification</h1>
<p>Published, but not yet checked against the issuing board.</p>
<ul style="margin:1rem 0 0">${rows.join('') || '<li style="padding:12px 0">Everything is verified.</li>'}</ul>`);
}

async function handleVerify(request, env) {
  const url = new URL(request.url);
  const slug = url.searchParams.get('slug') || '';
  if (!safeEqual((url.searchParams.get('sig') || '').trim(), await hmac((env.SIGNING_SECRET || '').trim(), 'verify:' + slug))) {
    return page('Invalid link', '<h1>That link is not valid</h1>', 403);
  }
  const current = await readFile(env, 'data/listings.json');
  const listings = current ? JSON.parse(fromB64(current.content)) : [];
  const row = listings.find((l) => l.slug === slug);
  if (!row) return page('Not found', '<h1>Not found</h1>', 404);
  if (row.verified === true) return page('Already verified', '<h1>Already verified</h1>');
  row.verified = true;
  await commitFiles(env, `Mark verified: ${row.name}`,
    [{ path: 'data/listings.json', contentBase64: b64(JSON.stringify(listings, null, 2) + '\n') }]);
  return page('Verified', `<h1>Verified</h1>
<p><strong>${esc(row.name)}</strong> is marked verified. The note will be gone in about a minute.</p>`);
}

// ---------------------------------------------------------------- selftest

/** Checks each dependency in turn and reports exactly which one fails. */
async function handleSelftest(request, env) {
  const url = new URL(request.url);
  const k = keyOk(url, env);
  if (!k.ok) {
    return page('Not authorised', `<h1>Not authorised</h1>
<p>The key in the URL does not match SIGNING_SECRET on the Worker.</p>
<p style="font-size:14px">Received ${k.got} characters; the Worker holds ${k.want}.
${k.want === 0 ? 'The Worker has no SIGNING_SECRET set at all — add it under Settings, Variables and Secrets.'
  : k.got === 0 ? 'No key was supplied in the URL.'
  : k.got === k.want ? 'Same length, so one or more characters differ — re-copy it.'
  : 'Different lengths, so the value was cut short or has something extra on the end.'}</p>`, 403);
  }

  const checks = [];
  const add = (name, ok, detail) => checks.push({ name, ok, detail });

  add('SIGNING_SECRET set', !!env.SIGNING_SECRET, '');
  add('GH_TOKEN set', !!env.GH_TOKEN, '');
  add('RESEND_API_KEY set', !!env.RESEND_API_KEY, '');
  add('GH_REPO', !!env.GH_REPO, env.GH_REPO || 'missing');
  add('ADMIN_EMAIL', !!env.ADMIN_EMAIL, env.ADMIN_EMAIL || 'missing');
  add('MAIL_FROM', !!env.MAIL_FROM, env.MAIL_FROM || 'default');

  // can the token see the repository at all?
  try {
    const res = await gh(env, `/repos/${env.GH_REPO}`);
    if (res.ok) {
      const r = await res.json();
      add('GitHub: repo visible', true, `${r.full_name}, default branch ${r.default_branch}`);
      add('GitHub: branch matches', (env.GH_BRANCH || 'main') === r.default_branch,
        `worker uses "${env.GH_BRANCH || 'main'}", repo default is "${r.default_branch}"`);
    } else {
      const body = (await res.text()).slice(0, 200);
      add('GitHub: repo visible', false, `HTTP ${res.status}. ${
        res.status === 404
          ? 'Either GH_REPO is wrong, or the fine-grained token has not been granted access to this repository. If the repo belongs to an organisation, an org owner must approve the token.'
          : res.status === 401 ? 'Token rejected — expired or mistyped.' : body}`);
    }
  } catch (e) { add('GitHub: repo visible', false, e.message); }

  // can it write? create a blob without committing anything
  try {
    const res = await gh(env, `/repos/${env.GH_REPO}/git/blobs`, {
      method: 'POST', body: JSON.stringify({ content: 'selftest', encoding: 'utf-8' }),
    });
    add('GitHub: write permission', res.ok, res.ok
      ? 'Contents: read and write confirmed'
      : `HTTP ${res.status} — the token needs Repository permissions -> Contents -> Read and write.`);
  } catch (e) { add('GitHub: write permission', false, e.message); }

  // is the listings file readable and valid?
  try {
    const f = await readFile(env, 'data/listings.json');
    if (!f) add('data/listings.json', false, 'Not found in the repo.');
    else {
      const parsed = JSON.parse(fromB64(f.content));
      add('data/listings.json', true, `${parsed.length} listing(s)`);
    }
  } catch (e) { add('data/listings.json', false, e.message); }

  // will Resend accept a send?
  try {
    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { authorization: `Bearer ${env.RESEND_API_KEY}`, 'content-type': 'application/json' },
      body: JSON.stringify({
        from: env.MAIL_FROM || 'FindWell Directory <noreply@findwelldirectory.com>',
        to: [env.ADMIN_EMAIL], subject: 'FindWell selftest',
        html: '<p>If you are reading this, sending works.</p>',
      }),
    });
    const body = (await res.text()).slice(0, 300);
    add('Resend: send test email', res.ok, res.ok
      ? `Sent to ${env.ADMIN_EMAIL} — check that inbox.`
      : `HTTP ${res.status}. ${body}`);
  } catch (e) { add('Resend: send test email', false, e.message); }

  const rows = checks.map((c) => `<li style="padding:8px 0;border-top:1px solid #dbe3e3">
    <strong style="color:${c.ok ? '#2e5f5c' : '#c23a4b'}">${c.ok ? 'PASS' : 'FAIL'}</strong>
    &nbsp;${esc(c.name)}${c.detail ? `<br><span style="font-size:14px;color:#5f7473">${esc(c.detail)}</span>` : ''}
  </li>`).join('');
  const failed = checks.filter((c) => !c.ok).length;
  return page('Self test', `<h1>Self test</h1>
<p>${failed ? `${failed} check(s) failed — the first failure is usually the cause.` : 'Everything passed.'}</p>
<ul style="margin:0">${rows}</ul>`);
}

// ---------------------------------------------------------------- entry

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    try {
      if (url.pathname === '/api/apply' && request.method === 'POST') return await handleApply(request, env);
      if (url.pathname === '/api/approve') return await handleApprove(request, env);
      if (url.pathname === '/api/decline') return await handleDecline(request, env);
      if (url.pathname === '/api/pending') return await handlePending(request, env);
      if (url.pathname === '/api/selftest') return await handleSelftest(request, env);
      if (url.pathname === '/api/review') return await handleReview(request, env);
      if (url.pathname === '/api/verify') return await handleVerify(request, env);
    } catch (err) {
      console.error(err);
      if (url.pathname === '/api/apply') {
        return json({ ok: false, error: `Server error: ${String(err.message).slice(0, 160)}` }, 500);
      }
      return page('Error', `<h1>Something went wrong</h1><p>${esc(err.message)}</p>`, 500);
    }
    return env.ASSETS.fetch(request);
  },
};
