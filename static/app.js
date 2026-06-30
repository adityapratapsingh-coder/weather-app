/* ===================== state & helpers ===================== */
const $ = (id) => document.getElementById(id);
const loader = $("loader"), errorBox = $("error"), errorText = $("error-text");
const panels = { today: $("panel-today"), forecast: $("panel-forecast"), map: $("panel-map"), population: $("panel-population") };
const THEMES = ["clear-day","clear-night","cloudy","rain","snow","storm","fog"];

const LS = {
    get: (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
    set: (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
};

let unit = LS.get("sky_unit", "c");
let theme = LS.get("sky_theme", "vivid");
let favorites = LS.get("sky_favs", []);
let recents = LS.get("sky_recent", []);
let latest = null, lastQuery = null;
let hourlyChart = null, dailyChart = null, clockTimer = null, refreshTimer = null, popTimer = null;
let map = null, mapReady = false, clickMarker = null, viewedMarker = null, radarLayer = null;

const UNITS = { c: { t: "°C", w: "km/h", v: "km" }, f: { t: "°F", w: "mph", v: "mi" } };
const tval = (c) => unit === "f" ? Math.round(c * 9 / 5 + 32) : Math.round(c);
const wval = (k) => unit === "f" ? Math.round(k * 0.621) : Math.round(k);
const vval = (km) => unit === "f" ? +(km * 0.621).toFixed(1) : km;
const ARROWS = { N:"↓", NE:"↙", E:"←", SE:"↖", S:"↑", SW:"↗", W:"→", NW:"↘" }; // arrow points the way wind blows TO

function setTheme(weatherTheme) {
    THEMES.forEach((t) => document.body.classList.remove("theme-" + t));
    document.body.classList.add("theme-" + (weatherTheme || "clear-day"));
    document.body.classList.toggle("light", theme === "light");
}
function showState(el) { [loader, errorBox].forEach((e) => e.classList.add("hidden")); if (el) el.classList.remove("hidden"); }
function fmt(n) { return Math.round(n).toLocaleString("en-US"); }
function abbr(n) {
    if (n == null) return "—";
    if (n >= 1e9) return (n / 1e9).toFixed(2) + " B";
    if (n >= 1e6) return (n / 1e6).toFixed(1) + " M";
    if (n >= 1e3) return (n / 1e3).toFixed(0) + " K";
    return "" + n;
}
function hhmm(iso) { return iso ? iso.slice(11, 16) : "—"; }
async function fetchJson(url) {
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Request failed.");
    return data;
}
function tempColor(t) {
    if (t == null) return "#888";
    const stops = [[-10,"#3b4cc0"],[0,"#5a78d8"],[10,"#5ac8e8"],[18,"#54d98b"],[25,"#f4d03f"],[32,"#f39c12"],[38,"#e8552d"],[45,"#a01818"]];
    if (t <= stops[0][0]) return stops[0][1];
    if (t >= stops[stops.length-1][0]) return stops[stops.length-1][1];
    for (let i=0;i<stops.length-1;i++){ const [t0,c0]=stops[i],[t1,c1]=stops[i+1];
        if (t>=t0&&t<=t1){ const f=(t-t0)/(t1-t0); const L=(a,b)=>Math.round(a+(b-a)*f);
            const h=(c)=>[1,3,5].map(k=>parseInt(c.substr(k,2),16)); const A=h(c0),B=h(c1);
            return `rgb(${L(A[0],B[0])},${L(A[1],B[1])},${L(A[2],B[2])})`; } }
    return "#888";
}

/* ===================== tabs ===================== */
document.querySelectorAll(".tab").forEach((btn) => btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    Object.values(panels).forEach((p) => p.classList.add("hidden"));
    const name = btn.dataset.tab;
    panels[name].classList.remove("hidden");
    if (name === "map") initMap();
    if (name === "population") initPopulation();
}));

