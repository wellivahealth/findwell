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

/** "Arizona" truncated to two characters is "AR" — Arkansas. Map full names
 *  properly, and fall back to the ZIP code when the field is unusable. */
const STATE_NAMES_TO_ABBR = {
  alabama:'AL', alaska:'AK', arizona:'AZ', arkansas:'AR', california:'CA', colorado:'CO',
  connecticut:'CT', delaware:'DE', 'district of columbia':'DC', florida:'FL', georgia:'GA',
  hawaii:'HI', idaho:'ID', illinois:'IL', indiana:'IN', iowa:'IA', kansas:'KS',
  kentucky:'KY', louisiana:'LA', maine:'ME', maryland:'MD', massachusetts:'MA',
  michigan:'MI', minnesota:'MN', mississippi:'MS', missouri:'MO', montana:'MT',
  nebraska:'NE', nevada:'NV', 'new hampshire':'NH', 'new jersey':'NJ', 'new mexico':'NM',
  'new york':'NY', 'north carolina':'NC', 'north dakota':'ND', ohio:'OH', oklahoma:'OK',
  oregon:'OR', pennsylvania:'PA', 'rhode island':'RI', 'south carolina':'SC',
  'south dakota':'SD', tennessee:'TN', texas:'TX', utah:'UT', vermont:'VT',
  virginia:'VA', washington:'WA', 'west virginia':'WV', wisconsin:'WI', wyoming:'WY',
};

/** First three digits of a ZIP identify the state — used as a cross-check. */
const ZIP_STATE = [
  [995,999,'AK'],[850,865,'AZ'],[716,729,'AR'],[900,961,'CA'],[800,816,'CO'],
  [60,69,'CT'],[197,199,'DE'],[200,205,'DC'],[320,349,'FL'],[300,319,'GA'],
  [967,968,'HI'],[832,838,'ID'],[600,629,'IL'],[460,479,'IN'],[500,528,'IA'],
  [660,679,'KS'],[400,427,'KY'],[700,714,'LA'],[39,49,'ME'],[206,219,'MD'],
  [10,27,'MA'],[480,499,'MI'],[550,567,'MN'],[386,397,'MS'],[630,658,'MO'],
  [590,599,'MT'],[680,693,'NE'],[889,898,'NV'],[30,38,'NH'],[70,89,'NJ'],
  [870,884,'NM'],[100,149,'NY'],[270,289,'NC'],[580,588,'ND'],[430,459,'OH'],
  [730,749,'OK'],[970,979,'OR'],[150,196,'PA'],[28,29,'RI'],[290,299,'SC'],
  [570,577,'SD'],[370,385,'TN'],[750,799,'TX'],[840,847,'UT'],[50,59,'VT'],
  [220,246,'VA'],[980,994,'WA'],[247,268,'WV'],[530,549,'WI'],[820,831,'WY'],
];

function stateFromZip(zip) {
  const n = parseInt(String(zip || '').replace(/\D/g, '').slice(0, 3), 10);
  if (!Number.isFinite(n)) return '';
  for (const [lo, hi, ab] of ZIP_STATE) if (n >= lo && n <= hi) return ab;
  return '';
}

function normaliseState(raw, zip) {
  const t = String(raw || '').trim();
  const byName = STATE_NAMES_TO_ABBR[t.toLowerCase()];
  if (byName) return byName;
  const two = t.toUpperCase().replace(/[^A-Z]/g, '').slice(0, 2);
  const fromZip = stateFromZip(zip);
  // a two-letter code that contradicts the ZIP is usually a truncated name
  if (two.length === 2 && (!fromZip || two === fromZip)) return two;
  return fromZip || two;
}

