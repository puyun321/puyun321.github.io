/* =============================================================
   Shared site behaviour: search + tag filtering,
   stats counters and small animations.

   A list becomes filterable by giving it class "filter-list", an id,
   and data-groups="year,type,topic,method" (any subset). Each <li>
   carries the matching data-* attributes; multiple values are "|"-separated.
   A <div class="filter-bar" data-for="<list id>"> is filled with the
   search box and tag chips.
   ============================================================= */
(function () {
    const GROUP_LABELS = { year: "Year", type: "Type", topic: "Topic", method: "Method" };

    const el = (tag, cls, text) => {
        const e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text != null) e.textContent = text;
        return e;
    };
    const values = (li, g) => (li.dataset[g] || "").split("|").map((s) => s.trim()).filter(Boolean);
    const escapeHtml = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

    /* ---------- filterable lists ---------- */
    function initFilterList(list) {
        const items = Array.from(list.children).filter((n) => n.tagName === "LI");
        const groups = (list.dataset.groups || "").split(",").map((s) => s.trim()).filter(Boolean);
        const bar = document.querySelector('.filter-bar[data-for="' + list.id + '"]');
        const sel = {};
        groups.forEach((g) => (sel[g] = new Set()));
        let query = "";

        // tag chips on each item (year is already shown as a badge)
        items.forEach((li) => {
            const tags = el("div", "tags");
            groups.filter((g) => g !== "year").forEach((g) => {
                values(li, g).forEach((v) => {
                    const t = el(bar ? "button" : "span", "tag tag-" + g, v);
                    if (bar) {
                        t.type = "button";
                        t.onclick = () => toggle(g, v);
                    }
                    tags.appendChild(t);
                });
            });
            if (tags.children.length) li.appendChild(tags);
            const title = li.querySelector(".item-title, a");
            if (title) li._title = { node: title, text: title.textContent.trim() };
        });

        if (!bar) return;

        // search box
        const searchWrap = el("div", "search-container");
        const input = el("input");
        input.type = "search";
        input.id = "search-input";
        input.placeholder = bar.dataset.placeholder || "Search…  (press / to focus)";
        input.setAttribute("aria-label", "Search");
        input.oninput = () => { query = input.value; apply(); };
        searchWrap.appendChild(input);
        searchWrap.appendChild(el("kbd", "kbd-hint", "/"));
        bar.appendChild(searchWrap);

        // chip rows, one per group
        const chipIndex = {};
        groups.forEach((g) => {
            const counts = new Map();
            items.forEach((li) => values(li, g).forEach((v) => counts.set(v, (counts.get(v) || 0) + 1)));
            if (!counts.size) return;
            let entries = Array.from(counts.entries());
            entries.sort(g === "year" ? (a, b) => b[0].localeCompare(a[0]) : (a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
            const row = el("div", "chip-row");
            row.appendChild(el("span", "chip-label", GROUP_LABELS[g] || g));
            entries.forEach(([v, n]) => {
                const c = el("button", "chip chip-" + g);
                c.type = "button";
                c.innerHTML = escapeHtml(v) + '<span class="chip-count">' + n + "</span>";
                c.title = v + ": " + n + (n === 1 ? " item" : " items");
                c.onclick = () => toggle(g, v);
                row.appendChild(c);
                chipIndex[g + "\u0000" + v] = c;
            });
            bar.appendChild(row);
        });

        const status = el("div", "filter-status");
        const countText = el("span", "result-count");
        const clear = el("button", "clear-btn", "Clear filters ✕");
        clear.type = "button";
        clear.onclick = () => {
            query = input.value = "";
            groups.forEach((g) => sel[g].clear());
            apply();
        };
        status.append(countText, clear);
        bar.appendChild(status);

        const empty = el("p", "empty-state", "No matches — try a different keyword or clear the filters.");
        list.after(empty);

        function toggle(g, v) {
            sel[g].has(v) ? sel[g].delete(v) : sel[g].add(v);
            apply();
            bar.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }

        function highlight(li, terms) {
            if (!li._title) return;
            const { node, text } = li._title;
            if (!terms.length) { node.textContent = text; return; }
            const re = new RegExp("(" + terms.map(escapeRe).join("|") + ")", "gi");
            node.innerHTML = text.split(re).map((part, i) => (i % 2 ? "<mark>" + escapeHtml(part) + "</mark>" : escapeHtml(part))).join("");
        }

        function apply() {
            const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
            let shown = 0;
            items.forEach((li) => {
                const hay = (li._title ? li._title.text : "") + " " + li.textContent + " " +
                    groups.map((g) => li.dataset[g] || "").join(" ");
                const lower = hay.toLowerCase();
                // AND across groups, OR within a group
                const ok = terms.every((t) => lower.includes(t)) &&
                    groups.every((g) => !sel[g].size || values(li, g).some((v) => sel[g].has(v)));
                li.hidden = !ok;
                if (ok) shown++;
                highlight(li, terms);
                li.querySelectorAll(".tags .tag").forEach((t) => {
                    const g = t.className.match(/tag-(\w+)/)[1];
                    t.classList.toggle("active", sel[g] && sel[g].has(t.textContent));
                });
            });
            Object.entries(chipIndex).forEach(([k, c]) => {
                const [g, v] = k.split("\u0000");
                c.classList.toggle("active", sel[g].has(v));
            });
            const active = terms.length || groups.some((g) => sel[g].size);
            countText.innerHTML = "Showing <b>" + shown + "</b> of " + items.length;
            clear.hidden = !active;
            empty.hidden = shown > 0;
            syncUrl();
        }

        function syncUrl() {
            const p = new URLSearchParams();
            if (query.trim()) p.set("q", query.trim());
            groups.forEach((g) => { if (sel[g].size) p.set(g, Array.from(sel[g]).join("|")); });
            const qs = p.toString();
            history.replaceState(null, "", location.pathname + (qs ? "?" + qs : "") + location.hash);
        }

        // restore state from the URL so filtered views can be shared
        const params = new URLSearchParams(location.search);
        query = input.value = params.get("q") || "";
        groups.forEach((g) => (params.get(g) || "").split("|").filter(Boolean).forEach((v) => sel[g].add(v)));
        apply();

        document.addEventListener("keydown", (e) => {
            if (e.key === "/" && document.activeElement.tagName !== "INPUT") {
                e.preventDefault();
                input.focus();
            }
        });
    }

    /* ---------- stats counters ---------- */
    // data-stats="total:Label,type=Journal:Label,span:Label"
    function initStats(box) {
        const list = document.getElementById(box.dataset.for);
        if (!list) return;
        const items = Array.from(list.children).filter((n) => n.tagName === "LI");
        box.dataset.stats.split(",").forEach((spec) => {
            const [key, label] = spec.split(":");
            let n;
            if (key === "total") n = items.length;
            else if (key === "span") {
                const ys = items.flatMap((li) => values(li, "year")).map(Number).filter(Boolean);
                n = ys.length ? Math.max(...ys) - Math.min(...ys) + 1 : 0;
            } else {
                const [g, v] = key.split("=");
                n = items.filter((li) => values(li, g).includes(v)).length;
            }
            const card = el("div", "stat");
            const num = el("div", "stat-num", "0");
            num.dataset.target = n;
            card.append(num, el("div", "stat-label", label));
            box.appendChild(card);
        });
        const run = () => box.querySelectorAll(".stat-num").forEach((num) => {
            const target = +num.dataset.target, t0 = performance.now(), dur = 1100;
            const step = (t) => {
                const k = Math.min(1, (t - t0) / dur);
                num.textContent = Math.round(target * (1 - Math.pow(1 - k, 3)));
                if (k < 1) requestAnimationFrame(step);
            };
            requestAnimationFrame(step);
        });
        run();
    }

    /* ---------- cursor glow on cards + scroll reveal ---------- */
    function initEffects() {
        document.querySelectorAll(".info-box, .info-box2").forEach((card) => {
            card.addEventListener("pointermove", (e) => {
                const r = card.getBoundingClientRect();
                card.style.setProperty("--mx", e.clientX - r.left + "px");
                card.style.setProperty("--my", e.clientY - r.top + "px");
            });
        });

        if (!("IntersectionObserver" in window) || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
        const io = new IntersectionObserver((entries) => entries.forEach((en) => {
            if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
        }), { rootMargin: "0px 0px -40px 0px" });
        document.querySelectorAll(".filter-list > li, .stat").forEach((n, i) => {
            n.classList.add("reveal");
            n.style.transitionDelay = Math.min(i % 12, 12) * 35 + "ms";
            io.observe(n);
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll(".filter-list[id]").forEach(initFilterList);
        document.querySelectorAll(".stats[data-for]").forEach(initStats);
        initEffects();
    });
})();