/* ===================== render weather ===================== */
function render(data) {
    latest = data;
    LS.set("sky_last", data);
    setTheme(data.current.theme);
    Fx.set(data.current.theme);
    const c = data.current;

    $("city-name").textContent = data.location.name;
    $("region").textContent = data.location.region || "";
    $("now-emoji").textContent = c.emoji;
    $("now-temp").textContent = tval(c.temperature);
    $("now-desc").textContent = c.description;

    $("feels").textContent = tval(c.feels_like) + "°";
    $("humidity").textContent = c.humidity + "%";
    $("wind").textContent = wval(c.wind_speed) + " " + UNITS[unit].w;
    $("wind-dir").textContent = c.wind_compass ? (ARROWS[c.wind_compass] || "") + " " + c.wind_compass : "";
    $("pressure").textContent = c.pressure != null ? c.pressure + " hPa" : "—";
    $("visibility").textContent = c.visibility_km != null ? vval(c.visibility_km) + " " + UNITS[unit].v : "—";
    $("cloud").textContent = c.cloud_cover != null ? c.cloud_cover + "%" : "—";
    $("dew").textContent = c.dew_point != null ? tval(c.dew_point) + "°" : "—";
    $("uv").textContent = c.uv_index != null ? c.uv_index + " " + c.uv_label : "—";
    $("coords").textContent = (data.location.latitude != null)
        ? (+data.location.latitude).toFixed(2) + ", " + (+data.location.longitude).toFixed(2) : "—";
    $("tz").textContent = data.timezone || "—";

    if (data.aqi && data.aqi.value != null) {
        $("aqi-tile").style.display = "";
        $("aqi-value").textContent = data.aqi.value;
        $("aqi-label").textContent = data.aqi.label;
        $("aqi-dot").style.background = data.aqi.color;
    } else { $("aqi-tile").style.display = "none"; }

    if (data.location.population) { $("pop-tile").style.display = ""; $("city-pop").textContent = abbr(data.location.population); }
    else { $("pop-tile").style.display = "none"; }

    $("sunrise").textContent = hhmm(c.sunrise);
    $("sunset").textContent = hhmm(c.sunset);
    $("moon-emoji").textContent = data.moon.emoji;
    $("moon-name").textContent = data.moon.name;

    const alertsBox = $("alerts");
    if (data.alerts && data.alerts.length) {
        alertsBox.classList.remove("hidden");
        alertsBox.innerHTML = data.alerts.map((a) => `<div class="alert-item ${a.level}">⚠️ ${a.text}</div>`).join("");
    } else { alertsBox.classList.add("hidden"); alertsBox.innerHTML = ""; }

    buildAssistant(data);

    const named = data.location.name && data.location.name !== "Selected location";
    const favBtn = $("fav-btn");
    favBtn.style.display = named ? "" : "none";
    favBtn.textContent = favorites.includes(data.location.name) ? "★" : "☆";
    if (named) addRecent(data.location.name);

    startClock(data.utc_offset_seconds);
    renderHourly(data.hourly);
    renderForecast(data.forecast);
    if (mapReady) updateViewedMarker(data.location.latitude, data.location.longitude, data.location.name);

    showState(null);
    panels.today.classList.remove("hidden");
}

