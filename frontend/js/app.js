/**
 * SoundBox Pallet Optimizer - Módulo Principal da Aplicação
 */

document.addEventListener("DOMContentLoaded", () => {
    initVisualization();
    setupUnitSystem();
    setupCasesManager();
    setupCalculation();
    setupExport();
    setupBoxTypeToggle();
});

// ============================================================
// Sistema de Unidades
// ============================================================

const UNIT_DEFAULTS = {
    metric: {
        pSizex: 120, pSizey: 100, pSizez: 150, pMaxWeight: 1000,
        cSizex: 30, cSizey: 25, cSizez: 20, cWeight: 2.5,
        lengthLabel: "cm", weightLabel: "kg",
    },
    imperial: {
        pSizex: 48, pSizey: 40, pSizez: 60, pMaxWeight: 2500,
        cSizex: 12, cSizey: 10, cSizez: 8, cWeight: 5,
        lengthLabel: "inches", weightLabel: "lbs",
    },
};

function setupUnitSystem() {
    const select = document.getElementById("unit-system");
    select.addEventListener("change", (e) => {
        applyUnitSystem(e.target.value);
    });
}

function applyUnitSystem(system) {
    const d = UNIT_DEFAULTS[system];

    // Atualiza labels
    document.querySelectorAll(".unit-length").forEach((el) => (el.textContent = d.lengthLabel));
    document.querySelectorAll(".unit-weight").forEach((el) => (el.textContent = d.weightLabel));

    // Atualiza valores do palete
    document.getElementById("p-sizex").value = d.pSizex;
    document.getElementById("p-sizey").value = d.pSizey;
    document.getElementById("p-sizez").value = d.pSizez;
    document.getElementById("p-max-weight").value = d.pMaxWeight;

    // Atualiza valores da primeira caixa
    const firstCase = document.querySelector(".case-row");
    if (firstCase) {
        firstCase.querySelector(".case-sizex").value = d.cSizex;
        firstCase.querySelector(".case-sizey").value = d.cSizey;
        firstCase.querySelector(".case-sizez").value = d.cSizez;
        firstCase.querySelector(".case-weight").value = d.cWeight;
    }
}

// ============================================================
// Toggle tipo de caixa (Retangular / L)
// ============================================================

function setupBoxTypeToggle() {
    const select = document.getElementById("box-type");
    select.addEventListener("change", (e) => {
        const lSection = document.getElementById("l-box-section");
        const regularSection = document.getElementById("regular-box-section");

        if (e.target.value === "l-shape") {
            lSection.classList.remove("hidden");
            // Mostra as caixas retangulares só se o usuário quiser
            updateRegularVisibility();
        } else {
            lSection.classList.add("hidden");
            regularSection.classList.remove("hidden");
        }
    });

    // Toggle para incluir retangulares junto com L
    const includeRegular = document.getElementById("include-regular");
    if (includeRegular) {
        includeRegular.addEventListener("change", updateRegularVisibility);
    }
}

function updateRegularVisibility() {
    const includeRegular = document.getElementById("include-regular");
    const regularSection = document.getElementById("regular-box-section");
    if (includeRegular && includeRegular.value === "yes") {
        regularSection.classList.remove("hidden");
    } else if (document.getElementById("box-type").value === "l-shape") {
        regularSection.classList.add("hidden");
    }
}

// ============================================================
// Gerenciamento de Caixas (adicionar/remover tipos)
// ============================================================

let caseCounter = 1;

function setupCasesManager() {
    document.getElementById("add-case-btn").addEventListener("click", addCaseRow);

    // Remove handler para a primeira caixa
    document.querySelector(".btn-remove-case").addEventListener("click", removeCaseRow);
}

