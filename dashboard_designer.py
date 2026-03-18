from http.server import BaseHTTPRequestHandler, HTTPServer
import socket
import requests
import json
import os
import time
import base64
from urllib.parse import urlparse, parse_qs

PORT = int(os.getenv("DESIGNER_PORT", "8586"))
HA_BASE_URL = os.getenv("HA_BASE_URL", "http://192.168.0.180:8123")
HA_TOKEN = os.getenv("HA_TOKEN", "..-")


def get_ha_headers():
    headers = {"Accept": "application/json"}
    if HA_TOKEN:
        headers["Authorization"] = "Bearer " + HA_TOKEN
    return headers


def fetch_ha_states():
    url = HA_BASE_URL.rstrip("/") + "/api/states"
    resp = requests.get(url, headers=get_ha_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()


DESIGNER_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard Designer</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    --sidebar-w: 340px;
    --props-w: 280px;
    --bg: #1a1a2e;
    --panel: #16213e;
    --border: #334;
    --text: #e0e0e0;
    --accent: #0f3460;
    --highlight: #e94560;
}

html, body { height: 100%; overflow: hidden; font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); }

#app { display: flex; height: 100vh; }

/* ── left sidebar: entity list ── */
#sidebar {
    width: var(--sidebar-w);
    min-width: var(--sidebar-w);
    background: var(--panel);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

#sidebar header {
    padding: 12px;
    border-bottom: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 8px;
}

#sidebar header h2 { font-size: 15px; letter-spacing: .5px; }

#entitySearch {
    width: 100%;
    padding: 7px 10px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg);
    color: var(--text);
    font-size: 13px;
    outline: none;
}

#entityList {
    flex: 1;
    overflow-y: auto;
    padding: 4px 0;
}

.entity-item {
    padding: 6px 12px;
    font-size: 12px;
    cursor: grab;
    border-bottom: 1px solid rgba(255,255,255,.04);
    display: flex;
    flex-direction: column;
    gap: 1px;
    user-select: none;
}

.entity-item:hover { background: rgba(255,255,255,.06); }
.entity-item .eid { color: #8cf; font-size: 11px; word-break: break-all; }
.entity-item .eval { color: #aaa; font-size: 11px; }

/* ── center: canvas area ── */
#center {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    overflow: auto;
    background: var(--bg);
}

#toolbar {
    width: 100%;
    padding: 8px 16px;
    display: flex;
    gap: 10px;
    align-items: center;
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}

#toolbar button, #toolbar label {
    padding: 6px 14px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--accent);
    color: var(--text);
    font-size: 13px;
    cursor: pointer;
}

#toolbar button:hover, #toolbar label:hover { background: var(--highlight); }
#toolbar .spacer { flex: 1; }
#imageUpload, #htmlUpload { display: none; }

#canvasWrap {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
}

#canvas {
    position: relative;
    width: 600px;
    height: 800px;
    background: #ffffff;
    border: 2px solid var(--border);
    overflow: hidden;
    flex-shrink: 0;
}

/* items placed on canvas */
.placed {
    position: absolute;
    cursor: move;
    user-select: none;
    white-space: pre;
    font-family: Arial, Helvetica, sans-serif;
    outline: 2px solid transparent;
    padding: 2px;
}

.placed.selected { outline: 2px solid var(--highlight); }

.placed img {
    width: 100%;
    height: 100%;
    display: block;
    pointer-events: none;
}

/* resize handle */
.placed .resize-handle {
    position: absolute;
    right: -4px;
    bottom: -4px;
    width: 10px;
    height: 10px;
    background: var(--highlight);
    cursor: nwse-resize;
    border-radius: 2px;
    display: none;
}

.placed.selected .resize-handle { display: block; }

/* ── right sidebar: properties ── */
#props {
    width: var(--props-w);
    min-width: var(--props-w);
    background: var(--panel);
    border-left: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow-y: auto;
}

#props header {
    padding: 12px;
    border-bottom: 1px solid var(--border);
}

#props header h2 { font-size: 15px; }

#propsBody {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.prop-group label {
    display: block;
    font-size: 11px;
    color: #888;
    margin-bottom: 3px;
    text-transform: uppercase;
    letter-spacing: .5px;
}

.prop-group input, .prop-group select {
    width: 100%;
    padding: 5px 8px;
    border: 1px solid var(--border);
    border-radius: 5px;
    background: var(--bg);
    color: var(--text);
    font-size: 13px;
}

.prop-group input[type="color"] {
    height: 32px;
    padding: 2px;
    cursor: pointer;
}

.prop-row {
    display: flex;
    gap: 8px;
}

.prop-row .prop-group { flex: 1; }

#propDelete {
    margin-top: 16px;
    padding: 7px;
    border: 1px solid #a33;
    border-radius: 6px;
    background: #411;
    color: #f99;
    cursor: pointer;
    font-size: 13px;
}

#propDelete:hover { background: #622; }
#propsEmpty { padding: 12px; color: #666; font-size: 13px; }

/* scrollbars */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #444; border-radius: 4px; }
</style>
</head>
<body>
<div id="app">

<!-- left sidebar -->
<div id="sidebar">
    <header>
        <h2>HA Entities</h2>
        <input id="entitySearch" type="text" placeholder="Filter entities..." autocomplete="off">
    </header>
    <div id="entityList"></div>
</div>

<!-- center -->
<div id="center">
    <div id="toolbar">
        <button id="btnAddText" title="Add a static text label">+ Text</button>
        <button id="btnAddBox" title="Draw a box (rectangle) with rounded corners">+ Box</button>
        <button id="btnAddLine" title="Draw a line">+ Line</button>
        <label for="imageUpload" title="Upload an image (PNG, JPG, GIF)">+ Image</label>
        <input type="file" id="imageUpload" accept=".png,.jpg,.jpeg,.gif,image/png,image/jpeg,image/gif">
        <label for="htmlUpload" title="Import exported HTML file">Import HTML</label>
        <input type="file" id="htmlUpload" accept=".html,text/html">
        <div class="spacer"></div>
        <button id="btnExport">Export HTML</button>
    </div>
    <div id="canvasWrap">
        <div id="canvas"></div>
    </div>
