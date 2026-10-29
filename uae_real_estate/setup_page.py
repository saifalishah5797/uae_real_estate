"""
Creates the "Real Estate Command Center" page (/app/re-dashboard).

Copy to: apps/uae_real_estate/uae_real_estate/setup_page.py   (same folder as hooks.py)
Needs dashboard_api.py in the same folder.

Run from ~/frappe-bench:
    bench --site uae.localhost execute uae_real_estate.setup_page.run
    bench --site uae.localhost clear-cache && bench restart

Re-run any time: it rewrites the page JS (so you can tweak the design and re-run).
"""
import json
import os

import frappe

MODULE = "UAE Real Estate"
PAGE = "re-dashboard"

PAGE_JS = r"""frappe.pages["re-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Real Estate Command Center"),
		single_column: true,
	});
	wrapper.red = new REDashboard(page, wrapper);
};

frappe.pages["re-dashboard"].on_page_show = function (wrapper) {
	if (wrapper.red && wrapper.red.loaded) wrapper.red.load();
};

const RED_STATUS = {
	Available: "#10b981",
	Hold: "#f59e0b",
	Booked: "#3b82f6",
	Sold: "#8b5cf6",
};
const RED_PALETTE = ["#6366f1", "#06b6d4", "#f59e0b", "#ec4899", "#10b981", "#8b5cf6"];

const esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));

class REDashboard {
	constructor(page, wrapper) {
		this.page = page;
		this.wrapper = wrapper;
		this.currency = "AED";
		this.loaded = false;
		this.$root = $('<div class="red-wrap"></div>').appendTo(page.main);
		this.inject_css();
		this.project_field = page.add_field({
			fieldname: "project",
			label: __("Project"),
			fieldtype: "Link",
			options: "RE Project",
			change: () => this.load(),
		});
		page.set_secondary_action(__("Refresh"), () => this.load(), "refresh");
		this.$root.html(this.skeleton());
		this.load();
	}

	// ------------------------------------------------------------ data
	load() {
		frappe.call({
			method: "uae_real_estate.dashboard_api.get_dashboard_data",
			args: { project: this.project_field.get_value() || null },
			callback: (r) => {
				if (r.message) {
					this.loaded = true;
					this.render(r.message);
				}
			},
		});
	}

	// ------------------------------------------------------------ helpers
	compact(n) {
		n = flt(n);
		const a = Math.abs(n);
		if (a >= 1e9) return (n / 1e9).toFixed(2) + "B";
		if (a >= 1e6) return (n / 1e6).toFixed(2) + "M";
		if (a >= 1e3) return (n / 1e3).toFixed(1) + "K";
		return n.toFixed(0);
	}
	money(n) {
		return `${this.currency} ${this.compact(n)}`;
	}
	skeleton() {
		return `<div class="red-hero"><div class="red-hero-left"><h1>${__("Loading your portfolio...")}</h1></div></div>`;
	}

	animate() {
		this.$root.find("[data-count]").each((_, el) => {
			const target = flt(el.dataset.count);
			const kind = el.dataset.kind || "num";
			const suffix = el.dataset.suffix || "";
			const t0 = performance.now();
			const dur = 900;
			const step = (t) => {
				const p = Math.min(1, (t - t0) / dur);
				const v = target * (1 - Math.pow(1 - p, 3));
				el.textContent =
					kind === "money" ? this.money(v) : Math.round(v).toLocaleString() + suffix;
				if (p < 1) requestAnimationFrame(step);
			};
			requestAnimationFrame(step);
		});
		setTimeout(() => this.$root.find(".red-ring-bar").each((_, el) => {
			el.style.strokeDashoffset = el.dataset.offset;
		}), 80);
	}

	// ------------------------------------------------------------ render
	render(d) {
		this.currency = d.currency || "AED";
		const k = d.kpis;
		const C = 2 * Math.PI * 54;
		const offset = C * (1 - Math.min(100, k.collection_pct) / 100);
		const occupancy = k.total_units ? Math.round(((k.booked + k.sold) / k.total_units) * 100) : 0;
		const today = frappe.datetime.str_to_user(frappe.datetime.get_today());
		const name = esc((frappe.session.user_fullname || "").split(" ")[0] || "there");

		const kpi = (icon, color, label, value, sub, kind) => `
			<div class="red-kpi">
				<div class="red-kpi-icon" style="background:${color}">${icon}</div>
				<div class="red-kpi-body">
					<div class="red-kpi-label">${label}</div>
					<div class="red-kpi-value" data-count="${value}" data-kind="${kind || "num"}">0</div>
					<div class="red-kpi-sub">${sub}</div>
				</div>
			</div>`;

		const html = `
		<div class="red-hero">
			<div class="red-hero-left">
				<div class="red-eyebrow">${today}</div>
				<h1>${__("Welcome back")}, ${name} <span class="red-wave">👋</span></h1>
				<p>${__("Here is how your portfolio is performing right now.")}</p>
				<div class="red-hero-stats">
					<div><span>${__("Sales Value")}</span><b data-count="${k.sales}" data-kind="money">0</b></div>
					<div><span>${__("Collected")}</span><b data-count="${k.collected}" data-kind="money">0</b></div>
					<div><span>${__("Outstanding")}</span><b data-count="${k.outstanding}" data-kind="money">0</b></div>
				</div>
			</div>
			<div class="red-ring">
				<svg viewBox="0 0 128 128" width="176" height="176">
					<defs>
						<linearGradient id="redg" x1="0" y1="0" x2="1" y2="1">
							<stop offset="0%" stop-color="#34d399"/><stop offset="100%" stop-color="#22d3ee"/>
						</linearGradient>
					</defs>
					<circle cx="64" cy="64" r="54" class="red-ring-bg"/>
					<circle cx="64" cy="64" r="54" class="red-ring-bar" stroke="url(#redg)"
						style="stroke-dasharray:${C};stroke-dashoffset:${C}" data-offset="${offset}"
						transform="rotate(-90 64 64)"/>
				</svg>
				<div class="red-ring-label">
					<b data-count="${k.collection_pct}" data-suffix="%">0%</b>
					<span>${__("Collected")}</span>
				</div>
			</div>
		</div>

		<div class="red-kpis">
			${kpi("🏢", "linear-gradient(135deg,#6366f1,#8b5cf6)", __("Total Units"), k.total_units, `${occupancy}% ${__("sold / booked")}`)}
			${kpi("🔑", "linear-gradient(135deg,#10b981,#06b6d4)", __("Available"), k.available, `${k.hold} ${__("on hold")}`)}
			${kpi("📝", "linear-gradient(135deg,#3b82f6,#06b6d4)", __("Active Bookings"), k.bookings, `${k.booked} ${__("units booked")}`)}
			${kpi("⏰", "linear-gradient(135deg,#f43f5e,#f59e0b)", __("Overdue"), k.overdue_amount, `${k.overdue_count} ${__("milestones past due")}`, "money")}
		</div>

		<div class="red-grid red-grid-2-1">
			<div class="red-card">
				<div class="red-card-head"><h3>${__("Sales Trend")}</h3><span>${__("last 12 months")}</span></div>
				<div id="red-trend"></div>
			</div>
			<div class="red-card">
				<div class="red-card-head"><h3>${__("Inventory Status")}</h3><span>${k.total_units} ${__("units")}</span></div>
				<div id="red-status"></div>
			</div>
		</div>

		<div class="red-grid red-grid-1-1">
			<div class="red-card">
				<div class="red-card-head"><h3>${__("Sales by Project")}</h3><span>${__("value")}</span></div>
				<div id="red-projects"></div>
			</div>
			<div class="red-card">
				<div class="red-card-head"><h3>${__("Collected vs Outstanding")}</h3><span>${__("by project")}</span></div>
				<div id="red-collect"></div>
			</div>
		</div>

		<div class="red-section-title"><h2>${__("Unit Stack Plan")}</h2>
			<div class="red-legend">${Object.keys(RED_STATUS)
				.map((s) => `<span><i style="background:${RED_STATUS[s]}"></i>${__(s)}</span>`)
				.join("")}</div>
		</div>
		<div class="red-towers">${this.render_towers(d)}</div>

		<div class="red-grid red-grid-2-1">
			<div class="red-card">
				<div class="red-card-head"><h3>${__("Recent Bookings")}</h3>
					<a href="/app/re-booking">${__("View all")} →</a></div>
				${this.render_recent(d.recent)}
			</div>
			<div class="red-card">
				<div class="red-card-head"><h3>${__("Payments Due")}</h3><span>${__("next up")}</span></div>
				${this.render_due(d.due)}
			</div>
		</div>`;

		this.$root.html(html);
		this.draw_charts(d);
		this.bind(d);
		this.animate();
	}

	render_towers(d) {
		if (!d.towers.length) return `<div class="red-empty">${__("No towers yet")}</div>`;
		const by_tower = {};
		d.units.forEach((u) => (by_tower[u.tower] = by_tower[u.tower] || []).push(u));

		return d.towers
			.map((t) => {
				const units = by_tower[t.name] || [];
				const floors = {};
				units.forEach((u) => (floors[u.floor] = floors[u.floor] || []).push(u));
				const counts = {};
				units.forEach((u) => (counts[u.status] = (counts[u.status] || 0) + 1));

				const rows = Object.keys(floors)
					.map(Number)
					.sort((a, b) => b - a)
					.map(
						(f) => `<div class="red-floor"><span class="red-floor-no">F${f}</span>
						<div class="red-tiles">${floors[f]
							.map(
								(u) => `<div class="red-tile" data-unit="${esc(u.name)}"
								style="--c:${RED_STATUS[u.status] || "#94a3b8"}"
								title="${esc(u.unit_type || "")} · ${esc(this.money(u.total_price))} · ${esc(u.status)}">${esc(u.unit_no)}</div>`
							)
							.join("")}</div></div>`
					)
					.join("");

				const chips = Object.keys(counts)
					.map((s) => `<span class="red-chip" style="--c:${RED_STATUS[s] || "#94a3b8"}">${counts[s]} ${__(s)}</span>`)
					.join("");

				return `<div class="red-card red-tower">
					<div class="red-card-head"><h3>${esc(t.project)} · ${__("Tower")} ${esc(t.tower_name)}</h3></div>
					<div class="red-chips">${chips}</div>
					<div class="red-floors">${rows || `<div class="red-empty">${__("No units")}</div>`}</div>
				</div>`;
			})
			.join("");
	}

	render_recent(rows) {
		if (!rows.length) return `<div class="red-empty">${__("No bookings yet")}</div>`;
		return `<div class="red-table-wrap"><table class="red-table">
			<thead><tr><th>${__("Booking")}</th><th>${__("Customer")}</th><th>${__("Unit")}</th>
			<th class="r">${__("Value")}</th><th>${__("Paid")}</th></tr></thead>
			<tbody>${rows
				.map((r) => {
					const pct = flt(r.grand_total) ? Math.min(100, (flt(r.total_paid) / flt(r.grand_total)) * 100) : 0;
					return `<tr data-booking="${esc(r.name)}">
						<td><b>${esc(r.name)}</b><div class="red-muted">${frappe.datetime.str_to_user(r.booking_date)}</div></td>
						<td>${esc(r.customer)}</td>
						<td>${esc(r.unit)}</td>
						<td class="r">${this.money(r.grand_total)}</td>
						<td style="min-width:110px"><div class="red-bar"><i style="width:${pct}%"></i></div>
							<div class="red-muted">${Math.round(pct)}%</div></td>
					</tr>`;
				})
				.join("")}</tbody></table></div>`;
	}

	render_due(rows) {
		if (!rows.length) return `<div class="red-empty">🎉 ${__("Nothing pending")}</div>`;
		const today = frappe.datetime.get_today();
		return `<div class="red-due">${rows
			.map((r) => {
				const days = frappe.datetime.get_diff(r.due_date, today);
				const cls = days < 0 ? "late" : days <= 7 ? "soon" : "ok";
				const label = days < 0 ? `${Math.abs(days)}d ${__("overdue")}` : days === 0 ? __("Due today") : `${__("in")} ${days}d`;
				return `<div class="red-due-item" data-booking="${esc(r.booking)}">
					<div><b>${esc(r.milestone)}</b>
						<div class="red-muted">${esc(r.customer)} · ${esc(r.unit)}</div></div>
					<div class="r"><b>${this.money(r.pending)}</b>
						<span class="red-pill ${cls}">${label}</span></div>
				</div>`;
			})
			.join("")}</div>`;
	}

	// ------------------------------------------------------------ charts
	draw_charts(d) {
		const empty = (sel, text) => $(sel).html(`<div class="red-empty">${text}</div>`);

		// trend
		new frappe.Chart("#red-trend", {
			type: "line",
			height: 260,
			colors: ["#6366f1"],
			axisOptions: { xIsSeries: 1 },
			lineOptions: { regionFill: 1, hideDots: 0, dotSize: 5 },
			data: {
				labels: d.monthly.map((m) => m.label),
				datasets: [{ name: __("Sales value"), values: d.monthly.map((m) => m.value) }],
			},
			tooltipOptions: { formatTooltipY: (v) => this.money(v) },
		});

		// status donut
		const st = Object.keys(d.units_by_status);
		if (st.length) {
			new frappe.Chart("#red-status", {
				type: "donut",
				height: 260,
				colors: st.map((s) => RED_STATUS[s] || "#94a3b8"),
				data: { labels: st.map((s) => __(s)), datasets: [{ values: st.map((s) => d.units_by_status[s]) }] },
			});
		} else empty("#red-status", __("No units"));

		// by project
		if (d.by_project.length) {
			const labels = d.by_project.map((p) => p.project);
			new frappe.Chart("#red-projects", {
				type: "bar",
				height: 260,
				colors: RED_PALETTE,
				barOptions: { spaceRatio: 0.45 },
				data: { labels, datasets: [{ name: __("Sales"), values: d.by_project.map((p) => flt(p.sales)) }] },
				tooltipOptions: { formatTooltipY: (v) => this.money(v) },
			});
			new frappe.Chart("#red-collect", {
				type: "bar",
				height: 260,
				colors: ["#10b981", "#f43f5e"],
				barOptions: { stacked: 1, spaceRatio: 0.45 },
				data: {
					labels,
					datasets: [
						{ name: __("Collected"), values: d.by_project.map((p) => flt(p.collected)) },
						{ name: __("Outstanding"), values: d.by_project.map((p) => flt(p.outstanding)) },
					],
				},
				tooltipOptions: { formatTooltipY: (v) => this.money(v) },
			});
		} else {
			empty("#red-projects", __("No bookings yet"));
			empty("#red-collect", __("No bookings yet"));
		}
	}

	// ------------------------------------------------------------ events
	bind() {
		this.$root.on("click", "[data-unit]", (e) =>
			frappe.set_route("Form", "RE Unit", $(e.currentTarget).data("unit"))
		);
		this.$root.on("click", "[data-booking]", (e) =>
			frappe.set_route("Form", "RE Booking", $(e.currentTarget).data("booking"))
		);
	}

	// ------------------------------------------------------------ styles
	inject_css() {
		if (document.getElementById("red-style")) return;
		const css = `
		.red-wrap{--red-card:var(--card-bg,#fff);--red-line:var(--border-color,#e5e7eb);--red-text:var(--text-color,#111827);--red-muted:var(--text-muted,#6b7280);padding:6px 0 40px;color:var(--red-text)}
		.red-wrap h1,.red-wrap h2,.red-wrap h3,.red-wrap p{margin:0}
		.red-hero{position:relative;overflow:hidden;display:flex;justify-content:space-between;align-items:center;gap:24px;flex-wrap:wrap;padding:34px 38px;border-radius:22px;color:#fff;background:radial-gradient(1200px 400px at 0% 0%,rgba(124,58,237,.55),transparent 60%),radial-gradient(900px 400px at 100% 100%,rgba(6,182,212,.45),transparent 60%),linear-gradient(135deg,#0f172a,#1e3a8a);box-shadow:0 18px 40px -18px rgba(30,58,138,.6)}
		.red-hero:after{content:"";position:absolute;right:-60px;top:-60px;width:260px;height:260px;border-radius:50%;background:rgba(255,255,255,.06)}
		.red-eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;opacity:.7;margin-bottom:8px}
		.red-hero h1{font-size:30px;font-weight:800;letter-spacing:-.02em}
		.red-wave{display:inline-block;animation:redwave 2.2s ease-in-out infinite;transform-origin:70% 70%}
		@keyframes redwave{0%,60%,100%{transform:rotate(0)}10%,30%{transform:rotate(14deg)}20%{transform:rotate(-8deg)}40%{transform:rotate(-4deg)}50%{transform:rotate(10deg)}}
		.red-hero p{opacity:.75;margin-top:6px;font-size:14px}
		.red-hero-stats{display:flex;gap:14px;flex-wrap:wrap;margin-top:24px;position:relative;z-index:1}
		.red-hero-stats>div{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.16);backdrop-filter:blur(8px);padding:12px 18px;border-radius:14px;min-width:150px}
		.red-hero-stats span{display:block;font-size:11px;letter-spacing:.08em;text-transform:uppercase;opacity:.7}
		.red-hero-stats b{font-size:22px;font-weight:800}
		.red-ring{position:relative;width:176px;height:176px;z-index:1}
		.red-ring-bg{fill:none;stroke:rgba(255,255,255,.15);stroke-width:11}
		.red-ring-bar{fill:none;stroke-width:11;stroke-linecap:round;transition:stroke-dashoffset 1.2s cubic-bezier(.22,1,.36,1)}
		.red-ring-label{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
		.red-ring-label b{font-size:30px;font-weight:800}
		.red-ring-label span{font-size:11px;letter-spacing:.1em;text-transform:uppercase;opacity:.7}
		.red-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin:20px 0}
		.red-kpi{display:flex;align-items:center;gap:16px;padding:20px;background:var(--red-card);border:1px solid var(--red-line);border-radius:18px;transition:transform .2s,box-shadow .2s}
		.red-kpi:hover{transform:translateY(-4px);box-shadow:0 14px 30px -14px rgba(15,23,42,.35)}
		.red-kpi-icon{width:54px;height:54px;border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:26px;box-shadow:0 10px 20px -8px rgba(0,0,0,.35)}
		.red-kpi-label{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--red-muted)}
		.red-kpi-value{font-size:28px;font-weight:800;letter-spacing:-.02em;line-height:1.25}
		.red-kpi-sub{font-size:12px;color:var(--red-muted)}
		.red-grid{display:grid;gap:16px;margin-bottom:16px}
		.red-grid-2-1{grid-template-columns:2fr 1fr}
		.red-grid-1-1{grid-template-columns:1fr 1fr}
		.red-card{background:var(--red-card);border:1px solid var(--red-line);border-radius:18px;padding:20px 22px;min-width:0}
		.red-card-head{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px}
		.red-card-head h3{font-size:16px;font-weight:700}
		.red-card-head span,.red-card-head a{font-size:12px;color:var(--red-muted)}
		.red-section-title{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin:26px 2px 12px}
		.red-section-title h2{font-size:20px;font-weight:800}
		.red-legend{display:flex;gap:16px;font-size:12px;color:var(--red-muted)}
		.red-legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px}
		.red-towers{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px;margin-bottom:16px}
		.red-chips{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
		.red-chip{font-size:11px;font-weight:600;padding:3px 10px;border-radius:99px;color:var(--c);background:color-mix(in srgb,var(--c) 14%,transparent)}
		.red-floors{display:flex;flex-direction:column;gap:8px;max-height:360px;overflow:auto}
		.red-floor{display:flex;align-items:center;gap:10px}
		.red-floor-no{width:30px;font-size:11px;font-weight:700;color:var(--red-muted)}
		.red-tiles{display:flex;gap:8px;flex-wrap:wrap}
		.red-tile{min-width:52px;padding:9px 10px;text-align:center;border-radius:10px;font-size:12px;font-weight:700;color:#fff;background:var(--c);cursor:pointer;transition:transform .15s,box-shadow .15s;box-shadow:0 6px 14px -8px var(--c)}
		.red-tile:hover{transform:translateY(-3px) scale(1.06);box-shadow:0 12px 20px -8px var(--c)}
		.red-table-wrap{overflow:auto}
		.red-table{width:100%;border-collapse:collapse;font-size:13px}
		.red-table th{text-align:left;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--red-muted);padding:8px 10px;border-bottom:1px solid var(--red-line)}
		.red-table td{padding:12px 10px;border-bottom:1px solid var(--red-line);vertical-align:middle}
		.red-table tr[data-booking]{cursor:pointer;transition:background .15s}
		.red-table tr[data-booking]:hover{background:rgba(99,102,241,.07)}
		.red-table .r,.red-due .r{text-align:right}
		.red-muted{font-size:11px;color:var(--red-muted)}
		.red-bar{height:7px;border-radius:99px;background:var(--red-line);overflow:hidden}
		.red-bar i{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,#10b981,#06b6d4)}
		.red-due{display:flex;flex-direction:column;gap:10px}
		.red-due-item{display:flex;justify-content:space-between;gap:10px;padding:12px 14px;border:1px solid var(--red-line);border-radius:12px;cursor:pointer;transition:transform .15s,border-color .15s}
		.red-due-item:hover{transform:translateX(3px);border-color:#6366f1}
		.red-pill{display:inline-block;margin-top:4px;font-size:11px;font-weight:700;padding:2px 9px;border-radius:99px}
		.red-pill.late{background:rgba(244,63,94,.14);color:#e11d48}
		.red-pill.soon{background:rgba(245,158,11,.16);color:#d97706}
		.red-pill.ok{background:rgba(16,185,129,.14);color:#059669}
		.red-empty{padding:30px;text-align:center;color:var(--red-muted)}
		@media(max-width:960px){.red-grid-2-1,.red-grid-1-1{grid-template-columns:1fr}.red-hero{padding:24px}.red-hero h1{font-size:24px}}
		`;
		$('<style id="red-style"></style>').text(css).appendTo("head");
	}
}
"""