function addCaseRow() {
    const container = document.getElementById("cases-container");
    const system = document.getElementById("unit-system").value;
    const d = UNIT_DEFAULTS[system];

    const div = document.createElement("div");
    div.className = "case-row";
    div.dataset.index = caseCounter;

    div.innerHTML = `
        <div class="input-row">
            <label>Código:
                <input type="text" class="case-code" value="BOX-${String.fromCharCode(65 + caseCounter)}">
            </label>
            <label>Comp. (<span class="unit-length">${d.lengthLabel}</span>):
                <input type="number" class="case-sizex" value="${d.cSizex}" step="0.1">
            </label>
            <label>Larg. (<span class="unit-length">${d.lengthLabel}</span>):
                <input type="number" class="case-sizey" value="${d.cSizey}" step="0.1">
            </label>
            <label>Alt. (<span class="unit-length">${d.lengthLabel}</span>):
                <input type="number" class="case-sizez" value="${d.cSizez}" step="0.1">
            </label>
        </div>
        <div class="input-row">
            <label>Peso (<span class="unit-weight">${d.weightLabel}</span>):
                <input type="number" class="case-weight" value="${d.cWeight}" step="0.1">
            </label>
            <label>Quantidade:
                <input type="number" class="case-quantity" value="20" min="1">
            </label>
            <label>Resistência:
                <input type="number" class="case-strength" value="5" min="1" title="Quantas caixas aguenta em cima">
            </label>
            <button class="btn-remove-case" title="Remover caixa">&times;</button>
        </div>
    `;

    container.appendChild(div);
    div.querySelector(".btn-remove-case").addEventListener("click", removeCaseRow);
    caseCounter++;
}

function removeCaseRow(e) {
    const container = document.getElementById("cases-container");
    if (container.children.length <= 1) {
        alert("É necessário pelo menos um tipo de caixa.");
        return;
    }
    e.target.closest(".case-row").remove();
}

// ============================================================
// Cálculo
// ============================================================

let lastResult = null;

function setupCalculation() {
    document.getElementById("calculate-btn").addEventListener("click", calculate);
}

async function calculate() {
    const btn = document.getElementById("calculate-btn");
    btn.textContent = "Calculando...";
    btn.classList.add("loading");

    const boxType = document.getElementById("box-type").value;

    try {
        let data;

        if (boxType === "l-shape") {
            data = await calculateLShape();
        } else {
            data = await calculateRegular();
        }

        if (!data) return;

        lastResult = data;
        displayResults(data);
    } catch (err) {
        alert("Erro de conexão com o servidor. Verifique se o backend está rodando.");
        console.error(err);
    } finally {
        btn.textContent = "Calcular Empacotamento";
        btn.classList.remove("loading");
    }
}

async function calculateRegular() {
    const payload = buildPayload();

    const response = await fetch("/api/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
        alert(data.error || "Erro ao calcular.");
        return null;
    }

    if (data.total_cases === 0) {
        alert("Nenhuma caixa pôde ser posicionada com essas dimensões e restrições.");
        return null;
    }

    return data;
}

