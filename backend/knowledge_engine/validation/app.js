let DATA = null;

async function loadData() {
  const response = await fetch("./data/phase_13_1.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load validation data (${response.status})`);
  }
  return response.json();
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function chipRow(values, limit = 4) {
  const wrap = el("div", "chip-row");
  const items = values || [];
  if (!items.length) {
    wrap.appendChild(el("span", "chip", "—"));
    return wrap;
  }
  for (const value of items.slice(0, limit)) {
    wrap.appendChild(el("span", "chip", String(value)));
  }
  if (items.length > limit) {
    wrap.appendChild(el("span", "chip", `+${items.length - limit}`));
  }
  return wrap;
}

function capabilityLabel(value) {
  const map = {
    supported: "✅ Supported",
    missing: "❌ Missing",
    reserved: "Reserved",
    not_applicable: "N/A",
  };
  return map[value] || value || "—";
}

function renderStats(stats) {
  const grid = document.getElementById("stats-grid");
  grid.innerHTML = "";
  const items = [
    ["Documents processed", stats.documents_processed],
    ["Knowledge Objects", stats.knowledge_objects_generated],
    ["Success", stats.success_count],
    ["Partial", stats.partial_count],
    ["Failures", stats.failure_count],
    ["Avg confidence*", Number(stats.avg_confidence || 0).toFixed(2)],
    ["Avg time (ms)", Number(stats.avg_processing_time_ms || 0).toFixed(1)],
  ];
  for (const [label, value] of items) {
    const card = el("div", "stat-card");
    card.appendChild(el("div", "label", label));
    card.appendChild(el("div", "value", String(value ?? 0)));
    grid.appendChild(card);
  }
}

function renderDecisionQuestions(questions) {
  const list = document.getElementById("decision-questions");
  list.innerHTML = "";
  for (const question of questions || []) {
    list.appendChild(el("li", null, question));
  }
}

function renderRoadmap(roadmap) {
  const root = document.getElementById("roadmap");
  root.innerHTML = "";
  for (const item of roadmap || []) {
    const active = ["validation", "in_progress"].includes(item.status);
    const card = el("div", `roadmap-card${active ? " active" : ""}`);
    card.appendChild(el("div", "id", item.id));
    card.appendChild(el("div", "name", item.name));
    card.appendChild(
      el("span", `status ${item.status}`, String(item.status || "not_started").replaceAll("_", " ")),
    );
    if (item.note) card.appendChild(el("p", "hint", item.note));
    root.appendChild(card);
  }
}

function formatChecklistDetails(detailKey, details) {
  const fragment = document.createDocumentFragment();
  const payload = details?.[detailKey];
  if (!payload) {
    fragment.appendChild(el("div", "detail-block", "No detail payload for this check."));
    return fragment;
  }

  if (Array.isArray(payload) && typeof payload[0] === "string") {
    for (const line of payload) {
      fragment.appendChild(el("div", "detail-block", line));
    }
    return fragment;
  }

  for (const entry of payload.slice(0, 12)) {
    const block = el("div", "detail-block");
    const title = el("strong", null, entry.filename || "Item");
    block.appendChild(title);

    if (entry.short || entry.detailed) {
      block.appendChild(el("div", null, `Short: ${entry.short || "—"}`));
      if (entry.detailed) block.appendChild(el("div", null, `Detailed: ${entry.detailed}`));
    } else if (entry.document_type) {
      block.appendChild(el("div", null, `Type: ${entry.document_type}`));
    } else if (entry.departments) {
      block.appendChild(el("div", null, `Departments: ${(entry.departments || []).join(", ")}`));
    } else if (entry.keywords) {
      block.appendChild(el("div", null, `Keywords: ${(entry.keywords || []).slice(0, 10).join(", ")}`));
    } else if (entry.tags) {
      block.appendChild(el("div", null, `Tags: ${(entry.tags || []).join(", ")}`));
    } else if (entry.samples || entry.entities) {
      block.appendChild(el("div", null, `Samples: ${(entry.samples || []).join(", ") || "—"}`));
      if (entry.counts) {
        block.appendChild(el("div", null, `Counts: ${JSON.stringify(entry.counts)}`));
      }
    } else if (entry.metadata) {
      block.appendChild(el("div", null, JSON.stringify(entry.metadata)));
    } else if (entry.pipeline_version) {
      block.appendChild(
        el(
          "div",
          null,
          `${entry.model_used} · v${entry.pipeline_version} · ${entry.processing_time_ms} ms · ${entry.status}`,
        ),
      );
    } else {
      block.appendChild(el("div", null, JSON.stringify(entry)));
    }
    fragment.appendChild(block);
  }

  if (Array.isArray(payload) && payload.length > 12) {
    fragment.appendChild(el("div", "hint", `Showing 12 of ${payload.length} documents.`));
  }
  return fragment;
}

function renderChecklist(checklist, details) {
  const list = document.getElementById("checklist");
  list.innerHTML = "";
  for (const item of checklist || []) {
    const li = el("li");
    const button = el("button", "checklist-item");
    button.type = "button";
    button.setAttribute("aria-expanded", "false");
    button.appendChild(el("span", `check ${item.passed ? "ok" : "bad"}`, item.passed ? "✓" : "✗"));
    const body = el("div");
    body.appendChild(el("div", null, item.label));
    body.appendChild(el("div", "hint", item.expandable ? "Click to expand details" : ""));
    button.appendChild(body);

    const detail = el("div", "checklist-details");
    detail.appendChild(formatChecklistDetails(item.detail_key || item.id, details));

    button.addEventListener("click", () => {
      const open = button.getAttribute("aria-expanded") === "true";
      button.setAttribute("aria-expanded", open ? "false" : "true");
    });

    li.appendChild(button);
    li.appendChild(detail);
    list.appendChild(li);
  }
}

function renderApprovalGate(gate) {
  const list = document.getElementById("approval-gate");
  const note = document.getElementById("approval-note");
  const banner = document.getElementById("approval-banner");
  list.innerHTML = "";
  note.textContent = gate?.note || "";

  for (const item of gate?.items || []) {
    const li = el("li");
    const label = el("span", null, item.label);
    if (item.note) {
      label.appendChild(el("div", "hint", item.note));
    }
    li.appendChild(label);
    li.appendChild(el("span", `status ${item.status}`, String(item.status).replaceAll("_", " ")));
    list.appendChild(li);
  }

  if (gate?.officially_approved) {
    banner.className = "approval-banner ready";
    banner.textContent = "Phase 13.1 is officially approved.";
  } else if (gate?.ready_for_final_approval) {
    banner.className = "approval-banner ready";
    banner.textContent = "Auto-checks passed. Manual review + Final Approval still required before 13.2.";
  } else {
    banner.className = "approval-banner blocked";
    banner.textContent = "Not ready for final approval — resolve failing auto-checks first.";
  }
}

function renderCapabilityComparison(rows, notes) {
  const body = document.getElementById("capability-body");
  const notesList = document.getElementById("compare-notes");
  body.innerHTML = "";
  notesList.innerHTML = "";

  for (const row of rows || []) {
    const tr = el("tr");
    tr.appendChild(el("td", null, row.feature));
    const legacy = el("td");
    legacy.appendChild(el("span", `cap ${row.legacy}`, capabilityLabel(row.legacy)));
    tr.appendChild(legacy);
    const kie = el("td");
    kie.appendChild(el("span", `cap ${row.knowledge_engine}`, capabilityLabel(row.knowledge_engine)));
    tr.appendChild(kie);
    body.appendChild(tr);
  }

  for (const note of notes || []) {
    notesList.appendChild(el("li", null, note));
  }
}

function renderConfidence(explanation, stats) {
  const root = document.getElementById("confidence-panel");
  root.innerHTML = "";
  const box = el("div", "confidence-box");

  const card = el("div", "confidence-card");
  card.appendChild(el("div", "label", "Average confidence"));
  card.appendChild(el("div", "value", Number(stats?.avg_confidence || 0).toFixed(3)));
  card.appendChild(el("div", "warn-label", explanation?.label || "Heuristic estimate"));
  card.appendChild(el("p", "hint", explanation?.disclaimer || ""));
  card.appendChild(el("p", "hint", `Method: ${explanation?.model_or_heuristic || "heuristic"}`));
  card.appendChild(el("p", "hint", explanation?.how_calculated || ""));

  const fields = el("dl", "field-list");
  fields.appendChild(el("dt", null, "How each field is scored"));
  for (const [key, value] of Object.entries(explanation?.fields || {})) {
    fields.appendChild(el("dt", null, key));
    fields.appendChild(el("dd", null, value));
  }

  box.appendChild(card);
  box.appendChild(fields);
  root.appendChild(box);
}

function renderDocuments(documents) {
  const body = document.getElementById("documents-body");
  body.innerHTML = "";
  if (!documents?.length) {
    const row = el("tr");
    const cell = el("td", "empty", "No validation data yet. Run the Phase 13.1 validation script.");
    cell.colSpan = 9;
    row.appendChild(cell);
    body.appendChild(row);
    return;
  }

  documents.forEach((doc, index) => {
    const row = el("tr", "doc-row");
    row.tabIndex = 0;
    row.title = "Open Knowledge Object Inspector";
    row.appendChild(el("td", null, doc.filename || doc.document_id || "—"));
    row.appendChild(el("td", null, doc.document_type || "Unknown"));

    const deptCell = el("td");
    deptCell.appendChild(chipRow(doc.departments));
    row.appendChild(deptCell);

    const confCell = el("td", "confidence-cell");
    confCell.appendChild(document.createTextNode(Number(doc.confidence ?? 0).toFixed(2)));
    confCell.appendChild(el("span", "kind", "heuristic"));
    row.appendChild(confCell);

    row.appendChild(el("td", null, (doc.short_summary || "").slice(0, 110)));

    const entityCell = el("td");
    entityCell.appendChild(chipRow(doc.entity_samples || []));
    row.appendChild(entityCell);

    const topicCell = el("td");
    topicCell.appendChild(chipRow(doc.topics || []));
    row.appendChild(topicCell);

    row.appendChild(el("td", null, Number(doc.processing_time_ms ?? 0).toFixed(1)));

    const statusCell = el("td");
    statusCell.appendChild(el("span", `badge ${doc.status || "partial"}`, doc.status || "partial"));
    row.appendChild(statusCell);

    const open = () => openInspector(doc);
    row.addEventListener("click", open);
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        open();
      }
    });

    body.appendChild(row);
  });
}

