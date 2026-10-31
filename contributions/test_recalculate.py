"""Regression checks for source attribution; run with unittest discovery."""
import copy
import json
import unittest
from pathlib import Path

from recalculate import calculate, validate


class AttributionChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(Path(__file__).with_name("2026-10-31.json").read_text())

    def test_reviewed_split_scopes_and_totals(self):
        result = calculate(self.ledger)
        self.assertEqual(result["maintenance_total"], 1814)
        self.assertEqual(result["project_total"], 2454)
        self.assertEqual(sum(r["share_tenths"] for r in result["maintenance"]), 1000)

    def test_renaming_a_row_does_not_make_its_evidence_reusable(self):
        data = copy.deepcopy(self.ledger)
        item = copy.deepcopy(data["maintenance"][0])
        item["id"] += "-renamed"
        item["title"] += " another label"
        data["maintenance"].append(item)
        with self.assertRaisesRegex(AssertionError, "overlapping evidence"):
            validate(data)

    def test_a_new_source_label_does_not_make_its_evidence_reusable(self):
        data = copy.deepcopy(self.ledger)
        item = copy.deepcopy(data["maintenance"][0])
        item["id"] += "-issue-copy"
        item["title"] += " issue follow-up"
        item["source_issues"].append(999)
        data["maintenance"].append(item)
        with self.assertRaisesRegex(AssertionError, "overlapping evidence"):
            validate(data)

    def test_excerpt_must_match_the_stored_source(self):
        data = copy.deepcopy(self.ledger)
        data["maintenance"][0]["scoring_evidence"][0]["excerpt"] += " unproven work"
        with self.assertRaises(AssertionError):
            validate(data)

    def test_disjoint_passages_still_require_a_reviewed_split(self):
        data = copy.deepcopy(self.ledger)
        del data["split_maintenance_scopes"]["m-yuppiez99999-204-b"]
        with self.assertRaises(AssertionError):
            validate(data)


if __name__ == "__main__":
    unittest.main()
