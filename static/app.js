// Dublin Spots front-end: Leaflet map talking to the Django REST API.

const COLORS = {cafe: '#8c510a', park: '#1b7837', museum: '#762a83', library: '#2166ac', transport: '#b2182b', landmark: '#e08214'};

const map = L.map('map').setView([53.345, -6.262], 13);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);
L.control.scale().addTo(map);

const areasLayer = L.geoJSON(null, {style: {color: '#555', weight: 1, fillOpacity: 0.08}}).addTo(map);
const routesLayer = L.geoJSON(null, {style: f => ({color: f.properties.kind === 'cycle' ? '#d6604d' : '#4393c3', weight: 5})}).addTo(map);
const placesLayer = L.geoJSON(null, {pointToLayer: placeMarker, onEachFeature: bindPlacePopup}).addTo(map);
const highlightLayer = L.layerGroup().addTo(map);
L.control.layers(null, {Areas: areasLayer, Routes: routesLayer, Places: placesLayer}).addTo(map);

const modal = new bootstrap.Modal('#placeModal');
let addMode = false;
let editing = null; // {id} when editing, {lat, lng} when creating

// ---------- helpers ----------

function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s ?? '';
    return div.innerHTML;
}

function csrfToken() {
    return document.cookie.split('; ').find(c => c.startsWith('csrftoken='))?.split('=')[1];
}

async function api(url, options = {}) {
    const res = await fetch(url, {
        ...options,
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken()},
    });
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(Object.values(body).flat().join(' ') || res.statusText);
    }
    return res.status === 204 ? null : res.json();
}

function placeMarker(feature, latlng) {
    // bubblingMouseEvents off so clicking a marker doesn't also run the map's "nearest" query
    return L.circleMarker(latlng, {radius: 8, color: '#fff', weight: 2, fillOpacity: 0.9, bubblingMouseEvents: false,
                                   fillColor: COLORS[feature.properties.category] || '#333'});
}

function bindPlacePopup(feature, layer) {
    const p = feature.properties;
    let html = `<strong>${escapeHtml(p.name)}</strong><br><span class="text-muted">${escapeHtml(p.category)}</span>`;
    if (p.description) html += `<p class="mb-1">${escapeHtml(p.description)}</p>`;
    if (p.distance_m != null) html += `<div>${p.distance_m} m away</div>`;
    if (LOGGED_IN) {
        html += `<div class="mt-2"><button class="btn btn-sm btn-outline-primary" onclick="editPlace(${feature.id})">Edit</button>
                 <button class="btn btn-sm btn-outline-danger" onclick="deletePlace(${feature.id})">Delete</button></div>`;
    }
    layer.bindPopup(html);
}

function showResults(title, features) {
    document.getElementById('resultsTitle').textContent = `${title} (${features.length})`;
    const list = document.getElementById('results');
    list.innerHTML = '';
    for (const f of features) {
        const item = document.createElement('button');
        item.className = 'list-group-item list-group-item-action';
        item.textContent = f.properties.name + (f.properties.distance_m != null ? ` - ${f.properties.distance_m} m` : '');
        item.onclick = () => {
            const [lng, lat] = f.geometry.coordinates;
            map.flyTo([lat, lng], 16);
            placesLayer.eachLayer(l => { if (l.feature.id === f.id) l.openPopup(); });
        };
        list.appendChild(item);
    }
    highlightLayer.clearLayers();
    L.geoJSON({type: 'FeatureCollection', features}, {
        pointToLayer: (f, latlng) => L.circleMarker(latlng, {radius: 14, color: '#ffd400', weight: 4, fill: false}),
        interactive: false,
    }).addTo(highlightLayer);
}

function reportError(err) {
    document.getElementById('resultsTitle').textContent = 'Error: ' + err.message;
}

// ---------- loading ----------

async function loadPlaces() {
    const category = document.getElementById('category').value;
    const data = await api('/api/places/' + (category ? `?category=${encodeURIComponent(category)}` : ''));
    placesLayer.clearLayers().addData(data);
}

async function loadAll() {
    const [areas, routes] = await Promise.all([api('/api/neighbourhoods/'), api('/api/routes/')]);
    areasLayer.addData(areas);
    routesLayer.addData(routes);
    await loadPlaces();
}

// ---------- spatial queries ----------

