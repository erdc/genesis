import param
import logging
import numpy as np

import panel as pn
import holoviews as hv
from .util import Projection, GVTS
import cartopy.crs as ccrs

from holoviews.operation.datashader import rasterize
from geoviews import Polygons, Points, TriMesh, Path as GeoPath
import datashader as ds
from earthsim.annotators import PolyAndPointAnnotator

import holoviews.plotting.bokeh
import geoviews.plotting.bokeh

log = logging.getLogger('genesis')


class Model(PolyAndPointAnnotator):
    """
    Allows drawing and annotating Points and Polygons using a bokeh
    DataTable.
    """
    projection = param.ClassSelector(default=Projection(), class_=Projection)

    wmts = param.ClassSelector(default=GVTS(), class_=GVTS)

    default_value = param.Number(default=-99999, doc="default value to set for new points and polys", precedence=-1)

    viewable_polys = param.Boolean(default=True, doc='Will the polygons be viewable in the map',
                                   label='Polygons', precedence=20)

    viewable_points = param.Boolean(default=True, doc='Will the points be viewable in the map',
                                    label='Points', precedence=21)
    # line cross section options
    resolution = param.Number(default=1000, doc="""
                Distance between samples in meters. Used for interpolation
                of the cross-section paths.""")
    aggregator = param.ClassSelector(class_=ds.reductions.Reduction,
                                     default=ds.mean(), precedence=-1)

    def __init__(self, *args, **params):
        super(Model, self).__init__(*args, **params)
        self.conceptual_model = None

    # line cross section
    def _gen_samples(self, geom):
        """
        Interpolates a LineString geometry to the defined
        resolution. Returning the x- and y-coordinates along
        with the distance along the path.
        """
        xs, ys, distance = [], [], []
        dist = geom.length
        for d in np.linspace(0, dist, int(dist / self.resolution)):
            point = geom.interpolate(d)
            xs.append(point.x)
            ys.append(point.y)
            distance.append(d)
        return xs, ys, distance

    # line cross section
    def _sample(self, obj, data):
        """
        Rasterizes the supplied object in the current region
        and samples it with the drawn paths returning an
        NdOverlay of Curves.

        Note: Because the function returns an NdOverlay containing
        a variable number of elements batching must be enabled and
        the legend_limit must be set to 0.
        """
        if self.poly_stream.data is None:
            path = self.polys
        else:
            path = self.poly_stream.element
        if isinstance(obj, TriMesh):
            vdim = obj.nodes.vdims[0]
        else:
            vdim = obj.vdims[0]
        if len(path) > 2:
            x_range = path.range(0)
            y_range = path.range(1)
        else:
            return hv.NdOverlay({0: hv.Curve([], 'Distance', vdim)})

        (x0, x1), (y0, y1) = x_range, y_range
        width, height = (max([min([(x1 - x0) / self.resolution, 500]), 10]),
                         max([min([(y1 - y0) / self.resolution, 500]), 10]))
        raster = rasterize(obj, x_range=x_range, y_range=y_range,
                           aggregator=self.aggregator, width=int(width),
                           height=int(height), dynamic=False)
        x, y = raster.kdims
        sections = []
        for g in path.geom():
            xs, ys, distance = self._gen_samples(g)
            indexes = {x.name: xs, y.name: ys}
            points = raster.data.sel_points(method='nearest', **indexes).to_dataframe()
            points['Distance'] = distance
            sections.append(hv.Curve(points, 'Distance', vdims=[vdim, x, y]))
        return hv.NdOverlay(dict(enumerate(sections)))

    # line cross section
    def _pos_indicator(self, obj, x):
        """
        Returns an NdOverlay of Points indicating the current
        mouse position along the cross-sections.

        Note: Because the function returns an NdOverlay containing
        a variable number of elements batching must be enabled and
        the legend_limit must be set to 0.
        """
        points = []
        elements = obj or []
        for el in elements:
            if len(el) < 1:
                continue
            p = Points(el[x], ['x', 'y'], crs=ccrs.GOOGLE_MERCATOR)
            points.append(p)
        if not points:
            return hv.NdOverlay({0: Points([], ['x', 'y'])})
        return hv.NdOverlay(enumerate(points))

    def map_view(self):

        if self.viewable_points:
            view_points = self.points.options(tools=['hover'], clone=False,
                                              height=self.height, width=self.width)
        else:
            view_points = hv.Curve([])  # todo use empty layouts when they become available
        if self.viewable_polys:
            view_polys = self.polys.options(clone=False, line_width=5,
                                            height=self.height, width=self.width)
        else:
            view_polys = hv.Curve([])  # todo use empty layouts when they become available

        return hv.DynamicMap(self.wmts.view) * view_polys * view_points

    def table_view(self):
        return pn.Tabs(('Polygons', self.poly_table), ('Vertices', self.vertex_table),
                       ('Points', self.point_table), name='View Data')

    def panel(self):
        return pn.Row(self.map_view(), self.table_view())

    def view(self):
        if self.viewable_points:
            view_points = self.points.opts(tools=['hover'], clone=False, active_tools=['pan', 'wheel_zoom'],
                                           height=self.height, width=self.width)
        else:
            view_points = hv.Curve([])
        if self.viewable_polys:
            view_polys = self.polys.opts(clone=False, line_width=5, active_tools=['pan', 'wheel_zoom'],
                                         height=self.height, width=self.width)
        else:
            view_polys = hv.Curve([])
        return(hv.DynamicMap(self.wmts.view) * view_polys * view_points +
               self.poly_table + self.point_table + self.vertex_table).cols(1)

    @param.output(path=hv.Path)
    def path_output(self):
        return self.poly_stream.element
