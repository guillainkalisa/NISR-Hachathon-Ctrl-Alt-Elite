(function () {
  const data = JSON.parse(document.getElementById("indicators-data").textContent);
  const metrics = JSON.parse(document.getElementById("metrics-data").textContent);
  const metricSel = document.getElementById("metric");
  const roundSel = document.getElementById("round");
  const css = getComputedStyle(document.documentElement);
  const seq = [1, 2, 3, 4, 5].map((i) => css.getPropertyValue(`--seq-${i}`).trim());
  const noData = css.getPropertyValue("--nodata").trim();
  const surface = css.getPropertyValue("--surface").trim();

  const fmt = (m, v) => {
    if (v == null) return "—";
    if (metrics[m].unit === "count") return Math.round(v).toLocaleString();
    if (metrics[m].unit === "radiance") return v.toFixed(2);
    return `${(v * 100).toFixed(0)}%`;
  };

  // No basemap tiles: the district shapes carry the map, and nothing depends on a third-party tile service.
  const map = L.map("map", { zoomSnap: 0.25, scrollWheelZoom: false, maxZoom: 12 }).setView([-1.95, 29.9], 8.25);
  map.attributionControl.addAttribution("Boundaries: geoBoundaries (CC BY 4.0)");

  let layer, breaks = [];

  function value(name) {
    const row = (data[name] || {})[roundSel.value];
    return row ? row[metricSel.value] : null;
  }

  // Quantile breaks: five classes with roughly equal numbers of districts.
  function computeBreaks() {
    const vals = Object.keys(data).map(value).filter((v) => v != null).sort((a, b) => a - b);
    breaks = [1, 2, 3, 4].map((q) => vals[Math.floor((q / 5) * (vals.length - 1))]);
    breaks.unshift(vals[0]);
    breaks.push(vals[vals.length - 1]);
  }

  function color(v) {
    if (v == null) return noData;
    for (let i = 1; i < 5; i++) if (v <= breaks[i]) return seq[i - 1];
    return seq[4];
  }

  function style(feature) {
    return { fillColor: color(value(feature.properties.shapeName)), fillOpacity: 0.92, color: surface, weight: 2 };
  }

  function tooltip(name) {
    const row = (data[name] || {})[roundSel.value];
    const m = metricSel.value;
    if (!row) return `<strong>${name}</strong><br>No data`;
    const flag = row.reliable ? "" : "<br><em>Small sample - interpret with care</em>";
    const source = metrics[m].source === "satellite" ? "<br><span style='opacity:.75'>VIIRS satellite, Oct 2023 – Oct 2024</span>" : "";
    return `<strong>${name}</strong><br>${metrics[m].label}: <strong>${fmt(m, row[m])}</strong>${source}${row.reliable || metrics[m].source === "satellite" ? "" : flag}`;
  }

  function render() {
    computeBreaks();
    if (layer) layer.setStyle(style);
    renderLegend();
    renderRanking();
    renderTable();
  }

  function renderLegend() {
    const m = metricSel.value;
    document.getElementById("legend").innerHTML =
      `<span>${fmt(m, breaks[0])}</span><span class="swatches">${seq.map((c) => `<span style="background:${c}"></span>`).join("")}</span>` +
      `<span>${fmt(m, breaks[5])}</span><span style="margin-left:1rem"><span class="nodata"></span> no estimate</span>`;
  }

  function sortedRows() {
    const m = metricSel.value;
    const worse = metrics[m].higher_is_worse;
    return Object.keys(data)
      .map((name) => ({ name, row: data[name][roundSel.value] }))
      .filter((d) => d.row && d.row[m] != null)
      .sort((a, b) => (worse ? b.row[m] - a.row[m] : a.row[m] - b.row[m]));
  }

  function link(d) {
    return `<a href="${window.DISTRICT_URL.replace("SLUG", d.row.slug)}">${d.name}</a>`;
  }

  function renderRanking() {
    const m = metricSel.value;
    document.getElementById("rank-title").textContent =
      metrics[m].higher_is_worse ? "Highest 10 districts" : "Lowest 10 districts";
    document.getElementById("ranked").innerHTML = sortedRows().slice(0, 10)
      .map((d, i) => `<li><span class="n">${i + 1}</span>${link(d)}<span class="v">${fmt(m, d.row[m])}</span></li>`).join("");
  }

  function renderTable() {
    const cols = Object.keys(metrics);
    document.getElementById("table").innerHTML =
      `<thead><tr><th>District</th>${cols.map((c) => `<th class="r">${metrics[c].label}</th>`).join("")}</tr></thead><tbody>` +
      sortedRows().map((d) => `<tr><td>${link(d)}${d.row.reliable ? "" : " *"}</td>${cols.map((c) => `<td class="r">${fmt(c, d.row[c])}</td>`).join("")}</tr>`).join("") +
      `</tbody><caption class="muted" style="caption-side:bottom;text-align:left">* fewer than 30 poor households sampled</caption>`;
  }

  fetch(window.GEOJSON_URL).then((r) => r.json()).then((geo) => {
    layer = L.geoJSON(geo, {
      style,
      onEachFeature(feature, lyr) {
        const name = feature.properties.shapeName;
        lyr.bindTooltip(() => tooltip(name), { sticky: true });
        lyr.on({
          mouseover: () => lyr.setStyle({ weight: 3, color: css.getPropertyValue("--text").trim() }),
          mouseout: () => layer.resetStyle(lyr),
          click: () => {
            const row = Object.values(data[name] || {})[0];
            if (row) window.location = window.DISTRICT_URL.replace("SLUG", row.slug);
          },
        });
      },
    }).addTo(map);
    map.fitBounds(layer.getBounds(), { padding: [10, 10] });
    render();
  });

  metricSel.addEventListener("change", render);
  roundSel.addEventListener("change", render);
  render();
})();
