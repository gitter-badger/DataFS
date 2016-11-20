from __future__ import absolute_import

from datafs.managers.manager import BaseDataManager
from datafs.services.service import DataService

import time

class DataAPI(object):

    DatabaseName = 'MyDatabase'
    DataTableName = 'DataFiles'

    TimestampFormat = '%Y%m%d-%H%M%S'

    def __init__(self, username, contact, manager=None, services={}, download_priority=None, upload_services=None):
        self.username = username
        self.contact = contact

        self.manager = manager
        self.services = services

        self._download_priority = download_priority
        self._upload_services = upload_services

    @property
    def download_priority(self):
        if self._download_priority is None:
            return self.services.keys()
        else:
            return self._download_priority

    @download_priority.setter
    def download_priority(self, value):
        self.download_priority = value

    @property
    def upload_services(self):
        if self._upload_services is None:
            return self.services.keys()
        else:
            return self._upload_services

    @upload_services.setter
    def upload_services(self, value):
        self.upload_services = value

    def attach_service(self, service_name, service):
        service.api = self
        self.services[service_name] = DataService(service)

    def attach_manager(self, manager):
        manager.api = self
        self.manager = manager

    def create_archive(self, archive_name, raise_if_exists=True, **metadata):
        self.manager.create_archive(archive_name, raise_if_exists=raise_if_exists, **metadata)

    def get_archive(self, archive_name):
        return self.manager.get_archive(archive_name)

    @property
    def archives(self):
        self.manager.get_archives()

    @archives.setter
    def archives(self):
        raise AttributeError('archives attribute cannot be set')

    @classmethod
    def create_timestamp(cls):
        '''
        Utility function for formatting timestamps

        Overload this function to change timestamp formats
        '''

        return time.strftime(cls.TimestampFormat, time.gmtime())

    @classmethod
    def create_version_id(cls, archive_name, filepath):
        '''
        Utility function for creating version IDs

        Overload this function to change version naming scheme
        '''

        return cls.create_timestamp()