const SCOPE_TO_KEY = {
  'Ayurveda': 'Ayurveda',
  'Acupuncture': 'Acupuncture',
  'Traditional Chinese Medicine': 'TCM',
  'Naturopathic Medicine': 'Naturopathy',
  'Chiropractic': 'Chiropractic',
  'Massage Therapy': 'Massage',
  'Body Work': 'Bodywork',
  'Energy Work': 'EnergyMedicine',
  'Integrative / Functional Medicine': 'IntegrativeMedicine',
  'Counseling': 'Counseling',
  'Health & Wellness Coaching': 'Coaching',
  'Herbalism': 'Herbalism',
  'Farmer': 'Farms',
  'Grocer': 'Grocers',
};

/** The issuing authority to check, by discipline and state. Extend as the
 *  directory grows into new states. */
const BOARDS = {
  Acupuncture: { AZ: ['the Arizona Acupuncture Board of Examiners', 'https://acupuncture.az.gov/'] },
  TCM:         { AZ: ['the Arizona Acupuncture Board of Examiners', 'https://acupuncture.az.gov/'] },
  Naturopathy: { AZ: ['the Arizona Naturopathic Physicians Medical Board', 'https://nd.az.gov/resources/license-verification-request'] },
  Chiropractic:{ AZ: ['the Arizona Board of Chiropractic Examiners', 'https://chiroboard.az.gov/find-chiropractor'] },
  Massage:     { AZ: ['the Arizona Massage Therapy Board', 'https://massagetherapy.az.gov/applications/status'] },
  Bodywork:    { AZ: ['the Arizona Massage Therapy Board', 'https://massagetherapy.az.gov/applications/status'] },
  Counseling:  { AZ: ['the Arizona Board of Behavioral Health Examiners', 'https://azbbhe.us/'] },
  IntegrativeMedicine: { AZ: ['the Arizona Medical Board', 'https://www.azmd.gov/'] },
  Ayurveda:    { '*': ['NAMA Certification Board', 'https://www.namacb.org/'] },
  Coaching:    { '*': ['the National Board for Health & Wellness Coaching', 'https://nbhwc.org/'] },
  Herbalism:   { '*': ['the American Herbalists Guild', 'https://www.americanherbalistsguild.com/'] },
};

function boardFor(listing) {
  for (const c of listing.categories || []) {
    const byState = BOARDS[c];
    if (!byState) continue;
    const hit = byState[listing.state] || byState['*'];
    if (hit) return { name: hit[0], url: hit[1] };
  }
  return null;
}

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
 * Base64 contents of a file, whatever its size.
 * The contents API returns an empty `content` for anything over 1 MB — which
 * is most phone photographs — so fall back to the blob API, which handles up
 * to 100 MB. Reading the contents response alone silently produced empty files.
 */
