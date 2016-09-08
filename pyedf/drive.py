#!/usr/bin/python
#
# Author: Johnson Kachikaran (johnsoncharles26@gmail.com)
# Date: 7th August 2016
# Google Drive API:
# https://developers.google.com/drive/v3/reference/
# https://developers.google.com/resources/api-libraries/documentation/drive/v3/python/latest/
import io
import os

from googleapiclient.http import MediaIoBaseDownload

from columbus.settings import TEMP_DIRPATH
from pyedf.security import CredentialManager


def list_files(json_credentials, query=None, order_by=None, files=False):
    drive_service = CredentialManager.build_drive_service(json_credentials)
    response = drive_service.files().list(orderBy=order_by, q=query, pageSize=1000,
                                          fields='nextPageToken, files(id, name, mimeType, fileExtension, parents)').execute()
    result, resources, names, parents = [], [], {}, {}
    for drive_file in response.get('files', []):
        names[str(drive_file['id'])] = str(drive_file['name'])
        parents[str(drive_file['id'])] = drive_file.get('parents', [])
        resources.append({'id': drive_file['id'], 'name': drive_file['name'],
                          'parents': [str(parent) for parent in drive_file.get('parents', [])],
                          'mimeType': drive_file['mimeType']})
    while response.get('nextPageToken', None):
        drive_files = drive_service.files()
        response = drive_files.list(orderBy=order_by, q=query, pageSize=1000, pageToken=response['nextPageToken'],
                                    fields='nextPageToken, files(id, name, mimeType, fileExtension, parents)').execute()
        for drive_file in response.get('files', []):
            names[str(drive_file['id'])] = str(drive_file['name'])
            parents[str(drive_file['id'])] = drive_file.get('parents', [])
            resources.append({'id': drive_file['id'], 'name': drive_file['name'],
                              'parents': [str(parent) for parent in drive_file.get('parents', [])],
                              'mimeType': drive_file['mimeType']})
    for resource in resources:
        if resource['parents']:
            for parent in resource['parents']:
                path = str(names.get(parent, '')) + str('/') + str(resource['name'])
                while parents.get(parent, []):
                    parent = str(parents[parent][0])
                    path = str(names.get(parent, '')) + str('/') + path
                resource['name'] = path
                if files:
                    if resource['mimeType'] != 'application/vnd.google-apps.folder':
                        result.append(resource)
                else:
                    result.append(resource)
        else:
            if files:
                if resource['mimeType'] != 'application/vnd.google-apps.folder':
                    result.append(resource)
            else:
                result.append(resource)
    return result


def get_metadata(json_credentials, file_id):
    drive_service = CredentialManager.build_drive_service(json_credentials)
    files_service = drive_service.files().get(fileId=file_id,
                                              fields='id, mimeType, size, parents, kind, name, fileExtension, webContentLink')
    return files_service.execute()


def get_file_contents(json_credentials, file_id, meta_err=False):
    metadata = get_metadata(json_credentials, file_id)
    if (metadata.get('fileExtension', None) == 'csv' or metadata.get('mimeType', None) == 'text/csv') and metadata.get(
            'webContentLink', None):
        drive_service = CredentialManager.build_drive_service(json_credentials)
        if not os.path.exists(TEMP_DIRPATH):
            os.makedirs(TEMP_DIRPATH)
        file_path = TEMP_DIRPATH + str(file_id) + ".csv"
        if not os.path.exists(file_path):
            request = drive_service.files().get_media(fileId=file_id)
            fh = io.FileIO(file_path, mode='wb')
            downloader = MediaIoBaseDownload(fh, request, chunksize=1024 * 1024)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            fh.close()
        header, rows = [], []
        with open(file_path, 'rb') as csv_file:
            for line in csv_file.readlines():
                if not header:
                    header = [str(heading).strip() for heading in str(line).split(',')]
                else:
                    row = line.split(',')
                    row_dict = {}
                    for index, column in enumerate(row):
                        row_dict[header[index]] = str(column).strip()
                    rows.append(row_dict)
        return rows
    elif metadata.get('mimeType', None) == 'application/vnd.google-apps.fusiontable':
        ft_service = CredentialManager.build_fusion_table_service(json_credentials)
        query = ft_service.query()
        table = query.sql(sql='SELECT * FROM ' + str(file_id), hdrs=False).execute()
        result_rows = []
        columns = [str(column) for column in table['columns']]
        rows = table['rows']
        for row in rows:
            result_row = {}
            for index, cell in enumerate(row):
                result_row[columns[index]] = str(cell) if isinstance(cell, unicode) else cell
            result_rows.append(result_row)
        return result_rows
    elif meta_err:
        raise Exception('Unsupported file type for the file - ' + str(metadata['name'] + '.'))
    return []
