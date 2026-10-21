-- Euro-SDT v2: citation-anchored elite graph.
-- Invariants:
--   * every assertion references at least one evidence row
--   * every evidence row references a source document and a sentence span
--   * every evidence quote is located by a deterministic locator, not by an LLM
--   * claims may exist as candidates; only assertions enter the graph
--   * one claim per (subject, predicate, object, role); evidence is many-to-one

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS run (
    id             TEXT PRIMARY KEY,
    kind           TEXT NOT NULL,
    started_at     TEXT NOT NULL,
    finished_at    TEXT,
    model          TEXT,
    prompt_sha256  TEXT,
    params_json    TEXT,
    git_commit     TEXT
);

CREATE TABLE IF NOT EXISTS source_document (
    id             TEXT PRIMARY KEY,          -- stable slug
    kind           TEXT NOT NULL,             -- wikipedia | dg_cv | declaration | cjeu | revolving_door | org_site | entity_md
    title          TEXT NOT NULL,
    url            TEXT,
    local_path     TEXT NOT NULL,
    text_sha256    TEXT NOT NULL,
    char_count     INTEGER NOT NULL,
    sentence_count INTEGER NOT NULL DEFAULT 0,
    retrieved_at   TEXT,
    revision_id    TEXT,
    access_date    TEXT,
    license        TEXT,
    subject_id     TEXT REFERENCES entity(id), -- person the document is about, if any
    metadata_json  TEXT
);

CREATE TABLE IF NOT EXISTS sentence (
    id           TEXT PRIMARY KEY,            -- doc_id:ordinal
    doc_id       TEXT NOT NULL REFERENCES source_document(id) ON DELETE CASCADE,
    ordinal      INTEGER NOT NULL,
    char_start   INTEGER NOT NULL,
    char_end     INTEGER NOT NULL,
    text         TEXT NOT NULL,
    text_sha256  TEXT NOT NULL,
    UNIQUE (doc_id, ordinal)
);
CREATE INDEX IF NOT EXISTS idx_sentence_doc ON sentence(doc_id, ordinal);