async function readBlob(env, path) {
  const meta = await readFile(env, path);
  if (!meta) return null;
  if (meta.content && meta.encoding === 'base64' && meta.content.trim()) {
    return meta.content.replace(/\n/g, '');
  }
  if (!meta.sha) return null;
  const blob = await ghJson(env, `/repos/${env.GH_REPO}/git/blobs/${meta.sha}`);
  if (!blob || !blob.content) return null;
  return blob.content.replace(/\n/g, '');
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
${row('Logo', s.logo_note || (s.logo_name ? s.logo_name : 'none'))}
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
    city: g('City'), state: normaliseState(g('State'), g('ZIP code')), zip: g('ZIP code'),
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

/** A licence field containing only a state name, or nothing, has no number. */
function looksLikeLicence(v) {
  const t = String(v || '').trim();
  if (!t) return false;
  const stripped = t.toLowerCase().replace(/[^a-z]/g, '');
  if (STATE_NAMES_TO_ABBR[t.trim().toLowerCase()]) return false;
  if (stripped.length && !/\d/.test(t) && stripped.length < 12) return false;
  return true;
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
    // Never leave a row blank when the applicant gave us something. Someone
    // who is licensed often puts everything in the licence field and leaves
    // certifications empty, and vice versa.
    // Both fields are now asked of every applicant, so certifications are the
    // credential and the licence stands on its own line.
    credentials: s.certs || '—',
    licensure: s.licensed === 'Yes'
      ? (looksLikeLicence(s.license) ? s.license : 'State licensed — number not provided')
      : (s.certs
          ? 'No state licensure exists for this discipline'
          : 'No state licensure exists for this discipline'),
    training: s.training || '—',
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

  // Accept the upload generously and record why anything was skipped, rather
  // than dropping it silently. Some browsers send an empty or unexpected MIME
  // type, so fall back to the file extension.
  const file = form.get('Logo or headshot');
  if (file && typeof file === 'object' && typeof file.arrayBuffer === 'function') {
    const name = (file.name || '').toLowerCase();
    const byName = name.match(/\.(png|jpe?g|webp|heic|heif|gif)$/);
    const type = (file.type || '').toLowerCase();
    const isImage = type.startsWith('image/') || !!byName;

    let ext = null;
    if (type.includes('png') || /\.png$/.test(name)) ext = 'png';
    else if (type.includes('webp') || /\.webp$/.test(name)) ext = 'webp';
    else if (type.includes('gif') || /\.gif$/.test(name)) ext = 'gif';
    else if (type.includes('heic') || type.includes('heif') || /\.heic$|\.heif$/.test(name)) ext = 'heic';
    else if (isImage) ext = 'jpg';

    if (file.size === 0) {
      s.logo_note = 'no file chosen';
    } else if (!isImage) {
      s.logo_note = `skipped — not an image (${esc(file.name || 'unnamed')}, ${type || 'no type'})`;
    } else if (file.size > 10 * 1024 * 1024) {
      s.logo_note = `skipped — ${Math.round(file.size / 1048576)} MB, over the 10 MB limit`;
    } else {
      try {
        s.logo_name = file.name || `logo.${ext}`;
        s.logo_ext = ext;
        s.logo_size = file.size;
        files.push({
          path: `data/pending/${id}-logo.${ext}`,
          contentBase64: b64bytes(await file.arrayBuffer()),
        });
        s.logo_note = `${s.logo_name}, ${Math.round(file.size / 1024)} KB`;
      } catch (err) {
        s.logo_note = `failed to read — ${err.message}`;
      }
    }
  } else {
    s.logo_note = 'no file field received';
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
  let logoProblem = '';
  if (s.logo_ext) {
    const path = `data/pending/${id}-logo.${s.logo_ext}`;
    const content = await readBlob(env, path);
    if (content) {
      logoPath = `/assets/img/providers/${slug}.${s.logo_ext}`;
      files.push({
        path: `public/assets/img/providers/${slug}.${s.logo_ext}`,
        contentBase64: content,
      });
      files.push({ path, remove: true });
    } else {
      logoProblem = `The uploaded image could not be read back from ${esc(path)}.`;
    }
  } else {
    logoProblem = s.logo_note ? `At intake: ${esc(s.logo_note)}` : 'No image was received with the application.';
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
${logoPath
  ? '<p>Their logo was published with it.</p>'
  : `<p style="color:#c23a4b">No logo was published. ${logoProblem}</p>`}
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
  const waiting = listings.filter((l) => !l.verification);
  const base = env.SITE_URL || 'https://findwelldirectory.com';
  const today = new Date().toLocaleDateString('en-GB',
    { day: 'numeric', month: 'short', year: 'numeric' });

  const rows = await Promise.all(waiting.map(async (l) => {
    const sig = await hmac((env.SIGNING_SECRET || '').trim(), 'verify:' + l.slug);
    const board = boardFor(l);
    const what = l.licensure && !/no state licensure/i.test(l.licensure)
      ? l.licensure : 'Credentials confirmed';
    return `<li style="padding:16px 0;border-top:1px solid #dbe3e3">
      <strong>${esc(l.name)}</strong> — ${esc(l.person)}, ${esc(l.city)}, ${esc(l.state)}<br>
      <span style="color:#5f7473;font-size:14px">${esc(l.licensure || '')}</span><br>
      ${board ? `<a href="${esc(board.url)}" target="_blank" rel="noopener"
          style="font-size:14px">Open ${esc(board.name)} &#8599;</a> &nbsp;·&nbsp;` : ''}
      <a href="${base}/provider/${esc(l.slug)}/" target="_blank" style="font-size:14px">view listing</a>
      <form method="POST" action="${base}/api/verify" style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap;align-items:center">
        <input type="hidden" name="slug" value="${esc(l.slug)}">
        <input type="hidden" name="sig" value="${sig}">
        <input type="hidden" name="key" value="${esc((env.SIGNING_SECRET || '').trim())}">
        <input name="what" value="${esc(what)}" style="flex:1 1 16rem;padding:6px 8px;border:1px solid #dbe3e3;border-radius:5px;font:inherit;font-size:14px">
        <input name="source" value="${esc(board ? board.name : '')}" placeholder="checked with…"
               style="flex:1 1 16rem;padding:6px 8px;border:1px solid #dbe3e3;border-radius:5px;font:inherit;font-size:14px">
        <input name="date" value="${esc(today)}" style="width:8rem;padding:6px 8px;border:1px solid #dbe3e3;border-radius:5px;font:inherit;font-size:14px">
        <button type="submit" style="background:#2e5f5c;color:#fff;border:0;padding:8px 14px;border-radius:5px;font:inherit;font-weight:600;cursor:pointer">Mark confirmed</button>
      </form>
    </li>`;
  }));

  return page('Awaiting verification', `<h1>Awaiting verification</h1>
<p>Listings published as reported by the practitioner. Open the board, check the
number, then press the button — the fields are already filled in.</p>
<ul style="margin:1rem 0 0">${rows.join('') ||
  '<li style="padding:12px 0">Everything has been checked.</li>'}</ul>`);
}

async function handleVerify(request, env) {
  const url = new URL(request.url);
  let slug, sig, what, source, date, key;

  if (request.method === 'POST') {
    const f = await request.formData();
    slug = (f.get('slug') || '').toString();
    sig = (f.get('sig') || '').toString();
    key = (f.get('key') || '').toString();
    what = (f.get('what') || '').toString().trim();
    source = (f.get('source') || '').toString().trim();
    date = (f.get('date') || '').toString().trim();
  } else {
    slug = url.searchParams.get('slug') || '';
    sig = url.searchParams.get('sig') || '';
  }

  const expected = await hmac((env.SIGNING_SECRET || '').trim(), 'verify:' + slug);
  if (!safeEqual(sig.trim(), expected)) {
    return page('Invalid link', '<h1>That link is not valid</h1>', 403);
  }
  if (!source) {
    return page('Missing source',
      '<h1>Name the source</h1><p>Say which body the credential was checked with. ' +
      'A confirmation without a source is not worth publishing.</p>', 400);
  }

  const current = await readFile(env, 'data/listings.json');
  const listings = current ? JSON.parse(fromB64(current.content)) : [];
  const row = listings.find((l) => l.slug === slug);
  if (!row) return page('Not found', '<h1>Not found</h1>', 404);

  row.verification = {
    what: what || 'Credentials confirmed',
    source,
    date: date || new Date().toISOString().slice(0, 10),
    by: 'admin',
    recorded_at: new Date().toISOString(),
  };

  await commitFiles(env, `Verified: ${row.name}`,
    [{ path: 'data/listings.json', contentBase64: b64(JSON.stringify(listings, null, 2) + '\n') }]);

  const base = env.SITE_URL || 'https://findwelldirectory.com';
  return page('Confirmed', `<h1>Confirmed</h1>
<p><strong>${esc(row.name)}</strong> now reads:</p>
<p style="background:#eff6f2;border:1px solid #cfe4d8;border-radius:6px;padding:10px 12px">
<strong>${esc(row.verification.what)}</strong> with ${esc(source)}, ${esc(row.verification.date)}.</p>
<p>Live in about a minute. <a href="${base}/api/review?key=${encodeURIComponent((env.SIGNING_SECRET || '').trim())}">Back to the list</a></p>`);
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
