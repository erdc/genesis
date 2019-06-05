import unittest
import cartopy.crs as ccrs
from genesis.mesh import Mesh, Unstructured, Unstructured2D


class TestMeshMain(unittest.TestCase):

    def test_mesh_instantiation(self):
        # set crs
        crs = ccrs.PlateCarree()
        # instantiate mesh object
        mesh_object = Mesh(crs=crs)

        self.assertIsInstance(mesh_object, Mesh)

    def test_mesh_unstruct_instantiation(self):
        # set crs
        crs = ccrs.PlateCarree()
        # instantiate mesh object
        mesh_object = Unstructured(crs=crs)

        self.assertIsInstance(mesh_object, Unstructured)

    def test_mesh_unstruct2d_instantiation(self):
        # set crs
        crs = ccrs.PlateCarree()
        # instantiate mesh object
        mesh_object = Unstructured2D(crs=crs)

        self.assertIsInstance(mesh_object, Unstructured2D)
