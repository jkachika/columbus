#!/usr/bin/python
#
# Author: Johnson Kachikaran (johnsoncharles26@gmail.com)
# Date: 19th May 2016
# BigQuery Service Python API:
# https://developers.google.com/resources/api-libraries/documentation/bigquery/v2/python/latest/index.html

"""
This file handles the bigquery service api access
"""
from pyedf.utils import *
from pyedf.security import CredentialManager


def _fetch_projects():
    bq_service = CredentialManager.get_big_query_service()
    projects = bq_service.projects()
    response = projects.list().execute()
    project_list = response["projects"]
    result = []
    for project in project_list:
        result.append(project["projectReference"]["projectId"])
    return result


def _fetch_datasets(project_id):
    bq_service = CredentialManager.get_big_query_service()
    datasets = bq_service.datasets()
    response = datasets.list(projectId=project_id).execute()
    dataset_list = response["datasets"]
    result = []
    for dataset in dataset_list:
        result.append(dataset["datasetReference"]["datasetId"])
    return result


def _fetch_tables(project_id, dataset_id):
    bq_service = CredentialManager.get_big_query_service()
    tables = bq_service.tables()
    response = tables.list(projectId=project_id, datasetId=dataset_id).execute()
    table_list = response["tables"]
    result = []
    for table in table_list:
        result.append(table["tableReference"]["tableId"])
    return result


def _describe_table(table_id, dataset_id, project_id):
    bq_service = CredentialManager.get_big_query_service()
    tables = bq_service.tables()
    response = tables.get(projectId=project_id, datasetId=dataset_id, tableId=table_id).execute()
    return response


def _execute_job(project_id, dataset_id, query, sync=False):
    bq_service = CredentialManager.get_big_query_service()
    jobs = bq_service.jobs()
    body = {  # uses queryCache feature by default
        "timeoutMs": 45 * 1000,
        "defaultDataset": {
            "projectId": project_id,
            "datasetId": dataset_id
        },
        "maxResults": 5000,
        "query": query
    }
    job = jobs.query(projectId=project_id, body=body).execute()
    job_id = job["jobReference"]["jobId"]
    response = {}
    result_rows = []
    if sync:  # synchronous call. will wait until the job is finished.
        while not job["jobComplete"]:
            job = jobs.getQueryResults(projectId=project_id, jobId=job_id, timeoutMs=45 * 1000,
                                       maxResults=5000).execute()
    if job["jobComplete"]:
        total_rows = int(job["totalRows"])
        cached = str(job["cacheHit"])
        fields = []
        python_types = {"INTEGER": int, "FLOAT": float, "STRING": str}
        for field in job["schema"]["fields"]:
            fields.append({"name": str(field["name"]), "type": str(field["type"])})
        more_results = True
        while more_results:
            for row in job["rows"]:
                result_row = []
                for index, field in enumerate(row["f"]):
                    result_row.append({"v": python_types.get(fields[index]["type"], str)(field["v"])})
                result_rows.append(result_row)
            page_token = job.get("pageToken", None)
            more_results = True if page_token else False
            if more_results:
                job = jobs.getQueryResults(projectId=project_id, jobId=job_id, timeoutMs=45 * 1000,
                                           pageToken=page_token, maxResults=5000).execute()
        response['fields'] = fields
        response['rows'] = result_rows
        response['total'] = total_rows
        response['cached'] = cached
    return response


def _parse_table_name(qualified_table_name):
    project_index = qualified_table_name.index(':')
    dataset_index = qualified_table_name.index('.')
    project_id = qualified_table_name[0:project_index]
    dataset_id = qualified_table_name[project_index + 1:dataset_index]
    table_id = qualified_table_name[dataset_index + 1:]
    return dict(tid=table_id, did=dataset_id, pid=project_id)


def get_all_tables():
    all_tables = []
    projects = _fetch_projects()
    for project in projects:
        datasets = _fetch_datasets(project)
        for dataset in datasets:
            tables = _fetch_tables(project_id=project, dataset_id=dataset)
            group = []
            for table in tables:
                group.append(str(table))
            all_tables.append({str(project + ":" + dataset): group})
    return all_tables


def get_features(qualified_table_name):
    try:
        metadata = _parse_table_name(qualified_table_name)
        table = _describe_table(table_id=metadata["tid"], dataset_id=metadata["did"], project_id=metadata["pid"])
        schema = table.get('schema', None)
        if schema is not None:
            features = schema.get('fields', None)
            if features is not None:
                types = {'INTEGER': 1, 'FLOAT': 3, 'STRING': 9}
                return [{str(feature['name']): types.get(feature['type'], 9)} for feature in sorted(features)]
    except BaseException as e:
        log_n_suppress(e)
    return []


def get_distinct_feature(feature, qualified_table_name, where=None, sync=False):
    table = _parse_table_name(qualified_table_name)
    if where is not None:
        query = "SELECT " + str(feature) + ", COUNT(" + str(feature) + ") AS count FROM [" + str(
            qualified_table_name) + "] WHERE " + where + " GROUP BY " + str(
            feature) + " ORDER BY " + str(feature) + " ASC"
    else:
        query = "SELECT " + str(feature) + ", COUNT(" + str(feature) + ") AS count FROM [" + str(
            qualified_table_name) + "] GROUP BY " + str(
            feature) + " ORDER BY " + str(feature) + " ASC"
    return _execute_job(project_id=table["pid"], dataset_id=table["did"], query=query, sync=sync)


def get_first_feature(feature, qualified_table_name):
    table = _parse_table_name(qualified_table_name)
    return _execute_job(project_id=table["pid"], dataset_id=table["did"],
                        query="SELECT " + str(feature) + " FROM [" + str(qualified_table_name) + "] WHERE " +
                              str(feature) + " IS NOT NULL LIMIT 1", sync=True)


def select_star(qualified_table_name, where=None, sync=False):
    table = _parse_table_name(qualified_table_name)
    if where is not None:
        query = "SELECT * FROM [" + str(qualified_table_name) + "] WHERE " + where
    else:
        query = "SELECT * FROM [" + str(qualified_table_name) + "]"
    return _execute_job(project_id=table["pid"], dataset_id=table["did"], query=query, sync=sync)


def get_query_results(qualified_table_name, query):
    table = _parse_table_name(qualified_table_name)
    return _execute_job(project_id=table["pid"], dataset_id=table["did"],
                        query=query, sync=True)

# print fetch_tables(project_id='earth-outreach', dataset_id='airview')
# pprint.pprint(get_features(table_id='chino_avall_two', dataset_id='airview', project_id='earth-outreach'))
# pprint.pprint(fetch_all_tables())
# pprint.pprint((fetch_distinct_feature(feature='date',
#                                       qualified_table_name='earth-outreach:airview.chino_avall_two')))