function renderHistory(history) {
  const body = document.getElementById("history-body");
  body.innerHTML = "";
  if (!history?.length) {
    const row = el("tr");
    const cell = el("td", "empty", "No previous runs yet.");
    cell.colSpan = 7;
    row.appendChild(cell);
    body.appendChild(row);
    return;
  }

  history.forEach((run, index) => {
    const row = el("tr", index === 0 ? "history-current" : "");
    row.appendChild(el("td", null, run.run_date || "—"));
    row.appendChild(el("td", null, String(run.documents_processed ?? 0)));
    row.appendChild(el("td", null, String(run.success ?? 0)));
    row.appendChild(el("td", null, String(run.failures ?? 0)));
    row.appendChild(el("td", null, Number(run.average_confidence ?? 0).toFixed(3)));
    row.appendChild(el("td", null, Number(run.average_processing_time_ms ?? 0).toFixed(1)));
    row.appendChild(
      el(
        "td",
        null,
        run.checklist_passed ? "PASS" : "FAIL",
      ),
    );
    body.appendChild(row);
  });
}

function renderIssues(targetId, issues) {
  const list = document.getElementById(targetId);
  list.innerHTML = "";
  if (!issues?.length) {
    list.appendChild(el("li", null, "None recorded."));
    return;
  }
  for (const issue of issues) {
    const li = el("li");
    const body = el("div");
    const heading = issue.resolved_in
      ? `${issue.id} · resolved in ${issue.resolved_in}`
      : `${issue.id} · ${issue.severity || "low"}`;
    body.appendChild(el("div", `severity ${issue.severity || "low"}`, heading));
    body.appendChild(el("div", null, issue.summary || ""));
    if (issue.mitigation) body.appendChild(el("div", "hint", `Mitigation: ${issue.mitigation}`));
    if (issue.resolution) body.appendChild(el("div", "hint", `Resolution: ${issue.resolution}`));
    li.appendChild(body);
    list.appendChild(li);
  }
}

function section(title, contentNode) {
  const wrap = el("div", "inspector-section");
  wrap.appendChild(el("h3", null, title));
  wrap.appendChild(contentNode);
  return wrap;
}

