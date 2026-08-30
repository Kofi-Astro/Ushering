// Book Us page — interactive event-location picker (Leaflet + OpenStreetMap).
// Lets a visitor click or drag a pin to their venue instead of typing an
// address blind; the picked point is reverse-geocoded (via OSM's free
// Nominatim service) into a readable address and dropped into the
// #location field. Typing the address directly still works exactly as
// before — this is purely an assist, not a requirement.
//
// Nominatim's usage policy asks for an identifying User-Agent or Referer;
// browsers won't let JS set a custom User-Agent, but they always send the
// page's Referer, which satisfies it for this kind of light, occasional
// client-side use. A site seeing heavy booking-form traffic should move
// this behind a server-side proxy or a paid geocoding provider instead.

document.addEventListener('DOMContentLoaded', () => {
  const mapEl = document.getElementById('location-picker');
  if (!mapEl || typeof L === 'undefined') return;

  const locationInput = document.getElementById('location');
  const ACCRA = [5.6037, -0.187];

  const map = L.map(mapEl).setView(ACCRA, 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map);

  const marker = L.marker(ACCRA, { draggable: true }).addTo(map);

  async function reverseGeocode(lat, lng) {
    if (locationInput) locationInput.placeholder = 'Looking up address…';
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=17`,
        { headers: { Accept: 'application/json' } }
      );
      const data = await res.json();
      if (locationInput && data && data.display_name) {
        locationInput.value = data.display_name;
      }
    } catch (err) {
      // Offline or Nominatim unreachable — the visitor can still type the
      // address manually, so fail silently rather than blocking the form.
    } finally {
      if (locationInput) locationInput.placeholder = 'Venue and city/town';
    }
  }

  function moveMarker(lat, lng) {
    marker.setLatLng([lat, lng]);
    reverseGeocode(lat, lng);
  }

  map.on('click', (e) => moveMarker(e.latlng.lat, e.latlng.lng));
  marker.on('dragend', () => {
    const pos = marker.getLatLng();
    moveMarker(pos.lat, pos.lng);
  });
});
