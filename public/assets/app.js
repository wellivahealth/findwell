/* FindWell Directory — client behaviour.
   Every page is real HTML rendered at build time. This file only enhances:
   the menu, the home search console, filtering on directory pages, and the
   join form. With JavaScript off, all listings are still readable. */
(function () {
  'use strict';
  var $  = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---------- place lookup ----------
     Turns "85704", "T2P 1J9", "Denver" or "Springfield, MO" into coordinates.
     The lookup tables live in /assets/geo/ (built by make_geo.py) and are
     fetched in small pieces only when someone searches. */
  var STATE_NAMES = {
    alabama:'AL', alaska:'AK', arizona:'AZ', arkansas:'AR', california:'CA',
    colorado:'CO', connecticut:'CT', delaware:'DE', 'district of columbia':'DC',
    florida:'FL', georgia:'GA', hawaii:'HI', idaho:'ID', illinois:'IL', indiana:'IN',
    iowa:'IA', kansas:'KS', kentucky:'KY', louisiana:'LA', maine:'ME', maryland:'MD',
    massachusetts:'MA', michigan:'MI', minnesota:'MN', mississippi:'MS', missouri:'MO',
    montana:'MT', nebraska:'NE', nevada:'NV', 'new hampshire':'NH', 'new jersey':'NJ',
    'new mexico':'NM', 'new york':'NY', 'north carolina':'NC', 'north dakota':'ND',
    ohio:'OH', oklahoma:'OK', oregon:'OR', pennsylvania:'PA', 'rhode island':'RI',
    'south carolina':'SC', 'south dakota':'SD', tennessee:'TN', texas:'TX', utah:'UT',
    vermont:'VT', virginia:'VA', washington:'WA', 'west virginia':'WV',
    wisconsin:'WI', wyoming:'WY'
  };
  var PROVINCES = {
    alberta:'AB', 'british columbia':'BC', manitoba:'MB', 'new brunswick':'NB',
    newfoundland:'NL', 'newfoundland and labrador':'NL', 'nova scotia':'NS',
    'northwest territories':'NT', nunavut:'NU', ontario:'ON', 'prince edward island':'PE',
    quebec:'QC', 'québec':'QC', saskatchewan:'SK', yukon:'YT'
  };
  var REGIONS = {};
  Object.keys(STATE_NAMES).forEach(function (k) { REGIONS[STATE_NAMES[k]] = 1; });
  Object.keys(PROVINCES).forEach(function (k) { REGIONS[PROVINCES[k]] = 1; });
  function regionCode(s) {
    s = s.trim().toLowerCase().replace(/\./g, '');
    if (STATE_NAMES[s]) return STATE_NAMES[s];
    if (PROVINCES[s]) return PROVINCES[s];
    if (s.length === 2 && REGIONS[s.toUpperCase()]) return s.toUpperCase();
    return '';
  }
  var geoCache = {};
  function geoFile(path) {
    if (!geoCache[path]) geoCache[path] = fetch('/assets/geo/' + path)
      .then(function (r) { return r.ok ? r.json() : {}; })
      .catch(function () { delete geoCache[path]; return {}; });
    return geoCache[path];
  }
  function normPlace(s) {
    return s.toLowerCase().replace(/[.']/g, '').replace(/\bsaint\b/g, 'st')
            .replace(/\s+/g, ' ').trim();
  }
  function titleCase(s) {
    return s.replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }
  /* resolves to {lat, lng, label}, {state: 'AZ'} for a bare US state, or null */
  function geocode(text) {
    var t = (text || '').trim();
    if (!t) return Promise.resolve(null);
    var z = t.match(/^(\d{5})(?:-\d{4})?$/);
    if (z) return geoFile('zip/' + z[1].slice(0, 3) + '.json').then(function (d) {
      var c = d[z[1]]; return c ? { lat: c[0], lng: c[1], label: z[1] } : null;
    });
    var pc = t.toUpperCase().match(/^([A-Z]\d[A-Z])\s*(\d[A-Z]\d)?$/);
    if (pc) return geoFile('ca.json').then(function (d) {
      var c = d[pc[1]]; return c ? { lat: c[0], lng: c[1], label: t.toUpperCase() } : null;
    });
    var US = {};
    Object.keys(STATE_NAMES).forEach(function (k) { US[STATE_NAMES[k]] = 1; });
    var lower = t.toLowerCase().replace(/\./g, '');
    if (STATE_NAMES[lower]) return Promise.resolve({ state: STATE_NAMES[lower] });
    if (/^[a-z]{2}$/.test(lower) && US[lower.toUpperCase()]) return Promise.resolve({ state: lower.toUpperCase() });
    var city = t, region = '';
    var parts = t.split(',');
    if (parts.length > 1) { region = regionCode(parts.slice(1).join(',')); city = parts[0]; }
    else {
      var m = t.match(/^(.*\S)\s+([A-Za-z]{2})$/);
      if (m && regionCode(m[2])) { city = m[1]; region = regionCode(m[2]); }
    }
    var key = normPlace(city);
    if (!key) return Promise.resolve(null);
    var letter = /[a-z]/.test(key[0]) ? key[0] : '0';
    return geoFile('places/' + letter + '.json').then(function (d) {
      var hits = d[key];
      if (!hits || !hits.length) return null;
      var hit = hits[0];
      if (region) {
        hit = null;
        hits.forEach(function (h) { if (!hit && h[0] === region) hit = h; });
        if (!hit) return null;
      }
      return { lat: hit[1], lng: hit[2], label: titleCase(city.trim()) + ', ' + hit[0] };
    });
  }

  /* ---------- menu ---------- */
  var burger = $('#burger'), nav = $('#nav');
  if (burger && nav) {
    burger.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      burger.setAttribute('aria-expanded', open);
    });
  }

  /* ---------- "Find a provider" dropdown ---------- */
  var findToggle = document.getElementById('find-toggle');
  if (findToggle) {
    var findGroup = findToggle.parentNode;
    var close = function () { findToggle.setAttribute('aria-expanded', 'false'); };
    findToggle.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = findToggle.getAttribute('aria-expanded') === 'true';
      findToggle.setAttribute('aria-expanded', open ? 'false' : 'true');
    });
    document.addEventListener('click', function (e) {
      if (!findGroup.contains(e.target)) close();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { close(); findToggle.focus(); }
    });
  }

  /* ---------- masthead compacts on scroll ---------- */
  var masthead = document.querySelector('.masthead');
  if (masthead) {
    var compact = false;
    var onScroll = function () {
      var want = window.scrollY > 48;
      if (want !== compact) { compact = want; masthead.classList.toggle('compact', want); }
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* ---------- home search console ---------- */
  var cons = $('#console');
  if (cons) {
    cons.addEventListener('submit', function (e) {
      e.preventDefault();
      var q = $('#c-q').value.trim();
      var loc = $('#c-loc').value.trim();
      var p = new URLSearchParams();
      if (q) p.set('q', q);
      if (loc) p.set('where', loc);
      location.href = '/directory/' + (p.toString() ? '?' + p : '');
    });
    $$('[data-chip]', cons).forEach(function (c) {
      c.addEventListener('click', function () {
        location.href = '/directory/?cat=' + encodeURIComponent(c.dataset.chip);
      });
    });
    var nearBtn = $('[data-near]', cons);
    if (nearBtn) nearBtn.addEventListener('click', function () {
      locate(function (lat, lng) {
        location.href = '/directory/?lat=' + lat + '&lng=' + lng + '&radius=50&sort=distance';
      }, function (msg) { nearBtn.textContent = msg; });
    });
  }

  /* "Use my location" on pages that hand off to the directory */
  $$('[data-near-go]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      locate(function (lat, lng) {
        location.href = '/directory/?lat=' + lat + '&lng=' + lng + '&radius=50&sort=distance';
      }, function (msg) { btn.textContent = msg; });
    });
  });

  function locate(ok, fail) {
    if (!navigator.geolocation) return fail('Location unavailable');
    fail('Locating…');
    navigator.geolocation.getCurrentPosition(
      function (pos) { ok(pos.coords.latitude.toFixed(4), pos.coords.longitude.toFixed(4)); },
      function () { fail('Location unavailable — use a ZIP'); },
      { timeout: 8000 }
    );
  }

  function miles(a, b, c, d) {
    var R = 3958.8, rad = function (x) { return x * Math.PI / 180; };
    var dLat = rad(c - a), dLng = rad(d - b);
    var h = Math.pow(Math.sin(dLat / 2), 2) +
            Math.cos(rad(a)) * Math.cos(rad(c)) * Math.pow(Math.sin(dLng / 2), 2);
    return 2 * R * Math.asin(Math.sqrt(h));
  }

  /* ---------- directory filtering ---------- */
  var list = $('#records');
  if (!list) return;

  var records = $$('.record', list);
  var state = { q: '', cats: [], city: '', st: '', tele: false, sort: 'name', near: null, radius: 50, label: '' };

  var params = new URLSearchParams(location.search);
  state.q = params.get('q') || '';
  state.cats = (params.get('cat') || '').split(',').filter(Boolean).slice(0, 1);
  state.city = params.get('city') || '';
  state.st = (params.get('state') || '').toUpperCase();
  state.tele = params.get('tele') === '1';
  state.sort = params.get('sort') || 'name';
  state.radius = params.has('radius') ? Number(params.get('radius')) : 50;
  if ([10, 25, 50, 100, 250, 0].indexOf(state.radius) < 0) state.radius = 50;
  state.typed = '';
  if (params.get('lat') && params.get('lng')) {
    state.near = [Number(params.get('lat')), Number(params.get('lng'))];
    state.label = 'your location'; state.sort = 'distance';
  }

  /* reflect state into the controls */
  if ($('#f-q')) $('#f-q').value = state.q;
  if ($('#f-state')) $('#f-state').value = state.st;
  if ($('#f-tele')) $('#f-tele').checked = state.tele;
  if ($('#f-radius')) $('#f-radius').value = String(state.radius);
  $$('[data-cat]').forEach(function (cb) {
    if (!cb.dataset.href) cb.checked = state.cats.indexOf(cb.dataset.cat) > -1;
  });
  var geoMsg = $('#geo-msg');
  function say(m) { if (geoMsg) geoMsg.textContent = m || ''; }

  /* look up a typed place and apply it: a US state becomes the state
     filter, anything else becomes a distance search around that spot */
  function goTo(text, quiet) {
    text = (text || '').trim();
    if (!text) { state.near = null; state.label = ''; state.typed = ''; state.sort = 'name'; say(''); apply(); return; }
    say('Looking that up\u2026');
    geocode(text).then(function (g) {
      if (!g) {
        say('We couldn\u2019t find \u201C' + text + '\u201D. Try a ZIP or postal code, or add the state, e.g. Springfield, MO.');
        return;
      }
      say('');
      if (g.state) {
        state.st = g.state; state.city = ''; state.near = null; state.label = ''; state.typed = '';
        if (state.sort === 'distance') state.sort = 'name';
        if ($('#f-state')) $('#f-state').value = g.state;
      } else {
        state.near = [g.lat, g.lng]; state.label = g.label; state.typed = text;
        state.st = ''; state.city = ''; state.sort = 'distance';
        if ($('#f-state') && !quiet) $('#f-state').value = '';
      }
      if ($('#f-where')) $('#f-where').value = g.state ? '' : text;
      apply();
    });
  }
  var startPlace = params.get('near') || params.get('where') || params.get('zip') || '';

  function syncURL() {
    var p = new URLSearchParams();
    if (state.q) p.set('q', state.q);
    if (state.cats.length) p.set('cat', state.cats.join(','));
    if (state.city) p.set('city', state.city);
    if (state.st) p.set('state', state.st);
    if (state.tele) p.set('tele', '1');
    if (state.sort !== 'name') p.set('sort', state.sort);
    if (state.near) {
      if (state.typed) p.set('near', state.typed);
      else { p.set('lat', state.near[0]); p.set('lng', state.near[1]); }
      p.set('radius', state.radius);
    }
    history.replaceState(null, '', location.pathname + (p.toString() ? '?' + p : ''));
  }

  function apply() {
    var q = state.q.trim().toLowerCase();
    var shown = [], nearest = null;

    records.forEach(function (el) {
      var d = el.dataset, ok = true;
      if (state.cats.length) {
        var mine = d.cats.split(' ');
        ok = state.cats.some(function (c) { return mine.indexOf(c) > -1; });
      }
      if (ok && state.city && d.city !== state.city) ok = false;
      if (ok && state.st && d.state !== state.st) ok = false;
      if (ok && state.tele && d.tele !== '1') ok = false;
      if (ok && q && d.text.indexOf(q) === -1 && d.name.toLowerCase().indexOf(q) === -1) ok = false;

      var dist = null;
      if (ok && state.near) {
        var la = parseFloat(d.lat), ln = parseFloat(d.lng);
        dist = (isFinite(la) && isFinite(ln)) ? miles(state.near[0], state.near[1], la, ln) : null;
        if (dist === null) ok = false;
        else {
          if (nearest === null || dist < nearest) nearest = dist;
          if (state.radius && dist > state.radius) ok = false;
        }
      }
      el._dist = dist;
      var span = $('.record-dist', el);
      if (span) span.textContent = (ok && dist !== null) ? '· ' + dist.toFixed(1) + ' mi' : '';
      el.hidden = !ok;
      if (ok) shown.push(el);
    });

    var by = {
      name: function (a, b) { return a.dataset.name.localeCompare(b.dataset.name); },
      years: function (a, b) { return Number(a.dataset.since) - Number(b.dataset.since); },
      distance: function (a, b) { return (a._dist === null ? 1e9 : a._dist) - (b._dist === null ? 1e9 : b._dist); }
    };
    var mode = (state.sort === 'distance' && !state.near) ? 'name' : state.sort;
    shown.sort(by[mode] || by.name).forEach(function (el) { list.appendChild(el); });

    $('#count').textContent = shown.length;
    $('#count-word').textContent = shown.length === 1 ? 'practitioner' : 'practitioners';
    $('#count-where').textContent = !state.near ? '' :
      state.radius ? ' within ' + state.radius + ' mi of ' + state.label : ' nearest to ' + state.label;
    $('#empty').hidden = shown.length > 0;
    var wider = $('#empty-wider'), emsg = $('#empty-msg');
    if (wider && emsg) {
      var widen = null;
      if (!shown.length && state.near && nearest !== null) {
        widen = [10, 25, 50, 100, 250].filter(function (r) { return r >= nearest; })[0] || 0;
      }
      wider.hidden = widen === null;
      if (widen !== null) {
        emsg.textContent = 'The closest match is about ' + Math.round(nearest) + ' miles from ' + state.label +
          '. Many practitioners also see people by telehealth.';
        var wb = $('#empty-widen');
        wb.textContent = widen ? 'Show within ' + widen + ' miles' : 'Show at any distance';
        wb.onclick = function () { state.radius = widen; if ($('#f-radius')) $('#f-radius').value = String(widen); apply(); };
      } else {
        emsg.textContent = 'Try widening the distance, choosing another kind of care, or searching a nearby city. Many practitioners also offer telehealth.';
      }
    }
    var distOpt = $('#f-sort option[value="distance"]');
    if (distOpt) distOpt.disabled = !state.near;
    if ($('#f-sort')) $('#f-sort').value = mode;

    chips();
    syncURL();
  }

  function chips() {
    var box = $('#active-filters');
    if (!box) return;
    var bits = [];
    if (state.q) bits.push(['q', '\u201C' + state.q + '\u201D']);
    state.cats.forEach(function (c) {
      var cb = $('[data-cat="' + c + '"]');
      bits.push(['cat:' + c, cb ? cb.parentNode.textContent.trim().replace(/\s*\d+$/, '') : c]);
    });
    if (state.city) bits.push(['city', state.city]);
    if (state.st) {
      var sel = $('#f-state option[value="' + state.st + '"]');
      bits.push(['state', sel ? sel.textContent.replace(/\s*\(\d+\)$/, '') : state.st]);
    }
    if (state.tele) bits.push(['tele', 'Telehealth']);
    if (state.near) bits.push(['near', state.radius ? state.radius + ' mi of ' + state.label : 'Near ' + state.label]);
    box.innerHTML = bits.map(function (b) {
      return '<span class="tagx">' + b[1] +
             '<button data-drop="' + b[0] + '" aria-label="Remove filter">\u00D7</button></span>';
    }).join('');
    $$('[data-drop]', box).forEach(function (btn) {
      btn.addEventListener('click', function () {
        var k = btn.dataset.drop;
        if (k === 'q') { state.q = ''; if ($('#f-q')) $('#f-q').value = ''; }
        else if (k === 'city') { state.city = ''; }
        else if (k === 'state') { state.st = ''; if ($('#f-state')) $('#f-state').value = ''; }
        else if (k === 'tele') { state.tele = false; if ($('#f-tele')) $('#f-tele').checked = false; }
        else if (k === 'near') { state.near = null; state.label = ''; state.typed = ''; state.sort = 'name'; if ($('#f-where')) $('#f-where').value = ''; }
        else if (k.indexOf('cat:') === 0) {
          var key = k.slice(4);
          state.cats = state.cats.filter(function (c) { return c !== key; });
          var cb = $('[data-cat="' + key + '"]');
          if (cb) cb.checked = false;
        }
        apply();
      });
    });
  }

  var rail = $('#rail'), railToggle = $('#rail-toggle');
  if (rail && railToggle) railToggle.addEventListener('click', function () {
    var open = rail.classList.toggle('open');
    railToggle.setAttribute('aria-expanded', open);
  });

  var t;
  if ($('#f-q')) $('#f-q').addEventListener('input', function (e) {
    clearTimeout(t);
    var v = e.target.value;
    t = setTimeout(function () { state.q = v.trim(); apply(); }, 250);
  });
  /* one discipline at a time: a new choice replaces the old one, and on a
     discipline's own page it opens that discipline's page instead */
  $$('[data-cat]').forEach(function (cb) {
    cb.addEventListener('change', function () {
      if (cb.dataset.href) { location.href = cb.dataset.href; return; }
      var k = cb.dataset.cat;
      $$('[data-cat]').forEach(function (o) { if (o !== cb) o.checked = false; });
      state.cats = cb.checked ? [k] : [];
      apply();
    });
  });
  if ($('#f-state')) $('#f-state').addEventListener('change', function (e) {
    state.st = e.target.value; state.city = ''; apply();
  });
  if ($('#f-tele')) $('#f-tele').addEventListener('change', function (e) { state.tele = e.target.checked; apply(); });
  if ($('#f-sort')) $('#f-sort').addEventListener('change', function (e) { state.sort = e.target.value; apply(); });
  if ($('#f-radius')) $('#f-radius').addEventListener('change', function (e) {
    state.radius = Number(e.target.value); apply();
  });
  if ($('#where-bar')) $('#where-bar').addEventListener('submit', function (e) {
    e.preventDefault();
    goTo($('#f-where').value);
  });
  if ($('#f-near')) $('#f-near').addEventListener('click', function () {
    locate(function (lat, lng) {
      state.near = [Number(lat), Number(lng)];
      state.label = 'your location'; state.typed = ''; state.sort = 'distance';
      if ($('#f-where')) $('#f-where').value = '';
      say(''); apply();
    }, say);
  });
  function clearAll() { location.href = location.pathname; }
  if ($('#f-clear')) $('#f-clear').addEventListener('click', clearAll);
  if ($('#empty-clear')) $('#empty-clear').addEventListener('click', clearAll);

  apply();
  if (startPlace) { if ($('#f-where')) $('#f-where').value = startPlace; goTo(startPlace, true); }
})();