function openInspector(doc) {
  const drawer = document.getElementById("inspector");
  const backdrop = document.getElementById("drawer-backdrop");
  const body = document.getElementById("inspector-body");
  const title = document.getElementById("inspector-title");
  const ko = doc.knowledge_object || {};
  const entities = ko.entities || {};

  title.textContent = doc.filename || "Document";
  body.innerHTML = "";

  body.appendChild(section("Document name", el("p", null, doc.filename || "—")));
  body.appendChild(section("Document type", el("p", null, doc.document_type || "—")));
  body.appendChild(section("Department(s)", chipRow(doc.departments || [], 12)));
  body.appendChild(
    section(
      "Summary",
      el(
        "p",
        null,
        `Short:\n${doc.short_summary || "—"}\n\nDetailed:\n${doc.detailed_summary || "—"}`,
      ),
    ),
  );
  body.appendChild(section("Topics", chipRow(doc.topics || [], 20)));
  body.appendChild(section("Keywords", chipRow(doc.keywords || [], 20)));

  const entityWrap = el("div");
  for (const [key, values] of Object.entries(entities)) {
    if (!Array.isArray(values) || !values.length) continue;
    entityWrap.appendChild(el("div", "hint", key));
    entityWrap.appendChild(chipRow(values, 20));
  }
  if (!entityWrap.childNodes.length) entityWrap.appendChild(el("p", null, "No entities extracted."));
  body.appendChild(section("Entities", entityWrap));

  body.appendChild(section("Tags", chipRow(doc.tags || [], 20)));
  body.appendChild(section("Language", el("p", null, doc.language || ko.language || "—")));

  const conf = el("div");
  conf.appendChild(el("p", null, `Overall (heuristic estimate): ${Number(doc.confidence ?? 0).toFixed(3)}`));
  conf.appendChild(el("p", "hint", "Not calibrated model confidence."));
  if (doc.confidence_breakdown) {
    conf.appendChild(el("pre", null, JSON.stringify(doc.confidence_breakdown, null, 2)));
  }
  body.appendChild(section("Confidence", conf));

  const processing = el("div");
  processing.appendChild(
    el(
      "p",
      null,
      `Model/heuristic: ${doc.model_used}\nPipeline: ${doc.pipeline_version}\nTime: ${doc.processing_time_ms} ms\nStatus: ${doc.status}`,
    ),
  );
  body.appendChild(section("Processing metadata", processing));

  body.appendChild(
    section(
      "Warnings",
      el("p", null, (doc.warnings || []).length ? doc.warnings.join("\n") : "None"),
    ),
  );
  body.appendChild(
    section(
      "Errors",
      el("p", null, (doc.errors || []).length ? doc.errors.join("\n") : "None"),
    ),
  );

  const timeline = el("ul", "timeline");
  for (const step of doc.processing_timeline || []) {
    const li = el("li");
    li.appendChild(el("div", "step", step.step));
    li.appendChild(el("div", "meta", `${step.at || "—"} · ${step.status || ""}`));
    if (step.note) li.appendChild(el("div", "hint", step.note));
    timeline.appendChild(li);
  }
  body.appendChild(section("Processing timeline", timeline));

  body.appendChild(
    section("Raw Knowledge Object", el("pre", null, JSON.stringify(ko, null, 2))),
  );

  drawer.hidden = false;
  backdrop.hidden = false;
  drawer.setAttribute("aria-hidden", "false");
}

function closeInspector() {
  const drawer = document.getElementById("inspector");
  const backdrop = document.getElementById("drawer-backdrop");
  drawer.hidden = true;
  backdrop.hidden = true;
  drawer.setAttribute("aria-hidden", "true");
}

function renderRegistry(registry) {
  const statsRoot = document.getElementById("registry-stats");
  if (!statsRoot) return;
  statsRoot.innerHTML = "";
  if (!registry) {
    statsRoot.appendChild(el("div", "hint", "No registry payload — re-run the validation script."));
    return;
  }
  const stats = registry.statistics || {};
  const cards = [
    ["Registered", stats.registered_count],
    ["Collections", Object.keys(stats.collection_counts || {}).length],
    ["Taxonomy paths", (stats.taxonomy_paths || []).length],
    ["Version groups", stats.version_groups],
    ["Duplicate candidates", stats.duplicate_candidates],
    ["Alias rules", stats.alias_count],
    ["Collection coverage", `${Math.round((stats.coverage_with_collection || 0) * 100)}%`],
    ["Category coverage", `${Math.round((stats.coverage_with_category || 0) * 100)}%`],
  ];
  for (const [label, value] of cards) {
    const card = el("div", "stat-card");
    card.appendChild(el("div", "label", label));
    card.appendChild(el("div", "value", String(value ?? 0)));
    statsRoot.appendChild(card);
  }

  const checklist = document.getElementById("registry-checklist");
  checklist.innerHTML = "";
  for (const item of registry.checklist || []) {
    const li = el("li");
    const row = el("div", "checklist-item");
    row.appendChild(el("span", `check ${item.passed ? "ok" : "bad"}`, item.passed ? "✓" : "✗"));
    row.appendChild(el("div", null, item.label));
    li.appendChild(row);
    checklist.appendChild(li);
  }

  const collections = document.getElementById("registry-collections");
  collections.innerHTML = "";
  for (const item of registry.collections || []) {
    collections.appendChild(el("span", "chip", `${item.slug}: ${item.count}`));
  }

  const health = document.getElementById("registry-health");
  health.innerHTML = "";
  for (const [name, count] of Object.entries(registry.health || {})) {
    health.appendChild(el("span", "chip", `${name}: ${count}`));
  }

  const coverage = document.getElementById("registry-coverage");
  coverage.innerHTML = "";
  coverage.appendChild(
    el("li", null, `With collection: ${Math.round((registry.coverage?.with_collection || 0) * 100)}%`),
  );
  coverage.appendChild(
    el("li", null, `With category/taxonomy: ${Math.round((registry.coverage?.with_category || 0) * 100)}%`),
  );

  const taxonomy = document.getElementById("registry-taxonomy");
  taxonomy.innerHTML = "";
  for (const path of (registry.taxonomy || []).slice(0, 24)) {
    taxonomy.appendChild(el("li", null, path));
  }

  const aliases = document.getElementById("registry-aliases");
  aliases.innerHTML = "";
  for (const item of (registry.aliases || []).slice(0, 12)) {
    aliases.appendChild(
      el("li", null, `${item.canonical} ← ${(item.aliases || []).slice(0, 4).join(", ")}`),
    );
  }

  const versions = document.getElementById("registry-versions");
  versions.innerHTML = "";
  for (const group of (registry.version_groups || []).slice(0, 16)) {
    versions.appendChild(el("li", null, group));
  }
  if (!(registry.version_groups || []).length) {
    versions.appendChild(el("li", null, "None detected in this run."));
  }

  const duplicates = document.getElementById("registry-duplicates");
  duplicates.innerHTML = "";
  for (const item of (registry.duplicates || []).slice(0, 16)) {
    duplicates.appendChild(
      el("li", null, `${item.filename} → ${item.duplicate_of} (${item.score})`),
    );
  }
  if (!(registry.duplicates || []).length) {
    duplicates.appendChild(el("li", null, "None detected in this run."));
  }

  const missing = document.getElementById("registry-missing-collections");
  missing.innerHTML = "";
  const missingItems = registry.missing_collections || [];
  if (!missingItems.length) missing.appendChild(el("li", null, "None — full collection coverage."));
  for (const name of missingItems) missing.appendChild(el("li", null, name));

  const review = document.getElementById("registry-manual-review");
  review.innerHTML = "";
  const reviewItems = registry.manual_review || [];
  if (!reviewItems.length) review.appendChild(el("li", null, "None flagged."));
  for (const name of reviewItems) review.appendChild(el("li", null, name));

  const body = document.getElementById("registry-entries-body");
  body.innerHTML = "";
  for (const entry of registry.entries || []) {
    const row = el("tr");
    row.appendChild(el("td", null, entry.filename || "—"));
    row.appendChild(el("td", null, (entry.knowledge_id || "").slice(0, 8) + "…"));
    row.appendChild(el("td", null, entry.primary_collection || "—"));
    row.appendChild(el("td", null, entry.taxonomy_path || "—"));
    row.appendChild(el("td", null, entry.version_label || "—"));
    row.appendChild(el("td", null, entry.health || "—"));
    row.appendChild(el("td", null, entry.needs_manual_review ? "Yes" : "No"));
    body.appendChild(row);
  }
}