async function calculateLShape() {
    const pallet = {
        sizex: parseFloat(document.getElementById("p-sizex").value),
        sizey: parseFloat(document.getElementById("p-sizey").value),
        sizez: parseFloat(document.getElementById("p-sizez").value),
        max_weight: parseFloat(document.getElementById("p-max-weight").value) || 99999,
    };

    const l_box = {
        comp_total: parseFloat(document.getElementById("l-comp-total").value),
        largura: parseFloat(document.getElementById("l-largura").value),
        alt_vertical: parseFloat(document.getElementById("l-alt-vertical").value),
        alt_perpendicular: parseFloat(document.getElementById("l-alt-perpendicular").value),
        comp_braco: parseFloat(document.getElementById("l-comp-braco").value),
        l_orientation: document.getElementById("l-orientation").value || "vertical",
        weight: parseFloat(document.getElementById("l-weight").value) || 0,
        quantity: parseInt(document.getElementById("l-quantity").value) || 1,
    };

    // Verifica se inclui caixas retangulares também
    let regular_box = null;
    const includeRegular = document.getElementById("include-regular");
    if (includeRegular && includeRegular.value === "yes") {
        const firstCase = document.querySelector(".case-row");
        if (firstCase) {
            regular_box = {
                code: firstCase.querySelector(".case-code").value || "BOX-RECT",
                sizex: parseFloat(firstCase.querySelector(".case-sizex").value),
                sizey: parseFloat(firstCase.querySelector(".case-sizey").value),
                sizez: parseFloat(firstCase.querySelector(".case-sizez").value),
                weight: parseFloat(firstCase.querySelector(".case-weight").value) || 0,
                quantity: parseInt(firstCase.querySelector(".case-quantity").value) || 0,
                strength: parseInt(firstCase.querySelector(".case-strength").value) || 100,
            };
        }
    }

    const payload = { pallet, l_box, regular_box, overhang: parseFloat(document.getElementById("p-overhang").value) || 0 };

    const response = await fetch("/api/calculate-l", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
        alert(data.error || "Erro ao calcular.");
        return null;
    }

    const lResult = data.l_result;
    if (!lResult.success) {
        alert(lResult.error || "Não foi possível posicionar caixas em L.");
        return null;
    }

    // O resultado já vem no formato correto do backend
    const cases = lResult.caixas.map((c) => ({
        code: c.code,
        x: c.x,
        y: c.y,
        z: c.z,
        sizex: c.sizex,
        sizey: c.sizey,
        sizez: c.sizez,
        weight: c.weight,
        rotated: c.rotated || false,
    }));

    // Adiciona caixas retangulares se houver
    if (data.regular_result && data.regular_result.cases) {
        cases.push(...data.regular_result.cases);
    }

    const totalWeight = lResult.peso_total + (data.regular_result ? data.regular_result.total_weight : 0);
    const totalCases = lResult.total + (data.regular_result ? data.regular_result.total_cases : 0);
    const palletVol = pallet.sizex * pallet.sizey * pallet.sizez;
    const casesVol = cases.reduce((sum, c) => sum + c.sizex * c.sizey * c.sizez, 0);

    return {
        pallet: data.pallet,
        cases: cases,
        total_cases: totalCases,
        total_weight: totalWeight,
        volume_utilization: Math.round((casesVol / palletVol) * 10000) / 100,
        weight_utilization: Math.round((totalWeight / pallet.max_weight) * 10000) / 100,
        requested_cases: l_box.quantity + (regular_box ? regular_box.quantity : 0),
        l_info: {
            caixas_por_camada: lResult.caixas_por_camada,
            num_camadas: lResult.num_camadas,
            cabe_tudo: lResult.cabe_tudo,
        },
    };
}

function buildPayload() {
    const pallet = {
        sizex: parseFloat(document.getElementById("p-sizex").value),
        sizey: parseFloat(document.getElementById("p-sizey").value),
        sizez: parseFloat(document.getElementById("p-sizez").value),
        max_weight: parseFloat(document.getElementById("p-max-weight").value) || null,
    };

    const overhang = parseFloat(document.getElementById("p-overhang").value) || 0;

    const cases = [];
    document.querySelectorAll(".case-row").forEach((row) => {
        cases.push({
            code: row.querySelector(".case-code").value || "BOX",
            sizex: parseFloat(row.querySelector(".case-sizex").value),
            sizey: parseFloat(row.querySelector(".case-sizey").value),
            sizez: parseFloat(row.querySelector(".case-sizez").value),
            weight: parseFloat(row.querySelector(".case-weight").value) || 0,
            quantity: parseInt(row.querySelector(".case-quantity").value) || 1,
            strength: parseInt(row.querySelector(".case-strength").value) || 100,
            pallet_face: row.querySelector(".case-pallet-face") ? row.querySelector(".case-pallet-face").value : "xy",
            interlocking_type: row.querySelector(".case-interlocking") ? row.querySelector(".case-interlocking").value : "mirror",
        });
    });

    return { pallet, cases, overhang };
}

function displayResults(data) {
    const resultsSection = document.getElementById("results");
    resultsSection.classList.remove("hidden");

    const weightUnit = document.getElementById("unit-system").value === "metric" ? "kg" : "lbs";

    document.getElementById("stat-total").textContent = data.total_cases;
    document.getElementById("stat-volume").textContent = data.volume_utilization + "%";
    document.getElementById("stat-weight").textContent =
        data.total_weight.toFixed(1) + " " + weightUnit;
    document.getElementById("stat-weight-util").textContent = data.weight_utilization + "%";

    // Aviso se não coube todas as caixas
    const warningEl = document.getElementById("packing-warning");
    if (data.requested_cases && data.total_cases < data.requested_cases) {
        const missing = data.requested_cases - data.total_cases;
        warningEl.textContent =
            `⚠️ Apenas ${data.total_cases} de ${data.requested_cases} caixas foram posicionadas. ` +
            `${missing} caixa(s) não coube(ram) no palete.`;
        warningEl.classList.remove("hidden");
    } else {
        warningEl.classList.add("hidden");
    }

    // Desenha na visualização 3D
    drawResult(data);
}