/* ===================== smart assistant ===================== */
function buildAssistant(data) {
    const c = data.current, tips = [];
    const t = c.temperature;
    const maxRain = Math.max(0, ...data.hourly.slice(0, 12).map((h) => h.rain_chance || 0));

    if (t >= 38) tips.push(["🥵", "It's very hot. Wear light, loose, breathable clothing and drink plenty of water."]);
    else if (t >= 30) tips.push(["☀️", "Warm out — light cotton clothes will keep you comfortable."]);
    else if (t >= 20) tips.push(["🙂", "Pleasant temperature. A t-shirt is perfect for today."]);
    else if (t >= 10) tips.push(["🧥", "A bit cool — carry a light jacket or sweater."]);
    else if (t >= 0) tips.push(["🧣", "Cold outside. Dress in warm layers, a coat and a scarf."]);
    else tips.push(["❄️", "Freezing — heavy winter gear, gloves and a hat are a must."]);

    if (maxRain >= 40 || ["rain", "storm"].includes(c.theme))
        tips.push(["☔", `Rain is likely (up to ${maxRain}% chance) — carry an umbrella.`]);
    else if (c.theme === "snow")
        tips.push(["🌨️", "Snow expected — wear waterproof boots and drive carefully."]);

    if (c.uv_index != null && c.uv_index >= 8) tips.push(["🧴", "Very high UV — use sunscreen, sunglasses and avoid the midday sun."]);
    else if (c.uv_index != null && c.uv_index >= 6) tips.push(["🧴", "UV is high — sunscreen and a hat are a good idea."]);

    if (data.aqi && data.aqi.value != null && data.aqi.value > 150) tips.push(["😷", "Air quality is poor — limit outdoor exertion and consider a mask."]);
    else if (data.aqi && data.aqi.value != null && data.aqi.value > 100) tips.push(["🫁", "Air quality is moderate — sensitive groups should take it easy outdoors."]);

    if (c.theme === "storm") tips.push(["⛈️", "Thunderstorm around — a good day to stay indoors."]);
    else if (["clear-day", "cloudy"].includes(c.theme) && t >= 15 && t <= 30 && maxRain < 30)
        tips.push(["🚶", "Great conditions for a walk, a run or outdoor plans."]);

    if (c.wind_speed >= 40) tips.push(["💨", "Strong winds — secure loose objects and be careful on two-wheelers."]);

    $("assistant-list").innerHTML = tips.slice(0, 5)
        .map(([e, txt]) => `<li><span class="a-emoji">${e}</span><span>${txt}</span></li>`).join("");
}

/* ===================== share ===================== */
function shareSummary() {
    if (!latest) return "";
    const c = latest.current;
    return `${latest.location.name}: ${tval(c.temperature)}${UNITS[unit].t}, ${c.description}. ` +
        `Feels ${tval(c.feels_like)}°, humidity ${c.humidity}%, wind ${wval(c.wind_speed)} ${UNITS[unit].w}. — via Skyline`;
}
document.querySelectorAll(".share-btn").forEach((btn) => btn.addEventListener("click", () => {
    const text = shareSummary(); if (!text) return;
    const enc = encodeURIComponent(text);
    const kind = btn.dataset.share;
    if (kind === "copy") {
        navigator.clipboard?.writeText(text).then(() => { btn.textContent = "✓ Copied"; setTimeout(() => btn.textContent = "📋 Copy", 1500); });
    } else if (kind === "whatsapp") window.open("https://wa.me/?text=" + enc, "_blank");
    else if (kind === "twitter") window.open("https://twitter.com/intent/tweet?text=" + enc, "_blank");
    else if (kind === "telegram") window.open("https://t.me/share/url?url=" + encodeURIComponent(location.href) + "&text=" + enc, "_blank");
}));

