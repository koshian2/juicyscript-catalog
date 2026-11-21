import unittest

from build import ROOT, read_json, receipt


class PublishedSheetTest(unittest.TestCase):
    def test_displayed_yen(self):
        expected = {
            "mosaic_2020": [1677, 2310, 1440, 2312, 2310, 1358, 1600, 1950],
            "mlblog_01": [497],
            "infinity_numpy": [1677, 1656, 1440, 907, 1651, 1656, 1656, 1520, 1560, 1000],
            "solo_dl_paper_2021_01": [1300, 1120, 891, 1274, 1502, 1502, 1120, 839],
            "docker": [1866, 1848, 1600, 923, 1840, 1694, 1520, 879],
            "art1": [1394, 1200, 1082, 1934, 1920, 1028],
            "eki01_hidaka": [1280, 312, 1462, 1771, 1771, 1440, 1560],
            "soya": [1280, 312, 1462, 1502, 1502, 1520, 1300, 2367],
            "goods_mugcup_anko01": [990],
        }
        groups = read_json(ROOT / "data/receipt-examples.json")["groups"]
        actual = {g["id"]: [receipt(o) for o in g["offers"]] for g in groups}
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
