
"use strict";

(function () {
    const NS = "http://www.w3.org/2000/svg";

    // Dostępne kształty herbów
    const paths = {
        shield: "M50 5 L90 18 L86 65 Q77 85 50 96 Q23 85 14 65 L10 18 Z",
        circle: "M50 5 A45 45 0 1 1 49.99 5 Z",
        hex: "M50 5 L89 27 L89 73 L50 95 L11 73 L11 27 Z",
        round: "M23 7 H77 Q93 7 93 23 V70 Q93 87 50 96 Q7 87 7 70 V23 Q7 7 23 7 Z"
    };

    // Domyślny wygląd herbu
    const defaults = {
        shape: "shield",
        color: "#1765d1",
        accent: "#f7c948",
        symbol: "ball",
        initials: "FC"
    };

    // Tworzenie elementów SVG
    function element(name, attrs, parent) {
        const node = document.createElementNS(NS, name);

        Object.entries(attrs || {}).forEach(([key, value]) => {
            node.setAttribute(key, String(value));
        });

        if (parent) {
            parent.appendChild(node);
        }

        return node;
    }

    // Rysowanie herbu
    function renderCrest(target, input) {
        const data = {
            ...defaults,
            ...(input || {})
        };

        if (!paths[data.shape]) {
            data.shape = "shield";
        }

        const svg = element("svg", {
            viewBox: "0 0 100 110",
            role: "img",
            "aria-label": "Herb klubu"
        });

        // Tło i obramowanie
        element("path", {
            d: paths[data.shape],
            fill: data.color,
            stroke: data.accent,
            "stroke-width": 4
        }, svg);

        // Symbol na herbie
        if (data.symbol === "stripes") {
            element("path", {
                d: "M35 22 V81 M50 20 V87 M65 22 V81",
                stroke: data.accent,
                "stroke-width": 6,
                opacity: 0.8
            }, svg);

        } else if (data.symbol === "ball") {
            element("circle", {
                cx: 50,
                cy: 58,
                r: 18,
                fill: "white"
            }, svg);

            element("path", {
                d: "M50 47 L60 54 L56 65 L44 65 L40 54 Z",
                fill: "#172230"
            }, svg);

        } else if (data.symbol === "star") {
            element("path", {
                d: "M50 34 L56 48 L71 49 L60 59 L63 75 L50 66 L37 75 L40 59 L29 49 L44 48 Z",
                fill: data.accent
            }, svg);

        } else if (data.symbol === "crown") {
            element("path", {
                d: "M27 48 L39 57 L50 40 L61 57 L73 48 L68 73 H32 Z",
                fill: data.accent
            }, svg);
        }

        // Inicjały klubu
        const letters = element("text", {
            x: 50,
            y: data.symbol === "letters" ? 65 : 29,
            "text-anchor": "middle",
            fill: "white",
            "font-size": data.symbol === "letters" ? 24 : 12,
            "font-weight": "bold"
        }, svg);

        letters.textContent = String(data.initials || "FC")
            .slice(0, 3)
            .toUpperCase();

        target.replaceChildren(svg);
    }

    // Wyświetlanie zapisanych herbów
    document.querySelectorAll(".fm-crest[data-crest]").forEach(node => {
        let data;

        try {
            data = JSON.parse(node.dataset.crest);
        } catch {
            data = defaults;
        }

        renderCrest(node, data);
    });

    // Odczytywanie zapisanego herbu
    const initial = document.getElementById("crest-initial");

    if (!initial) {
        return;
    }

    let saved;

    try {
        saved = JSON.parse(initial.textContent);
    } catch {
        saved = defaults;
    }

    // Obsługa formularza
    const fields = [
        "shape",
        "color",
        "accent",
        "symbol",
        "initials"
    ];

    for (const key of fields) {
        const input = document.getElementById(key);

        input.value = saved[key] || defaults[key];
        input.addEventListener("input", update);
    }

    // Gotowe kolory
    document.querySelectorAll(".swatches button").forEach(button => {
        button.addEventListener("click", () => {
            const key = button.closest(".swatches").dataset.for;

            document.getElementById(key).value = button.dataset.color;

            update();
        });
    });

    // Pobieranie ustawień herbu
    function getData() {
        return Object.fromEntries(
            fields.map(key => [
                key,
                document.getElementById(key).value
            ])
        );
    }

    // Aktualizacja podglądu
    function update() {
        const preview = document.getElementById("crest-preview");

        renderCrest(preview, getData());
    }

    // Zapis herbu
    document.getElementById("crest-form").addEventListener("submit", () => {
        document.getElementById("crest-json").value = JSON.stringify(getData());
    });

    // Pierwsze wyświetlenie herbu
    update();
})();
