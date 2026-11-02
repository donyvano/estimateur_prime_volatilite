/* Volatility risk premium: static site. Reads web/data/*.json written by `python -m vrp.pipeline`. */
"use strict";

const FONT = '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif';
const DATA_FILES = ["summary", "volatility", "premium", "options", "forecast", "backtest"];
const STORAGE_KEY = "vrp-theme";

// Ordinal ramps for option maturities (short -> long), validated with the dataviz validator.
const RAMP = {
  light: ["#7AAEEB", "#4F96E6", "#1A73D9", "#0056B3", "#003A7A"],
  dark: ["#1F5FA8", "#2F7FD6", "#4D9BF5", "#7DB6F7", "#B3D4FA"],
};

const STRATEGY_COLOR = { always: "gray", har_x: "blue", lightgbm: "purple" };
const STRATEGY_SHORT = { always: "Toujours vendre", har_x: "Conditionnelle HAR + VIX", lightgbm: "Conditionnelle LightGBM" };
const MODEL_LABEL = {
  naive: "Naïf (21 derniers jours)", har: "HAR-RV", garch: "GARCH(1,1)",
  har_x: "HAR-RV + VIX", lightgbm: "LightGBM", implied: "VIX brut (référence)",
};
const FEATURE_LABEL = {
  implied: "VIX", rv_m: "Vol 22 j", rv_q: "Vol 63 j", rv_park: "Parkinson 21 j", rv_w: "Vol 5 j",
  ret_21: "Rendement 21 j", vrp_past: "Prime passée", vix_rv_ratio: "VIX / vol", ret_5: "Rendement 5 j",
  vix_chg_5: "Variation VIX 5 j", rv_d: "Vol 1 j", ret_1: "Rendement 1 j",
};
const CRISIS_SHORT = {
  "Global Financial Crisis": "Lehman 2008", "US downgrade / Euro crisis": "Dette 2011",
  "Volmageddon": "Volmageddon", "Covid crash": "Covid", "2022 bear market": "Inflation 2022",
  "Tariff shock": "Tarifs 2025",
};
const CRISIS_FR = {
  "Global Financial Crisis": "Crise financière 2008", "US downgrade / Euro crisis": "Dégradation US / crise euro 2011",
  "Volmageddon": "Volmageddon, février 2018", "Covid crash": "Krach Covid 2020",
  "2022 bear market": "Marché baissier 2022", "Tariff shock": "Choc des tarifs douaniers 2025",
};

const state = { data: {}, volEstimator: "rv", vrpRange: "all", smileView: "2d", fcModel: "har_x", btView: "equity" };
const rendered = new Set();

// ------------------------------------------------------------------ formatting
const nf = (d) => new Intl.NumberFormat("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d });
const num = (x, d = 1) => (x == null ? "–" : nf(d).format(x).replace("-", "−"));
const signed = (x, d = 1) => (x == null ? "–" : (x > 0 ? "+" : x < 0 ? "−" : "") + nf(d).format(Math.abs(x)));
const pct = (x, d = 1) => `${num(x, d)} %`;
const pts = (x, d = 1) => `${signed(x, d)} pts`;
const longDate = (s) => new Date(`${s}T12:00:00`).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
const monthYear = (s) => new Date(`${s}T12:00:00`).toLocaleDateString("fr-FR", { month: "short", year: "numeric" });

// ------------------------------------------------------------------ theme
function effectiveTheme() {
  const attr = document.documentElement.getAttribute("data-theme");
  if (attr) return attr;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function initTheme() {
  const btn = document.querySelector("[data-theme-toggle]");
  const sync = () => btn.setAttribute("aria-pressed", String(effectiveTheme() === "dark"));
  btn.addEventListener("click", () => {
    const next = effectiveTheme() === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem(STORAGE_KEY, next); } catch (e) { /* private mode */ }
    sync();
    rerenderAll();
  });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (!document.documentElement.getAttribute("data-theme")) rerenderAll();
  });
  sync();
}

function palette() {
  const css = getComputedStyle(document.documentElement);
  const v = (name) => css.getPropertyValue(name).trim();
  return {
    blue: v("--c-blue"), orange: v("--c-orange"), purple: v("--c-purple"), gray: v("--c-gray"),
    grid: v("--c-grid"), band: v("--c-band"), text: v("--apple-text-primary"),
    muted: v("--apple-text-secondary"), surface: v("--apple-elevated"),
    ramp: RAMP[effectiveTheme()],
  };
}

