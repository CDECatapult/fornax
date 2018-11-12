import unittest
import json
import fornax.api
import fornax.model
from test_base import TestCaseDB
from sqlalchemy.orm.session import Session


class TestGraph(TestCaseDB):

    @classmethod
    def setUp(self):
        # trick fornax into using the test database setup
        super().setUp(self)
        fornax.api.Session = lambda: Session(self._connection)

    def test_init_raises(self):
        """ raise an ValueError if a hadle to a graph is constructed that does not exist """
        self.assertRaises(ValueError, fornax.GraphHandle, 0)
        self.assertRaises(ValueError, fornax.GraphHandle.read, 0)

    def test_create(self):
        graph = fornax.GraphHandle.create()
        self.assertEqual(graph.graph_id, 0)

    def test_create_two(self):
        _ = fornax.api.GraphHandle.create()
        second = fornax.GraphHandle.create()
        self.assertEqual(second.graph_id, 1)

    def test_read(self):
        graph = fornax.api.GraphHandle.create()
        graph_id = graph.graph_id
        same_graph = fornax.GraphHandle.read(graph_id)
        self.assertEqual(same_graph.graph_id, graph_id)

    def test_delete(self):
        graph = fornax.GraphHandle.create()
        graph.delete()
        self.assertRaises(ValueError, fornax.api.GraphHandle.read, 0)

    def test_add_nodes(self):
        graph = fornax.GraphHandle.create()
        names = ['adam', 'ben', 'chris']
        graph.add_nodes(name=names)
        nodes = self.session.query(fornax.model.Node).filter(fornax.model.Node.graph_id==0).all()
        nodes = sorted(nodes, key=lambda node: node.node_id)
        self.assertListEqual(names, [json.loads(node.meta)['name'] for node in nodes])

    def test_add_nodes_more_meta(self):
        graph = fornax.GraphHandle.create()
        names = ['adam', 'ben', 'chris']
        ages = [9, 10 ,11]
        graph.add_nodes(name=names, age=ages)
        nodes = self.session.query(fornax.model.Node).filter(fornax.model.Node.graph_id==0).all()
        nodes = sorted(nodes, key=lambda node: node.node_id)
        self.assertListEqual(names, [json.loads(node.meta)['name'] for node in nodes])
        self.assertListEqual(ages, [json.loads(node.meta)['age'] for node in nodes])
        
    def test_missing_attribute(self):
        graph = fornax.GraphHandle.create()
        names = ['adam', 'ben', 'chris']
        ages = [9, 10]
        self.assertRaises(TypeError, graph.add_nodes, name=names, age=ages)

    def test_assign_id(self):
        graph = fornax.GraphHandle.create()
        ids = range(3)
        self.assertRaises(ValueError, graph.add_nodes, id=ids)

    def test_add_edges(self):
        graph = fornax.GraphHandle.create()
        names = ['adam', 'ben', 'chris']
        ages = [9, 10 ,11]
        graph.add_nodes(name=names, age=ages)
        relationships = ['is_friend', 'is_foe']
        graph.add_edges([0, 0], [1, 2], relationship=relationships)
        edges = self.session.query(fornax.model.Edge).filter(fornax.model.Edge.graph_id==graph.graph_id).all()
        edges = sorted(edges, key=lambda edge: (edge.start, edge.end))
        self.assertListEqual(relationships, [json.loads(edge.meta)['relationship'] for edge in edges])

    def test_add_edges_more_meta(self):
        graph = fornax.GraphHandle.create()
        names = ['adam', 'ben', 'chris']
        ages = [9, 10 ,11]
        graph.add_nodes(name=names, age=ages)
        relationships = ['is_friend', 'is_foe']
        types = [0 , 1]
        graph.add_edges([0, 0], [1, 2], relationship=relationships, type=types)
        edges = self.session.query(fornax.model.Edge).filter(fornax.model.Edge.graph_id==graph.graph_id).all()
        edges = sorted(edges, key=lambda edge: (edge.start, edge.end))
        self.assertListEqual(relationships, [json.loads(edge.meta)['relationship'] for edge in edges])
        self.assertListEqual(types, [json.loads(edge.meta)['type'] for edge in edges])

    def test_simple_graph(self):
        """Test for a simple graph.
        A simple graph is a graph with no loops.
        A loop is an edge that connects a vertex to itself 
        """
        graph = fornax.GraphHandle.create()
        names = ['adam', 'ben', 'chris']
        ages = [9, 10 ,11]
        graph.add_nodes(name=names, age=ages)
        self.assertRaises(ValueError, graph.add_edges, [1, 0], [1, 2], relationship=['is_friend', 'is_foe'])

    def test_bad_edge_offset(self):
        """Edges a specicified by integer offsetse into the list of nodes
        """
        graph = fornax.GraphHandle.create()
        names = ['adam', 'ben', 'chris']
        ages = [9, 10 ,11]
        graph.add_nodes(name=names, age=ages)
        self.assertRaises(ValueError, graph.add_edges, ['adam', 'adam'], ['ben', 'chris'], relationship=['is_friend', 'is_foe'])