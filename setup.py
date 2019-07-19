from setuptools import setup, find_packages
setup(
    name="genesis",
    version="0.0.4",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'param',
        'panel',
        'holoviews',
        'geoviews',
        'cartopy',
        'earthsim',
        'numpy',
        'pandas',
        'xarray',
        'datashader',
        'colorcet',
        'jupyter'
    ],
    description="GeneSIs (Generic Simulation Interfaces) is a suite of universal base classes for numerical modeling",
    url="https://github.com/erdc/genesis",
)