</div>

<!-- right sidebar -->
<div id="props">
    <header><h2>Properties</h2></header>
    <div id="propsEmpty">Select an element on the canvas.</div>
    <div id="propsBody" style="display:none">
        <div class="prop-group">
            <label>Entity / Label</label>
            <input id="propId" type="text" readonly>
        </div>
        <div class="prop-row">
            <div class="prop-group">
                <label>X</label>
                <input id="propX" type="number" min="0" max="600">
            </div>
            <div class="prop-group">
                <label>Y</label>
                <input id="propY" type="number" min="0" max="800">
            </div>
        </div>
        <div class="prop-row">
            <div class="prop-group">
                <label>Width</label>
                <input id="propW" type="number" min="10" max="600">
            </div>
            <div class="prop-group">
                <label>Height</label>
                <input id="propH" type="number" min="10" max="800">
            </div>
        </div>
        <div class="prop-group">
            <label>Font Size (px)</label>
            <input id="propFontSize" type="number" min="8" max="200" value="24">
        </div>
        <div class="prop-group">
            <label>Font Weight</label>
            <select id="propFontWeight">
                <option value="normal">Normal</option>
                <option value="bold" selected>Bold</option>
            </select>
        </div>
        <div class="prop-group">
            <label>Update Group (for staggered refresh)</label>
            <input id="propGroup" type="number" min="1" max="10" value="1">
        </div>
        <div class="prop-group">
            <label>Color</label>
            <input id="propColor" type="color" value="#000000">
        </div>
        <div class="prop-group">
            <label>Text Content (static text only)</label>
            <input id="propText" type="text">
        </div>
        <div class="prop-group">
            <label>Border Radius (px)</label>
            <input id="propBorderRadius" type="number" min="0" max="100" value="0">
        </div>
        <div class="prop-group">
            <label>Border Width (px)</label>
            <input id="propBorderWidth" type="number" min="0" max="20" value="0">
        </div>
        <div class="prop-group">
            <label>Border Color</label>
            <input id="propBorderColor" type="color" value="#000000">
        </div>
        <div class="prop-group">
            <label>Fill Entity (box only - controls fill level)</label>
            <input id="propFillEntity" type="text" placeholder="e.g. sensor.battery_level">
        </div>
        <div class="prop-group">
            <label>Fill Direction (box with entity)</label>
            <select id="propFillDirection">
                <option value="vertical">Vertical</option>
                <option value="horizontal">Horizontal</option>
            </select>
        </div>
        <div class="prop-group">
            <label><input type="checkbox" id="propTextAlign"> Center Text</label>
        </div>
        <button id="propDelete">Delete Element</button>
    </div>
</div>

</div>

<script>
/* ── state ── */
const canvas = document.getElementById('canvas');
let entities = [];          // {entity_id, state, friendly_name, unit}
let placed = [];            // {id, kind, entityId, x, y, w, h, fontSize, fontWeight, color, text, imageFile, borderRadius, borderWidth, borderColor, fillEntity, fillDirection, group, textAlign}
let selected = null;        // id of selected placed element
let nextId = 1;
let dragSource = null;      // entity being dragged from sidebar

/* ── load entities ── */
async function loadEntities() {
    try {
        const resp = await fetch('/api/states');
        const data = await resp.json();
        if (!Array.isArray(data)) { throw new Error(data.error || 'Unexpected response'); }
        entities = data.map(e => ({
            entity_id: e.entity_id,
            state: e.state,
            friendly_name: (e.attributes && e.attributes.friendly_name) || e.entity_id,
            unit: (e.attributes && e.attributes.unit_of_measurement) || ''
        }));
        entities.sort((a, b) => a.entity_id.localeCompare(b.entity_id));
        renderEntityList();
    } catch (err) {
        document.getElementById('entityList').textContent = 'Failed to load: ' + err.message;
    }
}

function renderEntityList(filter = '') {
    const list = document.getElementById('entityList');
    list.innerHTML = '';
    const lc = filter.toLowerCase();
    for (const e of entities) {
        if (lc && !e.entity_id.toLowerCase().includes(lc) && !e.friendly_name.toLowerCase().includes(lc)) continue;
        const div = document.createElement('div');
        div.className = 'entity-item';
        div.draggable = true;
        div.innerHTML = '<span class="eid">' + esc(e.entity_id) + '</span><span class="eval">' + esc(e.state + (e.unit ? ' ' + e.unit : '')) + '</span>';
        div.addEventListener('dragstart', ev => {
            dragSource = e;
            ev.dataTransfer.effectAllowed = 'copy';
            ev.dataTransfer.setData('text/plain', e.entity_id);
        });
        list.appendChild(div);
    }
}

document.getElementById('entitySearch').addEventListener('input', e => renderEntityList(e.target.value));

/* ── canvas drop ── */
canvas.addEventListener('dragover', e => { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; });
canvas.addEventListener('drop', e => {
    e.preventDefault();
    if (!dragSource) return;
    const rect = canvas.getBoundingClientRect();
    const x = Math.round(e.clientX - rect.left);
    const y = Math.round(e.clientY - rect.top);
    addEntity(dragSource, x, y);
    dragSource = null;
});

/* ── add items ── */
function addEntity(entity, x, y) {
    const item = {
        id: nextId++,
        kind: 'entity',
        entityId: entity.entity_id,
        x: Math.max(0, x - 40),
        y: Math.max(0, y - 12),
        w: null,   // auto
        h: null,
        fontSize: 24,
        fontWeight: 'bold',
        color: '#000000',
        text: entity.state + (entity.unit ? ' ' + entity.unit : ''),
        imageFile: null,
        group: 1,
        borderRadius: 0,
        borderWidth: 0,
        borderColor: '#000000',
        fillEntity: null,
        fillDirection: 'vertical',
        textAlign: 'left'
    };
    placed.push(item);
    renderPlaced(item);
    selectItem(item.id);
}

