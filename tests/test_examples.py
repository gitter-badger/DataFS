
from __future__ import absolute_import

import doctest
import datafs
import moto
from examples import (local, ondisk, s3, caching)
from examples.subclassing import client


def test_local():
    doctest.testmod(local)


def test_ondisk():

    has_special_dependencies = False

    try:
        import netCDF4
        import xarray as xr
        has_special_dependencies = True

    except ImportError:
        pass

    if has_special_dependencies:
        doctest.testmod(ondisk)


def test_s3():

    m = moto.mock_s3()
    mdb = moto.mock_dynamodb()
    m.start()
    mdb.start()

    try:
        doctest.testmod(s3)

    finally:
        # Stop mock
        m.stop()
        mdb.stop()


def test_caching():
    doctest.testmod(caching)


def test_subclassing():

    m = moto.mock_s3()
    mdb = moto.mock_dynamodb()
    m.start()
    mdb.start()

    try:
        doctest.testmod(client)

    finally:
        # Stop mock
        m.stop()
        mdb.stop()