/* ---------- join form ----------
   Posts to Formspree when an endpoint is configured on the form's action.
   If it isn't configured, or the request fails, it falls back to opening a
   pre-filled email so an application is never silently lost. */
(function () {
  'use strict';
  var form = document.getElementById('join-form');
  if (!form) return;
  var $ = function (id) { return document.getElementById(id); };
  var val = function (id) { var el = $(id); return el ? el.value.trim() : ''; };
  var radio = function (name) {
    var el = form.querySelector('input[name="' + name + '"]:checked');
    return el ? el.value : '';
  };
  var cats = [], pays = [];

  /* a gentle reminder, never a block: licensed, but no number given */
  function nudgeLicence() {
    var n = $('licence-nudge');
    if (n) n.hidden = !(radio('licensed') === 'Yes' && !val('j-license'));
  }
  Array.prototype.forEach.call(form.querySelectorAll('input[name="licensed"]'), function (r) {
    r.addEventListener('change', nudgeLicence);
  });
  if ($('j-license')) $('j-license').addEventListener('input', nudgeLicence);

  function toggler(attr, bucket, carrierId, errKey) {
    Array.prototype.forEach.call(form.querySelectorAll('[' + attr + ']'), function (c) {
      c.addEventListener('click', function () {
        var k = c.getAttribute(attr), i = bucket.indexOf(k);
        if (i > -1) bucket.splice(i, 1); else bucket.push(k);
        c.setAttribute('aria-pressed', i === -1);
        var carrier = $(carrierId);
        if (carrier) carrier.value = bucket.join(', ');
        var err = form.querySelector('[data-for="' + errKey + '"]');
        if (err && bucket.length) err.style.display = 'none';
      });
    });
  }
  toggler('data-jcat', cats, 'j-cats-value', 'cats');
  toggler('data-jpay', pays, 'j-pay-value', 'pay');

  var longEl = $('j-long'), wc = $('wordcount');
  if (longEl && wc) longEl.addEventListener('input', function () {
    var n = longEl.value.trim() ? longEl.value.trim().split(/\s+/).length : 0;
    wc.textContent = n;
    wc.style.color = n > 150 ? 'var(--accent)' : '';
  });

  // Two images maximum, 10 MB each — checked before anything is sent.
  var MAX_FILES = 2, MAX_BYTES = 10 * 1024 * 1024;
  var filesEl = $('j-files'), fileList = $('file-list');
  var fileProblem = '';
  function filesValid() {
    fileProblem = '';
    if (!filesEl || !filesEl.files.length) return true;
    if (filesEl.files.length > MAX_FILES) {
      fileProblem = 'Choose no more than two images.';
      return false;
    }
    for (var i = 0; i < filesEl.files.length; i++) {
      var f = filesEl.files[i];
      if (f.size > MAX_BYTES) {
        fileProblem = f.name + ' is ' + Math.round(f.size / 1048576) +
                      ' MB — the limit is 10 MB per image.';
        return false;
      }
      if (f.type && f.type.indexOf('image/') !== 0) {
        fileProblem = f.name + ' is not an image.';
        return false;
      }
    }
    return true;
  }
  if (filesEl) filesEl.addEventListener('change', function () {
    var names = [];
    for (var i = 0; i < filesEl.files.length; i++) {
      names.push(filesEl.files[i].name +
        ' (' + Math.round(filesEl.files[i].size / 1024) + ' KB)');
    }
    if (fileList) fileList.textContent = names.join(' \u00b7 ');
    var err = form.querySelector('[data-for="files"]');
    var okFiles = filesValid();
    if (err) {
      err.textContent = fileProblem || 'Choose no more than two images, 10 MB each.';
      err.style.display = okFiles ? 'none' : 'block';
    }
  });

  function showErr(sel, on) {
    var el = form.querySelector(sel);
    if (el) el.style.display = on ? 'block' : 'none';
  }

  /* ---------- five steps, one at a time ----------
     Without JavaScript every step shows and the form works as one page. */
  var steps = Array.prototype.slice.call(form.querySelectorAll('.join-step'));
  var cur = 1;
  var REQUIRED = ['j-first', 'j-last', 'j-practice', 'j-email', 'j-phone', 'j-website',
                  'j-city', 'j-state', 'j-zip', 'j-short', 'j-since', 'j-training',
                  'j-fees', 'j-long', 'j-size'];
  var RADIOS = ['physical', 'licensed', 'telehealth', 'openins', 'ehr'];
  function showStep(n, focus) {
    cur = Math.max(1, Math.min(n, steps.length));
    steps.forEach(function (st) { st.hidden = Number(st.dataset.step) !== cur; });
    var prog = $('join-progress');
    if (prog) prog.hidden = false;
    var lab = $('join-step-label'), name = steps[cur - 1] ? steps[cur - 1].dataset.name : '';
    if (lab) lab.textContent = 'Step ' + cur + ' of ' + steps.length + ' \u00b7 ' + name;
    var fill = $('join-bar-fill');
    if (fill) fill.style.width = (cur / steps.length * 100) + '%';
    var back = $('j-back'), next = $('j-next'), send = $('j-send');
    if (back) back.hidden = cur === 1;
    if (next) next.hidden = cur === steps.length;
    if (send) send.hidden = cur !== steps.length;
    var gate = document.getElementById('join-gate');
    if (gate) gate.style.display = cur === 1 ? '' : 'none';
    var msg = $('join-msg'); if (msg) msg.textContent = '';
    if (focus) {
      var top = form.getBoundingClientRect().top + window.scrollY - 120;
      window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    }
  }
  function stepOk(st) {
    var ok = true;
    var need = REQUIRED.slice();
    if (radio('physical') === 'Yes') need.push('j-addr1');
    need.forEach(function (id) {
      var el = $(id);
      if (!el || !st.contains(el)) return;
      var bad = !el.value.trim() ||
                (el.type === 'email' && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(el.value));
      el.setAttribute('aria-invalid', bad);
      if (bad) ok = false;
    });
    RADIOS.forEach(function (n) {
      if (!st.querySelector('input[name="' + n + '"]')) return;
      var missing = !radio(n);
      showErr('[data-for="' + n + '"]', missing);
      if (missing) ok = false;
    });
    if (st.querySelector('#j-cats')) { showErr('[data-for="cats"]', !cats.length); if (!cats.length) ok = false; }
    if (st.querySelector('#j-pay')) { showErr('[data-for="pay"]', !pays.length); if (!pays.length) ok = false; }
    if (st.querySelector('#j-files') && !filesValid()) { showErr('[data-for="files"]', true); ok = false; }
    return ok;
  }
  function firstProblemStep() {
    for (var i = 0; i < steps.length; i++) {
      var bad = steps[i].querySelector('[aria-invalid="true"]');
      var errs = Array.prototype.filter.call(steps[i].querySelectorAll('.err[data-for]'),
        function (e) { return e.style.display === 'block'; });
      if (bad || errs.length) return i + 1;
    }
    return 0;
  }
  if (steps.length) {
    showStep(1);
    var nextBtn = $('j-next'), backBtn = $('j-back');
    if (nextBtn) nextBtn.addEventListener('click', function () {
      if (!stepOk(steps[cur - 1])) {
        var m = $('join-msg');
        if (m) m.textContent = 'A few answers are still needed, marked above.';
        var firstBad = steps[cur - 1].querySelector('[aria-invalid="true"]');
        if (firstBad) firstBad.scrollIntoView({ block: 'center' });
        return;
      }
      showStep(cur + 1, true);
    });
    if (backBtn) backBtn.addEventListener('click', function () { showStep(cur - 1, true); });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var ok = true;

    var required = ['j-first', 'j-last', 'j-practice', 'j-email', 'j-phone', 'j-website',
                    'j-city', 'j-state', 'j-zip', 'j-short', 'j-since', 'j-training',
                    'j-fees', 'j-long', 'j-size'];
    if (radio('physical') === 'Yes') required.push('j-addr1');

    required.forEach(function (id) {
      var el = $(id);
      if (!el) return;
      var bad = !el.value.trim() ||
                (el.type === 'email' && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(el.value));
      el.setAttribute('aria-invalid', bad);
      if (bad) ok = false;
    });

    ['physical', 'licensed', 'telehealth', 'openins', 'ehr'].forEach(function (n) {
      var missing = !radio(n);
      showErr('[data-for="' + n + '"]', missing);
      if (missing) ok = false;
    });
    showErr('[data-for="cats"]', !cats.length);
    showErr('[data-for="pay"]', !pays.length);
    if (!cats.length || !pays.length) ok = false;
    showErr('[data-for="files"]', !filesValid());
    if (!filesValid()) ok = false;

    var attest = $('j-attest');
    showErr('[data-for="attest"]', !(attest && attest.checked));
    if (!attest || !attest.checked) ok = false;

    var msg = $('join-msg');
    if (!ok) {
      if (steps.length) {
        var where = firstProblemStep();
        if (where && where !== cur) showStep(where, true);
        msg = $('join-msg');
      }
      msg.textContent = 'A few answers are still needed, marked above.';
      var firstBad = form.querySelector('[aria-invalid="true"]');
      if (firstBad) firstBad.scrollIntoView({ block: 'center' });
      return;
    }
    msg.textContent = '';

    // Plain-text version, used only for the email fallback.
    function bl(title, rows) {
      var kept = rows.filter(function (r) { return r[1]; });
      if (!kept.length) return '';
      return title + '\n' + kept.map(function (r) { return r[0] + ': ' + r[1]; }).join('\n') + '\n\n';
    }
    var addr = [val('j-addr1'), val('j-addr2'),
                val('j-city') + ', ' + val('j-state') + ' ' + val('j-zip'),
                val('j-country')].filter(Boolean).join(', ');
    var body =
      bl('PROVIDER', [
        ['Provider name', (val('j-first') + ' ' + val('j-last')).trim()],
        ['Practice or business name', val('j-practice')],
        ['Email', val('j-email')], ['Phone', val('j-phone')],
        ['Website', val('j-website')], ['Social media', val('j-social')]]) +
      bl('LOCATION', [
        ['Physical location', radio('physical')],
        ['Address', radio('physical') === 'Yes' ? addr : 'No public premises']]) +
      bl('SCOPE OF PRACTICE', [
        ['Scope of practice', cats.join(', ')],
        ['Describe your practice', val('j-short')]]) +
      bl('CREDENTIALS & EXPERIENCE', [
        ['Holds a state license', radio('licensed')],
        ['State(s) and license number(s)', val('j-license')],
        ['Certificates or affiliations', val('j-certs')],
        ['Years in practice', val('j-since')],
        ['Primary training and education', val('j-training')]]) +
      bl('PRICING & INSURANCE', [
        ['Payment methods', pays.join(', ')],
        ['Pricing structure', val('j-fees')],
        ['Virtual/telehealth services', radio('telehealth')]]) +
      bl('LISTING DESCRIPTION', [['Description', val('j-long')]]) +
      bl('ATTESTATION', [
        ['Confirmed accurate and current', $('j-attest') && $('j-attest').checked ? 'Yes' : 'No']]) +
      bl('ADDITIONAL QUESTIONS \u2014 NOT PUBLISHED', [
        ['Desired size of practice', val('j-size')],
        ['Open to insurance if available', radio('openins')],
        ['Uses an EHR', radio('ehr')]]);

    var subject = 'Directory application \u2014 ' + val('j-practice');
    if ($('j-subject')) $('j-subject').value = subject;
    $('join-mail').href = 'mailto:info@findwelldirectory.com?subject=' +
      encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);

    var done = $('join-done'), title = $('join-done-title'),
        text = $('join-done-body'), mailWrap = $('join-mail-wrap');

    function reveal() { done.style.display = 'block'; done.scrollIntoView({ block: 'nearest' }); }
    function fallback(reason) {
      title.textContent = 'Almost there \u2014 one more step.';
      text.textContent = ' ' + reason + ' Press the button below to open your answers in an email, ' +
                         'then send it. Attach your logo or headshot to that email \u2014 ' +
                         'files chosen above cannot travel this way.';
      mailWrap.hidden = false;
      reveal();
    }

    var endpoint = form.getAttribute('action');
    if (!endpoint) { fallback('This form is not connected to a server yet.'); return; }

    // A 404 here means the API worker is not deployed yet; the catch below
    // turns that into the email fallback rather than a dead end.

    var btn = form.querySelector('button[type="submit"]');
    if (btn) { btn.disabled = true; btn.textContent = 'Sending\u2026'; }

    fetch(endpoint, {
      method: 'POST',
      body: new FormData(form),
      headers: { Accept: 'application/json' }
    }).then(function (res) {
      if (btn) { btn.disabled = false; btn.textContent = 'Send my application'; }
      if (!res.ok) return res.json().catch(function () { return {}; }).then(function (d) {
        throw new Error(d.error || 'rejected');
      });
      title.textContent = 'Thank you for your submission.';
      text.textContent = ' We have emailed you a confirmation. Your listing will be published ' +
                         'shortly, and we will email you again as soon as it is live.';
      mailWrap.hidden = true;
      reveal();
      form.reset();
      cats.length = 0; pays.length = 0;
      Array.prototype.forEach.call(form.querySelectorAll('[aria-pressed]'), function (c) {
        c.setAttribute('aria-pressed', 'false');
      });
      if ($('j-cats-value')) $('j-cats-value').value = '';
      if ($('j-pay-value')) $('j-pay-value').value = '';
      if (steps.length) { showStep(1); form.hidden = true; }
    }).catch(function (err) {
      if (btn) { btn.disabled = false; btn.textContent = 'Send my application'; }
      fallback(err && err.message && err.message !== 'rejected'
        ? err.message : 'We could not reach the server.');
    });
  });
})();