function filenameForKnowledgeId(knowledgeId, registry) {
  const entries = registry?.entries || [];
  const match = entries.find((entry) => entry.knowledge_id === knowledgeId);
  return match?.filename || (knowledgeId || "").slice(0, 8) + "…";
}

function renderRelationships(relationships, registry) {
  const statsRoot = document.getElementById("relationship-stats");
  if (!statsRoot) return;
  statsRoot.innerHTML = "";
  if (!relationships) {
    statsRoot.appendChild(el("div", "hint", "No relationships payload — re-run the validation script."));
    return;
  }

  document.getElementById("relationship-confidence-note").textContent =
    relationships.confidence_note ||
    "Confidence values are heuristic estimates, not calibrated AI confidence.";

  const stats = relationships.statistics || {};
  const cards = [
    ["Relationships", stats.relationship_count],
    ["Docs with edges", stats.documents_with_relationships],
    ["Coverage", `${Math.round((stats.coverage || 0) * 100)}%`],
    ["Avg confidence*", Number(stats.avg_confidence || 0).toFixed(2)],
    ["Edge types", Object.keys(stats.type_counts || {}).length],
  ];
  for (const [label, value] of cards) {
    const card = el("div", "stat-card");
    card.appendChild(el("div", "label", label));
    card.appendChild(el("div", "value", String(value ?? 0)));
    statsRoot.appendChild(card);
  }

  const checklist = document.getElementById("relationship-checklist");
  checklist.innerHTML = "";
  for (const item of relationships.checklist || []) {
    const li = el("li");
    const row = el("div", "checklist-item");
    row.appendChild(el("span", `check ${item.passed ? "ok" : "bad"}`, item.passed ? "✓" : "✗"));
    row.appendChild(el("div", null, item.label));
    li.appendChild(row);
    checklist.appendChild(li);
  }

  const types = document.getElementById("relationship-types");
  types.innerHTML = "";
  for (const item of relationships.types || []) {
    types.appendChild(el("span", "chip", `${item.type}: ${item.count}`));
  }

  const confidence = document.getElementById("relationship-confidence");
  confidence.innerHTML = "";
  for (const [bucket, count] of Object.entries(stats.confidence_buckets || {})) {
    confidence.appendChild(el("span", "chip", `${bucket}: ${count}`));
  }

  const coverage = document.getElementById("relationship-coverage");
  coverage.innerHTML = "";
  coverage.appendChild(el("li", null, `Coverage: ${Math.round((stats.coverage || 0) * 100)}%`));
  coverage.appendChild(el("li", null, `With relationships: ${stats.documents_with_relationships || 0}`));
  coverage.appendChild(
    el("li", null, `Without relationships: ${(stats.documents_without_relationships || []).length}`),
  );

  const top = document.getElementById("relationship-top");
  top.innerHTML = "";
  for (const item of relationships.top_connected || []) {
    top.appendChild(el("li", null, `${item.filename} · degree ${item.degree}`));
  }

  const without = document.getElementById("relationship-without");
  without.innerHTML = "";
  const missing = relationships.without_relationships || [];
  if (!missing.length) without.appendChild(el("li", null, "None — all documents have at least one edge."));
  for (const name of missing.slice(0, 20)) without.appendChild(el("li", null, name));

  const body = document.getElementById("relationship-edges-body");
  body.innerHTML = "";
  for (const edge of (relationships.edges || []).slice(0, 120)) {
    const row = el("tr", "doc-row");
    row.appendChild(el("td", null, filenameForKnowledgeId(edge.source_knowledge_id, registry)));
    row.appendChild(el("td", null, edge.relationship_type));
    row.appendChild(el("td", null, filenameForKnowledgeId(edge.target_knowledge_id, registry)));
    const conf = el("td", "confidence-cell");
    conf.appendChild(document.createTextNode(Number(edge.confidence || 0).toFixed(2)));
    conf.appendChild(el("span", "kind", edge.confidence_kind || "heuristic"));
    row.appendChild(conf);
    row.appendChild(el("td", null, edge.evidence_source || "—"));
    const evidenceText = (edge.evidence || []).map((item) => item.evidence).join(" · ");
    row.appendChild(el("td", null, evidenceText.slice(0, 140) || "—"));
    row.title = "Relationship inspector details in Evidence column / JSON payload";
    body.appendChild(row);
  }
}

