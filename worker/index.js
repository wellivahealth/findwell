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
  // Canadian provinces and territories
  alberta:'AB', 'british columbia':'BC', manitoba:'MB', 'new brunswick':'NB',
  'newfoundland and labrador':'NL', newfoundland:'NL', 'nova scotia':'NS',
  'northwest territories':'NT', nunavut:'NU', ontario:'ON', 'prince edward island':'PE',
  quebec:'QC', 'québec':'QC', saskatchewan:'SK', yukon:'YT',
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
  const digits = String(zip || '').replace(/\D/g, '');
  if (digits.length !== 5 && digits.length !== 9) return '';   // not a US ZIP
  const n = parseInt(digits.slice(0, 3), 10);
  if (!Number.isFinite(n)) return '';
  for (const [lo, hi, ab] of ZIP_STATE) if (n >= lo && n <= hi) return ab;
  return '';
}

function normaliseState(raw, zip, country) {
  const t = String(raw || '').trim();
  const byName = STATE_NAMES_TO_ABBR[t.toLowerCase()];
  if (byName) return byName;
  const c = String(country || '').trim();
  if (/^canada$/i.test(c)) return t.toUpperCase().replace(/[^A-Z]/g, '').slice(0, 2);
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
  'Integrative / Functional Medicine (MD, DO, NP, PA)': 'IntegrativeMedicine',
  'Integrative / Functional Medicine': 'IntegrativeMedicine',   // earlier wording
  'Counseling': 'Counseling',
  'Health & Wellness Coaching': 'Coaching',
  'Herbalism': 'Herbalism',
  'Farmer': 'Farms',
  'Grocer': 'Grocers',
};

/** The issuing authority to check, by discipline and state. Extend as the
 *  directory grows into new states. */
/** Where a credential is checked, per discipline. Mirrors the FindWell Directory
 *  tab of the credentialing matrix. `state` holds boards that license; `also`
 *  holds certifying bodies that apply everywhere. Keep the two apart: a
 *  certifying body is never an answer to a licensure question. */
