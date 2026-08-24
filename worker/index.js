/**
 * FindWell Directory — application intake and one-click publishing.
 *
 * POST /api/apply     the join form posts here
 * GET  /api/approve   the button in your notification email
 * GET  /api/decline   the other button
 * GET  /api/pending   a plain list of anything still waiting on you
 *
 * Everything else falls through to the static site in /public.
 *
 * Approving commits the listing into data/listings.json in your repo, which
 * triggers a Cloudflare rebuild. The listing is live in about a minute, as
 * real HTML on its own URL — same as every other listing.
 */

const SCOPE_TO_KEY = {
  'Ayurveda': 'Ayurveda',
  'Acupuncture': 'Acupuncture',
  'Traditional Chinese Medicine': 'TCM',
  'Naturopathic Medicine': 'Naturopathy',
  'Chiropractic': 'Chiropractic',
  'Body Work': 'Bodywork',
  'Energy Work': 'EnergyMedicine',
  'Counseling': 'Counseling',
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

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status, headers: { 'content-type': 'application/json' },
  });
}

function page(title, body, status = 200) {
  return new Response(`<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title>
<style>body{font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
background:#f7fafa;color:#17302f;display:grid;place-items:center;min-height:100vh;margin:0;padding:2rem}
.card{background:#fff;border:1px solid #dbe3e3;border-radius:10px;padding:2rem;max-width:34rem}
h1{font-size:1.4rem;margin:0 0 .6rem}p{margin:0 0 .8rem;color:#4a5f5f}
a{color:#2e5f5c}</style></head><body><div class="card">${body}</div></body></html>`,
    { status, headers: { 'content-type': 'text/html; charset=utf-8' } });
}

// ---------------------------------------------------------------- email

async function sendEmail(env, { to, subject, html, replyTo }) {
  if (!env.RESEND_API_KEY) return { skipped: true };
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      authorization: `Bearer ${env.RESEND_API_KEY}`,
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      from: env.MAIL_FROM || 'FindWell Directory <info@findwelldirectory.com>',
      to: [to], subject, html,
      ...(replyTo ? { reply_to: replyTo } : {}),
    }),
  });
  return { ok: res.ok, status: res.status, body: await res.text() };
}

const shell = (inner) => `<div style="font:16px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#17302f;max-width:36rem">
${inner}
<p style="margin-top:2rem;padding-top:1rem;border-top:1px solid #dbe3e3;font-size:13px;color:#5f7473">
FindWell Directory — a network of holistic health care providers<br>
<a href="https://findwelldirectory.com" style="color:#2e5f5c">findwelldirectory.com</a></p></div>`;

function receivedEmail(s) {
  return shell(`<h2 style="font-size:20px;margin:0 0 12px">We have your application</h2>
<p>Thank you for applying to the FindWell Directory. We have received your details for <strong>${esc(s.practice)}</strong>.</p>
<p>We review each application and verify credentials and license numbers against the issuing board before publishing. We will email you as soon as your listing goes live, and we will only be in touch before then if we have a question.</p>
<p>If anything you sent needs correcting, just reply to this email.</p>`);
}

function publishedEmail(s, url) {
  return shell(`<h2 style="font-size:20px;margin:0 0 12px">Your listing is live</h2>
<p>Thank you for joining the FindWell Directory. Your listing for <strong>${esc(s.practice)}</strong> is now published:</p>
<p><a href="${esc(url)}" style="display:inline-block;background:#c23a4b;color:#fff;text-decoration:none;padding:10px 18px;border-radius:6px;font-weight:600">View your listing</a></p>
<p>One more step on our side: we verify credentials and license numbers against the issuing board before a listing is considered confirmed. That is usually quick, and we will contact you only if we have questions or need something clarified.</p>
<p>If anything on your listing needs correcting, reply to this email and we will fix it.</p>`);
}