def run():
    if not frappe.conf.developer_mode:
        frappe.throw("Enable developer_mode first: bench --site uae.localhost set-config developer_mode 1")

    # 1. Page record (creates page/re_dashboard/ folder with json, js, py in developer mode)
    if not frappe.db.exists("Page", PAGE):
        frappe.get_doc({
            "doctype": "Page",
            "page_name": PAGE,
            "title": "Real Estate Command Center",
            "module": MODULE,
            "standard": "Yes",
            "roles": [{"role": r} for r in ("System Manager", "Sales Manager", "Sales User", "Accounts User")],
        }).insert()
        print("page created")
    else:
        print("page exists, updating JS only")

    # 2. Write the page JS
    folder = os.path.join(frappe.get_module_path(MODULE), "page", frappe.scrub(PAGE))
    os.makedirs(folder, exist_ok=True)
    js_path = os.path.join(folder, frappe.scrub(PAGE) + ".js")
    with open(js_path, "w") as fh:
        fh.write(PAGE_JS)
    print(f"wrote: {js_path}")

    # 3. Add a shortcut on the "Real Estate Dashboard" workspace (optional)
    try:
        if frappe.db.exists("Workspace", "Real Estate Dashboard"):
            ws = frappe.get_doc("Workspace", "Real Estate Dashboard")
            if not any(s.link_to == PAGE for s in ws.shortcuts):
                ws.append("shortcuts", {"label": "Command Center", "type": "Page", "link_to": PAGE})
                content = json.loads(ws.content or "[]")
                content.insert(1, {"id": frappe.generate_hash(length=10), "type": "shortcut",
                                   "data": {"shortcut_name": "Command Center", "col": 3}})
                ws.content = json.dumps(content)
                ws.save()
                print("shortcut added to workspace")
    except Exception as e:
        print(f"workspace shortcut skipped ({e})")

    frappe.db.commit()
    frappe.clear_cache()
    print("\nDone. Run: bench --site uae.localhost clear-cache && bench restart")
    print("Open: http://uae.localhost:8000/app/re-dashboard")