// ============================================================
// Exportação CSV
// ============================================================

function setupExport() {
    document.getElementById("export-csv-btn").addEventListener("click", exportCSV);
}

async function exportCSV() {
    if (!lastResult || !lastResult.cases.length) {
        alert("Calcule o empacotamento primeiro.");
        return;
    }

    try {
        const response = await fetch("/api/export-csv", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ cases: lastResult.cases }),
        });

        const data = await response.json();

        if (!response.ok) {
            alert(data.error || "Erro ao exportar.");
            return;
        }

        // Download do CSV
        const blob = new Blob([data.csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "pallet_coordinates.csv";
        a.click();
        URL.revokeObjectURL(url);
    } catch (err) {
        alert("Erro ao exportar CSV.");
        console.error(err);
    }
}


// ============================================================
// Gerenciamento de Presets (modelos salvos)
// ============================================================

let presetsCache = [];

function setupPresets() {
    document.getElementById("load-preset-btn").addEventListener("click", loadPreset);
    document.getElementById("save-preset-btn").addEventListener("click", savePreset);
    document.getElementById("delete-preset-btn").addEventListener("click", deletePreset);
    fetchPresets();
}

async function fetchPresets() {
    try {
        const response = await fetch("/api/presets");
        presetsCache = await response.json();
        renderPresetOptions();
    } catch (err) {
        console.error("Erro ao carregar presets:", err);
    }
}

function renderPresetOptions() {
    const select = document.getElementById("preset-select");
    select.innerHTML = '<option value="">-- Selecione um modelo --</option>';
    presetsCache.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = p.name;
        select.appendChild(opt);
    });
}

function loadPreset() {
    const select = document.getElementById("preset-select");
    const preset = presetsCache.find((p) => p.id === select.value);
    if (!preset) {
        alert("Selecione um modelo para carregar.");
        return;
    }

    // Pallet
    if (preset.pallet) {
        document.getElementById("p-sizex").value = preset.pallet.sizex || 120;
        document.getElementById("p-sizey").value = preset.pallet.sizey || 100;
        document.getElementById("p-sizez").value = preset.pallet.sizez || 150;
        document.getElementById("p-max-weight").value = preset.pallet.max_weight || 1000;
    }
    if (preset.overhang !== undefined) {
        document.getElementById("p-overhang").value = preset.overhang;
    }

    // Tipo de caixa
    const boxType = preset.type === "l-shape" ? "l-shape" : "regular";
    document.getElementById("box-type").value = boxType;
    document.getElementById("box-type").dispatchEvent(new Event("change"));

    if (boxType === "l-shape" && preset.l_box) {
        document.getElementById("l-comp-total").value = preset.l_box.comp_total || 91.4;
        document.getElementById("l-largura").value = preset.l_box.largura || 26.3;
        document.getElementById("l-alt-vertical").value = preset.l_box.alt_vertical || 43.5;
        document.getElementById("l-alt-perpendicular").value = preset.l_box.alt_perpendicular || 14.1;
        document.getElementById("l-comp-braco").value = preset.l_box.comp_braco || 45.7;
        document.getElementById("l-weight").value = preset.l_box.weight || 8;
        document.getElementById("l-quantity").value = preset.l_box.quantity || 10;
    }

    if (preset.cases && preset.cases.length > 0) {
        const firstCase = document.querySelector(".case-row");
        if (firstCase) {
            const c = preset.cases[0];
            firstCase.querySelector(".case-code").value = c.code || "BOX-A";
            firstCase.querySelector(".case-sizex").value = c.sizex || 30;
            firstCase.querySelector(".case-sizey").value = c.sizey || 25;
            firstCase.querySelector(".case-sizez").value = c.sizez || 20;
            firstCase.querySelector(".case-weight").value = c.weight || 2.5;
            firstCase.querySelector(".case-quantity").value = c.quantity || 40;
            firstCase.querySelector(".case-strength").value = c.strength || 10;
        }
    }
}