function adminEmail(s, id, approveUrl, declineUrl) {
  const row = (k, v) => v
    ? `<tr><td style="padding:4px 12px 4px 0;color:#5f7473;vertical-align:top;white-space:nowrap">${esc(k)}</td><td style="padding:4px 0">${esc(v)}</td></tr>`
    : '';
  return shell(`<h2 style="font-size:20px;margin:0 0 4px">New application — ${esc(s.practice)}</h2>
<p style="margin:0 0 16px;color:#5f7473">${esc(s.first)} ${esc(s.last)} · ${esc(s.city)}, ${esc(s.state)}</p>

<p style="margin:0 0 20px">
<a href="${esc(approveUrl)}" style="display:inline-block;background:#2e5f5c;color:#fff;text-decoration:none;padding:11px 20px;border-radius:6px;font-weight:600;margin-right:8px">Approve &amp; publish</a>
<a href="${esc(declineUrl)}" style="display:inline-block;background:#fff;color:#c23a4b;border:1px solid #c23a4b;text-decoration:none;padding:10px 19px;border-radius:6px;font-weight:600">Decline</a>
</p>

<table style="border-collapse:collapse;font-size:14px">
${row('Scope', s.scope.join(', '))}
${row('Licensed', s.licensed)}
${row('License no.', s.license)}
${row('Certifications', s.certs)}
${row('Years', s.years)}
${row('Training', s.training)}
${row('Telehealth', s.telehealth)}
${row('Physical location', s.physical)}
${row('Address', s.address)}
${row('Email', s.email)}
${row('Phone', s.phone)}
${row('Website', s.website)}
${row('Social', s.social)}
${row('Payments', s.payments.join(', '))}
${row('Pricing', s.pricing)}
${row('Short description', s.short)}
${row('Description', s.long)}
${row('Logo uploaded', s.logo_name || 'none')}
</table>

<p style="margin-top:20px;padding:12px;background:#eff4f4;border-radius:6px;font-size:14px">
<strong>Internal — not published</strong><br>
Desired size: ${esc(s.size) || '—'}<br>
Open to insurance: ${esc(s.openins) || '—'}<br>
Uses an EHR: ${esc(s.ehr) || '—'}</p>

<p style="font-size:13px;color:#5f7473">Submission ${esc(id)}. Approving commits the listing to your repo and rebuilds the site — live in about a minute.</p>`);
}

// ---------------------------------------------------------------- github

async function githubGet(env, path) {
  const res = await fetch(
    `https://api.github.com/repos/${env.GH_REPO}/contents/${path}?ref=${env.GH_BRANCH || 'main'}`,
    { headers: {
      authorization: `Bearer ${env.GH_TOKEN}`,
      accept: 'application/vnd.github+json',
      'user-agent': 'findwell-worker',
    } });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`github get ${res.status}: ${await res.text()}`);
  return res.json();
}

async function githubPut(env, path, contentBase64, message, sha) {
  const res = await fetch(`https://api.github.com/repos/${env.GH_REPO}/contents/${path}`, {
    method: 'PUT',
    headers: {
      authorization: `Bearer ${env.GH_TOKEN}`,
      accept: 'application/vnd.github+json',
      'content-type': 'application/json',
      'user-agent': 'findwell-worker',
    },
    body: JSON.stringify({
      message, content: contentBase64, branch: env.GH_BRANCH || 'main', ...(sha ? { sha } : {}),
    }),
  });
  if (!res.ok) throw new Error(`github put ${res.status}: ${await res.text()}`);
  return res.json();
}

const b64encode = (str) => {
  const bytes = new TextEncoder().encode(str);
  let bin = '';
  bytes.forEach((b) => { bin += String.fromCharCode(b); });
  return btoa(bin);
};

// ---------------------------------------------------------------- geocoding

async function geocode(address) {
  if (!address) return {};
  try {
    const url = 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress'
      + `?address=${encodeURIComponent(address)}&benchmark=Public_AR_Current&format=json`;
    const res = await fetch(url, { signal: AbortSignal.timeout(6000) });
    if (!res.ok) return {};
    const data = await res.json();
    const m = data?.result?.addressMatches?.[0]?.coordinates;
    return m ? { lat: Number(m.y), lng: Number(m.x) } : {};
  } catch { return {}; }
}

// ---------------------------------------------------------------- intake