const SOURCES = {
  Acupuncture: { licensed: true,
    state: {
      AZ: ['the Arizona Acupuncture Board of Examiners', 'https://acupuncture.az.gov/'],
      CA: ['the California Acupuncture Board, through the DCA licence search', 'https://search.dca.ca.gov/'],
      FL: ['the Florida Board of Acupuncture, through the Department of Health licence search',
           'https://appsmqa.doh.state.fl.us/IRM00PRAES/PRASLIST.ASP'] },
    also: [
      ['NCBAHM, formerly NCCAOM, for Dipl. Ac. and Dipl. O.M.', 'https://www.ncbahm.org/find-a-practitioner-directory/', 2],
    ] },
  TCM: { licensed: true,
    state: {
      AZ: ['the Arizona Acupuncture Board of Examiners', 'https://acupuncture.az.gov/'],
      CA: ['the California Acupuncture Board, through the DCA licence search', 'https://search.dca.ca.gov/'],
      FL: ['the Florida Board of Acupuncture, through the Department of Health licence search',
           'https://appsmqa.doh.state.fl.us/IRM00PRAES/PRASLIST.ASP'] },
    also: [
      ['NCBAHM, formerly NCCAOM, for Dipl. C.H. and Dipl. O.M.', 'https://www.ncbahm.org/find-a-practitioner-directory/', 2],
    ] },
  Naturopathy: { licensed: true, state: {
    AZ: ['the Arizona Naturopathic Physicians Medical Board', 'https://nd.az.gov/resources/license-verification-request'],
    CA: ['the California Board of Naturopathic Medicine, through the DCA licence search', 'https://search.dca.ca.gov/'] } },
  Chiropractic: { licensed: true, state: {
    AZ: ['the Arizona Board of Chiropractic Examiners', 'https://chiroboard.az.gov/find-chiropractor'],
    CA: ['the California Board of Chiropractic Examiners, through the DCA licence search',
         'https://search.dca.ca.gov/?BD=8500&TP=DC'] } },
  Massage: { licensed: true, state: {
    AZ: ['the Arizona Massage Therapy Board', 'https://massagetherapy.az.gov/applications/status'] } },
  Counseling: { licensed: true,
    state: {
      AZ: ['the Arizona Board of Behavioral Health Examiners', 'https://azbbhe.us/'],
      CA: ['the California Board of Behavioral Sciences, through the DCA licence search', 'https://search.dca.ca.gov/'] },
    stateAlso: { CA: [
      ['the California Board of Psychology, for a psychologist', 'https://search.dca.ca.gov/', 1],
    ] } },
  IntegrativeMedicine: { licensed: true,
    state: {
      AZ: ['the Arizona Medical Board', 'https://www.azmd.gov/PhysicianCenter/PhysicianCenter/license-verification'],
      CA: ['the Medical Board of California, through the DCA licence search', 'https://search.dca.ca.gov/'] },
    stateAlso: {
      CA: [
        ['the Osteopathic Medical Board of California, for a DO', 'https://search.dca.ca.gov/', 1],
        ['the California Physician Assistant Board, for a PA', 'https://search.dca.ca.gov/', 1],
        ['the California Board of Registered Nursing, for an NP', 'https://search.dca.ca.gov/', 1],
      ],
      AZ: [
      ['the Arizona Board of Osteopathic Examiners, for a DO', 'https://azdo.gov/', 1],
      ['the Arizona Regulatory Board of Physician Assistants, for a PA', 'https://www.azpa.gov/', 1],
    ] },
    also: [
      ['NCCPA, for PA-C certification', 'https://www.nccpa.net/', 2],
      ['ABOIM through ABPS, for integrative medicine certification', 'https://www.abpsus.org/integrative-medicine-board-certification/', 2],
      ['the American Board of Lifestyle Medicine', 'https://ablm.org/diplomates/', 2],
      ['the Institute for Functional Medicine, for FMCP or FMCP-M', 'https://www.ifm.org/certification', 2],
    ] },
  Bodywork: { licensed: false,
    state: { AZ: ['the Arizona Massage Therapy Board', 'https://massagetherapy.az.gov/applications/status'] },
    also: [
      ['NCBAHM, for Dipl. ABT', 'https://www.ncbahm.org/find-a-practitioner-directory/', 2],
      ['AOBTA, for Certified Practitioner or Instructor in Asian bodywork', 'https://aobta.org/search/custom.asp?id=5142', 3],
      ['Upledger Institute International, for CST-T or CST-D', 'https://www.upledger.com/courses/certification-programs/1', 3],
      ['BCTA/NA, for RCST', 'https://www.craniosacraltherapy.org/rcst-criteria-', 3],
    ] },
  Ayurveda: { licensed: false, also: [['the NAMA Certification Board', 'https://www.namacb.org/', 2]] },
  Coaching: { licensed: false, also: [
    ['the National Board for Health & Wellness Coaching', 'https://members.nbhwc.org/search/custom.asp?id=6956', 2],
    ['the International Coaching Federation', 'https://coachingfederation.org/credentialing/icf-credentials-overview/compare-credentials/', 2],
  ] },
  Herbalism: { licensed: false, also: [['the American Herbalists Guild', 'https://directory.americanherbalistsguild.com/support', 3]] },
  EnergyMedicine: { licensed: false },
  Farmer: { licensed: false },
  Grocer: { licensed: false },
};

const isLicensed = (c) => !!(SOURCES[c] || {}).licensed;

/** What a source can prove, strongest first. A listing's verification line may
 *  never claim a tier above the one actually checked, and for a licensed
 *  discipline tier 1 is the only answer to the licensure question. */
const TIERS = {
  1: 'Licence — legal authority to practise',
  2: 'National certification — earned by examination',
  3: 'Professional association — peer reviewed, renewable',
};