function addText(x, y) {
    const item = {
        id: nextId++,
        kind: 'text',
        entityId: null,
        x: x || 100,
        y: y || 100,
        w: null,
        h: null,
        fontSize: 24,
        fontWeight: 'bold',
        color: '#000000',
        text: 'Label',
        imageFile: null,
        group: 1,
        borderRadius: 0,
        borderWidth: 0,
        borderColor: '#000000',
        fillEntity: null,
        fillDirection: 'vertical',
        textAlign: 'left'
    };
    placed.push(item);
    renderPlaced(item);
    selectItem(item.id);
}

function addBox(x, y) {
    const item = {
        id: nextId++,
        kind: 'box',
        entityId: null,
        x: x || 100,
        y: y || 100,
        w: 100,
        h: 100,
        fontSize: 24,
        fontWeight: 'bold',
        color: '#000000',
        text: '',
        imageFile: null,
        group: 1,
        borderRadius: 8,
        borderWidth: 2,
        borderColor: '#000000',
        fillEntity: null,
        fillDirection: 'vertical'
    };
    placed.push(item);
    renderPlaced(item);
    selectItem(item.id);
}

function addLine(x, y) {
    const item = {
        id: nextId++,
        kind: 'line',
        entityId: null,
        x: x || 100,
        y: y || 100,
        w: 200,
        h: 2,
        fontSize: 24,
        fontWeight: 'bold',
        color: '#000000',
        text: '',
        imageFile: null,
        group: 1,
        borderRadius: 0,
        borderWidth: 0,
        borderColor: '#000000',
        fillEntity: null,
        fillDirection: 'vertical',
        textAlign: 'left'
    };
    placed.push(item);
    renderPlaced(item);
    selectItem(item.id);
}

function addImage(filename) {
    const item = {
        id: nextId++,
        kind: 'image',
        entityId: null,
        x: 100,
        y: 100,
        w: 80,
        h: 80,
        fontSize: 24,
        fontWeight: 'bold',
        color: '#000000',
        text: '',
        imageFile: filename,
        group: 1,
        dataUrl: null,
        borderRadius: 0,
        borderWidth: 0,
        borderColor: '#000000',
        fillEntity: null,
        fillDirection: 'vertical',
        textAlign: 'left'
    };
    placed.push(item);
    renderPlaced(item);
    selectItem(item.id);
}

/* ── render a placed element ── */
function renderPlaced(item) {
    let el = document.getElementById('p-' + item.id);
    if (!el) {
        el = document.createElement('div');
        el.id = 'p-' + item.id;
        el.className = 'placed';

        const handle = document.createElement('div');
        handle.className = 'resize-handle';
        el.appendChild(handle);

        el.addEventListener('mousedown', ev => {
            if (ev.target.classList.contains('resize-handle')) return;
            selectItem(item.id);
            startDrag(ev, item);
        });

        handle.addEventListener('mousedown', ev => {
            ev.stopPropagation();
            selectItem(item.id);
            startResize(ev, item);
        });

        canvas.appendChild(el);
    }

    el.style.left = item.x + 'px';
    el.style.top = item.y + 'px';
    el.style.fontSize = item.fontSize + 'px';
    el.style.fontWeight = item.fontWeight;
    el.style.color = item.color;

    if (item.w) el.style.width = item.w + 'px';
    else el.style.width = 'auto';
    if (item.h) el.style.height = item.h + 'px';
    else el.style.height = 'auto';

    // Apply border and border-radius styles
    el.style.borderRadius = (item.borderRadius || 0) + 'px';
    el.style.borderWidth = (item.borderWidth || 0) + 'px';
    el.style.borderColor = item.borderColor || '#000000';
    el.style.borderStyle = item.borderWidth ? 'solid' : 'none';
    el.style.textAlign = item.textAlign || 'left';

    // content (keep resize handle)
    const handle = el.querySelector('.resize-handle');
    el.innerHTML = '';
    el.appendChild(handle);

    if (item.kind === 'box') {
        el.style.background = item.color;
        el.style.overflow = 'hidden';
    } else if (item.kind === 'line') {
        el.style.background = item.color;
        el.style.overflow = 'hidden';
        el.style.borderRadius = 'none';
    } else if ((item.kind === 'image' || item.kind === 'imported') && (item.imageFile || item.dataUrl)) {
        // Handle image display - either from file or data URL
        const img = document.createElement('img');
        if (item.dataUrl) {
            img.src = item.dataUrl;
        } else if (item.imageFile) {
            img.src = '/images/' + item.imageFile;
        }
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'contain';
        el.appendChild(img);
    } else if ((item.kind === 'svg' || item.kind === 'imported') && item.svgData) {
        // Legacy SVG support (for imports)
        const img = document.createElement('img');
        img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(item.svgData)));
        el.appendChild(img);
    } else if (item.kind === 'imported' && (!item.text || item.text.trim().length === 0) && !item.entityId) {
        // Empty imported shape (box/line that wasn't detected) - render with background
        el.style.background = item.color;
        el.style.overflow = 'hidden';
    } else {
        const span = document.createElement('span');
        span.textContent = item.text || '';
        el.appendChild(span);
    }
}

/* ── selection ── */
function selectItem(id) {
    selected = id;
    document.querySelectorAll('.placed').forEach(el => el.classList.remove('selected'));
    const el = document.getElementById('p-' + id);
    if (el) el.classList.add('selected');
    updateProps();
}

function deselectAll() {
    selected = null;
    document.querySelectorAll('.placed').forEach(el => el.classList.remove('selected'));
    updateProps();
}