function renderHybridIndex(hybrid) {
  const summaryRoot = document.getElementById("hybrid-index-summary");
  if (!summaryRoot) return;
  summaryRoot.innerHTML = "";
  if (!hybrid) {
    summaryRoot.appendChild(el("div", "hint", "No hybrid index payload — re-run the validation script."));
    return;
  }

  const summary = hybrid.summary || {};
  for (const [label, value] of [
    ["Total indexes", summary.total_indexes],
    ["Documents indexed", summary.documents_indexed],
    ["Coverage", summary.coverage],
    ["Build time (ms)", summary.build_time_ms],
    ["Memory est. (bytes)", summary.memory_bytes_estimate],
    ["Index version", summary.index_version],
  ]) {
    const card = el("div", "stat-card");
    card.appendChild(el("div", "label", label));
    card.appendChild(el("div", "value", value == null ? "—" : String(value)));
    summaryRoot.appendChild(card);
  }

  const checklist = document.getElementById("hybrid-index-checklist");
  checklist.innerHTML = "";
  for (const item of hybrid.checklist || []) {
    const li = el("li");
    const row = el("div", "checklist-item");
    row.appendChild(el("span", `check ${item.passed ? "ok" : "bad"}`, item.passed ? "✓" : "✗"));
    row.appendChild(el("div", null, item.label));
    li.appendChild(row);
    checklist.appendChild(li);
  }

  const performance = document.getElementById("hybrid-index-performance");
  performance.innerHTML = "";
  const perf = hybrid.performance || {};
  for (const [label, value] of [
    ["Build time (ms)", perf.build_time_ms],
    ["Average lookup (ms)", perf.average_lookup_ms],
    ["Documents/sec", perf.documents_per_sec],
    ["Memory estimate", perf.memory_bytes_estimate],
    ["Index size (bytes)", perf.index_size_bytes],
  ]) {
    performance.appendChild(el("li", null, `${label}: ${value == null ? "—" : value}`));
  }

  const coverage = document.getElementById("hybrid-index-coverage");
  coverage.innerHTML = "";
  const health = hybrid.coverage || {};
  coverage.appendChild(el("li", null, `Health: ${health.status || "—"}`));
  coverage.appendChild(el("li", null, `Documents indexed: ${health.documents_indexed || 0}`));
  coverage.appendChild(
    el("li", null, `Missing indexes: ${(health.missing_indexes || []).join(", ") || "none"}`),
  );
  coverage.appendChild(
    el("li", null, `Missing metadata: ${(health.missing_metadata || []).length}`),
  );
  coverage.appendChild(
    el("li", null, `Unindexed entities: ${(health.unindexed_entities || []).length}`),
  );

  const statsBody = document.getElementById("hybrid-index-stats-body");
  statsBody.innerHTML = "";
  const perIndex = hybrid.per_index || {};
  for (const name of [
    "metadata",
    "collection",
    "department",
    "taxonomy",
    "relationship",
    "entity",
    "keyword",
    "topic",
    "tag",
    "version",
  ]) {
    const stats = perIndex[name] || {};
    const row = el("tr");
    row.appendChild(el("td", null, name));
    row.appendChild(el("td", null, String(stats.key_count ?? "—")));
    row.appendChild(el("td", null, String(stats.document_count ?? "—")));
    row.appendChild(el("td", null, String(stats.entry_count ?? "—")));
    row.appendChild(el("td", null, String(stats.memory_bytes_estimate ?? "—")));
    statsBody.appendChild(row);
  }

  const explorerSelect = document.getElementById("hybrid-index-doc-select");
  const explorerOut = document.getElementById("hybrid-index-explorer");
  const explorerItems = hybrid.explorer || [];
  explorerSelect.innerHTML = "";
  explorerOut.textContent = "Select a document to inspect index references.";
  for (const item of explorerItems) {
    const doc = item.document || {};
    const option = document.createElement("option");
    option.value = doc.document_id || "";
    option.textContent = `${doc.filename || doc.document_id || "document"}`;
    explorerSelect.appendChild(option);
  }
  function showExplorer(documentId) {
    const item = explorerItems.find((entry) => entry.document?.document_id === documentId);
    explorerOut.textContent = item
      ? JSON.stringify(item, null, 2)
      : "No index data for this document.";
  }
  if (explorerItems.length) {
    showExplorer(explorerItems[0].document?.document_id);
  }
  explorerSelect.onchange = () => showExplorer(explorerSelect.value);

  const lookups = document.getElementById("hybrid-index-lookups");
  lookups.innerHTML = "";
  for (const lookup of hybrid.sample_lookups || []) {
    const elapsed =
      typeof lookup.elapsed_ms === "number" ? lookup.elapsed_ms.toFixed(3) : lookup.elapsed_ms;
    lookups.appendChild(
      el(
        "li",
        null,
        `${lookup.index_name}: query=${JSON.stringify(lookup.query)} → ${
          (lookup.document_ids || []).length
        } docs (${elapsed} ms)`,
      ),
    );
  }
}