/* ===================== clock & charts ===================== */
function startClock(offsetSec) {
    if (clockTimer) clearInterval(clockTimer);
    const tick = () => {
        const utcMs = Date.now() + new Date().getTimezoneOffset() * 60000;
        const d = new Date(utcMs + offsetSec * 1000);
        $("local-clock").textContent =
            d.toLocaleDateString("en-US", { weekday: "long", day: "numeric", month: "short" }) + "  ·  " +
            d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    };
    tick(); clockTimer = setInterval(tick, 1000);
}
function renderHourly(hours) {
    const row = $("hourly-row"); row.innerHTML = "";
    hours.forEach((h, i) => {
        const label = i === 0 ? "Now" : h.time.slice(11, 16);
        const cell = document.createElement("div"); cell.className = "hcell";
        cell.innerHTML = `<div class="h-time">${label}</div><div class="h-emoji">${h.emoji}</div>` +
            `<div class="h-temp">${tval(h.temp)}°</div>` + (h.rain_chance ? `<div class="h-rain">💧${h.rain_chance}%</div>` : "");
        row.appendChild(cell);
    });
    const labels = hours.map((h, i) => i === 0 ? "Now" : h.time.slice(11, 16));
    if (hourlyChart) hourlyChart.destroy();
    hourlyChart = new Chart($("hourly-chart"), lineConfig(labels, [{
        label: "Temp " + UNITS[unit].t, data: hours.map((h) => tval(h.temp)),
        borderColor: chartInk(), backgroundColor: "rgba(120,160,220,0.18)", fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2 }]));
}
function renderForecast(days) {
    const row = $("forecast-row"); row.innerHTML = "";
    days.forEach((d, i) => {
        const date = new Date(d.date + "T00:00:00");
        const dayName = i === 0 ? "Today" : date.toLocaleDateString("en-US", { weekday: "long" });
        const dateStr = date.toLocaleDateString("en-US", { day: "numeric", month: "short" });
        const el = document.createElement("div"); el.className = "frow";
        el.innerHTML = `<div><div class="f-day">${dayName}</div><div class="f-date">${dateStr}</div></div>` +
            `<div class="f-emoji">${d.emoji}</div>` +
            `<div class="f-desc">${d.description}${d.rain_chance ? ` · <span class="f-rain">💧${d.rain_chance}%</span>` : ""}</div>` +
            `<div class="f-temps"><span class="f-hi">${tval(d.max)}°</span> <span class="f-lo">${tval(d.min)}°</span></div>`;
        row.appendChild(el);
    });
    const labels = days.map((d, i) => i === 0 ? "Today" : new Date(d.date + "T00:00:00").toLocaleDateString("en-US", { weekday: "short" }));
    if (dailyChart) dailyChart.destroy();
    dailyChart = new Chart($("daily-chart"), lineConfig(labels, [
        { label: "High " + UNITS[unit].t, data: days.map((d) => tval(d.max)), borderColor: "#ffb347", backgroundColor: "transparent", tension: 0.35, pointRadius: 2, borderWidth: 2 },
        { label: "Low " + UNITS[unit].t, data: days.map((d) => tval(d.min)), borderColor: "#5aa9ff", backgroundColor: "transparent", tension: 0.35, pointRadius: 2, borderWidth: 2 } ]));
}
function chartInk() { return theme === "light" ? "#16243a" : "#ffffff"; }
function lineConfig(labels, datasets) {
    const tick = theme === "light" ? "rgba(22,36,58,0.7)" : "rgba(255,255,255,0.7)";
    const grid = theme === "light" ? "rgba(22,36,58,0.1)" : "rgba(255,255,255,0.12)";
    return { type: "line", data: { labels, datasets }, options: { responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: datasets.length > 1, labels: { color: tick, boxWidth: 12, font: { size: 11 } } } },
        scales: { x: { ticks: { color: tick, maxRotation: 0, autoSkip: true, maxTicksLimit: 8, font: { size: 10 } }, grid: { color: grid } },
                  y: { ticks: { color: tick, font: { size: 10 } }, grid: { color: grid } } } } };
}

/* ===================== loaders ===================== */
async function loadByCity(city) {
    lastQuery = { type: "city", value: city };
    showState(loader); panels.today.classList.add("hidden");
    try { render(await fetchJson("/api/weather?city=" + encodeURIComponent(city))); }
    catch (e) { errorText.textContent = e.message; showState(errorBox); }
}
async function loadByCoords(lat, lon) {
    lastQuery = { type: "coords", value: [lat, lon] };
    showState(loader); panels.today.classList.add("hidden");
    try { render(await fetchJson(`/api/weather/coords?lat=${lat}&lon=${lon}`)); }
    catch (e) { errorText.textContent = e.message; showState(errorBox); }
}
function refresh() { if (!lastQuery) return locate();
    if (lastQuery.type === "city") loadByCity(lastQuery.value); else loadByCoords(lastQuery.value[0], lastQuery.value[1]); }

$("search-form").addEventListener("submit", (e) => { e.preventDefault();
    const city = $("city-input").value.trim(); if (city) { loadByCity(city); $("city-input").value = ""; } });
$("retry-btn").addEventListener("click", refresh);

