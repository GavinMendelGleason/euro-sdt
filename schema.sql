-- Citation-anchored knowledge graph for Euro-SDT
-- Every fact has a source. Every source has a quote. Every quote has a position.
-- The database is the single source of truth; the wiki is a build artefact.

-- ── Things we talk about ──────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS entity (
    id         TEXT PRIMARY KEY,  -- human slug, e.g. 'von-der-leyen-ursula'
    name       TEXT NOT NULL,     -- display name, e.g. 'Ursula von der Leyen'
    type       TEXT NOT NULL,     -- 'person', 'organisation', 'commission', 'institution', 'dataset'
    category   TEXT,              -- 'commissioner', 'dg', 'ddg', 'mep', 'cjeu_judge',
                                  -- 'think_tank', 'elite_network', 'university', 'bank',
                                  -- 'consultancy', 'ngo', 'foundation', 'forum'
    country    TEXT,              -- ISO 3166-1 alpha-3
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_entity_type ON entity(type);
CREATE INDEX idx_entity_category ON entity(category);


-- ── Individual assertions ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fact (
    id           TEXT PRIMARY KEY,  -- UUID
    entity_id    TEXT NOT NULL REFERENCES entity(id),
    predicate    TEXT NOT NULL,     -- controlled vocabulary, see below
    object       TEXT NOT NULL,     -- value: can be entity_id or literal string
    object_type  TEXT DEFAULT 'literal',  -- 'entity_id' or 'literal'
    qualifier    TEXT,              -- additional context, e.g. 'PhD in Economics, 1996'
    start_date   TEXT,              -- YYYY-MM-DD, YYYY-MM, or YYYY
    end_date     TEXT,
    confidence   TEXT DEFAULT 'confirmed',  -- 'confirmed', 'likely', 'disputed', 'inferred', 'unverified'
    verified_at  TEXT,              -- ISO date when AI-checked (NULL = not checked)
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (entity_id) REFERENCES entity(id)
);

CREATE INDEX idx_fact_entity ON fact(entity_id);
CREATE INDEX idx_fact_predicate ON fact(predicate);

/*
Controlled predicate vocabulary:
  educated_at         → person → institution
  held_position       → person → role/org
  member_of           → person → organisation
  member_of_board     → person → organisation (governance role)
  member_of_advisory  → person → organisation
  served_on_commission → person → commission
  attended_event      → person → event
  works_at            → person → department/org (current)
  headed_by           → organisation → person
  headquartered_in    → organisation → city
  founded_in          → organisation → year
  funded_by           → organisation → funder
  classified_as       → entity → type (atlanticist, nato_adjacent, us_linked)
  has_sector          → person → sector (prior to commission)
  born_in             → person → place
  born_on             → person → date
  studied_field       → person → field (law, economics, etc.)
  held_degree         → person → degree type (PhD, LLM, Staatsexamen, etc.)
  nominated_by        → person → country
*/


-- ── Sources that back facts ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS citation (
    id            TEXT PRIMARY KEY,  -- short slug
    source_name   TEXT NOT NULL,     -- human label, e.g. 'VdL II Declarations of Interests ZIP'
    source_type   TEXT NOT NULL,     -- 'ec_declaration', 'wikidata', 'wikipedia',
                                     -- 'commission_cv_pdf', 'cjeu_website',
                                     -- 'commoncrawl', 'usaspending_gov', 'wayback_machine'
    url           TEXT,              -- permalink / download URL
    access_date   TEXT,              -- ISO date when retrieved
    file_path     TEXT,              -- local path if cached
    description   TEXT               -- how the data was obtained
);

CREATE TABLE IF NOT EXISTS provenance (
    id            TEXT PRIMARY KEY,
    fact_id       TEXT NOT NULL REFERENCES fact(id),
    citation_id   TEXT NOT NULL REFERENCES citation(id),
    quote_text    TEXT NOT NULL,          -- exact words from the source
    phrase_index  INTEGER NOT NULL,      -- 0-based sentence index in the .phrases file
    context_text  TEXT                    -- surrounding sentences (for AI verification)
);

CREATE INDEX idx_provenance_fact ON provenance(fact_id);
CREATE INDEX idx_provenance_citation ON provenance(citation_id);


-- ── Links between facts (e.g. sequential positions) ────────────────────────

CREATE TABLE IF NOT EXISTS fact_link (
    id           TEXT PRIMARY KEY,
    fact_a       TEXT NOT NULL REFERENCES fact(id),
    fact_b       TEXT NOT NULL REFERENCES fact(id),
    relation     TEXT NOT NULL,     -- 'precedes', 'overlaps', 'contradicts', 'confirms'
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