function renderQueryPlanner(planner) {
  const summaryRoot = document.getElementById("query-planner-summary");
  if (!summaryRoot) return;
  summaryRoot.innerHTML = "";
  if (!planner) {
    summaryRoot.appendChild(
      el("div", "hint", "No query planner payload — re-run the validation script."),
    );
    return;
  }

  const summary = planner.summary || {};
  for (const [label, value] of [
    ["Queries analyzed", summary.queries_analyzed],
    ["Avg planning (ms)", summary.average_planning_time_ms],
    ["Unknown queries", summary.unknown_queries],
    ["Planner version", summary.planner_version],
  ]) {
    const card = el("div", "stat-card");
    card.appendChild(el("div", "label", label));
    card.appendChild(el("div", "value", value == null ? "—" : String(value)));
    summaryRoot.appendChild(card);
  }

  const checklist = document.getElementById("query-planner-checklist");
  checklist.innerHTML = "";
  for (const item of planner.checklist || []) {
    const li = el("li");
    const row = el("div", "checklist-item");
    row.appendChild(el("span", `check ${item.passed ? "ok" : "bad"}`, item.passed ? "✓" : "✗"));
    row.appendChild(el("div", null, item.label));
    li.appendChild(row);
    checklist.appendChild(li);
  }

  const metrics = document.getElementById("query-planner-metrics");
  metrics.innerHTML = "";
  const perf = planner.metrics || {};
  for (const [label, value] of [
    ["Average planning latency", perf.average_planning_latency_ms],
    ["Classification latency", perf.classification_latency_ms],
    ["Strategy latency", perf.strategy_latency_ms],
    ["Validation latency", perf.validation_latency_ms],
  ]) {
    metrics.appendChild(el("li", null, `${label}: ${value == null ? "—" : value} ms`));
  }

  const diagnostics = document.getElementById("query-planner-diagnostics");
  diagnostics.innerHTML = "";
  const diag = planner.diagnostics || {};
  diagnostics.appendChild(
    el("li", null, `Intent confusion: ${(diag.intent_confusion || []).join(", ") || "none"}`),
  );
  diagnostics.appendChild(
    el("li", null, `Missing indexes: ${(diag.missing_indexes || []).join(", ") || "none"}`),
  );
  diagnostics.appendChild(
    el(
      "li",
      null,
      `Unsupported constraints: ${(diag.unsupported_constraints || []).join(", ") || "none"}`,
    ),
  );
  diagnostics.appendChild(
    el("li", null, `Planning failures: ${(diag.planning_failures || []).join(", ") || "none"}`),
  );
  diagnostics.appendChild(
    el("li", null, `Unknown queries: ${(diag.unknown_queries || []).join(", ") || "none"}`),
  );

  const intents = document.getElementById("query-planner-intents");
  intents.innerHTML = "";
  for (const [intent, count] of Object.entries(summary.intent_distribution || {})) {
    intents.appendChild(el("span", "chip", `${intent}: ${count}`));
  }

  const strategies = document.getElementById("query-planner-strategies");
  strategies.innerHTML = "";
  for (const [strategy, count] of Object.entries(summary.strategy_distribution || {})) {
    strategies.appendChild(el("span", "chip", `${strategy}: ${count}`));
  }

  document.getElementById("query-planner-note").textContent =
    planner.note ||
    "Interactive Planner uses precomputed Shadow Mode plans (no production retrieval).";

  const select = document.getElementById("query-planner-select");
  const input = document.getElementById("query-planner-input");
  const output = document.getElementById("query-planner-output");
  const plansByQuery = planner.plans_by_query || {};
  const samples = planner.sample_queries || Object.keys(plansByQuery);
  select.innerHTML = "";
  for (const query of samples) {
    const option = document.createElement("option");
    option.value = query;
    option.textContent = query;
    select.appendChild(option);
  }

  function showPlan(query) {
    const plan = plansByQuery[query];
    if (!plan) {
      output.textContent =
        `No precomputed plan for "${query}". Choose a sample query or re-run validation after adding it to SAMPLE_PLANNER_QUERIES.`;
      return;
    }
    const view = {
      normalized_query: plan.normalized_query,
      primary_intent: plan.primary_intent,
      confidence: plan.confidence,
      intents: plan.intents,
      entities: plan.entities,
      constraints: plan.constraints,
      required_indexes: plan.required_indexes,
      preferred_strategy: plan.preferred_strategy,
      fallback_strategy: plan.fallback_strategy,
      expected_output: plan.expected_output,
      warnings: plan.warnings,
      diagnostics: plan.diagnostics,
      filters: plan.filters,
      sort: plan.sort,
      planner_version: plan.planner_version,
    };
    output.textContent = JSON.stringify(view, null, 2);
  }

  if (samples.length) {
    input.value = samples[0];
    showPlan(samples[0]);
  }
  select.onchange = () => {
    input.value = select.value;
    showPlan(select.value);
  };
  document.getElementById("query-planner-run").onclick = () => {
    const query = (input.value || select.value || "").trim();
    showPlan(query);
  };
}

function renderKnowledgeExecution(execution) {
  const summaryRoot = document.getElementById("knowledge-execution-summary");
  if (!summaryRoot) return;
  summaryRoot.innerHTML = "";
  if (!execution) {
    summaryRoot.appendChild(
      el("div", "hint", "No knowledge execution payload — re-run the validation script."),
    );
    return;
  }

  const summary = execution.summary || {};
  for (const [label, value] of [
    ["Executions", summary.executions],
    ["Avg latency (ms)", summary.average_latency_ms],
    ["Providers executed", summary.providers_executed_total],
    ["Evidence collected", summary.evidence_collected_total],
    ["Candidates", summary.candidates_generated_total],
    ["Avg candidate score", summary.average_candidate_score],
    ["Failures", summary.failures_total],
  ]) {
    const card = el("div", "stat-card");
    card.appendChild(el("div", "label", label));
    card.appendChild(el("div", "value", value == null ? "—" : String(value)));
    summaryRoot.appendChild(card);
  }

  const checklist = document.getElementById("knowledge-execution-checklist");
  checklist.innerHTML = "";
  for (const item of execution.checklist || []) {
    const li = el("li");
    const row = el("div", "checklist-item");
    row.appendChild(el("span", `check ${item.passed ? "ok" : "bad"}`, item.passed ? "✓" : "✗"));
    row.appendChild(el("div", null, item.label));
    li.appendChild(row);
    checklist.appendChild(li);
  }

  const providersBody = document.getElementById("knowledge-execution-providers-body");
  providersBody.innerHTML = "";
  for (const [name, metrics] of Object.entries(execution.provider_metrics || {})) {
    const row = el("tr");
    row.appendChild(el("td", null, name));
    row.appendChild(el("td", null, String(metrics.success_rate ?? "—")));
    row.appendChild(el("td", null, String(metrics.failure_rate ?? "—")));
    row.appendChild(el("td", null, String(metrics.average_elapsed_ms ?? "—")));
    row.appendChild(el("td", null, String(metrics.average_evidence_count ?? "—")));
    providersBody.appendChild(row);
  }

  document.getElementById("knowledge-execution-note").textContent =
    execution.note ||
    "Execution Explorer uses precomputed Shadow Mode CandidateEvidenceSets.";

  const select = document.getElementById("knowledge-execution-select");
  const output = document.getElementById("knowledge-execution-output");
  const candidateSelect = document.getElementById("knowledge-execution-candidate-select");
  const candidateOut = document.getElementById("knowledge-execution-candidate");
  const byQuery = execution.executions_by_query || {};
  const samples = execution.sample_queries || Object.keys(byQuery);
  select.innerHTML = "";
  for (const query of samples) {
    const option = document.createElement("option");
    option.value = query;
    option.textContent = query;
    select.appendChild(option);
  }

  function showCandidate(candidate) {
    if (!candidate) {
      candidateOut.textContent = "No candidate selected.";
      return;
    }
    candidateOut.textContent = JSON.stringify(
      {
        document_id: candidate.document_id,
        knowledge_id: candidate.knowledge_id,
        rank: candidate.rank,
        score: candidate.score,
        confidence: candidate.confidence,
        supporting_indexes: candidate.supporting_indexes,
        score_contributions: candidate.score_contributions,
        explanation: candidate.explanation,
        metadata: candidate.metadata,
        evidence: candidate.evidence,
      },
      null,
      2,
    );
  }

  function showExecution(query) {
    const result = byQuery[query];
    if (!result) {
      output.textContent = `No precomputed execution for "${query}".`;
      candidateSelect.innerHTML = "";
      candidateOut.textContent = "";
      return;
    }
    output.textContent = JSON.stringify(
      {
        execution_id: result.execution_id,
        plan_id: result.plan_id,
        normalized_query: result.normalized_query,
        providers_selected: result.diagnostics?.providers_selected,
        provider_timeline_ms: result.diagnostics?.provider_timeline_ms,
        statistics: result.statistics,
        ranking: result.ranking,
        confidence: result.confidence,
        diagnostics: result.diagnostics,
        provider_results: (result.provider_results || []).map((item) => ({
          provider_name: item.provider_name,
          success: item.success,
          elapsed_ms: item.elapsed_ms,
          evidence_count: (item.evidence || []).length,
          error: item.error,
        })),
      },
      null,
      2,
    );
    candidateSelect.innerHTML = "";
    for (const candidate of result.candidates || []) {
      const option = document.createElement("option");
      option.value = candidate.document_id;
      option.textContent = `#${candidate.rank} ${candidate.metadata?.filename || candidate.document_id} (${candidate.score})`;
      candidateSelect.appendChild(option);
    }
    if ((result.candidates || []).length) {
      showCandidate(result.candidates[0]);
    } else {
      candidateOut.textContent = "No candidates for this execution.";
    }
    candidateSelect.onchange = () => {
      const candidate = (result.candidates || []).find(
        (item) => item.document_id === candidateSelect.value,
      );
      showCandidate(candidate);
    };
  }

  if (samples.length) showExecution(samples[0]);
  select.onchange = () => showExecution(select.value);
}

