import unittest
from ca2lab.benchmark import require_coverage,setup_pass
class Gates(unittest.TestCase):
    def rows(self):return [dict(frequency_Hz=f,eligible_all_seeds=True,inside_compatibility_band=True,model_mean_ratio=2.) for f in [30,50]]
    def test_pass(self):self.assertTrue(setup_pass(self.rows(),[30,50],True))
    def test_missing_duplicate_ineligible_numerics(self):
        rows=self.rows()
        for subset in [[],rows[:1],rows+[rows[0]]]:self.assertFalse(setup_pass(subset,[30,50],True))
        rows[0]['eligible_all_seeds']=False;self.assertFalse(setup_pass(rows,[30,50],True))
        self.assertFalse(setup_pass(self.rows(),[30,50],False))
    def test_coverage(self):
        for rows in [[1],[1,1],[1,2,3]]:
            with self.assertRaises(ValueError):require_coverage(rows,{1,2},lambda x:x)
        require_coverage([1,2],{1,2},lambda x:x)