async function savePreset() {
    const name = prompt("Nome do modelo:");
    if (!name) return;

    const boxType = document.getElementById("box-type").value;

    const preset = {
        name: name,
        type: boxType,
        pallet: {
            sizex: parseFloat(document.getElementById("p-sizex").value),
            sizey: parseFloat(document.getElementById("p-sizey").value),
            sizez: parseFloat(document.getElementById("p-sizez").value),
            max_weight: parseFloat(document.getElementById("p-max-weight").value),
        },
        overhang: parseFloat(document.getElementById("p-overhang").value) || 0,
    };

    if (boxType === "l-shape") {
        preset.l_box = {
            comp_total: parseFloat(document.getElementById("l-comp-total").value),
            largura: parseFloat(document.getElementById("l-largura").value),
            alt_vertical: parseFloat(document.getElementById("l-alt-vertical").value),
            alt_perpendicular: parseFloat(document.getElementById("l-alt-perpendicular").value),
            comp_braco: parseFloat(document.getElementById("l-comp-braco").value),
            weight: parseFloat(document.getElementById("l-weight").value),
            quantity: parseInt(document.getElementById("l-quantity").value),
        };
    } else {
        const firstCase = document.querySelector(".case-row");
        if (firstCase) {
            preset.cases = [{
                code: firstCase.querySelector(".case-code").value,
                sizex: parseFloat(firstCase.querySelector(".case-sizex").value),
                sizey: parseFloat(firstCase.querySelector(".case-sizey").value),
                sizez: parseFloat(firstCase.querySelector(".case-sizez").value),
                weight: parseFloat(firstCase.querySelector(".case-weight").value),
                quantity: parseInt(firstCase.querySelector(".case-quantity").value),
                strength: parseInt(firstCase.querySelector(".case-strength").value),
            }];
        }
    }

    try {
        const response = await fetch("/api/presets", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(preset),
        });
        const data = await response.json();
        if (data.success) {
            await fetchPresets();
            document.getElementById("preset-select").value = data.id;
        }
    } catch (err) {
        alert("Erro ao salvar modelo.");
        console.error(err);
    }
}

async function deletePreset() {
    const select = document.getElementById("preset-select");
    if (!select.value) {
        alert("Selecione um modelo para excluir.");
        return;
    }
    const preset = presetsCache.find((p) => p.id === select.value);
    if (!confirm(`Excluir o modelo "${preset.name}"?`)) return;

    try {
        await fetch(`/api/presets/${select.value}`, { method: "DELETE" });
        await fetchPresets();
    } catch (err) {
        alert("Erro ao excluir modelo.");
        console.error(err);
    }
}


// ============================================================
// Banco de Modelos de Caixas (SQLite)
// ============================================================

let boxModelsCache = [];

document.addEventListener("DOMContentLoaded", () => {
    setupBoxModels();
});

function setupBoxModels() {
    document.getElementById("load-box-model-btn").addEventListener("click", loadBoxModel);
    document.getElementById("manage-box-models-btn").addEventListener("click", toggleBoxModelForm);
    document.getElementById("bm-save-btn").addEventListener("click", saveBoxModel);
    document.getElementById("bm-cancel-btn").addEventListener("click", hideBoxModelForm);
    document.getElementById("bm-delete-btn").addEventListener("click", deleteBoxModel);
    document.getElementById("bm-type").addEventListener("change", toggleBmFields);
    fetchBoxModels();
}

async function fetchBoxModels() {
    try {
        const response = await fetch("/api/boxes");
        boxModelsCache = await response.json();
        renderBoxModelOptions();
    } catch (err) {
        console.error("Erro ao carregar modelos:", err);
    }
}

function renderBoxModelOptions() {
    const select = document.getElementById("box-model-select");
    select.innerHTML = '<option value="">-- Selecione para carregar --</option>';
    boxModelsCache.forEach((m) => {
        const opt = document.createElement("option");
        opt.value = m.id;
        opt.textContent = `${m.name} (${m.type === "l-shape" ? "L" : m.sizex + "×" + m.sizey + "×" + m.sizez})`;
        select.appendChild(opt);
    });
}