/* ===================== favorites & recents ===================== */
function renderSavedBar() {
    const bar = $("saved-bar"); bar.innerHTML = "";
    favorites.forEach((name) => bar.appendChild(chip(name, true)));
    recents.filter((r) => !favorites.includes(r)).forEach((name) => bar.appendChild(chip(name, false)));
}
function chip(name, isFav) {
    const el = document.createElement("div"); el.className = "saved-chip";
    el.innerHTML = (isFav ? `<span class="star">★</span>` : "") + `<span>${name}</span><button class="rm" title="Remove">×</button>`;
    el.addEventListener("click", (e) => { if (!e.target.classList.contains("rm")) loadByCity(name); });
    el.querySelector(".rm").addEventListener("click", (e) => { e.stopPropagation();
        favorites = favorites.filter((f) => f !== name); recents = recents.filter((r) => r !== name);
        LS.set("sky_favs", favorites); LS.set("sky_recent", recents); renderSavedBar();
        if (latest) $("fav-btn").textContent = favorites.includes(latest.location.name) ? "★" : "☆"; });
    return el;
}
function addRecent(name) { recents = [name, ...recents.filter((r) => r !== name)].slice(0, 6); LS.set("sky_recent", recents); renderSavedBar(); }
$("fav-btn").addEventListener("click", () => {
    if (!latest) return; const name = latest.location.name;
    favorites = favorites.includes(name) ? favorites.filter((f) => f !== name) : [name, ...favorites].slice(0, 12);
    LS.set("sky_favs", favorites); $("fav-btn").textContent = favorites.includes(name) ? "★" : "☆"; renderSavedBar();
});

/* ===================== settings ===================== */
$("unit-toggle").addEventListener("click", () => { unit = unit === "c" ? "f" : "c"; LS.set("sky_unit", unit);
    $("unit-toggle").textContent = UNITS[unit].t; if (latest) render(latest); });
$("theme-toggle").addEventListener("click", () => { theme = theme === "light" ? "vivid" : "light"; LS.set("sky_theme", theme);
    $("theme-toggle").textContent = theme === "light" ? "☀️" : "🌙"; document.body.classList.toggle("light", theme === "light"); if (latest) render(latest); });
$("locate-btn").addEventListener("click", locate);

/* ===================== voice search ===================== */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SR) {
    const rec = new SR(); rec.lang = "en-US"; rec.interimResults = false;
    $("voice-btn").addEventListener("click", () => { try { rec.start(); $("voice-btn").classList.add("listening"); } catch {} });
    rec.onresult = (e) => { const text = e.results[0][0].transcript.replace(/[.?!]$/, "").trim(); if (text) loadByCity(text); };
    rec.onend = () => $("voice-btn").classList.remove("listening");
    rec.onerror = () => $("voice-btn").classList.remove("listening");
} else { $("voice-btn").style.display = "none"; }