canvas.addEventListener('mousedown', e => {
    if (e.target === canvas) deselectAll();
});

/* ── drag to move ── */
function startDrag(ev, item) {
    ev.preventDefault();
    const startX = ev.clientX, startY = ev.clientY;
    const origX = item.x, origY = item.y;

    function onMove(e) {
        item.x = clamp(origX + e.clientX - startX, 0, 600 - 20);
        item.y = clamp(origY + e.clientY - startY, 0, 800 - 20);
        renderPlaced(item);
        updatePropsValues();
    }
    function onUp() {
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
}

/* ── drag to resize ── */
function startResize(ev, item) {
    ev.preventDefault();
    const startX = ev.clientX, startY = ev.clientY;
    const el = document.getElementById('p-' + item.id);
    const origW = item.w || el.offsetWidth;
    const origH = item.h || el.offsetHeight;

    function onMove(e) {
        item.w = Math.max(20, origW + e.clientX - startX);
        item.h = Math.max(12, origH + e.clientY - startY);
        renderPlaced(item);
        updatePropsValues();
    }
    function onUp() {
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
}

/* ── properties panel ── */
function updateProps() {
    const body = document.getElementById('propsBody');
    const empty = document.getElementById('propsEmpty');
    if (!selected) {
        body.style.display = 'none';
        empty.style.display = 'block';
        return;
    }
    body.style.display = 'flex';
    empty.style.display = 'none';
    updatePropsValues();
}

function updatePropsValues() {
    const item = placed.find(p => p.id === selected);
    if (!item) return;
    document.getElementById('propId').value = item.entityId || item.kind;
    document.getElementById('propX').value = Math.round(item.x);
    document.getElementById('propY').value = Math.round(item.y);
    document.getElementById('propW').value = item.w ? Math.round(item.w) : '';
    document.getElementById('propH').value = item.h ? Math.round(item.h) : '';
    document.getElementById('propFontSize').value = item.fontSize;
    document.getElementById('propFontWeight').value = item.fontWeight;
    document.getElementById('propGroup').value = item.group || 1;
    document.getElementById('propColor').value = item.color;
    document.getElementById('propText').value = item.text || '';
    document.getElementById('propBorderRadius').value = item.borderRadius || 0;
    document.getElementById('propBorderWidth').value = item.borderWidth || 0;
    document.getElementById('propBorderColor').value = item.borderColor || '#000000';
    document.getElementById('propFillEntity').value = item.fillEntity || '';
    document.getElementById('propFillDirection').value = item.fillDirection || 'vertical';
    document.getElementById('propTextAlign').checked = item.textAlign === 'center';

    // Show and hide individual property groups per element type.
    const fontSizeGroup = document.getElementById('propFontSize').closest('.prop-group');
    const fontWeightGroup = document.getElementById('propFontWeight').closest('.prop-group');
    const textGroup = document.getElementById('propText').closest('.prop-group');
    const borderRadiusGroup = document.getElementById('propBorderRadius').closest('.prop-group');
    const borderWidthGroup = document.getElementById('propBorderWidth').closest('.prop-group');
    const borderColorGroup = document.getElementById('propBorderColor').closest('.prop-group');
    const fillEntityGroup = document.getElementById('propFillEntity').closest('.prop-group');
    const fillDirectionGroup = document.getElementById('propFillDirection').closest('.prop-group');

    const showTextControls = item.kind === 'text' || item.kind === 'entity' || (item.kind === 'imported' && (item.text || item.entityId));
    const showShapeControls = item.kind === 'box' || item.kind === 'line';
    const showFillControls = item.kind === 'box';

    fontSizeGroup.style.display = showTextControls ? 'block' : 'none';
    fontWeightGroup.style.display = showTextControls ? 'block' : 'none';
    textGroup.style.display = showTextControls ? 'block' : 'none';
    borderRadiusGroup.style.display = showShapeControls ? 'block' : 'none';
    borderWidthGroup.style.display = showShapeControls ? 'block' : 'none';
    borderColorGroup.style.display = showShapeControls ? 'block' : 'none';
    fillEntityGroup.style.display = showFillControls ? 'block' : 'none';
    fillDirectionGroup.style.display = showFillControls ? 'block' : 'none';
}

// bind property inputs
const propFieldsMap = {
    propId: 'entityId',
    propX: 'x',
    propY: 'y',
    propW: 'w',
    propH: 'h',
    propFontSize: 'fontSize',
    propFontWeight: 'fontWeight',
    propGroup: 'group',
    propColor: 'color',
    propText: 'text',
    propBorderRadius: 'borderRadius',
    propBorderWidth: 'borderWidth',
    propBorderColor: 'borderColor',
    propFillEntity: 'fillEntity',
    propFillDirection: 'fillDirection',
    propTextAlign: 'textAlign'
};

for (const [inputId, key] of Object.entries(propFieldsMap)) {
    if (inputId === 'propId') continue;
    const el = document.getElementById(inputId);
    const eventType = el.type === 'checkbox' ? 'change' : 'input';
    el.addEventListener(eventType, () => {
        const item = placed.find(p => p.id === selected);
        if (!item) return;
        if (key === 'x' || key === 'y' || key === 'w' || key === 'h' || key === 'fontSize' || key === 'borderRadius' || key === 'borderWidth' || key === 'group') {
            const v = parseInt(el.value, 10);
            if (!isNaN(v)) item[key] = v;
        } else if (key === 'textAlign') {
            item[key] = el.checked ? 'center' : 'left';
        } else {
            item[key] = el.value;
        }
        renderPlaced(item);
    });
}

/* ── delete ── */
document.getElementById('propDelete').addEventListener('click', () => {
    if (!selected) return;
    const el = document.getElementById('p-' + selected);
    if (el) el.remove();
    placed = placed.filter(p => p.id !== selected);
    deselectAll();
});

/* ── add text ── */
document.getElementById('btnAddText').addEventListener('click', () => addText(100, 100));
document.getElementById('btnAddBox').addEventListener('click', () => addBox(100, 100));
document.getElementById('btnAddLine').addEventListener('click', () => addLine(100, 100));

/* ── Image upload ── */
document.getElementById('imageUpload').addEventListener('change', async e => {
    const file = e.target.files[0];
    if (!file) return;
    
    // Upload the file to the server
    const formData = new FormData();
    formData.append('image', file);
    
    try {
        const response = await fetch('/api/upload_image', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Upload failed');
        }
        
        const data = await response.json();
        if (data.filename) {
            addImage(data.filename);
        } else {
            alert('Upload failed: ' + (data.error || 'Unknown error'));
        }
    } catch (err) {
        alert('Upload error: ' + err.message);
    }
    
    e.target.value = '';
});

/* ── HTML import ── */
document.getElementById('htmlUpload').addEventListener('change', e => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
        importHtml(ev.target.result);
    };
    reader.readAsText(file);
    e.target.value = '';
});

