import uuid
from collections import OrderedDict
import numpy as np
import pandas as pd
import xarray as xr
import logging

import param
import holoviews as hv
import geoviews as gv
from holoviews.operation.datashader import datashade, rasterize
import datashader as ds
from holoviews import opts

from .util import Projection


log = logging.getLogger('genesis')


class Mesh(param.Parameterized):
    name = param.String(
        default='default_mesh',
        doc='Name of the mesh.',
    )
    projection = param.ClassSelector(default=Projection(), class_=Projection)

    units = param.ObjectSelector(default='meters', objects=['meters', 'feet', 'none'])

    def __init__(self, **params):
        super(Mesh, self).__init__(**params)

    def read(self, *args, **kwargs):
        raise ChildProcessError('read method not set')

    def write(self, *args, **kwargs):
        raise ChildProcessError('write method not set')


class Unstructured(Mesh):
    tris = param.DataFrame(default=pd.DataFrame(data=[], columns=['v0', 'v1', 'v2']))
    verts = param.DataFrame(default=pd.DataFrame(data=[], columns=['x', 'y', 'z']))

    mesh_points = param.ClassSelector(default=gv.Points([]), class_=gv.Points)

    elements_toggle = param.Boolean(default=True, label='Elements', precedence=1)

    elevation_toggle = param.Boolean(default=False, label='Elevation', precedence=2)

    def __init__(self, **params):
        super(Unstructured, self).__init__(**params)

    def validate(self):
        if list(self.tris.columns) != ['v0', 'v1', 'v2']:
            raise RuntimeError('tris columns not set properly')
        if list(self.verts.columns) != ['x', 'y', 'z']:
            raise RuntimeError('verts columns not set properly')

    @param.depends('elements_toggle', watch=True)
    def view_elements(self):
        """ Method to display the mesh as wireframe elements"""
        raise ChildProcessError('view elements method not set')

    @param.depends('elevation_toggle', watch=True)
    def view_elevation(self):
        """ Method to display the mesh as continuous color contours"""
        raise ChildProcessError('view elevation method not set')

    def view_mesh(self):
        raise ChildProcessError('view mesh method not set')


class Unstructured2D(Unstructured):
    tri_mesh = param.ClassSelector(default=hv.TriMesh(data=()), class_=hv.TriMesh)

    def __init__(self, **params):
        super(Unstructured2D, self).__init__(**params)

    def view_elements(self, agg='any', line_color='black', cmap='black'):
        """ Method to display the mesh as wireframe elements"""
        if self.elements_toggle:
            # return datashade(self.tri_mesh.edgepaths.opts(line_color=line_color), aggregator=agg,
            #                  precompute=True, cmap=cmap)
            return datashade(self.tri_mesh.edgepaths.opts(opts.TriMesh(edge_cmap='yellow', edge_color='yellow')))
        else:
            return hv.Curve([])

    def view_elevation(self):
        """ Method to display the mesh as continuous color contours"""
        if self.elevation_toggle:
            return rasterize(self.tri_mesh, aggregator=ds.mean('z'), precompute=True)
        else:
            return hv.Curve([])

    def view_mesh(self, agg='any', line_color='black', cmap='black'):

        elements = self.view_elements(agg=agg, line_color=line_color, cmap=cmap)

        elevation = self.view_elevation()

        return elevation * elements


class Simulation(param.Parameterized):
    default = param.Boolean(default=True, precedence=-1)
    time = param.ObjectSelector()
    result_label = param.ObjectSelector()

    id = param.ClassSelector(default=uuid.uuid4(), class_=uuid.UUID, precedence=-1)

    sim_name = param.String(default='default_sim')

    def __init__(self, **params):
        super(Simulation, self).__init__(**params)
        self.xarr = xr.DataArray(data=())

    def read(self, *args,  **kwargs):
        raise ChildProcessError('read method not set')

    def write(self, *args,  **kwargs):
        raise ChildProcessError('write method not set')

    def solve(self, *args,  **kwargs):
        raise ChildProcessError('solve method not set')

    def set_result(self, model):
        self.default = False

        self.sim_name = model.attrs['project_name']

        self.xarr = model

        # precalculate the magnitudes of vector datasets
        for var in self.xarr.data_vars:
            # if this is a vector dataset
            if 'BEGVEC' in self.xarr[var].attrs.keys():
                # modify the attributes of the vector DataArray
                mag_attr = OrderedDict()
                for key in self.xarr[var].attrs.keys():
                    # change the key to scalar
                    if key == 'BEGVEC':
                        mag_attr['BEGSCL'] = ''
                    #  change the dimensions
                    elif key == 'DIM':
                        mag_attr[key] = 1
                    # copy everything else
                    else:
                        mag_attr[key] = self.xarr[var].attrs[key]

                # calculate magnitude
                mag = np.sqrt(self.xarr[var].data[:, :, 0] ** 2 +
                              self.xarr[var].data[:, :, 1] ** 2)  # dim: [time, nodes]

                # create magnitude DataArray
                mag_arr = xr.DataArray(
                    name=self.xarr[var].name + ' Magnitude',
                    coords=self.xarr[var].coords,
                    dims=('times', 'nodes_ids'),
                    data=mag,
                    attrs=mag_attr)
                # add DataArray into DataSet
                self.xarr[mag_arr.name] = mag_arr

        # get the labels of the result variables (that can be plotted with this class)
        labels = []
        for var in self.xarr.data_vars:
            # if model[var].dims == ('times', 'nodes_ids'):
            if 'times' in self.xarr[var].dims and 'nodes_ids' in self.xarr[var].dims:
                labels.append(var)

        if not labels:
            log.error('No results were found in dataset.')

        # sort the labels
        labels.sort()

        # set the list of labels into the parameter
        self.param.result_label.objects = labels
        # set the default label
        self.result_label = labels[0]

        # set the times into the parameter
        self.param.time.objects = list(self.xarr.times.data)
        # set the default time
        self.time = self.xarr.times.data[0]