/* ===================== map ===================== */
function buildLegend() {
    const marks = [-10, 0, 10, 18, 25, 32, 38, 45];
    $("temp-legend").innerHTML = "<span>Temp:</span>" +
        marks.map((t) => `<span><span class="swatch" style="background:${tempColor(t)}"></span>${t}°</span>`).join("");
}
function updateViewedMarker(lat, lon, name) {
    if (!map || lat == null) return;
    if (viewedMarker) map.removeLayer(viewedMarker);
    viewedMarker = L.marker([lat, lon]).addTo(map).bindPopup(`📍 ${name}`);
}
function initMap() {
    if (mapReady) { setTimeout(() => map.invalidateSize(), 80); return; }
    mapReady = true;
    map = L.map("map", { worldCopyJump: true }).setView([22, 30], 2);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "© OpenStreetMap", maxZoom: 12 }).addTo(map);
    buildLegend();
    fetchJson("/api/heatmap").then((d) => d.cities.forEach((c) => {
        if (c.temp == null) return;
        L.circleMarker([c.lat, c.lon], { radius: 9, color: "rgba(255,255,255,0.7)", weight: 1.5, fillColor: tempColor(c.temp), fillOpacity: 0.9 })
            .addTo(map).bindTooltip(`${c.name}: ${c.temp}°C`, { direction: "top" });
    })).catch(() => {});
    if (latest && latest.location.latitude != null) updateViewedMarker(latest.location.latitude, latest.location.longitude, latest.location.name);
    map.on("click", async (e) => {
        const { lat, lng } = e.latlng;
        const readout = $("map-readout"); readout.classList.remove("hidden"); readout.innerHTML = "Loading…";
        if (clickMarker) map.removeLayer(clickMarker); clickMarker = L.marker([lat, lng]).addTo(map);
        try {
            const w = await fetchJson(`/api/weather/coords?lat=${lat.toFixed(3)}&lon=${lng.toFixed(3)}`);
            const c = w.current;
            readout.innerHTML = `<div class="mr-temp">${c.emoji} ${tval(c.temperature)}${UNITS[unit].t} — ${c.description}</div>` +
                `<div class="card-hint" style="margin:6px 0 0">Feels ${tval(c.feels_like)}° · Humidity ${c.humidity}% · Wind ${wval(c.wind_speed)} ${UNITS[unit].w}` +
                (w.aqi && w.aqi.value != null ? ` · AQI ${w.aqi.value}` : "") + "</div>";
            clickMarker.bindPopup(`${c.emoji} ${tval(c.temperature)}${UNITS[unit].t}`).openPopup();
        } catch { readout.innerHTML = "Could not load weather for this point."; }
    });
}
/* rain radar (RainViewer — free, no key) */
$("radar-check").addEventListener("change", async (e) => {
    if (!map) return;
    if (radarLayer) { map.removeLayer(radarLayer); radarLayer = null; }
    if (!e.target.checked) return;
    try {
        const data = await fetch("https://api.rainviewer.com/public/weather-maps.json").then((r) => r.json());
        const frames = data.radar && data.radar.past ? data.radar.past : [];
        if (!frames.length) return;
        const path = frames[frames.length - 1].path;
        radarLayer = L.tileLayer(`${data.host}${path}/256/{z}/{x}/{y}/2/1_1.png`, { opacity: 0.6, attribution: "RainViewer" }).addTo(map);
    } catch { e.target.checked = false; }
});

/* ===================== population (with live counter) ===================== */
let countriesLoaded = false, allCountries = [];
async function initPopulation() {
    if (countriesLoaded) return; countriesLoaded = true;
    $("world-pop").textContent = "Loading…";
    try {
        const d = await fetchJson("/api/population/countries");
        startWorldCounter(d.world_live);
        allCountries = d.countries; renderCountries(allCountries);
    } catch (e) { $("world-pop").textContent = "—"; $("country-list").innerHTML = `<div class="card-hint">${e.message}</div>`; }
}
function startWorldCounter(live) {
    if (popTimer) clearInterval(popTimer);
    if (!live) return;
    const tick = () => {
        const elapsed = (Date.now() - live.base_epoch_ms) / 1000;
        $("world-pop").textContent = fmt(live.base + elapsed * live.per_second);
    };
    tick(); popTimer = setInterval(tick, 200);
}
function renderCountries(list) {
    const box = $("country-list"); box.innerHTML = "";
    list.forEach((c, i) => {
        const el = document.createElement("div"); el.className = "crow";
        el.innerHTML = `<span class="c-rank">${i + 1}</span>` +
            `<div><div class="c-name">${c.name}</div><div class="c-region">${c.region || ""}${c.capital ? " · " + c.capital : ""}</div></div>` +
            `<div class="c-pop">${fmt(c.population)}</div>`;
        box.appendChild(el);
    });
}
$("country-filter").addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();
    renderCountries(allCountries.filter((c) => c.name.toLowerCase().includes(q)));
});
$("city-pop-form").addEventListener("submit", async (e) => {
    e.preventDefault(); const name = $("city-pop-input").value.trim(); if (!name) return;
    const box = $("city-pop-result"); box.classList.remove("hidden"); box.innerHTML = "Loading…";
    try { const loc = await fetchJson("/api/city?name=" + encodeURIComponent(name));
        box.innerHTML = `<div class="cpr-name">${loc.name}${loc.region ? ", " + loc.region : ""}</div>` +
            `<div class="cpr-pop">${loc.population ? fmt(loc.population) + " people" : "Population data not available"}</div>`;
    } catch (err) { box.innerHTML = err.message; }
});