function loadBoxModel() {
    const select = document.getElementById("box-model-select");
    const model = boxModelsCache.find((m) => m.id == select.value);
    if (!model) { alert("Selecione um modelo."); return; }

    // Preenche pallet
    document.getElementById("p-sizex").value = model.pallet_sizex || 100;
    document.getElementById("p-sizey").value = model.pallet_sizey || 120;
    document.getElementById("p-sizez").value = model.pallet_sizez || 200;
    document.getElementById("p-max-weight").value = model.pallet_max_weight || 1200;
    document.getElementById("p-overhang").value = model.overhang || 5;

    if (model.type === "l-shape") {
        document.getElementById("box-type").value = "l-shape";
        document.getElementById("box-type").dispatchEvent(new Event("change"));
        document.getElementById("l-comp-total").value = model.comp_total || "";
        document.getElementById("l-largura").value = model.largura || "";
        document.getElementById("l-alt-vertical").value = model.alt_vertical || "";
        document.getElementById("l-alt-perpendicular").value = model.alt_perpendicular || "";
        document.getElementById("l-comp-braco").value = model.comp_braco || "";
        document.getElementById("l-orientation").value = model.l_orientation || "vertical";
        document.getElementById("l-weight").value = model.weight || "";
        document.getElementById("l-quantity").value = model.quantity || 10;
    } else {
        document.getElementById("box-type").value = "regular";
        document.getElementById("box-type").dispatchEvent(new Event("change"));
        const firstCase = document.querySelector(".case-row");
        if (firstCase) {
            firstCase.querySelector(".case-code").value = model.code || model.name;
            firstCase.querySelector(".case-sizex").value = model.sizex || "";
            firstCase.querySelector(".case-sizey").value = model.sizey || "";
            firstCase.querySelector(".case-sizez").value = model.sizez || "";
            firstCase.querySelector(".case-weight").value = model.weight || "";
            firstCase.querySelector(".case-quantity").value = model.quantity || 10;
            firstCase.querySelector(".case-strength").value = model.strength || 10;
            if (firstCase.querySelector(".case-pallet-face")) {
                firstCase.querySelector(".case-pallet-face").value = model.pallet_face || "xy";
            }
            if (firstCase.querySelector(".case-interlocking")) {
                firstCase.querySelector(".case-interlocking").value = model.interlocking_type || "mirror";
            }
        }
    }
}

function toggleBoxModelForm() {
    const form = document.getElementById("box-model-form");
    if (form.classList.contains("hidden")) {
        // Abrir para novo ou editar selecionado
        const select = document.getElementById("box-model-select");
        const model = boxModelsCache.find((m) => m.id == select.value);
        if (model) {
            fillBoxModelForm(model);
            document.getElementById("box-form-title").textContent = "Editar Modelo";
            document.getElementById("bm-delete-btn").classList.remove("hidden");
        } else {
            clearBoxModelForm();
            document.getElementById("box-form-title").textContent = "Novo Modelo de Caixa";
            document.getElementById("bm-delete-btn").classList.add("hidden");
        }
        form.classList.remove("hidden");
    } else {
        form.classList.add("hidden");
    }
}

function hideBoxModelForm() {
    document.getElementById("box-model-form").classList.add("hidden");
}

function toggleBmFields() {
    const type = document.getElementById("bm-type").value;
    document.getElementById("bm-regular-fields").classList.toggle("hidden", type === "l-shape");
    document.getElementById("bm-l-fields").classList.toggle("hidden", type !== "l-shape");
}

function fillBoxModelForm(model) {
    document.getElementById("bm-id").value = model.id;
    document.getElementById("bm-name").value = model.name || "";
    document.getElementById("bm-code").value = model.code || "";
    document.getElementById("bm-type").value = model.type || "regular";
    document.getElementById("bm-sizex").value = model.sizex || "";
    document.getElementById("bm-sizey").value = model.sizey || "";
    document.getElementById("bm-sizez").value = model.sizez || "";
    document.getElementById("bm-weight").value = model.weight || "";
    document.getElementById("bm-strength").value = model.strength || 10;
    document.getElementById("bm-quantity").value = model.quantity || 10;
    document.getElementById("bm-comp-total").value = model.comp_total || "";
    document.getElementById("bm-largura").value = model.largura || "";
    document.getElementById("bm-alt-vertical").value = model.alt_vertical || "";
    document.getElementById("bm-alt-perp").value = model.alt_perpendicular || "";
    document.getElementById("bm-comp-braco").value = model.comp_braco || "";
    document.getElementById("bm-l-orientation").value = model.l_orientation || "vertical";
    document.getElementById("bm-pallet-sizex").value = model.pallet_sizex || 100;
    document.getElementById("bm-pallet-sizey").value = model.pallet_sizey || 120;
    document.getElementById("bm-pallet-sizez").value = model.pallet_sizez || 200;
    document.getElementById("bm-pallet-weight").value = model.pallet_max_weight || 1200;
    document.getElementById("bm-overhang").value = model.overhang || 5;
    document.getElementById("bm-pallet-face").value = model.pallet_face || "xy";
    document.getElementById("bm-interlocking").value = model.interlocking_type || "mirror";
    document.getElementById("bm-notes").value = model.notes || "";
    toggleBmFields();
}

