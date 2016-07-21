#!/usr/bin/python
#
# Author: Johnson Kachikaran (johnsoncharles26@gmail.com)
# Date: 19th May 2016
# Fusion Tables API:
# https://developers.google.com/resources/api-libraries/documentation/fusiontables/v2/python/latest/index.html

import csv
# import cloudstorage
import os

from lxml import etree
from googleapiclient.http import MediaIoBaseUpload
from geojson import FeatureCollection
from pykml.factory import KML_ElementMaker as KML

from pyedf.security import CredentialManager
from pyedf.utils import log_n_suppress, info, log_n_raise
from columbus.settings import TEMP_DIRPATH


def create_table(name, description, columns, data=None, share_with=None, admin=None):
    """
    Creates a fusion table for the given data and returns the table id.

    :param name: Name of the fusion table to create
    :param description: Description of the table to be created
    :param columns: List of dictionaries having properties name and type
    :param data: List of dictionaries (optional)
    :param share_with: Single email addreess string or  a List of user email addresses (gmail only)
                      to share the created fusion table
    :param admin: email address of the administrator who must become the owner of the created fusion table

    :rtype: String, the table id of the created fusion table
    """
    ft_service = CredentialManager.get_fusion_tables_service()
    drive_service = CredentialManager.get_drive_service()

    # converting column type to fusion table supported type
    for column in columns:
        column["type"] = str(column["type"]).upper()
        column["type"] = "NUMBER" if column["type"] in ["INTEGER", "FLOAT", "NUMBER"] \
            else "DATETIME" if column["type"] in ["TIMESTAMP", "DATETIME", "DATE"] \
            else "LOCATION" if column["type"] == "LOCATION" \
            else "STRING"

    body = dict(name=name, description=description, attribution="Created by Columbus Workflow Engine",
                attributionLink="http://www.cs.colostate.edu/~sangmi/", columns=columns, isExportable=True)
    table = ft_service.table()
    result = table.insert(body=body).execute()
    table_id = result["tableId"]
    info("table created with id - " + table_id)
    permissions = drive_service.permissions()
    # give write access to the admin for all the created fusion tables
    if admin is not None:
        permissions.create(fileId=table_id, body={"emailAddress": admin, "type": "user", "role": "writer"},
                           sendNotificationEmail=False).execute()
    permissions.create(fileId=table_id,
                       body={"type": "anyone", "role": "reader", "allowFileDiscovery": False}).execute()
    if share_with is not None:
        if isinstance(share_with, list):
            for user_email in share_with:
                if user_email.endswith("gmail.com"):
                    info("setting drive permissions for user - " + user_email)
                    permissions.create(fileId=table_id,
                                       body={"emailAddress": user_email, "type": "user", "role": "reader"},
                                       sendNotificationEmail=False).execute()
        if isinstance(share_with, str) and share_with.endswith("gmail.com"):
            info("setting drive permissions for user - " + share_with)
            permissions.create(fileId=table_id,
                               body={"emailAddress": share_with, "type": "user", "role": "reader"},
                               sendNotificationEmail=False).execute()
    if data is not None:
        keys = [column["name"] for column in columns]
        if not os.path.exists(TEMP_DIRPATH):
            os.makedirs(TEMP_DIRPATH)
        filename = TEMP_DIRPATH + str(table_id) + ".csv"
        # with cloudstorage.open(filename, 'w', content_type='application/octet-stream',
        #                        options={'x-goog-acl': 'project-private'}) as upload_file:
        with open(filename, 'wb') as upload_file:
            dict_writer = csv.DictWriter(upload_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(data)
        info("created temporary file for upload. making call to import rows.")
        # upload_fd = cloudstorage.open(filename, 'r')
        upload_fd = open(filename, 'rb')
        media_body = MediaIoBaseUpload(fd=upload_fd, mimetype="application/octet-stream")
        result = table.importRows(tableId=table_id, media_body=media_body, startLine=1, isStrict=True,
                                  encoding="UTF-8", delimiter=",").execute()
        info("imported - " + str(result["numRowsReceived"]) + " rows")
    return table_id


def create_ft_from_ftc(name, description, ftc, parties=None, admin=None):
    if isinstance(ftc, FeatureCollection) and ftc.get("columns", None) and isinstance(ftc["columns"], dict):
        fields = sorted(ftc["columns"].keys())
        columns = [{"name": str(field), "type": str(ftc["columns"][field])} for field in fields]
        columns.append(
            {"name": "x__geometry__x", "type": "LOCATION"})  # special property to access fusion table from maps API
        data = []
        for feature in ftc["features"]:
            if feature["type"] == "Feature":
                ft_prop = feature["properties"]
                if feature["geometry"]["type"] == "Point":
                    point = feature["geometry"]["coordinates"]
                    location = KML.Point(KML.coordinates(str(point[0]) + "," + str(point[1])))
                    ft_prop["x__geometry__x"] = etree.tostring(location)
                elif feature["geometry"]["type"] == "MultiPoint":
                    multipoint = feature["geometry"]["coordinates"]
                    geometries = [KML.Point(KML.coordinates(str(point[0]) + "," + str(point[1]))) for point in
                                  multipoint]
                    location = KML.MultiGeometry()
                    for geometry in geometries:
                        location.append(geometry)
                    ft_prop["x__geometry__x"] = etree.tostring(location)
                elif feature["geometry"]["type"] == "Polygon":
                    polygon = feature["geometry"]["coordinates"]
                    location = KML.Polygon()
                    for index in range(len(polygon)):
                        if index == 0:
                            location.append(KML.outerBoundaryIs(KML.LinearRing(KML.coordinates(
                                " ".join([str(point[0]) + "," + str(point[1]) for point in polygon[index]])))))
                        else:
                            location.append(KML.innerBoundaryIs(KML.LinearRing(KML.coordinates(
                                " ".join([str(point[0]) + "," + str(point[1]) for point in polygon[index]])))))
                    ft_prop["x__geometry__x"] = etree.tostring(location)
                elif feature["geometry"]["type"] == "MultiPolygon":
                    multipolygon = feature["geometry"]["coordinates"]
                    location = KML.MultiGeometry()
                    for polygon in multipolygon:
                        kml = KML.Polygon()
                        for index in range(len(polygon)):
                            if index == 0:
                                kml.append(KML.outerBoundaryIs(KML.LinearRing(KML.coordinates(
                                    " ".join([str(point[0]) + "," + str(point[1]) for point in polygon[index]])))))
                            else:
                                kml.append(KML.innerBoundaryIs(KML.LinearRing(KML.coordinates(
                                    " ".join([str(point[0]) + "," + str(point[1]) for point in polygon[index]])))))
                        location.append(kml)
                    ft_prop["x__geometry__x"] = etree.tostring(location)
                elif feature["geometry"]["type"] == "LineString":
                    linestring = feature["geometry"]["coordinates"]
                    location = KML.LineString(
                        KML.coordinates(" ".join([str(point[0]) + "," + str(point[1]) for point in linestring])))
                    ft_prop["x__geometry__x"] = etree.tostring(location)
                elif feature["geometry"]["type"] == "MultiLineString":
                    multilinestring = feature["geometry"]["coordinates"]
                    location = KML.MultiGeometry()
                    for linestring in multilinestring:
                        location.append(KML.LineString(
                            KML.coordinates(" ".join([str(point[0]) + "," + str(point[1]) for point in linestring]))))
                    ft_prop["x__geometry__x"] = etree.tostring(location)
                str_prop = {}
                for key in ft_prop.keys():
                    str_prop[str(key) if isinstance(key, unicode) else key] = str(ft_prop[key]) if isinstance(
                        ft_prop[key], unicode) else ft_prop[key]
                data.append(str_prop)
        return create_table(name=name, description=description, columns=columns, data=data, share_with=parties,
                            admin=admin)
    return None


def delete_table(table_id):
    try:
        ft_keys = str(table_id).split(',')
        for key in ft_keys:
            ft_service = CredentialManager.get_fusion_tables_service()
            table = ft_service.table()
            table.delete(tableId=key).execute()
    except BaseException as e:
        log_n_raise(e)
