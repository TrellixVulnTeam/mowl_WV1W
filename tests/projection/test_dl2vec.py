from tests.datasetFactory import FamilyDataset
from mowl.projection import DL2VecProjector
from mowl.owlapi.defaults import TOP
from unittest import TestCase


class TestDl2Vec(TestCase):

    def test_constructor_parameter_types(self):
        """This should check if the constructor parameters are of the correct type"""
        self.assertRaisesRegex(
            TypeError, "Optional parameter bidirectional_taxonomy must be of type boolean",
            DL2VecProjector, "True")
        self.assertRaisesRegex(
            TypeError, "Optional parameter bidirectional_taxonomy must be of type boolean",
            DL2VecProjector, 1)
        self.assertRaisesRegex(
            TypeError, "Optional parameter bidirectional_taxonomy must be of type boolean",
            DL2VecProjector, {"a": 1, "b": 2, "c": 3})
        self.assertRaisesRegex(
            TypeError, "Optional parameter bidirectional_taxonomy must be of type boolean",
            DL2VecProjector, None)

    def test_project_method_parameter_types(self):
        """This should check if the project method parameters are of the correct type"""
        projector = DL2VecProjector()
        self.assertRaisesRegex(
            TypeError,
            "Parameter ontology must be of type org.semanticweb.owlapi.model.OWLOntology",
            projector.project, "True")
        self.assertRaisesRegex(
            TypeError,
            "Parameter ontology must be of type org.semanticweb.owlapi.model.OWLOntology",
            projector.project, 1)
        self.assertRaisesRegex(
            TypeError,
            "Parameter ontology must be of type org.semanticweb.owlapi.model.OWLOntology",
            projector.project, {"a": 1, "b": 2, "c": 3})
        self.assertRaisesRegex(
            TypeError,
            "Parameter ontology must be of type org.semanticweb.owlapi.model.OWLOntology",
            projector.project, None)

    # TODO: Add test to check if projection result is correct. To start, do this with
    # Family ontology.

    def test_project_family_ontology(self):
        """This should check if the projection result is correct"""
        ds = FamilyDataset()
        projector = DL2VecProjector()
        edges = projector.project(ds.ontology)
        edges = set([e.astuple() for e in edges])

        ground_truth_edges = set()
        ground_truth_edges.add(("http://Male", "http://subclassof", "http://Person"))
        ground_truth_edges.add(("http://Female", "http://subclassof", "http://Person"))
        ground_truth_edges.add(("http://Father", "http://subclassof", "http://Male"))
        ground_truth_edges.add(("http://Mother", "http://subclassof", "http://Female"))
        ground_truth_edges.add(("http://Father", "http://subclassof", "http://Parent"))
        ground_truth_edges.add(("http://Mother", "http://subclassof", "http://Parent"))
        ground_truth_edges.add(("http://Parent", "http://subclassof", "http://Person"))
        ground_truth_edges.add(("http://Parent", "http://hasChild", TOP))

        self.assertEqual(set(edges), ground_truth_edges)
