# SPDX-License-Identifier: GPL-3.0-only
import unittest
from decimal import Decimal
from production_fixtures import ROOT
from weekly_runtime.scoring import calculate, rounded, sort_key

class ScoringTests(unittest.TestCase):

    def test_hand_calculated_case(self):
        score = calculate({'view': 1000000, 'reply': 1000, 'danmaku': 500, 'favorite': 10000, 'coin': 20000})
        self.assertEqual(score['score'], 541802)
        self.assertEqual(score['coefficients'], {'P': '1.000', 'A': '1', 'B': '0.32', 'C': '0.02', 'D': '0.529'})
        self.assertEqual(Decimal(score['raw_score']), Decimal('541801.8'))

    def test_interaction_changes_order(self):
        low = calculate({'view': 100, 'reply': 0, 'danmaku': 0, 'favorite': 0, 'coin': 0})
        rich = calculate({'view': 100, 'reply': 10, 'danmaku': 5, 'favorite': 20, 'coin': 8})
        self.assertEqual((low['score'], rich['score']), (49, 403))
        self.assertGreater(rich['score'], low['score'])

    def test_zero_denominators_and_display_only_metrics(self):
        data = {k: 0 for k in ('view', 'reply', 'danmaku', 'favorite', 'coin')}
        self.assertEqual(calculate(data)['score'], 0)
        data.update(like=10000000, share=100000)
        self.assertEqual(calculate(data)['score'], 0)

    def test_half_up_not_bankers_rounding(self):
        self.assertEqual(rounded(Decimal('0.125'), 2), Decimal('0.13'))
        base = {'view': 1000, 'reply': 3, 'danmaku': 2, 'favorite': 10, 'coin': 5}
        self.assertEqual(calculate(base, 6)['coefficients']['P'], '0.444')

    def test_invalid_inputs_block_score(self):
        base = {'view': 100, 'reply': 1, 'danmaku': 0, 'favorite': 2, 'coin': 3}
        with self.assertRaises(ValueError):
            calculate({**base, 'reply': -1})
        with self.assertRaises(ValueError):
            calculate({**base, 'view': True})
        with self.assertRaises(ValueError):
            calculate(base, 0)
        with self.assertRaises(ValueError):
            calculate(base, algorithm='unknown')

    def test_ties_have_no_hidden_interaction_weight(self):
        rows = [{'bvid': 'BV2222222222', 'score': 100, 'metrics': {'like': 9000}}, {'bvid': 'BV1111111111', 'score': 100, 'metrics': {'like': 1}}]
        self.assertEqual(sorted(rows, key=sort_key)[0]['bvid'], 'BV1111111111')