function readForm(form) {
  const g = (k) => (form.get(k) || '').toString().trim();
  const split = (k) => g(k).split(',').map((s) => s.trim()).filter(Boolean);
  return {
    first: g('First name'), last: g('Last name'), practice: g('Practice or business name'),
    email: g('email'), phone: g('Phone'), website: g('Website'), social: g('Social media'),
    physical: g('physical'), country: g('Country'),
    addr1: g('Address line 1'), addr2: g('Address line 2'),
    city: g('City'), state: g('State').toUpperCase().slice(0, 2), zip: g('ZIP code'),
    scope: split('Scope of practice'), short: g('Describe your practice'),
    licensed: g('licensed'), license: g('State(s) and license number(s)'),
    certs: g('Certificates or affiliations'), years: g('Years in practice'),
    training: g('Primary training and education'),
    payments: split('Payment methods'), pricing: g('Pricing structure'),
    telehealth: g('telehealth'), long: g('Listing description'),
    size: g('Desired size of practice'), openins: g('openins'), ehr: g('ehr'),
    honeypot: g('_gotcha'),
  };
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
  const address = s.physical === 'Yes'
    ? [s.addr1, s.addr2, `${s.city}, ${s.state} ${s.zip}`.trim()].filter(Boolean).join(', ')
    : '';
  return {
    slug: slugify(s.practice),
    name: s.practice,
    person: `${s.first} ${s.last}`.trim(),
    logo: logoPath || null,
    categories: s.scope.map((x) => SCOPE_TO_KEY[x]).filter(Boolean),
    city: s.city, state: s.state, zip: s.zip, address,
    lat: coords.lat ?? null, lng: coords.lng ?? null,
    telehealth: s.telehealth === 'Yes',
    phone: s.phone, email: s.email, website: s.website,
    social: s.social.split(/[\s,]+/).filter((u) => /^https?:/.test(u)),
    credentials: s.certs || '',
    licensure: s.licensed === 'Yes'
      ? (s.license || 'State licensed — number pending verification')
      : 'No state licensure exists for this discipline',
    training: s.training || '',
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

  // honeypot: silently accept, publish nothing
  if (s.honeypot) return json({ ok: true });

  const missing = validate(s);
  if (missing.length) return json({ ok: false, error: `Missing ${missing.join(', ')}.` }, 400);

  const id = crypto.randomUUID();

  // stash an uploaded logo until the listing is approved
  let logoName = '';
  const file = form.get('Logo or headshot');
  if (file && typeof file === 'object' && file.size > 0 && file.size <= 10 * 1024 * 1024) {
    if (/^image\/(png|jpeg|webp)$/.test(file.type)) {
      logoName = file.name || 'logo.png';
      if (env.PENDING) {
        await env.PENDING.put(`logo:${id}`, await file.arrayBuffer(), {
          expirationTtl: 60 * 60 * 24 * 90,
          metadata: { name: logoName, type: file.type },
        });
      }
    }
  }
  s.logo_name = logoName;

  await env.DB.prepare(
    `INSERT INTO submissions (id, created_at, status, payload) VALUES (?, ?, 'pending', ?)`
  ).bind(id, new Date().toISOString(), JSON.stringify(s)).run();

  const sig = await hmac(env.SIGNING_SECRET, id);
  const base = env.SITE_URL || 'https://findwelldirectory.com';
  await Promise.all([
    sendEmail(env, {
      to: env.ADMIN_EMAIL, replyTo: s.email,
      subject: `New application — ${s.practice}`,
      html: adminEmail(s, id,
        `${base}/api/approve?id=${id}&sig=${sig}`,
        `${base}/api/decline?id=${id}&sig=${sig}`),
    }),
    sendEmail(env, {
      to: s.email, subject: 'We have your FindWell Directory application',
      html: receivedEmail(s),
    }),
  ]);

  return json({ ok: true });
}

async function handleApprove(request, env) {
  const url = new URL(request.url);
  const id = url.searchParams.get('id') || '';
  const sig = url.searchParams.get('sig') || '';
  if (!timingSafeEqual(sig, await hmac(env.SIGNING_SECRET, id))) {
    return page('Invalid link', '<h1>That link is not valid</h1><p>The approve link was incomplete or has been altered. Open the original email and try again.</p>', 403);
  }

  const row = await env.DB.prepare('SELECT status, payload FROM submissions WHERE id = ?')
    .bind(id).first();
  if (!row) return page('Not found', '<h1>Not found</h1><p>No submission with that reference.</p>', 404);
  if (row.status === 'approved') {
    return page('Already published', '<h1>Already published</h1><p>This listing was approved earlier. Nothing further to do.</p>');
  }

  const s = JSON.parse(row.payload);
  const coords = await geocode(s.physical === 'Yes'
    ? `${s.addr1}, ${s.city}, ${s.state} ${s.zip}`
    : `${s.city}, ${s.state} ${s.zip}`);

  // commit the logo first so the listing can point at it
  let logoPath = null;
  if (s.logo_name && env.PENDING) {
    const obj = await env.PENDING.getWithMetadata(`logo:${id}`, { type: 'arrayBuffer' });
    if (obj && obj.value) {
      const ext = (obj.metadata?.type || '').includes('png') ? 'png'
        : (obj.metadata?.type || '').includes('webp') ? 'webp' : 'jpg';
      const path = `public/assets/img/providers/${slugify(s.practice)}.${ext}`;
      const bytes = new Uint8Array(obj.value);
      let bin = '';
      for (let i = 0; i < bytes.length; i += 8192) {
        bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 8192));
      }
      const existing = await githubGet(env, path);
      await githubPut(env, path, btoa(bin), `Logo for ${s.practice}`, existing?.sha);
      logoPath = `/assets/img/providers/${slugify(s.practice)}.${ext}`;
      await env.PENDING.delete(`logo:${id}`);
    }
  }

  // merge into data/listings.json and commit — this triggers the rebuild
  const current = await githubGet(env, 'data/listings.json');
  let listings = [];
  if (current) {
    const bin = atob(current.content.replace(/\n/g, ''));
    listings = JSON.parse(new TextDecoder().decode(
      Uint8Array.from(bin, (c) => c.charCodeAt(0))));
  }
  const listing = toListing(s, coords, logoPath);
  const idx = listings.findIndex((l) => l.slug === listing.slug);
  if (idx > -1) listings[idx] = listing; else listings.push(listing);

  await githubPut(env, 'data/listings.json',
    b64encode(JSON.stringify(listings, null, 2) + '\n'),
    `Publish listing: ${s.practice}`, current?.sha);

  await env.DB.prepare('UPDATE submissions SET status = ?, decided_at = ? WHERE id = ?')
    .bind('approved', new Date().toISOString(), id).run();

  const base = env.SITE_URL || 'https://findwelldirectory.com';
  const listingUrl = `${base}/provider/${listing.slug}/`;
  await sendEmail(env, {
    to: s.email, subject: 'Your FindWell Directory listing is live',
    html: publishedEmail(s, listingUrl),
  });

  return page('Published', `<h1>Published</h1>
<p><strong>${esc(s.practice)}</strong> has been added and the site is rebuilding. It will be live at
<a href="${esc(listingUrl)}">${esc(listingUrl)}</a> in about a minute.</p>
<p>${esc(s.first)} has been emailed to say the listing is live and that credentials are still being verified.</p>
${coords.lat ? '' : '<p style="color:#c23a4b">The address could not be geocoded, so this listing will not appear in distance searches until coordinates are added by hand.</p>'}`);
}

