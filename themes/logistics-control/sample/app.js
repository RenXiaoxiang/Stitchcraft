/* Harborline Control — logistics sample.
   Vanilla JS, localStorage persistence, no external dependencies. */
(function () {
  'use strict';

  var KEY = 'stitchcraft:logistics-control:v1';
  var STATUS_LABEL = { booked: 'Booked', 'in-transit': 'In transit', customs: 'Customs', delivered: 'Delivered', delayed: 'Delayed' };
  var SEVERITY = { low: 'Low', medium: 'Medium', high: 'High' };
  var $ = function (id) { return document.getElementById(id); };
  var state = { shipments: [], carriers: [], incidents: [], query: '', status: 'all', mode: 'all' };

  function uid(prefix) { return prefix + '-' + Math.random().toString(36).slice(2, 8); }
  function hoursFromNow(hours) { var date = new Date(Date.now() + hours * 3600000); return date.toISOString(); }
  function shortDate(value) {
    var date = new Date(value); if (isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(date);
  }
  function timeOnly(value) {
    var date = new Date(value); if (isNaN(date.getTime())) return '—';
    return new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit', timeZone: 'UTC', hour12: false }).format(date) + ' UTC';
  }

  function seed() {
    var rows = [
      ['HB-2401', 'Shanghai', 'Rotterdam', 'Northline Ocean', 'ocean', 'in-transit', 18, 18400],
      ['HB-2402', 'Singapore', 'Los Angeles', 'Pacifica Line', 'ocean', 'in-transit', 42, 22100],
      ['HB-2403', 'Hamburg', 'New York', 'Meridian Freight', 'ocean', 'customs', 8, 9600],
      ['HB-2404', 'Chicago', 'Denver', 'Redwood Road', 'road', 'delayed', 3, 1240],
      ['HB-2405', 'Tokyo', 'Seattle', 'Bluewing Air', 'air', 'in-transit', 6, 820],
      ['HB-2406', 'Rotterdam', 'Dublin', 'North Sea RoRo', 'road', 'booked', 26, 4300],
      ['HB-2407', 'Los Angeles', 'Austin', 'Redwood Road', 'road', 'delivered', -6, 980],
      ['HB-2408', 'Shenzhen', 'Hamburg', 'Northline Ocean', 'ocean', 'in-transit', 64, 16700],
      ['HB-2409', 'Dubai', 'Mumbai', 'Dune Air Cargo', 'air', 'customs', 11, 610],
      ['HB-2410', 'Antwerp', 'Barcelona', 'Meridian Freight', 'ocean', 'booked', 35, 8200],
      ['HB-2411', 'Seoul', 'Vancouver', 'Bluewing Air', 'air', 'delayed', 5, 540],
      ['HB-2412', 'Chicago', 'Atlanta', 'Redwood Road', 'road', 'in-transit', 14, 1100]
    ];
    state.shipments = rows.map(function (row, index) {
      return { id: 'shp-' + (index + 1), reference: row[0], origin: row[1], destination: row[2], carrier: row[3], mode: row[4], status: row[5], eta: hoursFromNow(row[6]), weight_kg: row[7] };
    });
    state.carriers = [
      { name: 'Northline Ocean', contact: 'ops@northline.example', on_time_rate: 94, active_shipments: 2, service_level: 'Ocean priority' },
      { name: 'Redwood Road', contact: 'dispatch@redwood.example', on_time_rate: 87, active_shipments: 3, service_level: 'Road network' },
      { name: 'Meridian Freight', contact: 'control@meridian.example', on_time_rate: 91, active_shipments: 2, service_level: 'Ocean standard' },
      { name: 'Bluewing Air', contact: 'cargo@bluewing.example', on_time_rate: 97, active_shipments: 2, service_level: 'Air express' }
    ];
    state.incidents = [
      { id: uid('inc'), shipment_id: 'shp-3', severity: 'high', summary: 'Customs requested the commercial invoice and packing list again.', opened_at: new Date(Date.now() - 2 * 3600000).toISOString(), resolved: false },
      { id: uid('inc'), shipment_id: 'shp-4', severity: 'medium', summary: 'Weather delay on the I-80 corridor; revised ETA requested.', opened_at: new Date(Date.now() - 4 * 3600000).toISOString(), resolved: false },
      { id: uid('inc'), shipment_id: 'shp-11', severity: 'low', summary: 'Air cargo shifted to the next freighter; customer notified.', opened_at: new Date(Date.now() - 6 * 3600000).toISOString(), resolved: false },
      { id: uid('inc'), shipment_id: 'shp-7', severity: 'low', summary: 'Delivery signed; proof of delivery filed.', opened_at: new Date(Date.now() - 18 * 3600000).toISOString(), resolved: true }
    ];
  }

  function load() {
    var saved = null;
    try { saved = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (error) { saved = null; }
    if (saved && Array.isArray(saved.shipments) && Array.isArray(saved.carriers) && Array.isArray(saved.incidents)) {
      state.shipments = saved.shipments; state.carriers = saved.carriers; state.incidents = saved.incidents;
    } else { seed(); save(); }
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify({ shipments: state.shipments, carriers: state.carriers, incidents: state.incidents })); }
    catch (error) { toast('Local storage is unavailable — changes only last until reload.'); }
  }

  function toast(message) {
    var node = $('toast'); if (!node) return;
    node.textContent = message; node.hidden = false;
    clearTimeout(toast.timer); toast.timer = setTimeout(function () { node.hidden = true; }, 3200);
  }
  function shipmentById(id) { return state.shipments.find(function (item) { return item.id === id; }) || null; }
  function openIncidents() { return state.incidents.filter(function (incident) { return !incident.resolved; }); }

  function renderStats() {
    var inTransit = state.shipments.filter(function (item) { return item.status === 'in-transit'; }).length;
    var delivered = state.shipments.filter(function (item) { return item.status === 'delivered'; }).length;
    var onTime = state.shipments.length ? Math.round((delivered + state.shipments.filter(function (item) { return item.status !== 'delayed'; }).length) / (state.shipments.length * 2) * 100) : 0;
    var open = openIncidents().length;
    $('stat-transit').textContent = inTransit;
    $('stat-ontime').textContent = onTime + '%';
    $('stat-incidents').textContent = open;
    $('stat-carriers').textContent = state.carriers.length;
    $('alert-count').textContent = open + (open === 1 ? ' alert' : ' alerts');
    $('network-state').textContent = open ? 'Attention needed' : 'Stable';
  }

  function filtered() {
    return state.shipments.filter(function (item) {
      var haystack = [item.reference, item.origin, item.destination, item.carrier].join(' ').toLowerCase();
      if (state.query && haystack.indexOf(state.query.toLowerCase()) < 0) return false;
      if (state.status !== 'all' && item.status !== state.status) return false;
      if (state.mode !== 'all' && item.mode !== state.mode) return false;
      return true;
    });
  }

  function renderTable() {
    var body = $('shipment-body'); body.textContent = '';
    var rows = filtered();
    rows.forEach(function (shipment) {
      var row = $('shipment-template').content.firstElementChild.cloneNode(true);
      row.querySelector('.shipment-ref').textContent = shipment.reference;
      row.querySelector('.route').textContent = shipment.origin + ' → ' + shipment.destination;
      row.querySelector('td[data-label="Carrier"]').appendChild(document.createTextNode(shipment.carrier));
      row.querySelector('.eta').textContent = shortDate(shipment.eta);
      row.querySelector('.weight').textContent = Number(shipment.weight_kg).toLocaleString() + ' kg';
      var status = row.querySelector('.status-pill');
      status.textContent = STATUS_LABEL[shipment.status] || shipment.status; status.dataset.status = shipment.status;
      body.appendChild(row);
    });
    $('shipment-empty').hidden = rows.length > 0;
    $('result-line').textContent = rows.length + ' of ' + state.shipments.length + ' shipments shown';
    $('foot-status').textContent = 'Seeded network · ' + state.shipments.length + ' shipments · local mode · updated just now';
  }

  function renderTimeline() {
    var list = $('timeline-list'); list.textContent = '';
    var upcoming = state.shipments.filter(function (item) { return item.status !== 'delivered'; })
      .sort(function (a, b) { return new Date(a.eta) - new Date(b.eta); }).slice(0, 5);
    if (!upcoming.length) {
      var empty = document.createElement('li'); empty.className = 'timeline__body'; empty.textContent = 'No hand-offs scheduled.'; list.appendChild(empty); return;
    }
    upcoming.forEach(function (shipment) {
      var item = document.createElement('li');
      var time = document.createElement('span'); time.className = 'timeline__time'; time.textContent = timeOnly(shipment.eta);
      var dot = document.createElement('span'); dot.className = 'timeline__dot'; dot.setAttribute('aria-hidden', 'true');
      var copy = document.createElement('div');
      var title = document.createElement('h3'); title.className = 'timeline__title'; title.textContent = shipment.reference + ' · ' + shipment.carrier;
      var body = document.createElement('p'); body.className = 'timeline__body'; body.textContent = shipment.origin + ' → ' + shipment.destination + ' · ' + shipment.status;
      copy.append(title, body); item.append(time, dot, copy); list.appendChild(item);
    });
  }

  function renderIncidents() {
    var lanes = $('incident-lanes'); lanes.textContent = '';
    ['high', 'medium', 'low'].forEach(function (severity) {
      var lane = $('lane-template').content.firstElementChild.cloneNode(true);
      var incidents = openIncidents().filter(function (item) { return item.severity === severity; });
      lane.querySelector('.lane__name').textContent = SEVERITY[severity] + ' severity';
      lane.querySelector('.lane__count').textContent = incidents.length + ' open';
      var cards = lane.querySelector('.lane__cards');
      incidents.forEach(function (incident) {
        var card = $('incident-template').content.firstElementChild.cloneNode(true);
        var badge = card.querySelector('.severity'); badge.textContent = SEVERITY[incident.severity]; badge.dataset.level = incident.severity;
        card.querySelector('.incident-card__time').textContent = shortDate(incident.opened_at);
        card.querySelector('.incident-card__summary').textContent = incident.summary;
        var shipment = shipmentById(incident.shipment_id);
        card.querySelector('.incident-card__shipment').textContent = shipment ? shipment.reference + ' · ' + shipment.origin + ' → ' + shipment.destination : 'Shipment removed';
        card.querySelector('.resolve').addEventListener('click', function () { incident.resolved = true; save(); renderAll(); toast('Incident resolved.'); });
        cards.appendChild(card);
      });
      if (!incidents.length) { var clear = document.createElement('p'); clear.className = 'timeline__body'; clear.textContent = 'No open incidents.'; cards.appendChild(clear); }
      lanes.appendChild(lane);
    });
  }

  function renderCarriers() {
    var host = $('carrier-grid'); host.textContent = '';
    state.carriers.forEach(function (carrier) {
      var card = document.createElement('article'); card.className = 'carrier';
      var title = document.createElement('h3'); title.textContent = carrier.name;
      var contact = document.createElement('p'); contact.textContent = carrier.service_level + ' · ' + carrier.contact;
      var bar = document.createElement('div'); bar.className = 'bar';
      var fill = document.createElement('span'); fill.style.width = Math.max(0, Math.min(100, carrier.on_time_rate)) + '%';
      bar.appendChild(fill);
      var meta = document.createElement('div'); meta.className = 'carrier__meta';
      var rate = document.createElement('span'); rate.textContent = carrier.on_time_rate + '% on time';
      var active = document.createElement('span'); active.textContent = carrier.active_shipments + ' active';
      meta.append(rate, active); card.append(title, contact, bar, meta); host.appendChild(card);
    });
  }

  function renderAll() { renderStats(); renderTable(); renderTimeline(); renderIncidents(); renderCarriers(); }

  function openIncidentForm() {
    var select = $('incident-shipment'); select.textContent = '';
    state.shipments.forEach(function (shipment) {
      var option = document.createElement('option'); option.value = shipment.id; option.textContent = shipment.reference + ' · ' + shipment.origin + ' → ' + shipment.destination; select.appendChild(option);
    });
    $('incident-summary').value = ''; $('incident-owner').value = ''; $('incident-error').hidden = true;
    var dialog = $('incident-dialog');
    if (typeof dialog.showModal === 'function') dialog.showModal(); else dialog.setAttribute('open', '');
    $('incident-summary').focus();
  }
  function closeIncidentForm() { var dialog = $('incident-dialog'); if (typeof dialog.close === 'function') dialog.close(); else dialog.removeAttribute('open'); }

  function submitIncident(event) {
    event.preventDefault();
    var summary = $('incident-summary').value.trim();
    if (!summary) { $('incident-error').textContent = 'Describe the exception first.'; $('incident-error').hidden = false; return; }
    state.incidents.unshift({ id: uid('inc'), shipment_id: $('incident-shipment').value, severity: $('incident-severity').value, summary: summary, opened_at: new Date().toISOString(), resolved: false });
    save(); closeIncidentForm(); renderAll(); toast('Incident opened. The count updated.');
  }

  function exportCsv() {
    var rows = [['reference', 'origin', 'destination', 'carrier', 'mode', 'status', 'eta', 'weight_kg']];
    state.shipments.forEach(function (item) { rows.push([item.reference, item.origin, item.destination, item.carrier, item.mode, item.status, item.eta, item.weight_kg]); });
    var csv = rows.map(function (row) { return row.map(function (value) { return '"' + String(value).replace(/"/g, '""') + '"'; }).join(','); }).join('\n');
    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    var url = URL.createObjectURL(blob); var link = document.createElement('a');
    link.href = url; link.download = 'harborline-shipments.csv'; document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url);
    toast('Shipment snapshot exported.');
  }

  function tickClock() {
    var clock = $('utc-clock'); if (!clock) return;
    var now = new Date();
    clock.textContent = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC', hour12: false }).format(now) + ' UTC';
    clock.dateTime = now.toISOString();
  }

  function bind() {
    $('shipment-search').addEventListener('input', function (event) { state.query = event.target.value.trim(); renderTable(); });
    $('status-filter').addEventListener('change', function (event) { state.status = event.target.value; renderTable(); });
    $('mode-filter').addEventListener('change', function (event) { state.mode = event.target.value; renderTable(); });
    $('new-incident').addEventListener('click', openIncidentForm);
    $('incident-close').addEventListener('click', closeIncidentForm);
    $('incident-cancel').addEventListener('click', closeIncidentForm);
    $('incident-form').addEventListener('submit', submitIncident);
    $('export-csv').addEventListener('click', exportCsv);
    document.addEventListener('keydown', function (event) { if (event.key === 'Escape') closeIncidentForm(); });
    tickClock(); window.setInterval(tickClock, 30000);
  }

  function init() {
    load(); bind(); renderAll();
    $('mode-badge').textContent = (window.STITCHCRAFT_DB && window.STITCHCRAFT_DB.mode === 'remote') ? 'Remote data' : 'Local data';
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true }); else init();
})();