function importHtml(htmlString) {
    try {
        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlString, 'text/html');
        const board = doc.querySelector('.board');
        if (!board) {
            alert('Could not find .board element in HTML');
            return;
        }

        // Extract ENTITY_GROUPS from script tag to restore group assignments
        const entityGroupMap = {};
        const scripts = doc.querySelectorAll('script');
        for (const script of scripts) {
            const scriptText = script.textContent;
            const match = scriptText.match(/var ENTITY_GROUPS = (\{[\s\S]*?\});/);
            if (match) {
                try {
                    const groupsObj = eval('(' + match[1] + ')');
                    // Build reverse map: entityId -> groupNum
                    for (const [groupNum, entities] of Object.entries(groupsObj)) {
                        for (const entityId of entities) {
                            entityGroupMap[entityId] = parseInt(groupNum);
                        }
                    }
                } catch (e) {
                    console.warn('Could not parse ENTITY_GROUPS:', e);
                }
                break;
            }
        }

        placed = [];
        canvas.innerHTML = '';
        nextId = 1;

        const children = board.querySelectorAll('div:not(#statusText):not(#errorText)');
        for (const child of children) {
            // Check if this div contains an image
            const imgTag = child.querySelector('img');
            let imageFile = null;
            let dataUrl = null;
            let svgData = null;
            
            if (imgTag && imgTag.src) {
                // Check if it's a base64 data URL
                if (imgTag.src.startsWith('data:image/')) {
                    dataUrl = imgTag.src;
                } else {
                    // Extract filename from /images/filename.png
                    const match = imgTag.src.match(/\/images\/(.+)$/);
                    if (match) {
                        imageFile = match[1];
                    }
                }
            } else if (child.innerHTML.includes('<svg')) {
                svgData = child.innerHTML;
            }
            
            
            // Determine group from ENTITY_GROUPS if available
            let groupNum = 1;
            if (child.id) {
                // Try exact match first
                groupNum = entityGroupMap[child.id] || entityGroupMap[child.id.replace(/_/g, '.')] || 1;
            }
            
            // Detect if this is a line or box (has background, no text, no image)
            const hasBackground = child.style.background || child.style.backgroundColor;
            const hasText = child.textContent && child.textContent.trim().length > 0;
            const height = parseInt(child.style.height) || 0;
            
            let itemKind = 'imported';
            let itemColor = child.style.color || '#000000';
            
            if (hasBackground && !hasText && !imageFile && !dataUrl && !svgData && !child.id) {
                // This is a shape (line or box), not an entity
                // Extract background color
                const bgColor = child.style.background || child.style.backgroundColor;
                itemColor = bgColor;
                
                // Distinguish line from box by height
                if (height > 0 && height <= 15) {
                    itemKind = 'line';
                } else {
                    itemKind = 'box';
                }
            }
            
            const item = {
                id: nextId++,
                kind: itemKind,
                entityId: child.id || null,
                x: parseInt(child.style.left) || 0,
                y: parseInt(child.style.top) || 0,
                w: child.style.width ? parseInt(child.style.width) : null,
                h: child.style.height ? parseInt(child.style.height) : null,
                fontSize: parseInt(child.style.fontSize) || 24,
                fontWeight: child.style.fontWeight || 'normal',
                color: itemColor,
                text: child.textContent || '',
                imageFile: imageFile,
                dataUrl: dataUrl,
                svgData: svgData,
                borderRadius: parseInt(child.style.borderRadius) || 0,
                borderWidth: parseInt(child.style.borderWidth) || 0,
                borderColor: child.style.borderColor || '#000000',
                fillEntity: null,
                fillDirection: 'vertical',
                textAlign: child.style.textAlign || 'left',
                group: groupNum
            };
            placed.push(item);
            renderPlaced(item);
        }
        selectItem(placed[0]?.id || null);
    } catch (err) {
        alert('Error importing HTML: ' + err.message);
    }
}

/* ── export ── */
document.getElementById('btnExport').addEventListener('click', exportHtml);