// ------------------------------------------------------------------ plotly helpers
const isMobile = () => window.matchMedia("(max-width: 600px)").matches;

function merge(target, src) {
  for (const [k, v] of Object.entries(src || {})) {
    if (v && typeof v === "object" && !Array.isArray(v) && target[k] && typeof target[k] === "object") merge(target[k], v);
    else target[k] = v;
  }
  return target;
}

function baseLayout(p, extra) {
  const axis = {
    gridcolor: p.grid, linecolor: p.grid, tickcolor: "rgba(0,0,0,0)", zeroline: false,
    tickfont: { size: 11, color: p.muted }, automargin: true,
  };
  return merge(
    {
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: FONT, size: 12, color: p.muted },
      margin: { l: 8, r: 12, t: 12, b: 8 },
      separators: ", ",
      showlegend: false,
      hovermode: "x unified",
      hoverlabel: { bgcolor: p.surface, bordercolor: p.grid, font: { family: FONT, size: 13, color: p.text } },
      xaxis: { ...axis, showgrid: false, showline: true, showspikes: true, spikemode: "across", spikethickness: 1, spikecolor: p.muted, spikedash: "solid", spikesnap: "cursor" },
      yaxis: { ...axis, showline: false },
    },
    extra,
  );
}

const PLOT_CONFIG = { displayModeBar: false, responsive: true };

function draw(id, traces, layout) {
  Plotly.react(id, traces, layout, PLOT_CONFIG);
}

function legend(id, items) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = items
    .map(([label, color]) => `<span class="legend__item"><span class="legend__swatch" style="background:${color}"></span>${label}</span>`)
    .join("");
}

function line(x, y, name, color, extra = {}) {
  return merge({ type: "scatter", mode: "lines", x, y, name, line: { color, width: 2 }, hovertemplate: `${name} : %{y:.1f} %<extra></extra>` }, extra);
}

