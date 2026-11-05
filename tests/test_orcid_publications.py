import unittest
from scripts.update_orcid_publications import (
    canonical_doi, extract_work, merge_publications, normalize_orcid,
)

class OrcidTests(unittest.TestCase):
    def setUp(self):
        self.a = {"name": "Researcher A", "orcid": "0000-0002-3326-266X"}
        self.b = {"name": "Researcher B", "orcid": "0000-0002-3326-266X"}

    def work(self, title, kind, doi, year, person):
        return extract_work({
            "title": {"title": {"value": title}},
            "type": kind,
            "publication-date": {"year": {"value": str(year)}},
            "external-ids": {"external-id": [{
                "external-id-type": "doi", "external-id-value": doi,
                "external-id-relationship": "self",
            }]},
        }, person)

    def test_orcid_validation(self):
        self.assertEqual(normalize_orcid("https://orcid.org/0000-0002-3326-266X"), "0000-0002-3326-266X")
        with self.assertRaises(ValueError):
            normalize_orcid("0000-0002-3326-2669")

    def test_doi_normalization(self):
        self.assertEqual(canonical_doi("https://doi.org/10.1000/TEST"), "10.1000/test")

    def test_same_doi_deduplicates_and_preserves_group_members(self):
        self.b["orcid"] = "0000-0003-1179-9578"
        works = [self.work("The Paper", "journal-article", "10.1234/AAA", 2026, self.a),
                 self.work("The Paper", "journal-article", "https://doi.org/10.1234/aaa", 2026, self.b)]
        merged = merge_publications(works)
        self.assertEqual(len(merged), 1)
        self.assertEqual(len(merged[0]["researchers"]), 2)

    def test_preprint_and_journal_different_dois_both_kept(self):
        works = [self.work("The Paper", "preprint", "10.1101/test", 2025, self.a),
                 self.work("The Paper", "journal-article", "10.1111/test", 2026, self.a)]
        self.assertEqual(len(merge_publications(works)), 2)

    def test_sort_newest_first(self):
        works = [self.work("Old", "journal-article", "10.2000/old", 2020, self.a),
                 self.work("New", "journal-article", "10.2000/new", 2026, self.a)]
        self.assertEqual(merge_publications(works)[0]["title"], "New")

if __name__ == "__main__":
    unittest.main()