/** Every place worth opening for this listing, ordered by tier. */
function sourcesFor(listing) {
  const out = []; const seen = new Set();
  const add = (pair, tier) => {
    if (pair && !seen.has(pair[0])) {
      seen.add(pair[0]);
      out.push({ name: pair[0], url: pair[1], tier: pair[2] || tier });
    }
  };
  for (const c of listing.categories || []) add(((SOURCES[c] || {}).state || {})[listing.state], 1);
  for (const c of listing.categories || []) {
    (((SOURCES[c] || {}).stateAlso || {})[listing.state] || []).forEach((x) => add(x, 1));
  }
  for (const c of listing.categories || []) ((SOURCES[c] || {}).also || []).forEach((x) => add(x, 3));
  return out.sort((a, b) => a.tier - b.tier);
}

/** True when the listing claims a licensed discipline, so a certification or a
 *  membership must not be recorded as though it settled the licence. */
function licenceOutstanding(listing) {
  return (listing.categories || []).some(isLicensed) && !boardFor(listing);
}

function boardFor(listing) {
  const cats = listing.categories || [];
  for (const c of cats) {
    const hit = ((SOURCES[c] || {}).state || {})[listing.state];
    if (hit) return { name: hit[0], url: hit[1] };
  }
  // a licensed discipline in a state we have no board for: leave it to the
  // admin rather than offering a certifying body as if it answered the question
  if (cats.some(isLicensed)) return null;
  return sourcesFor(listing)[0] || null;
}

/** Checks that run before an application reaches the inbox. Nothing here
 *  approves or declines anything; it prepares the human decision. */
