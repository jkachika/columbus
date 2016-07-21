import ee
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials

from columbus.settings import BQ_CREDENTIALS, EE_CREDENTIALS, CS_CREDENTIALS, FT_CREDENTIALS


class CredentialManager:
    _bq_service = None
    _earth_engine = None
    _ft_service = None
    _drive_service = None
    _storage_service = None

    def __init__(self):
        pass

    @staticmethod
    def get_big_query_service():
        if CredentialManager._bq_service is not None:
            return CredentialManager._bq_service
        else:
            scope = ['https://www.googleapis.com/auth/bigquery']
            credentials = ServiceAccountCredentials.from_json_keyfile_name(BQ_CREDENTIALS, scope)
            http_auth = credentials.authorize(Http())
            CredentialManager._bq_service = build(serviceName='bigquery', version='v2', http=http_auth,
                                                  credentials=credentials)
            return CredentialManager._bq_service

    @staticmethod
    def get_earth_engine():
        if CredentialManager._earth_engine is not None:
            return CredentialManager._earth_engine
        else:
            scope = ['https://www.googleapis.com/auth/earthengine']
            credentials = ServiceAccountCredentials.from_json_keyfile_name(EE_CREDENTIALS, scope)
            ee.Initialize(credentials)
            CredentialManager._earth_engine = ee
            return CredentialManager._earth_engine

    @staticmethod
    def get_fusion_tables_service():
        if CredentialManager._ft_service is not None:
            return CredentialManager._ft_service
        else:
            scopes = ['https://www.googleapis.com/auth/fusiontables',
                      'https://www.googleapis.com/auth/drive']
            credentials = ServiceAccountCredentials.from_json_keyfile_name(FT_CREDENTIALS, scopes)
            http_auth = credentials.authorize(Http())
            CredentialManager._ft_service = build(serviceName='fusiontables', version='v2', http=http_auth,
                                                  credentials=credentials)
            return CredentialManager._ft_service

    @staticmethod
    def get_drive_service():
        if CredentialManager._drive_service is not None:
            return CredentialManager._drive_service
        else:
            scope = ['https://www.googleapis.com/auth/drive']
            credentials = ServiceAccountCredentials.from_json_keyfile_name(FT_CREDENTIALS, scope)
            http_auth = credentials.authorize(Http())
            CredentialManager._drive_service = build(serviceName='drive', version='v3', http=http_auth,
                                                     credentials=credentials)
            return CredentialManager._drive_service

    @staticmethod
    def get_storage_service():
        if CredentialManager._storage_service is not None:
            return CredentialManager._storage_service
        else:
            scope = ['https://www.googleapis.com/auth/devstorage.full_control']
            credentials = ServiceAccountCredentials.from_json_keyfile_name(CS_CREDENTIALS, scope)
            http_auth = credentials.authorize(Http())
            CredentialManager._storage_service = build(serviceName='storage', version='v1', http=http_auth,
                                                       credentials=credentials)
            return CredentialManager._storage_service