// 1. Nearest places to a clicked point (or add a place in add mode)
map.on('click', async e => {
    if (addMode) {
        toggleAddMode(false);
        openForm({lat: e.latlng.lat, lng: e.latlng.lng}, {name: '', category: 'cafe', description: ''});
        return;
    }
    try {
        const category = document.getElementById('category').value;
        const qs = new URLSearchParams({lat: e.latlng.lat, lng: e.latlng.lng, limit: 5});
        if (category) qs.set('category', category);
        const data = await api('/api/places/nearest/?' + qs);
        showResults('Nearest places', data.features);
        L.circleMarker(e.latlng, {radius: 5, color: '#000'}).addTo(highlightLayer);
    } catch (err) { reportError(err); }
});

// 2. Places inside / routes crossing a neighbourhood
areasLayer.on('click', async e => {
    if (addMode) return; // let the map click handler place the point
    L.DomEvent.stopPropagation(e);
    try {
        const area = e.layer.feature;
        const data = await api(`/api/neighbourhoods/${area.id}/contents/`);
        const routes = data.routes.features.map(r => r.properties.name).join(', ') || 'none';
        showResults(`In ${area.properties.name} (routes: ${routes})`, data.places.features);
        L.geoJSON(area, {style: {color: '#ffd400', weight: 3, fill: false}, interactive: false}).addTo(highlightLayer);
    } catch (err) { reportError(err); }
});

// 3. Places within a buffer of a route
let lastRoute = null; // re-queried when the distance box changes

routesLayer.on('click', e => {
    if (addMode) return;
    L.DomEvent.stopPropagation(e);
    lastRoute = e.layer.feature;
    queryRoute(lastRoute);
});

document.getElementById('buffer').addEventListener('change', () => { if (lastRoute) queryRoute(lastRoute); });

async function queryRoute(route) {
    try {
        const distance = document.getElementById('buffer').value;
        const data = await api(`/api/routes/${route.id}/nearby/?distance=${encodeURIComponent(distance)}`);
        showResults(`Within ${distance} m of ${route.properties.name}`, data.places.features);
        L.geoJSON(JSON.parse(data.corridor), {style: {color: '#ffd400', weight: 1, fillOpacity: 0.2}, interactive: false})
            .addTo(highlightLayer);
    } catch (err) { reportError(err); }
}

// ---------- CRUD ----------

function toggleAddMode(on) {
    addMode = on;
    const btn = document.getElementById('addBtn');
    btn.textContent = on ? 'Click the map… (cancel)' : 'Add a place';
    btn.setAttribute('aria-pressed', on);
    document.getElementById('map').classList.toggle('map-adding', on);
}

function openForm(target, props) {
    editing = target;
    document.getElementById('placeModalTitle').textContent = target.id ? 'Edit place' : 'New place';
    document.getElementById('fName').value = props.name;
    document.getElementById('fCategory').value = props.category;
    document.getElementById('fDescription').value = props.description || '';
    document.getElementById('fCoords').textContent = target.id ? '' : `Location: ${target.lat.toFixed(5)}, ${target.lng.toFixed(5)}`;
    document.getElementById('formError').classList.add('d-none');
    modal.show();
}

function findPlace(id) {
    let found;
    placesLayer.eachLayer(l => { if (l.feature.id === id) found = l.feature; });
    return found;
}

window.editPlace = id => openForm({id}, findPlace(id).properties);

window.deletePlace = async id => {
    if (!confirm('Delete this place?')) return;
    try {
        await api(`/api/places/${id}/`, {method: 'DELETE'});
        map.closePopup();
        await loadPlaces();
    } catch (err) { reportError(err); }
};

document.getElementById('placeForm').addEventListener('submit', async e => {
    e.preventDefault();
    const properties = {
        name: document.getElementById('fName').value,
        category: document.getElementById('fCategory').value,
        description: document.getElementById('fDescription').value,
    };
    try {
        if (editing.id) {
            await api(`/api/places/${editing.id}/`, {method: 'PATCH', body: JSON.stringify({properties})});
        } else {
            const geometry = {type: 'Point', coordinates: [editing.lng, editing.lat]};
            await api('/api/places/', {method: 'POST', body: JSON.stringify({type: 'Feature', geometry, properties})});
        }
        modal.hide();
        map.closePopup();
        await loadPlaces();
    } catch (err) {
        const box = document.getElementById('formError');
        box.textContent = err.message;
        box.classList.remove('d-none');
    }
});

document.getElementById('addBtn')?.addEventListener('click', () => toggleAddMode(!addMode));
document.getElementById('category').addEventListener('change', () => loadPlaces().catch(reportError));

loadAll().catch(reportError);
