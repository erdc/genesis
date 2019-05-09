import param
import cartopy.crs as ccrs
import geoviews as gv


class Projection(param.Parameterized):
    crs_label = param.ObjectSelector(default='UTM', objects=['Geographic', 'Mercator', 'UTM'], precedence=1)
    UTM_zone_hemi = param.ObjectSelector(default='North', objects=['North', 'South'], precedence=2)
    UTM_zone_num = param.Integer(52, bounds=(1, 60), precedence=3)

    @param.depends('crs_label', watch=True)
    def _watch_utm_projection(self):
        is_utm = self.crs_label == 'UTM'
        self.param.UTM_zone_hemi.constant = not is_utm
        self.param.UTM_zone_num.constant = not is_utm

    def get_crs(self):
        if self.crs_label == 'UTM':
            if self.UTM_zone_hemi == 'South':
                hemi = True
            else:
                hemi = False
            proj = ccrs.UTM(self.UTM_zone_num, southern_hemisphere=hemi)

        elif self.crs_label == 'Geographic':
            proj = ccrs.PlateCarree()

        elif self.crs_label == 'Mercator':
            proj = ccrs.GOOGLE_MERCATOR

        else:
            raise RuntimeError('Projection not found.')

        return proj

    def set_crs(self, crs):
        # ensure all params are enabled
        self.set_constant(value=False)

        if not isinstance(crs, ccrs.CRS):
            raise RuntimeError('Projection must be an instance of cartopy.crs')

        if isinstance(crs, ccrs.UTM):
            self.crs_label = 'UTM'
            self.UTM_zone_num = crs.proj4_params['zone']
            if 'south' in crs.proj4_init:
                self.UTM_zone_hemi = 'South'
            else:
                self.UTM_zone_hemi = 'North'

        elif isinstance(crs, ccrs.PlateCarree):
            self.crs_label = 'Geographic'

        elif crs is ccrs.GOOGLE_MERCATOR:
            self.crs_label = 'Mercator'

        else:
            raise RuntimeWarning('Projection {} not recognized.'.format(crs))

    def set_constant(self, value=True):
        """method to set all the parameters as enabled (value=False) or disabled (value=True)"""
        for p in self.param:
            self.param[p].constant = value


class WMTS(param.Parameterized):

    # Tile servers
    misc_servers = {'OpenStreetMap': 'http://c.tile.openstreetmap.org/{Z}/{X}/{Y}.png',
                    'Basemaps CartoCDN':
                        'https://s.basemaps.cartocdn.com/light_all/{Z}/{X}/{Y}.png',
                    'Stamen': 'http://tile.stamen.com/terrain/{Z}/{X}/{Y}.png'}

    arcgis_paths = {'World Imagery': 'World_Imagery/MapServer/tile/{Z}/{Y}/{X}',
                    'World Topo Map': 'World_Topo_Map/MapServer/tile/{Z}/{Y}/{X}',
                    'World Terrain Base': 'World_Terrain_Base/MapServer/tile/{Z}/{Y}/{X}',
                    'World Street Map': 'World_Street_Map/MapServer/tile/{Z}/{Y}/{X}',
                    'World Shaded Relief': 'World_Shaded_Relief/MapServer/tile/{Z}/{Y}/{X}',
                    'World Physical Map': 'World_Physical_Map/MapServer/tile/{Z}/{Y}/{X}',
                    'USA Topo Maps': 'USA_Topo_Maps/MapServer/tile/{Z}/{Y}/{X}',
                    'Ocean Basemap': 'Ocean_Basemap/MapServer/tile/{Z}/{Y}/{X}',
                    'NatGeo World Map': 'NatGeo_World_Map/MapServer/tile/{Z}/{Y}/{X}'}

    arcgis_urls = {k: 'https://server.arcgisonline.com/ArcGIS/rest/services/' + v
                   for k, v in arcgis_paths.items()}

    tile_urls = dict(misc_servers, **arcgis_urls)

    tile_server = param.ObjectSelector(default=tile_urls['World Imagery'], objects=tile_urls)

    @param.depends('tile_server')
    def element(self):
        return gv.WMTS(self.tile_server)

    def view(self):
        return gv.DynamicMap(self.element)


