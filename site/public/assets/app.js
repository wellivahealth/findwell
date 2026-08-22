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
      else if (loc) p.set('city', loc.split(',')[0].trim());
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
  var state = { q: '', cats: [], city: '', tele: false, sort: 'name', near: null, radius: 50, label: '' };

  var params = new URLSearchParams(location.search);
  state.q = params.get('q') || '';
  state.cats = (params.get('cat') || '').split(',').filter(Boolean);
  state.city = params.get('city') || '';
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
  if ($('#f-city')) $('#f-city').value = state.city;
  if ($('#f-tele')) $('#f-tele').checked = state.tele;
  if ($('#f-radius')) $('#f-radius').value = state.radius;
  if ($('#f-zip') && /^\d{5}$/.test(state.label)) $('#f-zip').value = state.label;
  $$('[data-cat]').forEach(function (cb) { cb.checked = state.cats.indexOf(cb.dataset.cat) > -1; });
  var rLabel = $('label[for="f-radius"]');
  if (rLabel) rLabel.textContent = 'Within ' + state.radius + ' miles';

  function syncURL() {
    var p = new URLSearchParams();
    if (state.q) p.set('q', state.q);
    if (state.cats.length) p.set('cat', state.cats.join(','));
    if (state.city) p.set('city', state.city);
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
        else if (k === 'city') { state.city = ''; if ($('#f-city')) $('#f-city').value = ''; }
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
  if ($('#f-city')) $('#f-city').addEventListener('change', function (e) { state.city = e.target.value; apply(); });
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

/* ---------- join form ---------- */
(function () {
  'use strict';
  var form = document.getElementById('join-form');
  if (!form) return;
  var $ = function (id) { return document.getElementById(id); };
  var picked = [];

  Array.prototype.forEach.call(form.querySelectorAll('[data-jcat]'), function (c) {
    c.addEventListener('click', function () {
      var k = c.dataset.jcat, i = picked.indexOf(k);
      if (i > -1) picked.splice(i, 1); else picked.push(k);
      c.setAttribute('aria-pressed', i === -1);
    });
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var ok = true;
    ['j-practice', 'j-name', 'j-email', 'j-city'].forEach(function (id) {
      var el = $(id);
      var bad = !el.value.trim() ||
                (el.type === 'email' && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(el.value));
      el.setAttribute('aria-invalid', bad);
      if (bad) ok = false;
    });
    var msg = $('join-msg');
    if (!ok) { msg.textContent = 'Fix the highlighted fields and send again.'; return; }
    if (!picked.length) { msg.textContent = 'Select at least one discipline.'; return; }
    msg.textContent = '';

    var rows = [
      ['Practice', $('j-practice').value], ['Practitioner', $('j-name').value],
      ['Email', $('j-email').value], ['Phone', $('j-phone').value],
      ['Disciplines', picked.join(', ')], ['City', $('j-city').value], ['ZIP', $('j-zip').value],
      ['Credentials', $('j-cred').value], ['Practising since', $('j-since').value],
      ['Telehealth', $('j-tele').value], ['Training', $('j-training').value],
      ['Fees and insurance', $('j-fees').value]
    ].filter(function (r) { return r[1] && r[1].trim(); })
     .map(function (r) { return r[0] + ': ' + r[1]; }).join('\n');

    $('join-mail').href = 'mailto:info@findwelldirectory.com?subject=' +
      encodeURIComponent('Directory listing — ' + $('j-practice').value) +
      '&body=' + encodeURIComponent(rows);
    $('join-done').style.display = 'block';
  });
})();