/* ===================== animated weather effects ===================== */
const Fx = (() => {
    const canvas = $("fx"); const ctx = canvas.getContext("2d");
    let mode = "clear-day", parts = [], raf = null, flash = 0;
    const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    function resize() { canvas.width = innerWidth; canvas.height = innerHeight; }
    function init() {
        parts = []; const W = canvas.width, H = canvas.height;
        if (mode === "rain" || mode === "storm") for (let i=0;i<120;i++) parts.push({x:Math.random()*W,y:Math.random()*H,l:8+Math.random()*12,s:6+Math.random()*6});
        else if (mode === "snow") for (let i=0;i<90;i++) parts.push({x:Math.random()*W,y:Math.random()*H,r:1.5+Math.random()*2.5,s:0.6+Math.random()*1.2,d:Math.random()*Math.PI});
        else if (mode === "cloudy" || mode === "fog") for (let i=0;i<7;i++) parts.push({x:Math.random()*W,y:Math.random()*H*0.6,r:60+Math.random()*120,s:0.15+Math.random()*0.25});
        else if (mode === "clear-night") for (let i=0;i<70;i++) parts.push({x:Math.random()*W,y:Math.random()*H*0.7,r:Math.random()*1.4,tw:Math.random()*Math.PI*2});
    }
    function draw() {
        const W = canvas.width, H = canvas.height; ctx.clearRect(0,0,W,H);
        if (mode === "rain" || mode === "storm") {
            ctx.strokeStyle = "rgba(174,205,235,0.55)"; ctx.lineWidth = 1.4;
            parts.forEach((p) => { ctx.beginPath(); ctx.moveTo(p.x,p.y); ctx.lineTo(p.x-2,p.y+p.l); ctx.stroke();
                p.y += p.s; p.x -= 1; if (p.y > H) { p.y = -10; p.x = Math.random()*W; } });
            if (mode === "storm") { if (Math.random() < 0.004) flash = 1;
                if (flash > 0) { ctx.fillStyle = `rgba(255,255,255,${flash*0.4})`; ctx.fillRect(0,0,W,H); flash -= 0.04; } }
        } else if (mode === "snow") {
            ctx.fillStyle = "rgba(255,255,255,0.85)";
            parts.forEach((p) => { ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,7); ctx.fill();
                p.y += p.s; p.x += Math.sin(p.d += 0.01)*0.6; if (p.y > H) { p.y = -5; p.x = Math.random()*W; } });
        } else if (mode === "cloudy" || mode === "fog") {
            parts.forEach((p) => { const g = ctx.createRadialGradient(p.x,p.y,0,p.x,p.y,p.r);
                g.addColorStop(0,"rgba(255,255,255,0.16)"); g.addColorStop(1,"rgba(255,255,255,0)");
                ctx.fillStyle = g; ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,7); ctx.fill();
                p.x += p.s; if (p.x - p.r > W) p.x = -p.r; });
        } else if (mode === "clear-night") {
            parts.forEach((p) => { const a = 0.4 + Math.sin(p.tw += 0.05)*0.4;
                ctx.fillStyle = `rgba(255,255,255,${a})`; ctx.beginPath(); ctx.arc(p.x,p.y,p.r+0.4,0,7); ctx.fill(); });
        }
        raf = requestAnimationFrame(draw);
    }
    addEventListener("resize", () => { resize(); init(); });
    return { set(m) { if (reduce) return; mode = m; resize(); init(); if (!raf) draw(); } };
})();

/* ===================== init ===================== */
function locate() {
    showState(loader); panels.today.classList.add("hidden");
    if (!navigator.geolocation) return loadByCity("New Delhi");
    navigator.geolocation.getCurrentPosition(
        (pos) => loadByCoords(pos.coords.latitude.toFixed(4), pos.coords.longitude.toFixed(4)),
        () => loadByCity("New Delhi"), { timeout: 8000 });
}
function init() {
    $("unit-toggle").textContent = UNITS[unit].t;
    $("theme-toggle").textContent = theme === "light" ? "☀️" : "🌙";
    document.body.classList.toggle("light", theme === "light");
    renderSavedBar();
    const cached = LS.get("sky_last", null);
    if (cached) { try { render(cached); } catch {} }
    locate();
    refreshTimer = setInterval(refresh, 5 * 60 * 1000);
}
init();
