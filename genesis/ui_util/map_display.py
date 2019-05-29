import param
import colorcet as cc
from holoviews.plotting.util import process_cmap

"""
Map display options
"""


class ColormapOpts(param.Parameterized):
    colormap = param.ObjectSelector(default=cc.coolwarm, objects={
                     'Rainbow': cc.rainbow,
                     'Rainbow Reverse': process_cmap('rainbow_r'),
                     'Fire': cc.fire,
                     'Fire Reverse': process_cmap('fire_r'),
                     'Gray': cc.gray,
                     'Gray Reverse': process_cmap('gray_r'),
                     'CoolWarm': cc.coolwarm,
                     'WarmCool': process_cmap('coolwarm_r')
                     })


class DisplayRangeOpts(param.Parameterized):
    color_range = param.Range(default=(0.0, 10), bounds=(-10, 20))