function clearBoxModelForm() {
    document.getElementById("bm-id").value = "";
    document.getElementById("bm-name").value = "";
    document.getElementById("bm-code").value = "";
    document.getElementById("bm-type").value = "regular";
    document.getElementById("bm-sizex").value = "";
    document.getElementById("bm-sizey").value = "";
    document.getElementById("bm-sizez").value = "";
    document.getElementById("bm-weight").value = "";
    document.getElementById("bm-strength").value = "10";
    document.getElementById("bm-comp-total").value = "";
    document.getElementById("bm-largura").value = "";
    document.getElementById("bm-alt-vertical").value = "";
    document.getElementById("bm-alt-perp").value = "";
    document.getElementById("bm-comp-braco").value = "";
    document.getElementById("bm-notes").value = "";
    toggleBmFields();
}

async function saveBoxModel() {
    const id = document.getElementById("bm-id").value;
    const data = {
        name: document.getElementById("bm-name").value,
        code: document.getElementById("bm-code").value,
        type: document.getElementById("bm-type").value,
        sizex: parseFloat(document.getElementById("bm-sizex").value) || null,
        sizey: parseFloat(document.getElementById("bm-sizey").value) || null,
        sizez: parseFloat(document.getElementById("bm-sizez").value) || null,
        weight: parseFloat(document.getElementById("bm-weight").value) || 0,
        strength: parseInt(document.getElementById("bm-strength").value) || 10,
        quantity: parseInt(document.getElementById("bm-quantity").value) || 10,
        comp_total: parseFloat(document.getElementById("bm-comp-total").value) || null,
        largura: parseFloat(document.getElementById("bm-largura").value) || null,
        alt_vertical: parseFloat(document.getElementById("bm-alt-vertical").value) || null,
        alt_perpendicular: parseFloat(document.getElementById("bm-alt-perp").value) || null,
        comp_braco: parseFloat(document.getElementById("bm-comp-braco").value) || null,
        l_orientation: document.getElementById("bm-l-orientation").value || "vertical",
        pallet_sizex: parseFloat(document.getElementById("bm-pallet-sizex").value) || 100,
        pallet_sizey: parseFloat(document.getElementById("bm-pallet-sizey").value) || 120,
        pallet_sizez: parseFloat(document.getElementById("bm-pallet-sizez").value) || 200,
        pallet_max_weight: parseFloat(document.getElementById("bm-pallet-weight").value) || 1200,
        overhang: parseFloat(document.getElementById("bm-overhang").value) || 5,
        pallet_face: document.getElementById("bm-pallet-face").value || "xy",
        interlocking_type: document.getElementById("bm-interlocking").value || "mirror",
        notes: document.getElementById("bm-notes").value,
    };

    if (!data.name) { alert("Nome é obrigatório."); return; }

    try {
        const url = id ? `/api/boxes/${id}` : "/api/boxes";
        const method = id ? "PUT" : "POST";
        const response = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
        const result = await response.json();
        if (result.success) {
            await fetchBoxModels();
            hideBoxModelForm();
        } else {
            alert(result.error || "Erro ao salvar.");
        }
    } catch (err) {
        alert("Erro ao salvar modelo.");
        console.error(err);
    }
}

async function deleteBoxModel() {
    const id = document.getElementById("bm-id").value;
    if (!id) return;
    if (!confirm("Excluir este modelo permanentemente?")) return;

    try {
        await fetch(`/api/boxes/${id}`, { method: "DELETE" });
        await fetchBoxModels();
        hideBoxModelForm();
    } catch (err) {
        alert("Erro ao excluir.");
    }
}