// ------------------------------------------------------------------ charts
const charts = {
  "chart-vol"(p) {
    const v = state.data.volatility;
    const s = v.series;
    const traces = [line(s.dates, s.rv, "Clôture à clôture", p.orange, { line: { width: 1.5 } })];
    if (state.volEstimator === "both") traces.push(line(s.dates, s.rv_park, "Parkinson", p.purple, { line: { width: 1.5 } }));
    const mobile = isMobile();
    const shapes = v.crises.map((c) => ({
      type: "rect", xref: "x", yref: "paper", x0: c.start, x1: c.end, y0: 0, y1: 1,
      fillcolor: p.band, line: { width: 0 }, layer: "below",
    }));
    const annotations = mobile ? [] : v.crises.map((c, i) => ({
      x: c.peak_date, y: c.peak_rv, xref: "x", yref: "y", text: CRISIS_SHORT[c.name] || c.name,
      showarrow: false, yshift: 14 + (i % 2) * 2, font: { size: 11, color: p.text },
    }));
    draw("chart-vol", traces, baseLayout(p, {
      shapes, annotations,
      xaxis: { hoverformat: "%d/%m/%Y" },
      yaxis: { ticksuffix: " %", rangemode: "tozero" },
    }));
    legend("legend-vol", state.volEstimator === "both" ? [["Clôture à clôture", p.orange], ["Parkinson (haut-bas)", p.purple]] : []);
  },

  "chart-vrp"(p) {
    const s = state.data.premium.series;
    const ranges = { all: null, 2008: ["2008-06-01", "2009-12-31"], 2020: ["2019-11-01", "2020-12-31"], 2025: ["2024-10-01", "2025-12-31"] };
    const r = ranges[state.vrpRange];
    draw("chart-vrp", [
      line(s.dates, s.implied, "VIX au jour t", p.blue, { line: { width: 1.5 } }),
      line(s.dates, s.rv_fwd, "Vol réalisée t+1 → t+21", p.orange, { line: { width: 1.5 } }),
    ], baseLayout(p, {
      xaxis: { range: r, autorange: r ? false : true, hoverformat: "%d/%m/%Y" },
      yaxis: { ticksuffix: " %", rangemode: "tozero", autorange: true },
    }));
    legend("legend-vrp", [["VIX au jour t (anticipée)", p.blue], ["Volatilité réalisée sur les 21 séances suivantes", p.orange]]);
  },

  "chart-hist"(p) {
    const h = state.data.premium.histogram;
    const x = h.counts.map((_, i) => (h.edges[i] + h.edges[i + 1]) / 2);
    draw("chart-hist", [{
      type: "bar", x, y: h.counts, width: 0.86,
      marker: { color: x.map((c) => (c < 0 ? p.orange : p.blue)) },
      hovertemplate: "Prime entre %{x:.1f} et +1 pt : %{y} jours<extra></extra>",
    }], baseLayout(p, {
      hovermode: "closest",
      xaxis: { showspikes: false, ticksuffix: " pts", zeroline: true, zerolinecolor: p.muted, zerolinewidth: 1 },
      yaxis: { title: { text: "" } },
      bargap: 0,
    }));
  },

  "chart-smile"(p) {
    const o = state.data.options;
    if (state.smileView === "3d") {
      const sf = o.surface;
      draw("chart-smile", [{
        type: "surface", x: sf.moneyness, y: sf.days, z: sf.iv,
        colorscale: p.ramp.map((c, i) => [i / (p.ramp.length - 1), c]),
        showscale: false, opacity: 0.95,
        contours: { z: { show: true, usecolormap: true, width: 1, project: { z: false } } },
        hovertemplate: "K/F %{x:.2f} · %{y} jours<br>Vol implicite %{z:.1f} %<extra></extra>",
      }], baseLayout(p, {
        hovermode: "closest",
        margin: { l: 0, r: 0, t: 0, b: 0 },
        scene: {
          xaxis: { title: { text: "K / F" }, gridcolor: p.grid, color: p.muted, backgroundcolor: "rgba(0,0,0,0)" },
          yaxis: { title: { text: "Jours" }, gridcolor: p.grid, color: p.muted, backgroundcolor: "rgba(0,0,0,0)" },
          zaxis: { title: { text: "Vol %" }, gridcolor: p.grid, color: p.muted, backgroundcolor: "rgba(0,0,0,0)" },
          camera: { eye: { x: 0.55, y: -1.8, z: 1.0 }, center: { x: 0, y: 0, z: -0.12 } },
          aspectmode: "manual", aspectratio: { x: 1.4, y: 1.1, z: 0.85 },
        },
      }));
      legend("legend-smile", [["Faisceau clair : échéances courtes · foncé : longues", p.ramp[2]]]);
      return;
    }
    const traces = o.smiles.map((s, i) => line(s.moneyness, s.iv, `${s.days} jours`, p.ramp[i], {
      hovertemplate: `${s.days} j · K/F %{x:.3f} : %{y:.1f} %<extra></extra>`,
    }));
    draw("chart-smile", traces, baseLayout(p, {
      hovermode: "closest",
      xaxis: { showspikes: false, tickformat: ".2f", title: { text: "Moneyness K / F", font: { size: 12 } } },
      yaxis: { ticksuffix: " %" },
      shapes: [{ type: "line", xref: "x", yref: "paper", x0: 1, x1: 1, y0: 0, y1: 1, line: { color: p.muted, width: 1 } }],
      annotations: [{ x: 1, y: 1, xref: "x", yref: "paper", text: "à la monnaie", showarrow: false, xanchor: "left", xshift: 6, font: { size: 11, color: p.muted } }],
    }));
    legend("legend-smile", o.smiles.map((s, i) => [`${s.days} jours`, p.ramp[i]]));
  },

  "chart-term"(p) {
    const t = state.data.options.term_structure;
    draw("chart-term", [line(t.days, t.atm_iv, "Vol ATM", p.blue, {
      mode: "lines+markers", marker: { size: 8, color: p.blue, line: { color: p.surface, width: 2 } },
      hovertemplate: "%{x} jours : %{y:.1f} %<extra></extra>",
    })], baseLayout(p, {
      hovermode: "closest",
      xaxis: { showspikes: false, ticksuffix: " j" },
      yaxis: { ticksuffix: " %" },
    }));
  },

  "chart-mc"(p) {
    const mc = state.data.options.monte_carlo;
    const n = mc.n_paths;
    const ref = n.map((k) => mc.std_error[0] * Math.sqrt(n[0] / k));
    draw("chart-mc", [
      line(n, ref, "1/√N", p.gray, { line: { width: 1 }, hovertemplate: "Pente théorique : %{y:.3f}<extra></extra>" }),
      line(n, mc.std_error, "Écart-type", p.blue, { mode: "lines+markers", marker: { size: 8, line: { color: p.surface, width: 2 } }, hovertemplate: "Écart-type : %{y:.3f} $<extra></extra>" }),
      line(n, mc.antithetic_std_error, "Antithétique", p.purple, { mode: "lines+markers", marker: { size: 8, line: { color: p.surface, width: 2 } }, hovertemplate: "Antithétique : %{y:.3f} $<extra></extra>" }),
      { type: "scatter", mode: "markers", x: n, y: mc.abs_error, name: "Erreur réelle", marker: { size: 9, color: p.orange, line: { color: p.surface, width: 2 } }, hovertemplate: "Erreur vs BS : %{y:.3f} $<extra></extra>" },
    ], baseLayout(p, {
      showlegend: true,
      legend: { orientation: "h", x: 0, y: 1.14, font: { size: 12, color: p.muted } },
      margin: { t: 36 },
      xaxis: { type: "log", showspikes: false, title: { text: "Nombre de trajectoires", font: { size: 12 } }, dtick: 1 },
      yaxis: { type: "log", tickprefix: "", ticksuffix: " $", dtick: 1 },
    }));
  },

  "chart-fc"(p) {
    const s = state.data.forecast.series;
    const m = state.fcModel;
    draw("chart-fc", [
      line(s.dates, s.rv_fwd, "Réalisée", p.orange, { line: { width: 1.5 } }),
      line(s.dates, s[m], MODEL_LABEL[m], p.blue, { line: { width: 1.5 } }),
    ], baseLayout(p, { xaxis: { hoverformat: "%d/%m/%Y" }, yaxis: { ticksuffix: " %", rangemode: "tozero" } }));
    legend("legend-fc", [["Volatilité réalisée (21 j suivants)", p.orange], [`Prévision ${MODEL_LABEL[m]}`, p.blue]]);
  },

  "chart-imp"(p) {
    const imp = state.data.forecast.importance.slice(0, 8).reverse();
    draw("chart-imp", [{
      type: "bar", orientation: "h", y: imp.map((d) => FEATURE_LABEL[d.feature] || d.feature),
      x: imp.map((d) => 100 * d.gain), marker: { color: p.blue }, width: 0.62,
      hovertemplate: "%{y} : %{x:.1f} % du gain<extra></extra>",
    }], baseLayout(p, {
      hovermode: "closest",
      xaxis: { showspikes: false, showline: false, showgrid: true, ticksuffix: " %" },
      yaxis: { tickfont: { size: 12, color: p.text } },
    }));
  },

  "chart-bt"(p) {
    const st = state.data.backtest.strategies;
    const dd = state.btView === "drawdown";
    const traces = Object.entries(st).map(([k, s]) => line(
      s.curve.dates, dd ? s.curve.drawdown : s.curve.equity, STRATEGY_SHORT[k], p[STRATEGY_COLOR[k]],
      { hovertemplate: dd ? `${STRATEGY_SHORT[k]} : %{y:.1f} %<extra></extra>` : `${STRATEGY_SHORT[k]} : %{y:.2f}<extra></extra>` },
    ));
    draw("chart-bt", traces, baseLayout(p, {
      xaxis: { hoverformat: "%m/%Y" },
      yaxis: dd
        ? { ticksuffix: " %", type: "linear" }
        : { type: "log", tickvals: [1, 1.5, 2, 3, 4, 5, 6, 8], tickformat: ".1f", ticksuffix: "×" },
    }));
    legend("legend-bt", Object.keys(st).map((k) => [STRATEGY_SHORT[k], p[STRATEGY_COLOR[k]]]));
  },

  "chart-rolls"(p) {
    const st = state.data.backtest.strategies;
    const keys = Object.keys(st).reverse();
    const traces = [];
    keys.forEach((k) => {
      const sh = st[k].roll_dates.sharpe;
      const c = p[STRATEGY_COLOR[k]];
      traces.push({
        type: "scatter", mode: "markers", x: sh, y: sh.map(() => STRATEGY_SHORT[k]),
        marker: { size: 10, color: c, opacity: 0.55, line: { color: p.surface, width: 2 } },
        hovertemplate: "Sharpe %{x:.2f}<extra></extra>",
      });
      const mean = sh.reduce((a, b) => a + b, 0) / sh.length;
      traces.push({
        type: "scatter", mode: "markers", x: [mean], y: [STRATEGY_SHORT[k]],
        marker: { size: 16, symbol: "diamond", color: c, line: { color: p.surface, width: 2 } },
        hovertemplate: "Moyenne %{x:.2f}<extra></extra>",
      });
    });
    draw("chart-rolls", traces, baseLayout(p, {
      hovermode: "closest",
      xaxis: { showspikes: false, showgrid: true, showline: false, title: { text: "Ratio de Sharpe annualisé", font: { size: 12 } } },
      yaxis: { tickfont: { size: 12, color: p.text } },
    }));
  },
};

