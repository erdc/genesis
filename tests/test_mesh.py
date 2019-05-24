import unittest
import cartopy.crs as ccrs
from genesis.mesh import Mesh


class TestMeshMain(unittest.TestCase):

    def test_mesh_instantiation(self):
        # set crs
        crs = ccrs.PlateCarree()
        # instantiate mesh object
        mesh_object = Mesh(crs=crs)

        self.assertIsInstance(mesh_object, Mesh)