function renderKnowledgeGraph(graph) {
  const summaryRoot = document.getElementById("knowledge-graph-summary");
  if (!summaryRoot) return;
  summaryRoot.innerHTML = "";
  if (!graph) {
    summaryRoot.appendChild(
      el("div", "hint", "No knowledge graph payload — re-run the validation script."),
    );
    return;
  }

  const summary = graph.summary || {};
  for (const [label, value] of [
    ["Nodes", summary.nodes],
    ["Edges", summary.edges],
    ["Components", summary.connected_components],
    ["Avg degree", summary.average_degree],
    ["Coverage", summary.coverage],
    ["Graph version", summary.graph_version],
    ["Build time (ms)", summary.build_time_ms],
  ]) {
    const card = el("div", "stat-card");
    card.appendChild(el("div", "label", label));
    card.appendChild(el("div", "value", value == null ? "—" : String(value)));
    summaryRoot.appendChild(card);
  }

  const checklist = document.getElementById("knowledge-graph-checklist");
  checklist.innerHTML = "";
  for (const item of graph.checklist || []) {
    const li = el("li");
    const row = el("div", "checklist-item");
    row.appendChild(el("span", `check ${item.passed ? "ok" : "bad"}`, item.passed ? "✓" : "✗"));
    row.appendChild(el("div", null, item.label));
    li.appendChild(row);
    checklist.appendChild(li);
  }

  const diagnostics = document.getElementById("knowledge-graph-diagnostics");
  diagnostics.innerHTML = "";
  const diag = graph.diagnostics || {};
  const health = diag.health || {};
  diagnostics.appendChild(el("li", null, `Health: ${health.status || "—"}`));
  diagnostics.appendChild(el("li", null, `Orphans: ${health.orphan_count ?? (diag.orphan_nodes || []).length}`));
  diagnostics.appendChild(el("li", null, `Cycles detected: ${health.cycles_detected ?? 0}`));
  diagnostics.appendChild(
    el("li", null, `Low confidence edges: ${health.low_confidence_edges ?? (diag.low_confidence_edges || []).length}`),
  );
  diagnostics.appendChild(
    el("li", null, `Validation errors: ${(diag.validation_errors || []).join(", ") || "none"}`),
  );

  const nodeSelect = document.getElementById("knowledge-graph-node-select");
  const nodeOut = document.getElementById("knowledge-graph-node-output");
  const explorer = graph.explorer || [];
  nodeSelect.innerHTML = "";
  for (const item of explorer) {
    const option = document.createElement("option");
    option.value = item.node?.id || "";
    option.textContent = `${item.node?.label || item.node?.id} (${item.node?.type || ""})`;
    nodeSelect.appendChild(option);
  }
  function showNode(nodeId) {
    const item = explorer.find((entry) => entry.node?.id === nodeId);
    nodeOut.textContent = item ? JSON.stringify(item, null, 2) : "No node selected.";
  }
  if (explorer.length) showNode(explorer[0].node?.id);
  nodeSelect.onchange = () => showNode(nodeSelect.value);

  const travSelect = document.getElementById("knowledge-graph-traversal-select");
  const travOut = document.getElementById("knowledge-graph-traversal-output");
  const travSamples = graph.traversal_samples || [];
  travSelect.innerHTML = "";
  for (const sample of travSamples) {
    const option = document.createElement("option");
    option.value = sample.query;
    option.textContent = sample.query;
    travSelect.appendChild(option);
  }
  function showTraversal(query) {
    const sample = travSamples.find((item) => item.query === query);
    travOut.textContent = sample ? JSON.stringify(sample, null, 2) : "No traversal sample.";
  }
  if (travSamples.length) showTraversal(travSamples[0].query);
  travSelect.onchange = () => showTraversal(travSelect.value);

  const expSelect = document.getElementById("knowledge-graph-expansion-select");
  const expOut = document.getElementById("knowledge-graph-expansion-output");
  const expSamples = graph.expansion_samples || [];
  expSelect.innerHTML = "";
  for (const sample of expSamples) {
    const option = document.createElement("option");
    option.value = sample.query;
    option.textContent = sample.query;
    expSelect.appendChild(option);
  }
  function showExpansion(query) {
    const sample = expSamples.find((item) => item.query === query);
    expOut.textContent = sample ? JSON.stringify(sample, null, 2) : "No expansion sample.";
  }
  if (expSamples.length) showExpansion(expSamples[0].query);
  expSelect.onchange = () => showExpansion(expSelect.value);
}