async function handleDecline(request, env) {
  const url = new URL(request.url);
  const id = url.searchParams.get('id') || '';
  const sig = url.searchParams.get('sig') || '';
  if (!timingSafeEqual(sig, await hmac(env.SIGNING_SECRET, id))) {
    return page('Invalid link', '<h1>That link is not valid</h1>', 403);
  }
  await env.DB.prepare('UPDATE submissions SET status = ?, decided_at = ? WHERE id = ?')
    .bind('declined', new Date().toISOString(), id).run();
  if (env.PENDING) await env.PENDING.delete(`logo:${id}`);
  return page('Declined', '<h1>Declined</h1><p>Nothing was published and no email was sent to the applicant. The submission stays in the database if you need it later.</p>');
}

async function handlePending(request, env) {
  const url = new URL(request.url);
  if (url.searchParams.get('key') !== env.SIGNING_SECRET) {
    return page('Not authorised', '<h1>Not authorised</h1>', 403);
  }
  const { results } = await env.DB.prepare(
    `SELECT id, created_at, payload FROM submissions WHERE status = 'pending' ORDER BY created_at DESC`
  ).all();
  const rows = (results || []).map((r) => {
    const s = JSON.parse(r.payload);
    return `<li><strong>${esc(s.practice)}</strong> — ${esc(s.first)} ${esc(s.last)},
      ${esc(s.city)}, ${esc(s.state)} <span style="color:#5f7473">(${esc(r.created_at.slice(0, 10))})</span></li>`;
  }).join('');
  return page('Pending applications',
    `<h1>Pending applications</h1><ul>${rows || '<li>Nothing waiting.</li>'}</ul>`);
}

// ---------------------------------------------------------------- entry

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    try {
      if (url.pathname === '/api/apply' && request.method === 'POST') return await handleApply(request, env);
      if (url.pathname === '/api/approve') return await handleApprove(request, env);
      if (url.pathname === '/api/decline') return await handleDecline(request, env);
      if (url.pathname === '/api/pending') return await handlePending(request, env);
    } catch (err) {
      console.error(err);
      if (url.pathname.startsWith('/api/apply')) {
        return json({ ok: false, error: 'Something went wrong on our side.' }, 500);
      }
      return page('Error', `<h1>Something went wrong</h1><p>${esc(err.message)}</p>`, 500);
    }
    return env.ASSETS.fetch(request);
  },
};