CREATE TABLE IF NOT EXISTS entity (
    id               TEXT PRIMARY KEY,
    kind             TEXT NOT NULL,            -- person | organisation | institution | commission | country | role
    name             TEXT NOT NULL,
    category         TEXT,
    country          TEXT,
    external_ids_json TEXT,
    status           TEXT NOT NULL DEFAULT 'active',  -- active | quarantined | merged
    merged_into      TEXT REFERENCES entity(id),
    created_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entity_kind ON entity(kind);
CREATE INDEX IF NOT EXISTS idx_entity_name ON entity(name);

CREATE TABLE IF NOT EXISTS entity_alias (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id  TEXT NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
    alias      TEXT NOT NULL,
    source     TEXT NOT NULL,
    UNIQUE (entity_id, alias)
);
CREATE INDEX IF NOT EXISTS idx_alias_entity ON entity_alias(entity_id);
CREATE INDEX IF NOT EXISTS idx_alias_name ON entity_alias(alias);

CREATE TABLE IF NOT EXISTS claim (
    id             TEXT PRIMARY KEY,
    subject_id     TEXT NOT NULL REFERENCES entity(id),
    predicate      TEXT NOT NULL,
    object_id      TEXT REFERENCES entity(id),
    object_literal TEXT,
    role           TEXT,                       -- normalised role
    role_raw       TEXT,
    start_date     TEXT,
    end_date       TEXT,
    source_hint    TEXT,
    extractor      TEXT NOT NULL,              -- v1_fact | v1_manifest | v2_llm | manual
    extractor_run  TEXT REFERENCES run(id),
    created_at     TEXT NOT NULL,
    CHECK (object_id IS NOT NULL OR object_literal IS NOT NULL)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_claim_key ON claim(
    subject_id, predicate, COALESCE(object_id, ''), COALESCE(object_literal, ''), COALESCE(role, '')
);
CREATE INDEX IF NOT EXISTS idx_claim_subject ON claim(subject_id);
CREATE INDEX IF NOT EXISTS idx_claim_object ON claim(object_id);
CREATE INDEX IF NOT EXISTS idx_claim_predicate ON claim(predicate);

CREATE TABLE IF NOT EXISTS evidence (
    id                TEXT PRIMARY KEY,
    claim_id          TEXT NOT NULL REFERENCES claim(id) ON DELETE CASCADE,
    doc_id            TEXT NOT NULL REFERENCES source_document(id),
    sentence_start_id TEXT REFERENCES sentence(id),
    sentence_end_id   TEXT REFERENCES sentence(id),
    char_start        INTEGER,
    char_end          INTEGER,
    quote             TEXT NOT NULL,
    locator_status    TEXT NOT NULL,           -- located | quote_not_found | source_missing | unlocatable
    matched_chars     INTEGER,
    subject_mentioned INTEGER NOT NULL DEFAULT 0,
    object_mentioned  INTEGER NOT NULL DEFAULT 0,
    role_mentioned    INTEGER NOT NULL DEFAULT 0,
    subject_context   TEXT,                    -- span | document | none
    notes             TEXT
);
CREATE INDEX IF NOT EXISTS idx_evidence_claim ON evidence(claim_id);
CREATE INDEX IF NOT EXISTS idx_evidence_doc ON evidence(doc_id);

CREATE TABLE IF NOT EXISTS assertion (
    id              TEXT PRIMARY KEY,
    claim_id        TEXT NOT NULL UNIQUE REFERENCES claim(id) ON DELETE CASCADE,
    status          TEXT NOT NULL,             -- verified | rejected | needs_review
    evidence_grade  TEXT NOT NULL,             -- A | B | C | none
    n_sources       INTEGER NOT NULL DEFAULT 0,
    reason          TEXT,
    adjudicator     TEXT,                      -- deterministic | llm:<model> | human
    adjudicated_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_assertion_status ON assertion(status);
CREATE INDEX IF NOT EXISTS idx_assertion_grade ON assertion(evidence_grade);

CREATE TABLE IF NOT EXISTS rejection (
    id         TEXT PRIMARY KEY,
    claim_id   TEXT NOT NULL REFERENCES claim(id),
    stage      TEXT NOT NULL,
    reason     TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Organisation classifications and descriptions. These are not graph edges.
CREATE TABLE IF NOT EXISTS organisation_profile (
    id          TEXT PRIMARY KEY,
    entity_id   TEXT NOT NULL REFERENCES entity(id),
    attribute   TEXT NOT NULL,                 -- org_type | atlanticist | nato_adjacent | us_linked | funding | description
    value       TEXT,
    sentence_id TEXT REFERENCES sentence(id),
    quote       TEXT,
    source_url  TEXT,
    source_date TEXT,
    status      TEXT NOT NULL,                 -- sourced | manual_seed | unverified
    notes       TEXT,
    UNIQUE (entity_id, attribute, value)
);
CREATE INDEX IF NOT EXISTS idx_profile_entity ON organisation_profile(entity_id);

CREATE TABLE IF NOT EXISTS review (
    id         TEXT PRIMARY KEY,
    claim_id   TEXT NOT NULL REFERENCES claim(id),
    decision   TEXT NOT NULL,       -- verified | rejected | needs_review
    reviewer   TEXT NOT NULL,
    reason     TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_review_claim ON review(claim_id);

CREATE TABLE IF NOT EXISTS adjudication (
    id             TEXT PRIMARY KEY,
    claim_id       TEXT NOT NULL REFERENCES claim(id),
    evidence_id    TEXT REFERENCES evidence(id),
    model          TEXT NOT NULL,
    prompt_sha256  TEXT,
    verdict        TEXT NOT NULL,
    reason         TEXT,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_adjudication_claim ON adjudication(claim_id);

CREATE TABLE IF NOT EXISTS pipeline_event (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    stage      TEXT NOT NULL,
    level      TEXT NOT NULL,
    message    TEXT NOT NULL
);
