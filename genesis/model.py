import param
import logging

import panel as pn
import holoviews as hv
import geoviews as gv
from .util import Projection, GVTS
from holoviews import Path, Table
from holoviews.plotting.links import DataLink
from holoviews.streams import PolyDraw, PolyEdit, PointDraw
import cartopy.crs as ccrs


from earthsim.models.custom_tools import CheckpointTool, RestoreTool, ClearTool
from earthsim.links import VertexTableLink, PointTableLink
from earthsim.annotators import initialize_tools

from holoviews.operation.datashader import rasterize
from geoviews import Polygons, Points, TriMesh, Path as GeoPath
import datashader as ds


log = logging.getLogger('genesis')


class Model(param.Parameterized):
    """
    Allows drawing and annotating Points and Polygons using a bokeh
    DataTable.
    """
    projection = param.ClassSelector(default=Projection(), class_=Projection)

    wmts = param.ClassSelector(default=GVTS(), class_=GVTS)

    extent = param.NumericTuple(default=(-180, -85, 180, 85), doc="""
             Initial extent if no data is provided.""", precedence=-1)

    path_type = param.ClassSelector(default=Polygons, class_=Path, is_instance=False, doc="""
         The element type to draw into.""")

    polys = param.ClassSelector(class_=Path, precedence=-1, doc="""
         Polygon or Path element to annotate""")

    points = param.ClassSelector(class_=Points, precedence=-1, doc="""
         Point element to annotate""")

    height = param.Integer(default=500, doc="Height of the plot",
                           precedence=-1)

    width = param.Integer(default=900, doc="Width of the plot",
                          precedence=-1)

    poly_columns = param.List(default=['Group'], doc="""
        Columns to annotate the Polygons with.""", precedence=-1)

    vertex_columns = param.List(default=[], doc="""
        Columns to annotate the Polygons with.""", precedence=-1)

    table_height = param.Integer(default=150, doc="Height of the table",
                                 precedence=-1)

    table_width = param.Integer(default=400, doc="Width of the table",
                                precedence=-1)

    point_columns = param.List(default=['Size'], doc="""
        Columns to annotate the Points with.""", precedence=-1)

    num_points = param.Integer(default=100, doc="Number of Point objects at any given time", precedence=-1)

    num_polys = param.Integer(default=100, doc="Number of Poly objects at any given time", precedence=-1)

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

    def __init__(self, polys=None, points=None, crs=None, **params):
        super(Model, self).__init__(**params)
        self.conceptual_model = None

        # GENERIC ANNOTATIONS
        # set plot options
        self.plot_opts = dict(height=self.height, width=self.width)
        # set style options for tables
        self.table_style = dict(editable=True)
        # set plot options for tables
        self.table_opts = dict(width=self.table_width, height=self.table_height)

        # if polys are not given, set as empty list
        polys = [] if polys is None else polys
        # if points are not give, set as empty list
        points = [] if points is None else points
        # if crs is not given, set as Mercator
        self.crs = ccrs.GOOGLE_MERCATOR if crs is None else crs
        # add custom earthsim tools
        tools = [CheckpointTool(), RestoreTool(), ClearTool()]
        # create options dict
        opts = dict(tools=tools, finalize_hooks=[initialize_tools], color_index=None,
                    height=self.height, width=self.width)

        # if polys is not an element
        if not isinstance(polys, Path):
            # set poly data into an element
            polys = self.path_type(polys, crs=self.crs).options(**opts)
        # apply options to the element
        self.polys = polys.options(**opts)
        # add additional annotation columns to poly data
        for col in self.poly_columns:
            if col not in self.polys:
                self.polys = self.polys.add_dimension(col, 0, '', True)

        # create stream for drawing/creating/moving and assigning attributes of polygons
        self.poly_stream = PolyDraw(source=self.polys, data={}, show_vertices=True,
                                    num_objects=self.num_polys, drag=False, empty_value=self.default_value)
        # create stream for editing and assigning attributes of vertices of polygons
        self.vertex_stream = PolyEdit(source=self.polys, vertex_style={'nonselection_alpha': 0.5})

        # POLYGON ANNOTATIONS
        # # add additional annotation columns to poly data
        # for col in self.poly_columns:
        #     if col not in self.polys:
        #         self.polys = self.polys.add_dimension(col, 0, '', True)

        # # set the source of poly stream as polys
        # self.poly_stream.source = self.polys  # todo ISN'T THIS REPETITIVE?
        # # set the source of the vertex stream as polys
        # self.vertex_stream.source = self.polys  # todo ISN'T THIS REPETITIVE?

        if len(self.polys):
            poly_data = gv.project(self.polys).split()
            self.poly_stream.event(data={kd.name: [p.dimension_values(kd) for p in poly_data]
                                         for kd in self.polys.kdims})
        poly_data = {c: self.polys.dimension_values(c, expanded=False) for c in self.poly_columns}
        if len(set(len(v) for v in poly_data.values())) != 1:
            raise ValueError('poly_columns must refer to value dimensions '
                             'which vary per path while at least one of '
                             '%s varies by vertex.' % self.poly_columns)
        # create polygon table
        self.poly_table = Table(poly_data, self.poly_columns, []).opts(plot=self.table_opts, style=self.table_style)
        # link polys data to the polygon table
        self.poly_link = DataLink(source=self.polys, target=self.poly_table)
        # create polygon vertex table (# todo empty_value='black')
        self.vertex_table = Table([], self.polys.kdims, self.vertex_columns).opts(plot=self.table_opts, style=self.table_style)
        # link polys data to the polygon vertex table
        self.vertex_link = VertexTableLink(self.polys, self.vertex_table)

        # POINT ANNOTATIONS
        # if points is already an element
        if isinstance(points, Points):
            self.points = points
        else:
            # set as Points element
            self.points = Points(points, self.polys.kdims, crs=self.crs).options(**opts)
        # add additional annotation columns to point data
        for col in self.point_columns:
            if col not in self.points:
                self.points = self.points.add_dimension(col, 0, None, True)
        # set the source of the points as points
        self.point_stream = PointDraw(source=self.points, drag=True, data={}, num_objects=self.num_points,
                                      empty_value=self.default_value)
        # reproject the points from their source crs into PlateCarree
        projected = gv.project(self.points, projection=ccrs.PlateCarree())
        # create point table
        self.point_table = Table(projected).opts(plot=self.table_opts, style=self.table_style)
        # link point data to the point table
        self.point_link = PointTableLink(source=self.points, target=self.point_table)

    def update_points(self, update_points=True):
        #  todo I'm pretty sure this doesn't cover everything. the instantiation of the annotators needs to be broken back out and just called right here.
        if update_points:
            self.points = self.point_stream.element or self.points
            self.point_stream = PointDraw(source=self.points, drag=True, data={}, num_objects=self.num_points,
                                          empty_value=self.default_value)
            projected = gv.project(self.points, projection=ccrs.PlateCarree())
            self.point_table = hv.Table(projected).opts(plot=self.table_opts, style=self.table_style)
            self.point_link = PointTableLink(source=self.points, target=self.point_table)

    def update_polys(self, update_polys=True):
        #  todo I'm pretty sure this doesn't cover everything. the instantiation of the annotators needs to be broken back out and just called right here.
        if update_polys:
            self.polys = self.polys  # todo below here is broken, this is a temp placeholder
            # self.polys = self.poly_stream.element or self.polys
            # self.poly_stream = PolyDraw(source=self.polys, data={}, show_vertices=True,
            #                             num_objects=self.num_polys, drag=False, empty_value=self.default_value)
            # # create stream for editing and assigning attributes of vertices of polygons
            # self.vertex_stream = PolyEdit(source=self.polys, vertex_style={'nonselection_alpha': 0.5})
            #
            # # add additional annotation columns to poly data
            # for col in self.poly_columns:
            #     if col not in self.polys:
            #         self.polys = self.polys.add_dimension(col, 0, '', True)  # empty_value
            # if len(self.polys):
            #     poly_data = gv.project(self.polys).split()
            #     self.poly_stream.event(data={kd.name: [p.dimension_values(kd) for p in poly_data]
            #                                  for kd in self.polys.kdims})
            # poly_data = {c: self.polys.dimension_values(c, expanded=False) for c in self.poly_columns}
            #
            # # create polygon table
            # self.poly_table = Table(poly_data, self.poly_columns, []).opts(plot=self.table_opts, style=self.table_style)
            # # link polys data to the polygon table
            # self.poly_link = DataLink(source=self.polys, target=self.poly_table)
            # # create polygon vertex table
            # self.vertex_table = Table([], self.polys.kdims, self.vertex_columns).opts(plot=self.table_opts,
            #                                                                           style=self.table_style)
            # # link polys data to the polygon vertex table
            # self.vertex_link = VertexTableLink(self.polys, self.vertex_table)

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

    @param.depends('viewable_points', 'viewable_polys', 'wmts')
    def map_view(self, update_points=True, update_polys=True):
        self.update_points(update_points)
        self.update_polys(update_polys)
        if self.viewable_points:
            view_points = self.points.options(tools=['hover'], clone=False)
        else:
            view_points = hv.Points([])  # todo use empty layouts when they become available
        if self.viewable_polys:
            view_polys = self.polys.options(clone=False, line_width=5)
        else:
            view_polys = hv.Points([])  # todo use empty layouts when they become available

        return self.wmts.view() * view_polys * view_points

    def table_view(self, update_points=True, update_polys=True):
        self.update_points(update_points)
        self.update_polys(update_polys)
        return pn.Tabs(('Polygons', self.poly_table), ('Vertices', self.vertex_table),
                       ('Points', self.point_table), name='View Data')

    def panel(self):
        self.update_points()
        self.update_polys()
        return pn.Row(self.map_view(update_points=False), self.table_view(update_points=False))

    @param.depends('viewable_points', 'viewable_polys', 'wmts')
    def view(self):
        self.update_points()
        self.update_polys()
        if self.viewable_points:
            view_points = self.points.options(tools=['hover'], clone=False)
        else:
            view_points = hv.Points([])
        if self.viewable_polys:
            view_polys = self.polys.options(clone=False, line_width=5)
        else:
            view_polys = hv.Points([])
        return(self.wmts.view() * view_polys * view_points +
               self.poly_table + self.point_table + self.vertex_table).cols(1)

    @param.output(path=hv.Path)
    def path_output(self):
        return self.poly_stream.element
