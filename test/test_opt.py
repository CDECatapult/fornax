import itertools
import unittest
import fornax.opt as opt
import fornax.model as model
import fornax.select as select
from test_base import TestCaseDB
from sqlalchemy.orm import Query, aliased

from sqlalchemy import or_, and_, literal
import numpy as np


class TestProximity(unittest.TestCase):

    def setUp(self):
        self.h = 2
        self.alpha = .3

    def test_zero(self):
        proximities = opt._proximity(self.h, self.alpha, np.array([0]))
        self.assertListEqual([1.0], proximities.tolist())

    def test_one(self):
        proximities = opt._proximity(self.h, self.alpha, np.array([1]))
        self.assertListEqual([self.alpha], proximities.tolist())

    def test_pow(self):
        proximities = opt._proximity(self.h, self.alpha, np.array([2, 3, 4]))
        self.assertListEqual([self.alpha**2, 0.0, 0.0], proximities.tolist())

    def test_assert_h(self):
        self.assertRaises(ValueError, opt._proximity, -1, 0.3, np.array([0]))

    def test_assert_alpha_big(self):
        self.assertRaises(ValueError, opt._proximity, 2, 1.1, np.array([0]))

    def test_assert_alpha_small(self):
        self.assertRaises(ValueError, opt._proximity, 2, -.1, np.array([0]))


class TestDeltaPlus(unittest.TestCase):

    def test_greater(self):
        self.assertListEqual(
            opt._delta_plus(np.array([2, 4, 6]), np.array([1, 2, 3])).tolist(),
            [1, 2, 3]
        )
        
    def test_less(self):
        self.assertListEqual(
            opt._delta_plus(np.array([1, 2, 3]), np.array([2, 4, 6])).tolist(),
            [0, 0, 0]
        )


class Frame(unittest.TestCase):

    def setUp(self):
        self.records = [
            (2, 2 ,3, 4, 5, 6, 7, 8, 9, 10),
            (1, 2 ,3, 4, 5, 6, 7, 8, 9, 10),
            (1, 2 ,2, 4, 5, 6, 7, 8, 9, 10),
            (1, 2 ,2, 4, 5, 6, 6, 8, 9, 10)
        ]
        self.frame = opt.Frame(self.records)

    def test_assert_columns(self):
        self.assertRaises(ValueError, self.frame.__getitem__, 'foo')

    def testGetItem(self):
        self.assertListEqual(
            self.frame['match_start'].tolist(),
            sorted([record[0] for record in self.records])
        )
    
    def test_set_item(self):
        frame = opt.Frame(self.frame.records.tolist())
        frame['match_end'] = [record[1] + 1 for record in self.records]
        self.assertListEqual(
            frame['match_end'].tolist(),
            [record[1] + 1 for record in self.records]
        )

    def test_len(self):
        self.assertEqual(len(self.frame), len(self.records))

    def test_sort(self):

        key_idx = [
            opt.Frame.columns.index(item) 
            for item in ['match_start', 'match_end', 'query_node_id', 'delta']
        ]

        target = sorted(self.records, key = lambda x: tuple(x[i] for i in key_idx))

        self.assertListEqual(
            self.frame['match_start'].tolist(),
            [row[0] for row in target]
        )

        self.assertListEqual(
            self.frame['match_end'].tolist(),
            [row[1] for row in target]
        )

        self.assertListEqual(
            self.frame['query_node_id'].tolist(),
            [row[2] for row in target]
        )

    def test_proximity(self):
        pass

    def test_totals(self):
        records = [
            (2, 2 ,3, 4, 5, 6, 7, 8, 9, 10),
            (2, 2 ,4, 5, 5, 6, 7, 8, 9, 10),
            (1, 2 ,1, 4, 5, 6, 7, 8, 9, 10),
            (1, 2 ,2, -1, 5, 6, 6, 8, 9, 10)
        ]

        frame = opt.Frame(records)
        self.assertListEqual(frame['totals'].tolist(), [1, 1, 2, 2])

    def test_misses(self):
        records = [
            (2, 2 ,3, 4, 5, 6, 7, 8, 9, 10),
            (2, 2 ,4, 5, 5, 6, 7, 8, 9, 10),
            (1, 2 ,2, None, 5, None, 7, 8, 9, 10),
            (1, 2 ,3, 5, 5, 6, 6, 8, 9, 10)
        ]

        frame = opt.Frame(records)
        self.assertListEqual(frame['misses'].tolist(), [1, 1, 0, 0])