function renderKnowledgeOrchestration(orch) {
  const summaryRoot = document.getElementById("knowledge-orchestration-summary");
  if (!summaryRoot) return;
  summaryRoot.innerHTML = "";
  if (!orch) {
    summaryRoot.appendChild(
      el("div", "hint", "No worker orchestration payload — re-run the validation script."),
    );
    return;
  }

  const summary = orch.summary || {};
  for (const [label, value] of [
    ["Registered workers", summary.registered_workers],
    ["Orchestration runs", summary.orchestration_runs],
    ["Avg elapsed (ms)", summary.average_elapsed_ms],
    ["Version", summary.orchestrator_version],
  ]) {
    const card = el("div", "stat-card");
    card.appendChild(el("div", "label", label));
    card.appendChild(el("div", "value", value == null ? "—" : String(value)));
    summaryRoot.appendChild(card);
  }

  const checklist = document.getElementById("knowledge-orchestration-checklist");
  checklist.innerHTML = "";
  for (const item of orch.checklist || []) {
    const li = el("li");
    const row = el("div", "checklist-item");
    row.appendChild(el("span", `check ${item.passed ? "ok" : "bad"}`, item.passed ? "✓" : "✗"));
    row.appendChild(el("div", null, item.label));
    li.appendChild(row);
    checklist.appendChild(li);
  }

  const workersBody = document.getElementById("knowledge-orchestration-workers");
  workersBody.innerHTML = "";
  for (const worker of orch.worker_registry || []) {
    const row = el("tr");
    const caps = (worker.capabilities || []).map((cap) => cap.name || cap).join(", ");
    const deps = (worker.depends_on || []).join(", ") || "—";
    const health = worker.health?.status || "—";
    row.appendChild(el("td", null, worker.id || "—"));
    row.appendChild(el("td", null, String(worker.priority ?? "—")));
    row.appendChild(el("td", null, caps || "—"));
    row.appendChild(el("td", null, deps));
    row.appendChild(el("td", null, health));
    workersBody.appendChild(row);
  }

  const querySelect = document.getElementById("knowledge-orchestration-query-select");
  const output = document.getElementById("knowledge-orchestration-output");
  const workerSelect = document.getElementById("knowledge-orchestration-worker-select");
  const workerOut = document.getElementById("knowledge-orchestration-worker-output");
  const mergerOut = document.getElementById("knowledge-orchestration-merger");
  const timelineOut = document.getElementById("knowledge-orchestration-timeline");
  const diagnostics = document.getElementById("knowledge-orchestration-diagnostics");
  const byQuery = orch.orchestrations_by_query || {};
  const samples = orch.sample_queries || Object.keys(byQuery);

  querySelect.innerHTML = "";
  for (const query of samples) {
    const option = document.createElement("option");
    option.value = query;
    option.textContent = query;
    querySelect.appendChild(option);
  }

  function showOrchestration(query) {
    const result = byQuery[query];
    output.textContent = result ? JSON.stringify(result, null, 2) : "No orchestration result.";
    const diag = result?.diagnostics || {};
    diagnostics.innerHTML = "";
    diagnostics.appendChild(
      el("li", null, `Eligible: ${(diag.eligible_workers || []).join(", ") || "none"}`),
    );
    diagnostics.appendChild(
      el("li", null, `Skipped: ${(diag.skipped_workers || []).join(", ") || "none"}`),
    );
    diagnostics.appendChild(
      el("li", null, `Failed: ${(diag.failed_workers || []).join(", ") || "none"}`),
    );
    diagnostics.appendChild(
      el("li", null, `Timeouts: ${(diag.timed_out_workers || []).join(", ") || "none"}`),
    );
    diagnostics.appendChild(
      el("li", null, `Status: ${result?.status || "—"} · ${result?.elapsed_ms ?? "—"} ms`),
    );

    mergerOut.textContent = JSON.stringify(diag.merger || {}, null, 2);
    timelineOut.textContent = JSON.stringify(
      {
        schedule: diag.schedule || {},
        timeline: diag.timeline || [],
      },
      null,
      2,
    );

    workerSelect.innerHTML = "";
    const evidence = result?.worker_evidence || [];
    for (const item of evidence) {
      const option = document.createElement("option");
      option.value = item.worker_id;
      option.textContent = `${item.worker_id} (${item.success ? "ok" : "fail"} · ${item.evidence_items?.length || 0})`;
      workerSelect.appendChild(option);
    }
    function showWorker(workerId) {
      const item = evidence.find((entry) => entry.worker_id === workerId);
      workerOut.textContent = item ? JSON.stringify(item, null, 2) : "No worker evidence.";
    }
    if (evidence.length) showWorker(evidence[0].worker_id);
    else workerOut.textContent = "No worker evidence.";
    workerSelect.onchange = () => showWorker(workerSelect.value);
  }

  if (samples.length) showOrchestration(samples[0]);
  querySelect.onchange = () => showOrchestration(querySelect.value);
}

async function main() {
  document.getElementById("inspector-close").addEventListener("click", closeInspector);
  document.getElementById("drawer-backdrop").addEventListener("click", closeInspector);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeInspector();
  });

  try {
    DATA = await loadData();
    document.getElementById("title").textContent = DATA.title || "Knowledge Intelligence Engine";
    document.getElementById("subtitle").textContent = DATA.subtitle || "";
    document.getElementById("phase-pill").textContent = `Phase ${DATA.phase || "—"}`;
    document.getElementById("mode-pill").textContent = `Mode ${DATA.mode || "shadow"}`;
    document.getElementById("version-pill").textContent = `v${DATA.pipeline_version || "—"}`;
    document.getElementById("generated-pill").textContent = DATA.generated_at
      ? `Generated ${DATA.generated_at}`
      : "Generated — run validation script";

    renderDecisionQuestions(DATA.decision_questions);
    renderStats(DATA.stats || {});
    renderRoadmap(DATA.roadmap || DATA.milestones || []);
    renderChecklist(DATA.checklist || [], DATA.checklist_details || {});
    renderApprovalGate(DATA.approval_gate || {});
    renderCapabilityComparison(
      DATA.capability_comparison || [],
      DATA.legacy_comparison?.notes || [],
    );
    renderConfidence(DATA.confidence_explanation || {}, DATA.stats || {});
    renderDocuments(DATA.documents || []);
    renderHistory(DATA.validation_history || []);
    renderIssues("issues", DATA.known_issues || []);
    renderIssues("resolved-issues", DATA.resolved_issues || []);
    renderRegistry(DATA.registry || null);
    renderRelationships(DATA.relationships || null, DATA.registry || null);
    renderHybridIndex(DATA.hybrid_index || null);
    renderQueryPlanner(DATA.query_planner || null);
    renderKnowledgeExecution(DATA.knowledge_execution || null);
    renderKnowledgeGraph(DATA.knowledge_graph || null);
    renderKnowledgeOrchestration(DATA.knowledge_orchestration || null);
  } catch (error) {
    const body = document.getElementById("documents-body");
    body.innerHTML = "";
    const row = el("tr");
    const cell = el(
      "td",
      "empty",
      `Failed to load data/phase_13_1.json: ${error.message}. Serve this folder over HTTP after running the validation script.`,
    );
    cell.colSpan = 9;
    row.appendChild(cell);
    body.appendChild(row);
  }
}

main();
