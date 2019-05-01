import param
import cartopy.crs as ccrs


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