async function exportHtml() {
    // Build the entity-to-element mapping
    const entityItems = placed.filter(p => ((p.kind === 'entity' || p.kind === 'imported') && p.entityId) || (p.kind === 'box' && p.fillEntity));
    const mapping = {};
    const fillMapping = {};
    const usedFieldIds = {};
    
    for (const item of entityItems) {
        if ((item.kind === 'entity' || item.kind === 'imported') && item.entityId) {
            let fieldId = item.entityId.replace(/\./g, '_');
            if (usedFieldIds[fieldId]) fieldId += '_' + item.id;
            usedFieldIds[fieldId] = true;
            mapping[fieldId] = item.entityId;
            item._fieldId = fieldId;
        }
        if (item.fillEntity) {
            let fillFieldId = item.fillEntity.replace(/\./g, '_');
            if (fillMapping[fillFieldId]) fillFieldId += '_' + item.id;
            fillMapping[fillFieldId] = {entity: item.fillEntity, direction: item.fillDirection, elementId: item._fieldId || ('fill_' + item.id)};
        }
    }

    // Fetch base64 data for all images that don't already have dataUrl
    const imageMap = {};
    for (const item of placed) {
        if ((item.kind === 'image' || item.kind === 'imported') && item.imageFile && !item.dataUrl && !imageMap[item.imageFile]) {
            try {
                const response = await fetch('/api/image_base64?file=' + encodeURIComponent(item.imageFile));
                const data = await response.json();
                if (data.dataUrl) {
                    imageMap[item.imageFile] = data.dataUrl;
                }
            } catch (err) {
                console.error('Failed to fetch base64 for', item.imageFile, err);
            }
        }
    }

    let cssRules = '';
    let htmlEls = '';

    for (const item of placed) {
        const style = [];
        style.push('position: absolute');
        style.push('left: ' + Math.round(item.x) + 'px');
        style.push('top: ' + Math.round(item.y) + 'px');
        if (item.w) style.push('width: ' + Math.round(item.w) + 'px');
        if (item.h) style.push('height: ' + Math.round(item.h) + 'px');
        style.push('font-size: ' + item.fontSize + 'px');
        style.push('font-weight: ' + item.fontWeight);
        style.push('color: ' + item.color);
        style.push('font-family: Arial, Helvetica, sans-serif');
        style.push('white-space: pre');
        if (item.textAlign) style.push('text-align: ' + item.textAlign);
        if (item.borderRadius) style.push('border-radius: ' + item.borderRadius + 'px');
        if (item.borderWidth) {
            style.push('border: ' + item.borderWidth + 'px solid ' + item.borderColor);
        }

        if (item.kind === 'entity') {
            const fid = item._fieldId || ('item_' + item.id);
            if (item.fillEntity) {
                // Box with fill level
                style.push('overflow: hidden');
                htmlEls += '    <div id="' + esc(fid) + '" style="' + style.join('; ') + '"><div id="' + esc(fid) + '_fill" style="position:absolute;left:0;top:0;background:' + item.color + ';overflow:hidden;width:100%;height:100%;"></div><span style="position:relative;z-index:1;display:inline-block;width:100%;height:100%;display:flex;align-items:center;justify-content:center;">' + esc(item.text) + '</span></div>\n';
                item._hasFill = true;
            } else {
                htmlEls += '    <div id="' + esc(fid) + '" style="' + style.join('; ') + '">' + esc(item.text) + '</div>\n';
            }
        } else if (item.kind === 'text') {
            htmlEls += '    <div style="' + style.join('; ') + '">' + esc(item.text) + '</div>\n';
        } else if (item.kind === 'box') {
            style.push('overflow: hidden');
            style.push('background: ' + item.color);
            if (item.fillEntity) {
                // Box with fill level
                htmlEls += '    <div style="' + style.join('; ') + '"><div id="fill_' + item.id + '" style="position:absolute;left:0;top:0;background:' + item.color + ';width:100%;height:100%;"></div></div>\n';
                item._hasFill = true;
                item._fillFieldId = 'fill_' + item.id;
            } else {
                htmlEls += '    <div style="' + style.join('; ') + '"></div>\n';
            }
        } else if (item.kind === 'line') {
            style.push('overflow: hidden');
            style.push('background: ' + item.color);
            if (item.borderRadius) style.push('border-radius: ' + item.borderRadius + 'px');
            htmlEls += '    <div style="' + style.join('; ') + '"></div>\n';
        } else if ((item.kind === 'image' || item.kind === 'imported') && (item.imageFile || item.dataUrl)) {
            // Handle image elements with base64 data or file reference
            style.push('overflow: hidden');
            let imgSrc;
            
            if (item.dataUrl) {
                // Use existing dataUrl (already base64)
                imgSrc = item.dataUrl;
            } else if (item.imageFile) {
                // Try to get base64 for file, or use imageMap if available
                imgSrc = imageMap[item.imageFile] || '/images/' + esc(item.imageFile);
            }
            
            htmlEls += '    <div style="' + style.join('; ') + '"><img src="' + imgSrc + '" style="width:100%;height:100%;object-fit:contain;"></div>\n';
        } else if (item.kind === 'svg' && item.svgData) {
            style.push('overflow: hidden');
            // For old browsers: ensure SVG has explicit width/height to fill container
            let svgData = item.svgData;
            // If SVG doesn't have width/height attributes, inject them
            if (svgData.includes('<svg') && !svgData.includes('width="100%"')) {
                svgData = svgData.replace(/<svg\s/, '<svg width="100%" height="100%" preserveAspectRatio="xMidYMid meet" ');
            }
            htmlEls += '    <div style="' + style.join('; ') + '">' + svgData + '</div>\n';
        } else if (item.kind === 'imported') {
            // Handle imported elements without imageFile
            if (item.svgData) {
                style.push('overflow: hidden');
                let svgData = item.svgData;
                if (svgData.includes('<svg') && !svgData.includes('width="100%"')) {
                    svgData = svgData.replace(/<svg\s/, '<svg width="100%" height="100%" preserveAspectRatio="xMidYMid meet" ');
                }
                htmlEls += '    <div style="' + style.join('; ') + '">' + svgData + '</div>\n';
            } else if (item.entityId) {
                // Imported entity element - use _fieldId if it was mapped
                const elemId = item._fieldId || item.entityId;
                htmlEls += '    <div id="' + esc(elemId) + '" style="' + style.join('; ') + '">' + esc(item.text) + '</div>\n';
            } else if (!item.text || item.text.trim().length === 0) {
                // Empty imported element - could be a box or line that wasn't detected
                // Export with background color if present
                style.push('overflow: hidden');
                style.push('background: ' + item.color);
                htmlEls += '    <div style="' + style.join('; ') + '"></div>\n';
            } else {
                // Static imported text
                htmlEls += '    <div style="' + style.join('; ') + '">' + esc(item.text) + '</div>\n';
            }
        }
    }

    // Build ENTITY_MAP python dict string
    let pyMap = '';
    for (const [fieldId, entityId] of Object.entries(mapping)) {
        pyMap += '    "' + fieldId + '": "' + entityId + '",\n';
    }

    let pyFillMap = '';
    for (const [fillId, fillInfo] of Object.entries(fillMapping)) {
        pyFillMap += '    "' + fillInfo.elementId + '": {"entity": "' + fillInfo.entity + '", "direction": "' + fillInfo.direction + '"},\n';
    }

    const exported = `<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta name="viewport" content="width=600, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Energy Dashboard</title>
<style>
html, body {
    margin: 0; padding: 0;
    width: 600px; height: 800px;
    overflow: hidden;
    background: #ffffff;
    color: #d8dee9;
    font-family: Arial, Helvetica, sans-serif;
}
.board {
    position: relative;
    width: 600px; height: 800px;
    background: #ffffff;
}
#statusText {
    position: absolute; left: 0; right: 0; bottom: 6px;
    text-align: center; font-size: 14px; color: #666;
}
#errorText {
    position: absolute; left: 20px; right: 20px; top: 400px;
    text-align: center; font-size: 20px; color: #fca5a5; display: none;
}
</style>
</head>
<body>
<div class="board">
` + htmlEls + `    <div id="statusText">Loading...</div>
    <div id="errorText"></div>
</div>
<script>
var HA_BASE_URL = '{{HA_BASE_URL}}';
var HA_TOKEN = '{{HA_TOKEN}}';

var ENTITIES = [
` + Object.values(mapping).map(eid => `    '${eid}'`).join(',\n') + `
];

function setText(id, value) {
    var el = document.getElementById(id);
    if (!el) return;
    if (el.innerHTML !== value) el.innerHTML = value;
}

function showError(msg) {
    var e = document.getElementById('errorText');
    if (e) { e.style.display = 'block'; e.innerHTML = msg; }
    setText('statusText', 'Error: ' + msg);
}

function clearError() {
    var e = document.getElementById('errorText');
    if (e) e.style.display = 'none';
}

\x3c/script>
</body>
</html>`;

    // also show the python ENTITY_MAP
    const pySnippet = `
# ── Paste this ENTITY_MAP into dashboard_server_ha.py ──
ENTITY_MAP = {
` + pyMap + `}

# ── Fill level mapping (for boxes with entity-controlled fill) ──
FILL_MAP = {
` + pyFillMap + `}

# ── In fetch_flow_from_ha(), build fields dict from ENTITY_MAP: ──
# fields = {}
# for field_id, entity_id in ENTITY_MAP.items():
#     fields[field_id] = read_entity_state(index, entity_id, "--")
#
# For fill level updates, calculate percentage and update fill element:
# for element_id, fill_info in FILL_MAP.items():
#     value = float(read_entity_state(index, fill_info['entity'], "0"))
#     percentage = min(100, max(0, value))
#     direction = fill_info['direction']
#     if direction == 'vertical':
#         # Update height percentage from bottom
#     else:
#         # Update width percentage from left
`;

    // create a download for regular HTML
    const blob = new Blob([exported], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'dashboard_export.html';
    a.click();
    URL.revokeObjectURL(url);

    // Build Python instructions
    const instructions = `
╔═══════════════════════════════════════════════════════════════════════════════╗
║  EXPORT COMPLETE - dashboard_export.html                                      ║
╚═══════════════════════════════════════════════════════════════════════════════╝

✅ File downloaded: dashboard_export.html
   Open in browser to preview your dashboard!

📋 PYTHON SERVER INTEGRATION (dashboard_server_ha.py)
────────────────────────────────────────────────────────────────────────────────

Paste this ENTITY_MAP into your dashboard_server_ha.py:

` + pySnippet + `

📊 ENTITY MAPPING REFERENCE
────────────────────────────────────────────────────────────────────────────────
HTML Element ID → Home Assistant Entity ID
` + Object.entries(mapping).map(([fieldId, entityId]) => {
    return `${fieldId} → ${entityId}`;
}).join('\n') + `

════════════════════════════════════════════════════════════════════════════════
✨ The exported HTML includes:
   • Base64-encoded images (works completely offline!)
   • JavaScript that auto-refreshes from Home Assistant
   • Placeholders {{HA_BASE_URL}} and {{HA_TOKEN}} for your credentials
   • Self-contained dashboard ready to deploy
════════════════════════════════════════════════════════════════════════════════
`;

    // show instructions in a modal
    showExportDialog(instructions);
}

function showExportDialog(text) {
    let overlay = document.getElementById('exportOverlay');
    if (overlay) overlay.remove();

    overlay = document.createElement('div');
    overlay.id = 'exportOverlay';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;z-index:9999';

    const box = document.createElement('div');
    box.style.cssText = 'background:#1a1a2e;border:1px solid #444;border-radius:10px;padding:20px;max-width:700px;width:90%;max-height:80vh;overflow:auto;color:#ddd;font-family:monospace;font-size:13px;white-space:pre-wrap;position:relative';

    const closeBtn = document.createElement('button');
    closeBtn.textContent = 'Close';
    closeBtn.style.cssText = 'position:absolute;top:10px;right:10px;padding:5px 12px;border:1px solid #555;border-radius:5px;background:#333;color:#ddd;cursor:pointer';
    closeBtn.addEventListener('click', () => overlay.remove());

    const copyBtn = document.createElement('button');
    copyBtn.textContent = 'Copy';
    copyBtn.style.cssText = 'position:absolute;top:10px;right:80px;padding:5px 12px;border:1px solid #555;border-radius:5px;background:#333;color:#ddd;cursor:pointer';
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(text);
        copyBtn.textContent = 'Copied!';
        setTimeout(() => copyBtn.textContent = 'Copy', 1500);
    });

    box.textContent = text;
    box.appendChild(closeBtn);
    box.appendChild(copyBtn);
    overlay.appendChild(box);
    overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
    document.body.appendChild(overlay);
}

