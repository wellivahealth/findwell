/* FindWell Directory — client behaviour.
   Every page is real HTML rendered at build time. This file only enhances:
   the menu, the home search console, filtering on directory pages, and the
   join form. With JavaScript off, all listings are still readable. */
(function () {
  'use strict';
  var $  = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* Approximate ZIP centroids. Replace with a geocoding call when the
     directory covers more ground than this. */
  var ZIPS = {
    '85704': [32.3390, -110.9950], '85712': [32.2620, -110.9060],
    '85716': [32.2540, -110.9200], '85718': [32.3080, -110.9270],
    '85719': [32.2360, -110.9430], '85749': [32.2830, -110.7420],
    '85701': [32.2180, -110.9660], '85705': [32.2412, -110.9720],
    '81428': [38.8686, -107.5931]
  };

  /* ---------- menu ---------- */
  var burger = $('#burger'), nav = $('#nav');
  if (burger && nav) {
    burger.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      burger.setAttribute('aria-expanded', open);
    });
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
      if (/^\d{5}$/.test(loc)) { p.set('zip', loc); p.set('radius', '50'); }
      else if (loc) p.set('where', loc);
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

  /* Full state names -> abbreviations, so "Arizona", "arizona" and "AZ" all work. */
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

  var params = new URLSearchParams(location.search);
  state.q = params.get('q') || '';
  state.cats = (params.get('cat') || '').split(',').filter(Boolean);
  state.city = params.get('city') || '';
  state.st = (params.get('state') || '').toUpperCase();
  state.tele = params.get('tele') === '1';
  state.sort = params.get('sort') || 'name';
  state.radius = Number(params.get('radius') || 50);
  var zip = params.get('zip');
  if (zip && ZIPS[zip]) { state.near = ZIPS[zip]; state.label = zip; state.sort = 'distance'; }
  else if (params.get('lat') && params.get('lng')) {
    state.near = [Number(params.get('lat')), Number(params.get('lng'))];
    state.label = 'your location'; state.sort = 'distance';
  }

  /* reflect state into the controls */
  if ($('#f-q')) $('#f-q').value = state.q;
  if ($('#f-state')) $('#f-state').value = state.st;
  if ($('#f-tele')) $('#f-tele').checked = state.tele;
  if ($('#f-radius')) $('#f-radius').value = state.radius;
  if ($('#f-zip') && /^\d{5}$/.test(state.label)) $('#f-zip').value = state.label;
  $$('[data-cat]').forEach(function (cb) { cb.checked = state.cats.indexOf(cb.dataset.cat) > -1; });
  var where = params.get('where');
  if (where) {
    var w = where.trim().toLowerCase();
    var abbrev = STATE_NAMES[w] || (w.length === 2 ? w.toUpperCase() : '');
    var knownStates = records.map(function (r) { return r.dataset.state; });
    var knownCities = records.map(function (r) { return r.dataset.city.toLowerCase(); });
    if (abbrev && knownStates.indexOf(abbrev) > -1) state.st = abbrev;
    else if (knownCities.indexOf(w) > -1) {
      state.city = records[knownCities.indexOf(w)].dataset.city;
    } else state.q = state.q ? state.q + ' ' + where : where;
    if ($('#f-state')) $('#f-state').value = state.st;
    if ($('#f-q')) $('#f-q').value = state.q;
  }

  var rLabel = $('label[for="f-radius"]');
  if (rLabel) rLabel.textContent = 'Within ' + state.radius + ' miles';

  function syncURL() {
    var p = new URLSearchParams();
    if (state.q) p.set('q', state.q);
    if (state.cats.length) p.set('cat', state.cats.join(','));
    if (state.city) p.set('city', state.city);
    if (state.st) p.set('state', state.st);
    if (state.tele) p.set('tele', '1');
    if (state.sort !== 'name') p.set('sort', state.sort);
    if (state.near) {
      if (/^\d{5}$/.test(state.label)) p.set('zip', state.label);
      else { p.set('lat', state.near[0]); p.set('lng', state.near[1]); }
      p.set('radius', state.radius);
    }
    history.replaceState(null, '', location.pathname + (p.toString() ? '?' + p : ''));
  }

  function apply() {
    var q = state.q.trim().toLowerCase();
    var shown = [];

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
        dist = miles(state.near[0], state.near[1], Number(d.lat), Number(d.lng));
        if (dist > state.radius) ok = false;
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
    $('#count-where').textContent = state.near ? ' within ' + state.radius + ' mi of ' + state.label : '';
    $('#empty').hidden = shown.length > 0;
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
    if (state.near) bits.push(['near', state.radius + ' mi of ' + state.label]);
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
        else if (k === 'near') { state.near = null; state.label = ''; state.sort = 'name'; if ($('#f-zip')) $('#f-zip').value = ''; }
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
  $$('[data-cat]').forEach(function (cb) {
    cb.addEventListener('change', function () {
      var k = cb.dataset.cat;
      if (cb.checked) state.cats.push(k);
      else state.cats = state.cats.filter(function (c) { return c !== k; });
      apply();
    });
  });
  if ($('#f-state')) $('#f-state').addEventListener('change', function (e) {
    state.st = e.target.value; state.city = ''; apply();
  });
  if ($('#f-tele')) $('#f-tele').addEventListener('change', function (e) { state.tele = e.target.checked; apply(); });
  if ($('#f-sort')) $('#f-sort').addEventListener('change', function (e) { state.sort = e.target.value; apply(); });
  if ($('#f-radius')) {
    $('#f-radius').addEventListener('input', function (e) {
      if (rLabel) rLabel.textContent = 'Within ' + e.target.value + ' miles';
    });
    $('#f-radius').addEventListener('change', function (e) { state.radius = Number(e.target.value); apply(); });
  }
  if ($('#f-zip')) $('#f-zip').addEventListener('change', function (e) {
    var z = e.target.value.trim();
    if (ZIPS[z]) { state.near = ZIPS[z]; state.label = z; state.sort = 'distance'; apply(); }
    else if ($('#geo-msg')) $('#geo-msg').textContent = 'No coordinates for that ZIP yet.';
  });
  if ($('#f-near')) $('#f-near').addEventListener('click', function () {
    locate(function (lat, lng) {
      state.near = [Number(lat), Number(lng)];
      state.label = 'your location'; state.sort = 'distance';
      if ($('#geo-msg')) $('#geo-msg').textContent = '';
      apply();
    }, function (m) { if ($('#geo-msg')) $('#geo-msg').textContent = m; });
  });
  function clearAll() { location.href = location.pathname; }
  if ($('#f-clear')) $('#f-clear').addEventListener('click', clearAll);
  if ($('#empty-clear')) $('#empty-clear').addEventListener('click', clearAll);

  apply();
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

  function showErr(sel, on) {
    var el = form.querySelector(sel);
    if (el) el.style.display = on ? 'block' : 'none';
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

    var msg = $('join-msg');
    if (!ok) {
      msg.textContent = 'Some required answers are missing \u2014 they are marked above.';
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
                         'then send it. Attach your logo or headshot before sending.';
      mailWrap.hidden = false;
      reveal();
    }

    var endpoint = form.getAttribute('action');
    if (!endpoint) { fallback('This form is not connected to a server yet.'); return; }

    var btn = form.querySelector('button[type="submit"]');
    if (btn) { btn.disabled = true; btn.textContent = 'Sending\u2026'; }

    fetch(endpoint, {
      method: 'POST',
      body: new FormData(form),
      headers: { Accept: 'application/json' }
    }).then(function (res) {
      if (btn) { btn.disabled = false; btn.textContent = 'Send'; }
      if (!res.ok) throw new Error('rejected');
      title.textContent = 'Thank you for your submission.';
      text.textContent = ' We will get back to you shortly. If you have a logo or headshot, ' +
                         'reply to the confirmation email with it attached.';
      mailWrap.hidden = true;
      reveal();
      form.reset();
      cats.length = 0; pays.length = 0;
      Array.prototype.forEach.call(form.querySelectorAll('[aria-pressed]'), function (c) {
        c.setAttribute('aria-pressed', 'false');
      });
      if ($('j-cats-value')) $('j-cats-value').value = '';
      if ($('j-pay-value')) $('j-pay-value').value = '';
    }).catch(function () {
      if (btn) { btn.disabled = false; btn.textContent = 'Send'; }
      fallback('We could not reach the server.');
    });
  });
})();