function preChecks(s, listing, existing) {
  const out = [];
  const flag = (t) => out.push({ level: 'flag', text: t });
  const note = (t) => out.push({ level: 'note', text: t });
  const cats = listing.categories || [];
  const licensedCats = cats.filter(isLicensed);
  const licenceText = `${s.licensed || ''} ${s.license || ''}`;
  const blob = `${s.short || ''} ${s.long || ''} ${s.certs || ''} ${s.training || ''}`;

  if (!s.attestation) flag('The accuracy attestation was not ticked.');

  if (licensedCats.length && !/\d/.test(licenceText)) {
    flag(`${licensedCats.join(' and ')} is a licensed discipline, but no licence number was given, `
       + 'so this listing cannot be confirmed as it stands.');
  }
  if (licenceOutstanding(listing) && sourcesFor(listing).length) {
    note('A licensed discipline here has no board on file, and the other links below are certifications '
       + 'and memberships. None of them settle the licence, so do not record one as the confirmation.');
  }
  for (const c of licensedCats) {
    if (!((SOURCES[c] || {}).state || {})[listing.state]) {
      note(`No board on file yet for ${c} in ${listing.state}. Find the regulator before `
         + 'confirming, and add it to the matrix while you are there.');
    }
  }
  if (!licensedCats.length && /^yes$/i.test(String(s.licensed || '').trim())) {
    note('They answered yes to holding a licence, but none of the disciplines they chose are licensed ones. '
       + 'Often this means the discipline was mis-ticked, so ask what the licence is in.');
  }
  if (!licensedCats.length && /\blicen[sc]/i.test(blob + ' ' + licenceText)) {
    note('None of the disciplines here are licensed, yet the application uses the word licensed. '
       + 'Worth reading closely before it becomes a published claim.');
  }
  if (cats.includes('IntegrativeMedicine')
      && !/\b(MD|DO|NP|PA-?C?|physician assistant|nurse practitioner|medical doctor|osteopath)\b/i.test(licenceText + ' ' + blob)) {
    note('Listed under integrative and functional medicine, which is defined by a medical licence, and nothing '
       + 'here shows one. If the licence is in another discipline, the listing belongs under that discipline with '
       + 'the functional medicine work described in the text.');
  }
  if (cats.includes('IntegrativeMedicine') && !s.integrative && !s.certs) {
    note('Listed under integrative and functional medicine with no integrative training or certification reported.');
  }
  if (/\b(shiatsu|acupressure|amma|anma|tui ?na|asian bodywork|thai (massage|bodywork)|AOBTA)\b/i.test(blob)) {
    note('Asian bodywork is described. The bodies are AOBTA, whose CP and Instructor grades sit on a '
       + '500 hour curriculum, and NCBAHM for Dipl. ABT. Allied membership at AOBTA is 30 hours and is '
       + 'not a practice credential, so read which one is claimed.');
  }
  if ((cats.includes('TCM') || cats.includes('Acupuncture')) && /herb/i.test(blob)) {
    note('Chinese herbs are mentioned. That is NCBAHM (Dipl. C.H. or Dipl. O.M.), not the herbalists guild, '
       + 'whose RH is a general membership and covers no tradition in particular.');
  }
  const titleish = `${s.practice || ''} ${blob}`;
  if (!cats.includes('IntegrativeMedicine')
      && /\b(medical (group|center|centre|clinic|practice)|physician|\bMD\b|\bDO\b)\b/i.test(titleish)) {
    note('The practice name or wording uses medical language while no medical licence is claimed. '
       + 'Some titles are real and state granted, such as Florida\'s Acupuncture Physician, so the fix '
       + 'is usually to publish the exact credential rather than to argue about the title.');
  }
  if (/IFMCP/i.test(blob)) note('IFMCP is named. IFM has replaced it with FMCP and FMCP-M, so ask which one they hold.');
  if (/ABIHM/i.test(blob)) note('ABIHM is named. It closed to new candidates in 2016 and ABOIM is the successor.');

  const year = (String(s.years || '').match(/\b(19|20)\d{2}\b/) || [])[0];
  const thisYear = new Date().getFullYear();
  if (year && (Number(year) > thisYear || thisYear - Number(year) > 60)) {
    note(`Practising since ${year} reads oddly, so it may be a typing slip.`);
  }

  const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return ''; } };
  for (const l of existing || []) {
    if (l.slug === listing.slug) {
      flag(`A listing already exists at /provider/${l.slug}/.`);
    } else if (l.email && s.email && String(l.email).toLowerCase() === String(s.email).toLowerCase()) {
      note(`Same email as the listing for ${l.name}. That may be a second practitioner at one practice, which is welcome, or a duplicate.`);
    } else if (l.website && s.website && host(l.website) && host(l.website) === host(s.website)) {
      note(`Same website as ${l.name}. If they practise together each listing still stands on its own credentials.`);
    }
  }

  if (/\b(our (team|practitioners|providers|clinicians|doctors|physicians)|we are a (group|team)|our staff)\b/i.test(blob)) {
    note('The description reads like a practice rather than one practitioner, and listings are individual.');
  }

  if (!out.length) out.push({ level: 'ok', text: 'Nothing caught here. The credential itself still needs checking.' });
  return out;
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
async function commitFiles(env, message, files, attempt = 0) {
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

  // If a deploy (or another application) commits between reading the branch
  // head and updating it, GitHub rejects this as not a fast-forward. Re-read
  // and try again rather than losing the submission.
  const res = await gh(env, `/repos/${repo}/git/refs/heads/${branch}`, {
    method: 'PATCH',
    body: JSON.stringify({ sha: commit.sha }),
  });
  if (!res.ok) {
    const body = (await res.text()).slice(0, 200);
    const conflict = res.status === 409 || res.status === 422;
    if (conflict && attempt < 3) {
      await new Promise((r) => setTimeout(r, 400 * (attempt + 1)));
      return commitFiles(env, message, files, attempt + 1);
    }
    throw new Error(`GitHub ref update ${res.status}: ${body}`);
  }
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

const publishedEmail = (s, url, joinUrl) => shell(`<h2 style="font-size:20px;margin:0 0 12px">Your listing is live</h2>
<p>Thank you for joining the FindWell Directory. Your listing for <strong>${esc(s.practice)}</strong> is now published:</p>
<p><a href="${esc(url)}" style="display:inline-block;background:#c23a4b;color:#fff;text-decoration:none;padding:10px 18px;border-radius:6px;font-weight:600">View your listing</a></p>
<p>Please take a look when you have a moment. If anything needs changing, whether a fee, the way a credential reads, or the photo, simply reply to this email and we will update it for you.</p>
<p>We also confirm license numbers and certifications with the issuing board. That is usually quick, and we will only be in touch if we have a question.</p>
<div style="margin:28px 0 8px;padding:18px 20px;background:#eff4f4;border-radius:8px">
<p style="margin:0 0 8px;font-weight:600;font-size:17px">Know a practitioner who belongs here?</p>
<p style="margin:0 0 12px">The directory becomes more useful to patients with every practitioner who joins, and the people who know good practitioners best are other practitioners. If there are colleagues whose work you trust, we would be grateful if you passed this along. Listing is free and always will be, with no paid placement and no leads sold, and the application takes about ten minutes.</p>
<p style="margin:0 0 12px"><a href="${esc(joinUrl)}" style="display:inline-block;background:#2e5f5c;color:#fff;text-decoration:none;padding:10px 18px;border-radius:6px;font-weight:600">Invite a colleague to join</a></p>
<p style="margin:0;font-size:14px;color:#5f7473">You are welcome to forward this email as it is. The link above works for anyone.</p>
</div>
<p style="margin-top:24px">Warmly,<br>Amita Nathwani<br>FindWell Directory</p>`);

function adminEmail(s, approveUrl, declineUrl, checks = [], places = []) {
  const tone = { flag: ['#c23a4b', 'Look at this'], note: ['#9a6b1f', 'Worth a look'], ok: ['#2e5f5c', 'Clear'] };
  const block = checks.length ? `<div style="margin:0 0 20px;padding:14px 16px;background:#fbfaf7;border:1px solid #e6e1d7;border-radius:8px">
<p style="margin:0 0 10px;font-weight:600">Before you approve</p>
${checks.map((c) => `<p style="margin:0 0 8px;font-size:14px;line-height:1.45">
<span style="color:${tone[c.level][0]};font-weight:600">${tone[c.level][1]}:</span> ${esc(c.text)}</p>`).join('')}
${places.length ? `<p style="margin:12px 0 4px;font-weight:600;font-size:14px">Where to check this one, in order</p>
${[1, 2, 3].map((t) => {
  const group = places.filter((p) => p.tier === t);
  if (!group.length) return '';
  return `<p style="margin:8px 0 2px;font-size:13px;color:#5f7473">${esc(TIERS[t])}</p>
<p style="margin:0;font-size:14px;line-height:1.7">${group.map((p) =>
  `<a href="${esc(p.url)}" style="color:#2e5f5c">${esc(p.name)} &#8599;</a>`).join('<br>')}</p>`;
}).join('')}` : ''}
</div>` : '';
  return adminEmailBody(s, approveUrl, declineUrl, block);
}

function adminEmailBody(s, approveUrl, declineUrl, checkBlock) {
  const row = (k, v) => v
    ? `<tr><td style="padding:4px 12px 4px 0;color:#5f7473;vertical-align:top;white-space:nowrap">${esc(k)}</td><td style="padding:4px 0">${esc(v)}</td></tr>`
    : '';
  return shell(`<h2 style="font-size:20px;margin:0 0 4px">New application — ${esc(s.practice)}</h2>
<p style="margin:0 0 16px;color:#5f7473">${esc(s.first)} ${esc(s.last)} · ${esc(s.city)}, ${esc(s.state)}</p>
<p style="margin:0 0 20px">
<a href="${esc(approveUrl)}" style="display:inline-block;background:#2e5f5c;color:#fff;text-decoration:none;padding:11px 20px;border-radius:6px;font-weight:600;margin-right:8px">Approve &amp; publish</a>
<a href="${esc(declineUrl)}" style="display:inline-block;background:#fff;color:#c23a4b;border:1px solid #c23a4b;text-decoration:none;padding:10px 19px;border-radius:6px;font-weight:600">Decline</a></p>
${checkBlock}
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
${row('Referred by', s.referred_by)}
${row('Attested accurate', s.attestation ? 'Yes' : 'NOT TICKED')}
</table>
<p style="margin-top:20px;padding:12px;background:#eff4f4;border-radius:6px;font-size:14px">
<strong>Internal — not published</strong><br>
Desired size: ${esc(s.size) || '—'}<br>
Open to Welliva coverage: ${esc(s.openins) || '—'}${/^(yes|tell me more)$/i.test(s.openins || '') ? ' (worth a follow up)' : ''}<br>
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
    if (m) return { lat: Number(m.y), lng: Number(m.x) };
  } catch { /* fall through */ }
  try {
    // Census covers the US only; OpenStreetMap covers Canada (and the US as a backup)
    const res = await fetch('https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=us,ca&q='
      + encodeURIComponent(address), {
      headers: { 'User-Agent': 'FindWellDirectory/1.0 (info@findwelldirectory.com)' },
      signal: AbortSignal.timeout(6000),
    });
    if (!res.ok) return {};
    const hit = (await res.json())?.[0];
    return hit ? { lat: Number(hit.lat), lng: Number(hit.lon) } : {};
  } catch { return {}; }
}

// ---------------------------------------------------------------- intake

/** The form sends the chosen scopes as one comma-joined string, and some
 *  labels now contain commas of their own, so match known scopes in the text
 *  rather than splitting on the comma. Also tolerates earlier wording. */
function scopeList(raw) {
  let rest = String(raw || '');
  const found = [];
  for (const label of Object.keys(SCOPE_TO_KEY).sort((a, b) => b.length - a.length)) {
    if (rest.includes(label)) {
      found.push(label);
      rest = rest.replace(label, '');
    }
  }
  return found;
}

function readForm(form) {
  const g = (k) => (form.get(k) || '').toString().trim();
  const split = (k) => g(k).split(',').map((s) => s.trim()).filter(Boolean);
  const s = {
    first: g('First name'), last: g('Last name'), practice: g('Practice or business name'),
    email: g('email'), phone: g('Phone'), website: g('Website'), social: g('Social media'),
    physical: g('physical'), country: g('Country'),
    addr1: g('Address line 1'), addr2: g('Address line 2'),
    city: g('City'), state: normaliseState(g('State'), g('ZIP code'), g('Country')), zip: g('ZIP code'),
    scope: scopeList(g('Scope of practice')), short: g('Describe your practice'),
    licensed: g('licensed'), license: g('State(s) and license number(s)'),
    certs: g('Certificates or affiliations'), years: g('Years in practice'),
    training: g('Primary training and education'), integrative: g('Integrative training'),
    payments: split('Payment methods'), pricing: g('Pricing structure'),
    telehealth: g('telehealth'), long: g('Listing description'),
    size: g('Desired size of practice'), openins: g('openins'), ehr: g('ehr'),
    attestation: g('Attestation'),
    referred_by: g('Referred by'),
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
    country: s.country || 'United States',
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

  if (s.country && !/^(united states|canada)$/i.test(s.country)) {
    return json({ ok: false, error: 'Thank you for your interest. FindWell currently lists practitioners in the United States and Canada only.' }, 400);
  }
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

  // run the checks before the notification goes out, so the email arrives
  // with the homework done rather than just the answers the applicant gave
  let checks = [], places = [];
  try {
    const preview = {
      slug: slugify(s.practice), state: s.state,
      categories: s.scope.map((x) => SCOPE_TO_KEY[x]).filter(Boolean),
    };
    const current = await readFile(env, 'data/listings.json');
    const existing = current ? JSON.parse(fromB64(current.content)) : [];
    checks = preChecks(s, preview, existing);
    places = sourcesFor(preview);
  } catch { /* the notification matters more than the checks */ }
  await Promise.all([
    sendEmail(env, {
      to: env.ADMIN_EMAIL, replyTo: s.email,
      subject: `New application — ${s.practice}`
        + (/^(yes|tell me more)$/i.test(s.openins || '') ? ` · Welliva: ${s.openins}` : ''),
      html: adminEmail(s,
        `${base}/api/approve?id=${encodeURIComponent(id)}&sig=${sig}`,
        `${base}/api/decline?id=${encodeURIComponent(id)}&sig=${sig}`,
        checks, places),
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
    html: publishedEmail(s, listingUrl, `${base}/join/?ref=${encodeURIComponent(listing.slug)}`),
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

/** Checks for listings written into build.py are kept in their own file. */
async function readChecks(env) {
  const f = await readFile(env, 'data/verifications.json');
  return f ? { data: JSON.parse(fromB64(f.content)), exists: true } : { data: {}, exists: false };
}

/** The original listings live in build.py, not data/listings.json. The build
 *  publishes a summary of every provider, which is how the review page sees them. */
async function seedListings(env) {
  try {
    const base = env.SITE_URL || 'https://findwelldirectory.com';
    const res = await env.ASSETS.fetch(new Request(`${base}/assets/data/providers.json`));
    if (!res.ok) return [];
    return (await res.json()).filter((p) => p.seed);
  } catch { return []; }
}

async function withSeeds(env, listings) {
  const have = new Set(listings.map((l) => l.slug));
  const [seeds, checks] = await Promise.all([seedListings(env), readChecks(env)]);
  return [...listings, ...seeds.filter((p) => !have.has(p.slug))]
    .map((l) => (checks.data[l.slug] ? { ...l, verification: checks.data[l.slug] } : l));
}

async function handleReview(request, env) {
  const url = new URL(request.url);
  if (!keyOk(url, env).ok) return page('Not authorised', '<h1>Not authorised</h1>', 403);

  const current = await readFile(env, 'data/listings.json');
  const listings = current ? JSON.parse(fromB64(current.content)) : [];
  const everyone = await withSeeds(env, listings);
  const showAll = url.searchParams.get('all') === '1';
  const waiting = showAll ? everyone : everyone.filter((l) => !l.verification);
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
      ${l.verification ? `<span style="font-size:13px;color:#c23a4b">Currently: ${esc(l.verification.what)} with ${esc(l.verification.source)}, ${esc(l.verification.date)}</span><br>` : ''}
      <span style="color:#5f7473;font-size:14px">${esc(l.licensure || '')}</span><br>
      ${licenceOutstanding(l) ? `<div style="font-size:13px;color:#c23a4b;margin-bottom:6px">
        Licence outstanding: find the regulator for ${esc(l.state)} first. A certification or membership
        below does not settle it.</div>` : ''}
      ${sourcesFor(l).map((p) => `<a href="${esc(p.url)}" target="_blank" rel="noopener"
          style="font-size:14px" title="${esc(TIERS[p.tier] || '')}">Open ${esc(p.name)} &#8599;</a>`).join(' &nbsp;·&nbsp; ')}
      ${sourcesFor(l).length ? ' &nbsp;·&nbsp; ' : ''}
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
  const verification = {
    what: what || 'Credentials confirmed',
    source,
    date: date || new Date().toISOString().slice(0, 10),
    by: 'admin',
    recorded_at: new Date().toISOString(),
  };

  let row = listings.find((l) => l.slug === slug);
  if (row) {
    row.verification = verification;
    await commitFiles(env, `Verified: ${row.name}`,
      [{ path: 'data/listings.json', contentBase64: b64(JSON.stringify(listings, null, 2) + '\n') }]);
  } else {
    // one of the original listings written into build.py
    row = (await seedListings(env)).find((p) => p.slug === slug);
    if (!row) return page('Not found', '<h1>Not found</h1>', 404);
    const checks = await readChecks(env);
    checks.data[slug] = verification;
    await commitFiles(env, `Verified: ${row.name}`,
      [{ path: 'data/verifications.json', contentBase64: b64(JSON.stringify(checks.data, null, 2) + '\n') }]);
  }
  row.verification = verification;

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
