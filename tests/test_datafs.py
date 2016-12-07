#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_datafs
----------------------------------

Tests for `datafs` module.
"""

import pytest

from datafs.managers.manager_mongo import MongoDBManager
from datafs.managers.manager_dynamo import DynamoDBManager
from datafs import DataAPI
from fs.osfs import OSFS
from fs.tempfs import TempFS
from fs.s3fs import S3FS
from ast import literal_eval
import os
import tempfile
import shutil
import hashlib
import random
import itertools
import time
import boto
import moto
from freezegun import freeze_time
import moto
from moto import mock_dynamodb
from moto.dynamodb import dynamodb_backend


from six import b

try:
    unicode
except NameError:
    unicode = str


def get_counter():
    '''
    Counts up. Ensure we don't have name collisions
    '''

    counter = random.randint(0, 10000)
    while True:
        yield counter
        counter += 1

counter = get_counter()




@mock_dynamodb
def test_list_tables():
    name = 'my-table'
    dynamodb_backend.create_table(name, hash_key_attr="_id", hash_key_type="S")
    conn = boto.connect_dynamodb('the_key', 'the_secret')
    assert conn.list_tables() == ['my-table']



@pytest.yield_fixture(scope='function')
def manager(mgr_name):

    if mgr_name == 'mongo':

        manager_mongo = MongoDBManager(
                database_name='MyDatabase',
                table_name='DataFiles')
        
        yield manager_mongo

    elif mgr_name == 'dynamo':

        m = moto.mock_s3()
        mdb = moto.mock_dynamodb()

        m.start()
        mdb.start()

        name = 'my-table'
        dynamodb_backend.create_table(name, hash_key_attr="_id", hash_key_type="S")
        manager_dynamo = DynamoDBManager(
            table_name=name,
            session_args={
            'aws_access_key_id':'my_key',
            'aws_secret_access_key':'my_secret_key'},
            resource_args={'region_name':'us-east-1'})

        yield manager_dynamo

        m.stop()
        mdb.stop()

@pytest.yield_fixture(scope='function')
def filesystem(fs_name):

    if fs_name == 'OSFS':

        tmpdir = tempfile.mkdtemp()

        try:
            local = OSFS(tmpdir)

            yield local

            local.close()

        finally:
            try:
                shutil.rmtree(tmpdir)
            except (WindowsError, OSError, IOError):
                time.sleep(0.5)
                shutil.rmtree(tmpdir)


    elif fs_name == 'TempFS':

        local = TempFS()

        yield local

        local.close()

    elif fs_name == 'S3FS':

        m = moto.mock_s3()
        m.start()

        s3 = S3FS(
            'test-bucket', 
            aws_access_key='MY_KEY',
            aws_secret_key='MY_SECRET_KEY')

        yield s3

        s3.close()
        m.stop()



@pytest.fixture
def api(manager, filesystem):

    api = DataAPI(
        username='My Name',
        contact='my.email@example.com')

    api.attach_manager(manager)

    api.attach_authority('filesys', filesystem)

    return api



@pytest.fixture
def archive(api):
    '''
    Create a temporary archive for use in testing
    '''

    test_id = next(counter)

    archive_name = 'test_archive_{}'.format(test_id)

    api.create_archive(
        archive_name,
        metadata=dict(description='My test data archive #{}'.format(test_id)))

    return api.get_archive(archive_name)


string_tests =[
    '', 
    'another test', 
    '9872387932487913874031713470304', 
    os.linesep.join(['ajfdsaion', 'daf', 'adfadsffdadsf'])]

class TestHashFunction(object):


    def update_and_hash(self, arch, contents):
        '''
        Save contents to archive ``arch`` and return the DataAPI's hash value
        '''

        f = tempfile.NamedTemporaryFile(delete=False)

        try:
            f.write(contents)
            f.close()

            alg, apihash = arch.api.hash_file(f.name)
            arch.update(f.name)

        finally:
            os.remove(f.name)

        return apihash

    @pytest.mark.parametrize('contents', string_tests)
    def test_hashfuncs(self, archive, contents):
        '''
        Run through a number of iterations of the hash functions
        '''

        contents = unicode(contents)

        direct = hashlib.md5(contents.encode('utf-8')).hexdigest()
        apihash = self.update_and_hash(archive, contents)

        assert direct == apihash, 'Manual hash "{}" != api hash "{}"'.format(
            direct, apihash)
        assert direct == archive.latest_hash, 'Manual hash "{}" != archive hash "{}"'.format(
            direct, archive.latest_hash)

        # Try uploading the same file
        apihash = self.update_and_hash(archive, contents)

        assert direct == apihash, 'Manual hash "{}" != api hash "{}"'.format(
            direct, apihash)
        assert direct == archive.latest_hash, 'Manual hash "{}" != archive hash "{}"'.format(
            direct, archive.latest_hash)

        # Update and test again!

        contents = unicode((os.linesep).join(
            [contents, contents, 'line 3!' + contents]))

        direct = hashlib.md5(contents.encode('utf-8')).hexdigest()
        apihash = self.update_and_hash(archive, contents)

        with archive.open('rb') as f:
            current = f.read()

        assert contents == current, 'Latest updates "{}" !=  archive contents "{}"'.format(
            contents, current)

        assert direct == apihash, 'Manual hash "{}" != api hash "{}"'.format(
            direct, apihash)
        assert direct == archive.latest_hash, 'Manual hash "{}" != archive hash "{}"'.format(
            direct, archive.latest_hash)

        # Update and test a different way!

        contents = unicode((os.linesep).join([contents, 'more!!!', contents]))
        direct = hashlib.md5(contents.encode('utf-8')).hexdigest()

        with archive.open('wb+') as f:
            f.write(b(contents))

        with archive.open('rb') as f2:
            current = f2.read()

        assert contents == current, 'Latest updates "{}" !=  archive contents "{}"'.format(
            contents, current)

        assert direct == archive.latest_hash, 'Manual hash "{}" != archive hash "{}"'.format(
            direct, archive.latest_hash)



class TestArchiveCreation(object):
    
    def test_create_archive(self, api):
        archive_name = 'test_recreation_error'

        api.create_archive(archive_name, metadata = {'testval': 'my test value'})
        var = api.get_archive(archive_name)

        testval = var.metadata['testval']

        with pytest.raises(KeyError) as excinfo:
            api.create_archive(archive_name)
        
        assert "already exists" in str(excinfo.value)

        api.create_archive(archive_name, metadata = {'testval': 'a different test value'}, raise_if_exists=False)
        var = api.get_archive(archive_name)

        assert testval == var.metadata['testval'], "Test archive was incorrectly updated!"

        var.update_metadata({'testval': 'a different test value'})
        
        assert var.metadata['testval'] == 'a different test value', "Test archive was not updated!"

        # Test archive deletion
        var.delete()

        with pytest.raises(KeyError) as excinfo:
            api.get_archive(archive_name)



