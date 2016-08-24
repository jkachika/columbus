import logging

import ee
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client.client import Credentials
from oauth2client.client import FlowExchangeError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.service_account import ServiceAccountCredentials

from columbus.settings import BQ_CREDENTIALS, EE_CREDENTIALS, CS_CREDENTIALS, FT_CREDENTIALS
from columbus.settings import GD_CREDENTIALS, OAUTH2_CALLBACK


class GetCredentialsException(Exception):
    """Error raised when an error occurred while retrieving credentials.

    Attributes:
      authorization_url: Authorization URL to redirect the user to in order to
                         request offline access.
    """

    def __init__(self, authorization_url):
        """Construct a GetCredentialsException."""
        self.authorization_url = authorization_url


class CodeExchangeException(GetCredentialsException):
    """Error raised when a code exchange has failed."""


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
            scope = ['https://www.googleapis.com/auth/earthengine',
                     'https://www.googleapis.com/auth/devstorage.full_control']
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

    @staticmethod
    def get_drive_authorization_url(state):
        """Retrieve the authorization URL.

        Args:
          state: State for the authorization URL.
        Returns:
          Authorization URL to redirect the user to.
        """
        scopes = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/fusiontables']
        flow = flow_from_clientsecrets(GD_CREDENTIALS, scope=' '.join(scopes), redirect_uri=OAUTH2_CALLBACK)
        flow.params['access_type'] = 'offline'
        flow.params['approval_prompt'] = 'force'
        flow.params['state'] = state
        return flow.step1_get_authorize_url()

    @staticmethod
    def get_drive_credentials(authorization_code):
        """Exchange an authorization code for OAuth 2.0 credentials.

        Args:
          authorization_code: Authorization code to exchange for OAuth 2.0
                              credentials.
        Returns:
          oauth2client.client.OAuth2Credentials instance.
        Raises:
          CodeExchangeException: an error occurred.
        """
        scopes = ['https://www.googleapis.com/auth/drive.readonly']
        flow = flow_from_clientsecrets(GD_CREDENTIALS, ' '.join(scopes))
        flow.redirect_uri = OAUTH2_CALLBACK
        try:
            credentials = flow.step2_exchange(authorization_code)
            return credentials
        except FlowExchangeError, error:
            logging.error('An error occurred: %s', error)
            raise CodeExchangeException(None)

    @staticmethod
    def build_drive_service(json_credentials):
        credentials = Credentials.new_from_json(json_data=json_credentials)
        http_auth = credentials.authorize(Http())
        return build(serviceName='drive', version='v3', http=http_auth, credentials=credentials)

    @staticmethod
    def build_fusion_table_service(json_credentials):
        credentials = Credentials.new_from_json(json_data=json_credentials)
        http_auth = credentials.authorize(Http())
        return build(serviceName='fusiontables', version='v2', http=http_auth, credentials=credentials)
