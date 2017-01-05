from __future__ import absolute_import
from datafs.managers.manager import BaseDataManager
from datafs.core.data_archive import DataArchive

import pytest
import os

#hack to get around installing these packages on Travis
has_special_dependencies = False

try:
	import netCDF4
	import xarray as xr
	import numpy as np
	import pandas as pd
	has_special_dependencies = True

except ImportError:
    pass

def requires_xarray(func):

	@pytest.mark.skipif(not has_special_dependencies, reason='Modules unable to install')
	def inner(*args, **kwargs):
		return func(*args, **kwargs)

	return inner






class TestVersionedMetadata(object):

	def test_versioned_metadata_open(self, api, opener, temporary_dir):

		fp = os.path.join(temporary_dir, 'test.txt')

		var = api.create_archive('my_archive')
		with open(fp, 'w+') as f:
			f.write(u'test test, this is a test')

		var.update(fp, version='patch', dependencies={'arch1': '0.1.0', 'arch2': '0.2.0'})

		assert len(var.get_history()[-1]['dependencies']) == 2

		with opener(var, 'w+', dependencies={'arch2': '0.1.2'}) as f:
			f.write(u'test and more test')


		assert var.get_history()[-1]['dependencies']['arch2'] == '0.1.2'


		assert len(var.get_dependencies(version='0.0.1')) == 2


	# @requires_xarray
	@pytest.mark.skipif(not has_special_dependencies, reason='Modules unable to install')
	def test_version_metadata_with_streaming(self,api,opener):

		np.random.seed(123)
		times = pd.date_range('2000-01-01', '2001-12-31', name='time')
		annual_cycle = np.sin(2 * np.pi * (times.dayofyear / 365.25 - 0.28))
		base = 10 + 15 * annual_cycle.reshape(-1, 1)


		tmin_values = base + 3 * np.random.randn(annual_cycle.size, 3)
		tmax_values = base + 3 * np.random.randn(annual_cycle.size, 3)


		ds = xr.Dataset({'tmin': (('time', 'location'), tmin_values), 
						 'tmax': (('time', 'location'), tmax_values)},
		                {'time': times, 'location': ['IA', 'IN', 'IL']})

	    

		var = api.create_archive('streaming_test')
		with var.get_local_path(bumpversion='patch', dependencies ={'arch1': '0.1.0', 'arch2': '0.2.0'}) as f:
			ds.to_netcdf(f)


		assert var.get_history()[-1]['dependencies']['arch2'] == '0.2.0'

		assert len(ds.tmin.shape) > 0

		tmin_values = base + 10 * np.random.randn(annual_cycle.size, 3)
		ds.update({'tmin': (('time', 'location'), tmin_values)})
		

		with var.get_local_path(bumpversion='patch', dependencies={'arch1': '0.1.0', 'arch2': '1.2.0'}) as f:
			with xr.open_dataset(f) as ds:

				mem = ds.load()
				ds.close()


			mem.to_netcdf(f)


		assert  var.get_history()[-1]['dependencies']['arch2'] == '1.2.0'
		assert  var.get_history()[-1]['checksum'] != var.get_history()[-2]['checksum']