function render(id) {
  if (!window.Plotly || !state.data.summary) return;
  charts[id](palette());
  rendered.add(id);
}

function rerenderAll() {
  rendered.forEach((id) => render(id));
}

// ------------------------------------------------------------------ tables
function table(id, head, rows, rowClass = () => "") {
  const el = document.getElementById(id);
  el.innerHTML =
    `<thead><tr>${head.map((h) => `<th scope="col">${h}</th>`).join("")}</tr></thead>` +
    `<tbody>${rows.map((r, i) => `<tr class="${rowClass(i)}">${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody>`;
}

const negSpan = (x, text) => (x < 0 ? `<span class="neg">${text}</span>` : text);

function fillTables() {
  const { premium, forecast, backtest } = state.data;

  table("table-regimes", ["VIX", "Part des jours", "Vol réalisée", "Prime", "Prime > 0"],
    premium.regimes.map((r) => [r.vix_bucket.replace("-", "–").replace("+", " et +"), pct(r.share_of_days, 0), pct(r.mean_rv_fwd), pts(r.mean_vrp), pct(r.pct_positive, 0)]));

  table("table-crises", ["Crise", "VIX max", "Vol réalisée max", "Prime moyenne", "Pire prime"],
    premium.crises.map((c) => [CRISIS_FR[c.name] || c.name, pct(c.peak_vix, 0), pct(c.peak_rv_fwd, 0), negSpan(c.mean_vrp, pts(c.mean_vrp)), negSpan(c.min_vrp, pts(c.min_vrp, 0))]));

  const metrics = forecast.metrics;
  const candidates = metrics.filter((m) => m.model !== "implied");
  const best = candidates.reduce((a, b) => (b.rmse < a.rmse ? b : a)).model;
  table("table-forecast", ["Modèle", "RMSE", "MAE", "Biais", "QLIKE", "RMSE vs naïf"],
    metrics.map((m) => [MODEL_LABEL[m.model], num(m.rmse, 2), num(m.mae, 2), signed(m.bias, 2), num(m.qlike, 3), m.model === "naive" ? "–" : `${signed(m.rmse_vs_naive, 1)} %`]),
    (i) => (metrics[i].model === best ? "is-best" : metrics[i].model === "implied" ? "muted" : ""));

  const st = backtest.strategies;
  const keys = Object.keys(st);
  table("table-bt", ["Stratégie", "Rendement annuel", "Volatilité", "Sharpe", "Drawdown max", "Pire mois", "Skew", "Investi"],
    keys.map((k) => {
      const m = st[k].metrics;
      return [STRATEGY_SHORT[k], pct(m.ann_return), pct(m.ann_vol), num(m.sharpe, 2), negSpan(-1, pct(m.max_drawdown)), negSpan(-1, pct(m.worst_period)), num(m.skew, 1), pct(m.pct_invested, 0)];
    }));

  const names = st.always.tails.map((t) => t.name);
  table("table-tails", ["Crise", "VIX à l'entrée", "Vol réalisée", ...keys.map((k) => STRATEGY_SHORT[k])],
    names.map((n) => {
      const base = st.always.tails.find((t) => t.name === n);
      return [CRISIS_FR[n] || n, pct(base.strike, 0), pct(base.realized, 0), ...keys.map((k) => {
        const t = st[k].tails.find((x) => x.name === n);
        if (!t || !t.invested) return "non investi";
        return negSpan(t.ret, pct(t.ret));
      })];
    }));
}

// ------------------------------------------------------------------ text bindings
function fillText() {
  const { summary: s, volatility: v, options: o, forecast: f, backtest: b } = state.data;
  const p = s.premium;
  const always = b.strategies.always.metrics;
  const values = {
    period: `${s.data_start.slice(0, 4)}–${s.data_end.slice(0, 4)}`,
    pct_positive: pct(p.pct_positive, 0),
    mean_implied: pct(p.mean_implied),
    mean_realized: pct(p.mean_realized),
    worst_vrp: `${signed(p.worst_vrp, 0)} pts`,
    worst_date: longDate(p.worst_date),
    median_vrp: signed(p.median_vrp),
    data_end: longDate(s.data_end),
    "vol.median_rv": pct(v.stats.median_rv),
    "vol.max_rv": pct(v.stats.max_rv, 0),
    "vol.max_rv_date": longDate(v.stats.max_rv_date),
    "vol.autocorr_21": num(v.stats.autocorr_21, 2),
    "vol.parkinson_ratio": `${num(v.stats.parkinson_ratio, 2)}×`,
    "opt.vix": pct(o.headline.vix),
    "opt.atm_1m": pct(o.headline.atm_1m),
    "opt.put_90": pct(o.headline.put_90),
    "opt.call_110": pct(o.headline.call_110),
    "opt.skew_90_110": `${num(o.headline.skew_90_110)} points`,
    "opt.valuation_date": longDate(o.valuation_date),
    "fc.sample": `${f.sample.start.slice(0, 4)}–${f.sample.end.slice(0, 4)}`,
    "fc.best": `${num(-s.forecast.best_rmse_vs_naive, 0)} %`,
    "bt.threshold": num(b.config.threshold_vol_points, 0),
    "bt.cost": num(b.config.cost_vol_points),
    "bt.skew": num(always.skew, 1),
    "bt.kurt": num(always.excess_kurtosis, 0),
    "bt.hit": pct(always.hit_rate, 0),
    "bt.roll_min": num(s.backtest_rolls.har_x.sharpe_min, 2),
    "bt.roll_max": num(s.backtest_rolls.har_x.sharpe_max, 2),
    "bt.dd_always": pct(s.backtest_rolls.always.dd_mean, 0),
    "bt.dd_harx": pct(s.backtest_rolls.har_x.dd_mean, 0),
  };
  document.querySelectorAll("[data-bind]").forEach((el) => {
    const key = el.dataset.bind;
    if (key in values) el.textContent = values[key];
  });
  const counter = document.querySelector("[data-counter]");
  animateCounter(counter, p.mean_vrp);
}

function animateCounter(el, target) {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) { el.textContent = signed(target); return; }
  const start = performance.now();
  const duration = 1400;
  const tick = (now) => {
    const t = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = signed(target * eased);
    if (t < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

// ------------------------------------------------------------------ controls & observers
function initControls() {
  const targets = { volEstimator: "chart-vol", vrpRange: "chart-vrp", smileView: "chart-smile", fcModel: "chart-fc", btView: "chart-bt" };
  document.querySelectorAll("[data-control]").forEach((group) => {
    const key = group.dataset.control;
    group.addEventListener("click", (e) => {
      const btn = e.target.closest(".segmented__btn");
      if (!btn) return;
      group.querySelectorAll(".segmented__btn").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      state[key] = btn.dataset.value;
      render(targets[key]);
    });
  });
}

function initObservers() {
  const fade = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("fade-in--visible");
        fade.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
  document.querySelectorAll(".fade-in").forEach((el) => fade.observe(el));

  // Charts are drawn only when they approach the viewport (Plotly is heavy).
  const lazy = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        render(entry.target.id);
        lazy.unobserve(entry.target);
      }
    });
  }, { rootMargin: "300px 0px" });
  Object.keys(charts).forEach((id) => lazy.observe(document.getElementById(id)));
}

async function loadData() {
  const results = await Promise.all(DATA_FILES.map((name) => fetch(`data/${name}.json`).then((r) => {
    if (!r.ok) throw new Error(`data/${name}.json: HTTP ${r.status}`);
    return r.json();
  })));
  DATA_FILES.forEach((name, i) => { state.data[name] = results[i]; });
}

async function main() {
  initTheme();
  initControls();
  try {
    await loadData();
  } catch (err) {
    console.error(err);
    document.querySelector(".hero__lede").textContent =
      "Les données n'ont pas pu être chargées. Lancez `python -m vrp.pipeline`, puis servez le dossier web/ avec un serveur HTTP.";
    return;
  }
  fillText();
  fillTables();
  initObservers();
  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(rerenderAll, 200);
  });
}

main();
