from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from euro_sdt.v2.db import init_db, normalize_name, org_merge_key, slugify
from euro_sdt.v2.graph import edge_class
from euro_sdt.v2.locate import DocumentIndex, alias_in_text
from euro_sdt.v2.claims import ISO_TO_COUNTRY, _literal_aliases, normalize_role, predicate_for_role
from euro_sdt.v2.tokenizer import normalize_text, normalize_with_map, sentence_spans


class TokenizerTests(unittest.TestCase):
    def test_offsets_round_trip(self):
        text = "Mr. Smith went to Washington. He met Dr. Jones at the ministry. The U.S. delegation agreed!"
        spans = sentence_spans(text)
        self.assertEqual(len(spans), 3)
        for span in spans:
            self.assertEqual(text[span.char_start:span.char_end], span.text)
        self.assertIn("Mr. Smith", spans[0].text)

    def test_html_entity_normalisation(self):
        normalised, offsets = normalize_with_map("A&amp;B &#91;3&#93; Café")
        self.assertEqual(normalised, "a&b [3] café")
        self.assertEqual(offsets[0], 0)
        self.assertEqual(len(offsets), len(normalised))

    def test_org_merge_keys(self):
        self.assertEqual(
            org_merge_key("European People's Party (EPP)"),
            org_merge_key("European People's Party"),
        )
        self.assertEqual(
            org_merge_key("European Peoples Party"),
            org_merge_key("European People's Party"),
        )
        self.assertNotEqual(
            org_merge_key("European People's Party (EPP) group"),
            org_merge_key("European People's Party"),
        )

    def test_slug_is_stable_for_diacritics(self):
        self.assertEqual(slugify("Hans-Gert Pöttering"), "hans-gert-pottering")
        self.assertEqual(slugify("Adina-Ioana Vălean"), "adina-ioana-valean")
        self.assertEqual(normalize_name("Hans-Gert Pöttering"), "hans gert pottering")


class LocatorTests(unittest.TestCase):
    def setUp(self):
        self.text = (
            "Ursula von der Leyen is a German politician. "
            "She is a member of the European People's Party (EPP). "
            "She graduated from the London School of Economics in 1978."
        )
        self.index = DocumentIndex(self.text, sentence_spans(self.text))

    def test_exact_quote_locates(self):
        location = self.index.locate("She is a member of the European People's Party (EPP).")
        self.assertEqual(location.status, "located")
        self.assertEqual(location.sentence_start_ordinal, 1)
        self.assertIn("European People", self.text[location.char_start:location.char_end])

    def test_quote_with_entity_and_whitespace_locates(self):
        location = self.index.locate("She graduated   from the London School of Economics in 1978.")
        self.assertEqual(location.status, "located")
        self.assertEqual(location.sentence_start_ordinal, 2)

    def test_missing_quote_is_not_guessed(self):
        location = self.index.locate("She was president of the Atlantic Council.")
        self.assertEqual(location.status, "quote_not_found")

    def test_hint_breaks_tie(self):
        text = "He joined the Council. He led the Council."
        index = DocumentIndex(text, sentence_spans(text))
        location = index.locate("He led the Council.", hint_ordinal=1)
        self.assertEqual(location.sentence_start_ordinal, 1)

    def test_alias_matching_includes_acronyms(self):
        self.assertTrue(alias_in_text(
            "She is a member of the European Council on Foreign Relations (ECFR).",
            ("European Council on Foreign Relations", "ECFR"),
        ))
        self.assertFalse(alias_in_text("She is a member of the Atlantic Council.", ("ECFR",)))


class RoleTests(unittest.TestCase):
    def test_role_normalisation(self):
        self.assertEqual(normalize_role("Member of the Board of Trustees"), "board_member")
        self.assertEqual(normalize_role("Chairman"), "chair")
        self.assertEqual(normalize_role("CEO"), "employed_by")
        self.assertEqual(normalize_role("participant"), "attendee")
        self.assertEqual(predicate_for_role("board_member"), "board_member")

    def test_country_literal_aliases(self):
        self.assertIn("Germany", _literal_aliases("DEU"))
        self.assertIn("Directorate-General for Health", " ".join(_literal_aliases("Director-General → Directorate-General for Health")))

    def test_edge_classes(self):
        self.assertEqual(edge_class("board_member"), "network")
        self.assertEqual(edge_class("employed_by"), "occupational")
        self.assertEqual(edge_class("educated_at"), "education")
        self.assertEqual(edge_class("served_on_commission"), "institutional")


class SchemaTests(unittest.TestCase):
    def test_schema_initialises_and_enforces_foreign_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.db"
            db = init_db(path)
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertIn("source_document", tables)
            self.assertIn("sentence", tables)
            self.assertIn("assertion", tables)
            self.assertIn("adjudication", tables)
            with self.assertRaises(Exception):
                db.execute("INSERT INTO claim (id, subject_id, predicate, object_literal, extractor, created_at) "
                           "VALUES ('c1','missing','member','x','test','now')")
            db.close()


if __name__ == "__main__":
    unittest.main()