/* ── helpers ── */
function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }
function esc(s) { if (!s) return ''; return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

/* ── keyboard shortcuts ── */
document.addEventListener('keydown', e => {
    if (!selected) return;
    const item = placed.find(p => p.id === selected);
    if (!item) return;

    let handled = false;
    if (e.key === 'Delete' || e.key === 'Backspace') {
        // only delete if not focused on an input
        if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA') return;
        document.getElementById('propDelete').click();
        handled = true;
    }
    if (e.key === 'ArrowLeft')  { item.x = clamp(item.x - (e.shiftKey ? 10 : 1), 0, 780); handled = true; }
    if (e.key === 'ArrowRight') { item.x = clamp(item.x + (e.shiftKey ? 10 : 1), 0, 780); handled = true; }
    if (e.key === 'ArrowUp')    { item.y = clamp(item.y - (e.shiftKey ? 10 : 1), 0, 580); handled = true; }
    if (e.key === 'ArrowDown')  { item.y = clamp(item.y + (e.shiftKey ? 10 : 1), 0, 580); handled = true; }

    if (handled) {
        e.preventDefault();
        renderPlaced(item);
        updatePropsValues();
    }
});

/* ── init ── */
loadEntities();
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/states":
            self.handle_api_states()
            return

        if parsed.path == "/api/image_base64":
            self.handle_image_base64(parsed.query)
            return

        if parsed.path.startswith("/images/"):
            self.handle_image(parsed.path[8:])  # Remove "/images/" prefix
            return

        if parsed.path == "/" or parsed.path == "/index.html":
            self.handle_index()
            return

        self.send_response(404)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Not found")

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/upload_image":
            self.handle_upload_image()
            return

        self.send_response(404)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Not found")

    def handle_image(self, filename):
        # Sanitize filename to prevent directory traversal
        filename = os.path.basename(filename)
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        if not os.path.exists(filepath):
            self.send_response(404)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Image not found")
            return

        # Determine content type
        content_type = "image/png"
        if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
            content_type = "image/jpeg"
        elif filename.lower().endswith(".gif"):
            content_type = "image/gif"

        try:
            with open(filepath, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(body)
        except Exception as ex:
            self.send_response(500)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(str(ex).encode("utf-8"))

    def handle_upload_image(self):
        try:
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                raise Exception("Invalid content type")

            # Extract boundary from content-type
            boundary = None
            for part in content_type.split(';'):
                if 'boundary=' in part:
                    boundary = part.split('boundary=')[1].strip()
                    break
            
            if not boundary:
                raise Exception("No boundary found in Content-Type")

            # Read the entire POST body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            # Simple multipart parser - find the file data
            boundary_bytes = ('--' + boundary).encode()
            parts = post_data.split(boundary_bytes)
            
            filename = None
            file_data = None
            
            for part in parts:
                if b'Content-Disposition' in part and b'filename=' in part:
                    # Extract filename
                    lines = part.split(b'\r\n')
                    for line in lines:
                        if b'filename=' in line:
                            # Parse filename from: filename="image.png"
                            fn_start = line.find(b'filename="') + 10
                            fn_end = line.find(b'"', fn_start)
                            filename = line[fn_start:fn_end].decode('utf-8')
                            break
                    
                    # Find file data (after double newline)
                    data_start = part.find(b'\r\n\r\n')
                    if data_start != -1:
                        file_data = part[data_start + 4:]
                        # Remove trailing \r\n
                        if file_data.endswith(b'\r\n'):
                            file_data = file_data[:-2]
                    break

            if not filename or not file_data:
                raise Exception("Could not parse uploaded file")

            # Sanitize filename and add timestamp
            filename = os.path.basename(filename)
            name, ext = os.path.splitext(filename)
            filename = "{0}_{1}{2}".format(name, int(time.time()), ext)

            filepath = os.path.join(os.path.dirname(__file__), filename)

            # Save the file
            with open(filepath, 'wb') as f:
                f.write(file_data)

            # Return success with filename
            body = json.dumps({"filename": filename}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        except Exception as ex:
            body = json.dumps({"error": str(ex)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def handle_index(self):
        body = DESIGNER_HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_image_base64(self, query_string):
        """Convert image file to base64 data URL"""
        try:
            params = parse_qs(query_string)
            filename = params.get('file', [''])[0]
            
            if not filename:
                raise Exception("No filename provided")
            
            # Sanitize filename
            filename = os.path.basename(filename)
            filepath = os.path.join(os.path.dirname(__file__), filename)
            
            if not os.path.exists(filepath):
                raise Exception("Image not found: " + filename)
            
            # Read file and encode to base64
            with open(filepath, 'rb') as f:
                image_data = f.read()
            
            # Determine mime type
            mime_type = "image/png"
            if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
                mime_type = "image/jpeg"
            elif filename.lower().endswith(".gif"):
                mime_type = "image/gif"
            
            # Create data URL
            b64_data = base64.b64encode(image_data).decode('utf-8')
            data_url = "data:{0};base64,{1}".format(mime_type, b64_data)
            
            body = json.dumps({"dataUrl": data_url, "filename": filename}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            
        except Exception as ex:
            body = json.dumps({"error": str(ex)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def handle_api_states(self):
        try:
            states = fetch_ha_states()
            body = json.dumps(states).encode("utf-8")
            self.send_response(200)
        except Exception as ex:
            body = json.dumps({"error": str(ex)}).encode("utf-8")
            self.send_response(500)

        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


def get_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
    finally:
        sock.close()
    return ip


if __name__ == "__main__":
    ip = get_ip()
    print("Dashboard Designer running at http://{0}:{1}".format(ip, PORT))
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()