class TestOpt(unittest.TestCase):
    """Reproduce the scenario set out in figure 4 of the paper"""

    def setUp(self):
        self.h = 2
        self.alpha = .3
        self.records = [
            (1, 1, 1, 1, 0, 0, 0, 0, 0, 1), (1, 1, 1, 4, 0, 1, 0, 0, 0, 1), (1, 1, 2, 5, 1, 2, 0, 0, 0, 1), 
            (1, 1, 3, 3, 1, 1, 0, 0, 0, 1), (1, 1, 3, 6, 1, 2, 0, 0, 0, 1), (1, 1, 4, 7, 2, 2, 0, 0, 0, 1), 
            (1, 4, 1, 1, 0, 1, 0, 0, 0, 1), (1, 4, 1, 4, 0, 0, 0, 0, 0, 1), (1, 4, 1, 8, 0, 2, 0, 0, 0, 1), 
            (1, 4, 2, 5, 1, 1, 0, 0, 0, 1), (1, 4, 3, 3, 1, 2, 0, 0, 0, 1), (1, 4, 3, 6, 1, 1, 0, 0, 0, 1), 
            (1, 4, 4, 7, 2, 2, 0, 0, 0, 1), (1, 8, 1, 4, 0, 2, 0, 0, 0, 1), (1, 8, 1, 8, 0, 0, 0, 0, 0, 1), 
            (1, 8, 2, 9, 1, 1, 0, 0, 0, 1), (1, 8, 3, 6, 1, 1, 0, 0, 0, 1), (1, 8, 3, 12, 1, 1, 0, 0, 0, 1), 
            (1, 8, 4, 10, 2, 2, 0, 0, 0, 1), (2, 5, 1, 1, 1, 2, 0, 0, 0, 1), (2, 5, 1, 4, 1, 1, 0, 0, 0, 1), 
            (2, 5, 2, 5, 0, 0, 0, 0, 0, 1), (2, 5, 3, 3, 2, 2, 0, 0, 0, 1), (2, 5, 3, 6, 2, 2, 0, 0, 0, 1), 
            (2, 5, 4, 7, 1, 1, 0, 0, 0, 1), (2, 5, 4, 10, 1, 2, 0, 0, 0, 1), (2, 5, 5, None, 2, None, 0, 0, 0, 1), 
            (2, 9, 1, 8, 1, 1, 0, 0, 0, 1), (2, 9, 2, 9, 0, 0, 0, 0, 0, 1), (2, 9, 3, 6, 2, 2, 0, 0, 0, 1), 
            (2, 9, 3, 12, 2, 2, 0, 0, 0, 1), (2, 9, 4, 7, 1, 2, 0, 0, 0, 1), (2, 9, 4, 10, 1, 1, 0, 0, 0, 1), 
            (2, 9, 5, 11, 2, 2, 0, 0, 0, 1), (3, 3, 1, 1, 1, 1, 0, 0, 0, 1), (3, 3, 1, 4, 1, 2, 0, 0, 0, 1), 
            (3, 3, 2, 5, 2, 2, 0, 0, 0, 1), (3, 3, 3, 3, 0, 0, 0, 0, 0, 1), (3, 6, 1, 1, 1, 2, 0, 0, 0, 1), 
            (3, 6, 1, 4, 1, 1, 0, 0, 0, 1), (3, 6, 1, 8, 1, 1, 0, 0, 0, 1), (3, 6, 2, 5, 2, 2, 0, 0, 0, 1), 
            (3, 6, 2, 9, 2, 2, 0, 0, 0, 1), (3, 6, 3, 6, 0, 0, 0, 0, 0, 1), (3, 6, 3, 12, 0, 2, 0, 0, 0, 1), 
            (3, 12, 1, 8, 1, 1, 0, 0, 0, 1), (3, 12, 2, 9, 2, 2, 0, 0, 0, 1), (3, 12, 3, 6, 0, 2, 0, 0, 0, 1), 
            (3, 12, 3, 12, 0, 0, 0, 0, 0, 1), (3, 12, 3, 13, 0, 2, 0, 0, 0, 1), (3, 13, 1, None, 1, None, 0, 0, 0, 1), 
            (3, 13, 2, None, 2, None, 0, 0, 0, 1), (3, 13, 3, 12, 0, 2, 0, 0, 0, 1), (3, 13, 3, 13, 0, 0, 0, 0, 0, 1), 
            (4, 7, 1, 1, 2, 2, 0, 0, 0, 1), (4, 7, 1, 4, 2, 2, 0, 0, 0, 1), (4, 7, 2, 5, 1, 1, 0, 0, 0, 1), 
            (4, 7, 2, 9, 1, 2, 0, 0, 0, 1), (4, 7, 4, 7, 0, 0, 0, 0, 0, 1), (4, 7, 4, 10, 0, 1, 0, 0, 0, 1), 
            (4, 7, 5, 11, 1, 2, 0, 0, 0, 1), (4, 10, 1, 8, 2, 2, 0, 0, 0, 1), (4, 10, 2, 5, 1, 2, 0, 0, 0, 1), 
            (4, 10, 2, 9, 1, 1, 0, 0, 0, 1), (4, 10, 4, 7, 0, 1, 0, 0, 0, 1), (4, 10, 4, 10, 0, 0, 0, 0, 0, 1), 
            (4, 10, 5, 11, 1, 1, 0, 0, 0, 1), (5, 11, 2, 9, 2, 2, 0, 0, 0, 1), (5, 11, 4, 7, 1, 2, 0, 0, 0, 1), 
            (5, 11, 4, 10, 1, 1, 0, 0, 0, 1), (5, 11, 5, 11, 0, 0, 0, 0, 0, 1)
        ]
        
    def test_optimal_matches(self):
        
        solutions = opt.solve(5, self.h, self.alpha, self.records)
        perfect = [graph for graph, score in solutions if score == 0]

        self.assertSequenceEqual(
            perfect[0], 
            [(1, 8), (2, 9), (3, 6), (4, 10), (5, 11)]
        )        

        self.assertSequenceEqual(
            perfect[1], 
            [(1, 8), (2, 9), (3, 12), (4, 10), (5, 11)]
        )


if __name__ == '__main__':
    unittest.main()
