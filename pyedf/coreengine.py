import Queue
import cPickle as pickle
import collections
import logging
import math
import os
import shutil
import socket
import threading
import time
import traceback
import smtplib
from operator import itemgetter
from threading import Thread
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

import cachetools
import jsonpickle
import requests
from colorker import settings as colorker_settings
from colorker.comm import messaging
from colorker.core import Component, Combiner, EngineResource
from colorker.core import TargetInput, TargetHistory, Target, Query, FlowStatus
from colorker.security import ClientCredentials, ServiceAccount
from colorker.service import bigquery, drive, gee
from colorker.utils import caught
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.timezone import localtime
from geojson import FeatureCollection

from columbus import settings as master_settings
from pyedf.models import ClientSecurityModel, ServerSecurityModel
from pyedf.models import ComponentModel, ConditionModel, CombinerModel, WorkflowModel
from pyedf.models import HistoryModel, TargetHistoryModel, DataSourceModel, FlowStatusModel
from pyedf.models import TypeModel, PolygonModel, ActivityTrackerModel

logger = logging.getLogger(__name__)


def verify_flow(component_id, flow=None, visited=None):
    """
    Verifies whether the graph is a DAG, throws Exception otherwise
    :param component_id: id of the last component in the graph
    :param flow:
    :param visited:
    """
    flow = [] if flow is None else flow
    visited = [] if visited is None else visited
    cm = ComponentModel.objects.get(pk=component_id)
    if component_id in flow:
        raise Exception("Circular dependency exists between the components.\n Hint: Component " +
                        cm.name + " is repeated in the flow.")
    flow.append(component_id)
    for parent in cm.parents.all():
        if parent.id not in visited:
            verify_flow(parent.id, flow, visited)
    visited.append(flow.pop())


def get_target_dictionaries(component_id, root=False, non_root=False, combiners=False):
    def component_chain(comp_id, flow=None):
        if flow is None:
            flow = []
        cm = ComponentModel.objects.get(pk=comp_id)
        for parent in cm.parents.all():
            p = dict(id=parent.id, name=parent.name, root=parent.root)
            if p not in flow:
                component_chain(parent.id, flow)
        for combiner in cm.combiners.all():
            m = dict(id=combiner.id, name=combiner.name, type='combiner')
            if m not in flow:
                flow.append(m)
        c = dict(id=cm.id, name=cm.name, root=cm.root, type='component')
        flow.append(c)
        return flow

    verify_flow(component_id)
    comp_chain = component_chain(component_id)
    if root:
        root_components = []
        for comp_dict in comp_chain:
            if comp_dict['type'] == 'component' and comp_dict['root']:
                root_components.append(comp_dict)
        return root_components
    elif non_root:
        non_root_components = []
        for comp_dict in comp_chain:
            if comp_dict['type'] == 'component' and not comp_dict['root']:
                non_root_components.append(comp_dict)
        return non_root_components
    elif combiners:
        combiner_targets = []
        for comp_dict in comp_chain:
            if comp_dict['type'] == 'combiner':
                combiner_targets.append(comp_dict)
        return combiner_targets
    else:
        return comp_chain


def linearize_flow(component_id, flow=None):
    """
    pre-condition - graph must be a DAG
    topologically sorts the graph which ends at the given component_id. The result is stored in flow.
    :param component_id: id of the component
    :param flow: a list that holds the sorted result
    """
    if flow is None:
        flow = []
    cm = ComponentModel.objects.get(pk=component_id)
    for parent in cm.parents.all():
        parties = []
        if parent.visualizer:
            for party in parent.parties.all():
                parties.append(party.email)
        p = Component(id=parent.id, name=parent.name, code=parent.code, type=parent.type.identifier,
                      visualizer=parent.visualizer, root=parent.root, parties=parties)
        if p not in flow:
            linearize_flow(parent.id, flow)
    parties = []
    if cm.visualizer:
        for party in cm.parties.all():
            parties.append(party.email)
    c = Component(id=cm.id, name=cm.name, code=cm.code, type=cm.type.identifier,
                  visualizer=cm.visualizer, root=cm.root, parties=parties)
    c.sys_parents = [parent.id for parent in cm.parents.all()]
    c.sys_combiners = [combiner.id for combiner in cm.combiners.all()]
    for combiner in cm.combiners.all():
        combiner_parties = []
        if combiner.visualizer:
            for party in combiner.parties.all():
                combiner_parties.append(party.email)
        m = Combiner(id=combiner.id, name=combiner.name, flow_id=combiner.flow.id, flow_name=combiner.flow.name,
                     code=combiner.code, start=combiner.start, end=combiner.end, type=combiner.type.identifier,
                     visualizer=combiner.visualizer, parties=combiner_parties)
        if m not in flow:
            flow.append(m)
    flow.append(c)
    return flow


def create_and_copy(src, dst):
    dstdir = os.path.dirname(dst)
    if not os.path.exists(dstdir):
        os.makedirs(dstdir)  # create all directories, raise an error if it already exists
    shutil.copy2(src, dstdir)


@cachetools.func.lru_cache(maxsize=50, typed=False, lock=threading.RLock)
def get_element(fsid):
    fs = FlowStatusModel.objects.get(pk=fsid)
    pickle_path = fs.pickle
    gcs_pickle_path = fs.gcs_pickle
    return EngineResource.load(local_pickle=pickle_path, global_pickle=gcs_pickle_path,
                               user_settings=get_global_settings())


def get_columns(element, ftcindex):
    output = element.sys_output
    columns = []
    if element.type == 'csv' and isinstance(output, list) and len(output) > 0 and isinstance(output[0], dict):
        columns = sorted(output[0].keys())
        if element.csv is None:
            element.csv = element.sys_output
    elif element.type == 'ftc' and isinstance(output, FeatureCollection) and output.get(
            "columns", None) and isinstance(output["columns"], dict):
        columns = sorted(output["columns"].keys())
        if element.csv is None:
            element.csv = [feature["properties"] for feature in output["features"]]
    elif element.type == 'mftc' and isinstance(output, list) and len(output) > ftcindex:
        if isinstance(output[ftcindex], FeatureCollection) and output[ftcindex].get(
                "columns", None) and isinstance(output[ftcindex]["columns"], dict):
            columns = sorted(output[ftcindex]["columns"].keys())
            if element.csv is None or element.ftcindex != ftcindex:
                element.ftcindex = ftcindex
                element.sorted_dir = None
                element.sorted_key = None
                element.csv = [feature["properties"] for feature in output[ftcindex]["features"]]
    return columns


def non_nan(value):
    if not caught(float, value):
        if math.isnan(float(value)):
            return "NaN"
        elif value == float('inf'):
            return "+Infinity"
        elif value == float('-inf'):
            return "-Infinity"
        else:
            return value
    return value


def is_json_serializable(value):
    if not caught(float, value):
        if math.isnan(float(value)):
            return False
        elif value == float('inf'):
            return False
        elif value == float('-inf'):
            return False
        else:
            return True
    return True


def get_output(fsid, what, ftcindex=0, order_by=0, desc=False, fields=None):
    element = get_element(fsid)
    logger.info('getting ' + what + ' for ftcindex - ' + str(ftcindex))
    if what == 'columns':
        columns = get_columns(element=element, ftcindex=ftcindex)
        return [str(column).replace(' ', '_').replace('-', '_') for column in columns]
    elif what == 'data':
        direction = 'asc' if not desc else 'desc'
        columns = get_columns(element=element, ftcindex=ftcindex)
        if columns:
            csv = element.csv
            if element.sorted_key != columns[order_by] or element.sorted_dir != direction:
                logger.info("sorting the data either because the direction changed or key changed")
                element.csv = sorted(csv, key=itemgetter(columns[order_by]), reverse=desc)
                element.sorted_dir = direction
                element.sorted_key = columns[order_by]
            return [[non_nan(row[key]) for key in columns] for row in element.csv]
    elif what == 'download':
        columns = get_columns(element=element, ftcindex=ftcindex)
        rows = [columns]
        for row in element.csv:
            rows.append([row[key] for key in columns])
        return rows
    elif what == 'chart':
        direction = 'asc' if not desc else 'desc'
        csv = element.csv
        if element.sorted_key != order_by or element.sorted_dir != direction:
            logger.info("sorting the data either because the direction changed or key changed")
            element.csv = sorted(csv, key=itemgetter(order_by), reverse=desc)
            element.sorted_dir = direction
            element.sorted_key = order_by
        all_rows = []
        for row in element.csv:
            skip_row = False
            for key in fields:
                if not is_json_serializable(row[key]):
                    skip_row = True
            if not skip_row:
                all_rows.append([non_nan(row[key]) for key in fields])
        return all_rows
    return []


def clean_statistics(stats):
    if isinstance(stats, dict):
        for key in stats.keys():
            stats[key] = non_nan(stats[key])
    else:
        stats = "none"
    return stats


def delete_pickle(filename):
    try:
        os.remove(filename)
    except Exception as e:
        logger.error(e.message)
        logger.error(traceback.format_exc())


def get_collections(fsid):
    element = get_element(fsid)
    output = element.sys_output
    result = []
    if element.type == 'ftc' and isinstance(output, FeatureCollection):
        id = output.get("id", "untitled")
        stats = clean_statistics(output.get("statistics", "none"))
        result.append({'id': id, 'statistics': stats})
    elif element.type == 'mftc' and isinstance(output, list):
        for ftc in output:
            if isinstance(ftc, FeatureCollection):
                id = ftc.get("id", "untitled")
                stats = clean_statistics(ftc.get("statistics", "none"))
                result.append({'id': id, 'statistics': stats})
    return result


class Workflow(object):
    def __init__(self, id, name, flow_id, component_id, user):
        self.id = id  # id of the workflow instance
        self.flow_id = flow_id  # id of the workflow model
        self.name = name
        self.timestamp = timezone.now()
        self.user = user
        self.component_id = component_id
        verify_flow(component_id)
        self.elements = collections.deque(linearize_flow(component_id))

    def serialize(self, directory, filename, user_settings):
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(directory + '/' + filename, 'wb') as handle:
            pickle.dump(self, handle)
        fqfn = "%s/%s" % (directory, filename)
        return gee.upload_object(bucket=user_settings.get(colorker_settings.STORAGE.PERSISTENT.CLOUD, None),
                                 filename=fqfn, readers=[], owners=[], user_settings=user_settings,
                                 access=ServiceAccount.GCS)

    @staticmethod
    def load(local_pickle, global_pickle, user_settings):
        try:
            with open(local_pickle, 'rb') as handle:
                element = pickle.load(handle)
        except:
            names = global_pickle.split('#')
            gee.download_object(bucket=names[0], filename=names[1], out_file=local_pickle, user_settings=user_settings,
                                access=ServiceAccount.GCS)
            with open(local_pickle, 'rb') as handle:
                element = pickle.load(handle)
        return element


def get_user_settings(username):
    settings = dict()
    settings[colorker_settings.CREDENTIALS.CLIENT] = {}
    settings[colorker_settings.CREDENTIALS.SERVER] = {}
    user = User.objects.get(username=username)
    drive_cred = ClientSecurityModel.objects.filter(user=user, service='drive').first()
    if drive_cred:
        # do not convert the credentials to json. credentials are needed in string format
        settings[colorker_settings.CREDENTIALS.CLIENT][ClientCredentials.DRIVE] = drive_cred.credentials
    bq_cred = ServerSecurityModel.objects.filter(user=user, service=ServiceAccount.BIG_QUERY).first()
    if bq_cred:
        cred = jsonpickle.decode(bq_cred.credentials)
        settings[colorker_settings.CREDENTIALS.SERVER][ServiceAccount.BIG_QUERY] = cred
    ft_cred = ServerSecurityModel.objects.filter(user=user, service=ServiceAccount.DRIVE).first()
    if ft_cred:
        cred = jsonpickle.decode(ft_cred.credentials)
        settings[colorker_settings.CREDENTIALS.SERVER][ServiceAccount.DRIVE] = cred
        settings[colorker_settings.CREDENTIALS.SERVER][ServiceAccount.FUSION_TABLES] = cred
    ee_cred = ServerSecurityModel.objects.filter(user=user, service=ServiceAccount.EARTH_ENGINE).first()
    if ee_cred:
        cred = jsonpickle.decode(ee_cred.credentials)
        settings[colorker_settings.CREDENTIALS.SERVER][ServiceAccount.EARTH_ENGINE] = cred
        settings[colorker_settings.STORAGE.TEMPORARY.CLOUD] = ee_cred.bucket
    cs_cred = ServerSecurityModel.objects.filter(user=user, service=ServiceAccount.STORAGE).first()
    if cs_cred:
        cred = jsonpickle.decode(cs_cred.credentials)
        settings[colorker_settings.CREDENTIALS.SERVER][ServiceAccount.STORAGE] = cred
        settings[colorker_settings.STORAGE.READABLE.CLOUD] = cs_cred.bucket
    return settings


def get_global_settings():
    settings = {colorker_settings.STORAGE.TEMPORARY.LOCAL: master_settings.TEMP_DIRPATH,
                colorker_settings.STORAGE.TEMPORARY.CLOUD: master_settings.CS_TEMP_BUCKET,
                colorker_settings.STORAGE.PERSISTENT.LOCAL: master_settings.USER_DIRPATH,
                colorker_settings.STORAGE.PERSISTENT.CLOUD: master_settings.USER_GCSPATH,
                colorker_settings.CREDENTIALS.SERVER: {}
                }
    with open(master_settings.FT_CREDENTIALS, 'r') as json_cred:
        cred = jsonpickle.decode(json_cred.read())
        settings[colorker_settings.CREDENTIALS.SERVER][ServiceAccount.FUSION_TABLES] = cred
        settings[colorker_settings.CREDENTIALS.SERVER][ServiceAccount.DRIVE] = cred
    with open(master_settings.EE_CREDENTIALS, 'r') as json_cred:
        cred = jsonpickle.decode(json_cred.read())
        settings[colorker_settings.CREDENTIALS.SERVER][ServiceAccount.EARTH_ENGINE] = cred
    with open(master_settings.CS_CREDENTIALS, 'r') as json_cred:
        cred = jsonpickle.decode(json_cred.read())
        settings[colorker_settings.CREDENTIALS.SERVER][ServiceAccount.GCS] = cred
    return settings


def serialize_query(query, user_settings):
    queries = []
    if query['source'] == 'bigquery':
        if query.get('runType', None) == 'for-each':
            where = ConditionModel.objects.get(
                pk=int(query['constraint'])).get_string() if query['constraint'] else None
            tmp = bigquery.get_distinct_feature(feature=query['feature'], qualified_table_name=query['identifier'],
                                                sync=True, where=where, user_settings=user_settings)
            distinct = [(row[0]["v"], row[1]["v"]) for row in tmp["rows"]]
            for distinct_value in distinct:
                q = Query(source=query['source'], identifier=query['identifier'],
                          description="%d rows" % int(distinct_value[1]))
                q.set_attribute_filter(feature=query['feature'], primitive=query['primitive'], op="=",
                                       value=str(distinct_value[0]))
                queries.append(q)
        else:
            where = ConditionModel.objects.get(
                pk=int(query['constraint'])).get_string() if query['constraint'] else None
            value = "'%s'" % query['value'] if int(query['primitive']) == 9 else query['value']
            if where:
                where = "%s %s %s AND %s" % (query['feature'], query['op'], value, where)
            else:
                where = "%s %s %s" % (query['feature'], query['op'], value)
            result = bigquery.get_count_star(qualified_table_name=query['identifier'], where=where, sync=True,
                                             user_settings=user_settings)
            count = result["rows"][0][0]["v"]
            q = Query(source=query['source'], identifier=query['identifier'], description="%d rows" % int(count))
            q.set_attribute_filter(feature=query['feature'], primitive=query['primitive'], op=query['op'],
                                   value=query['value'])
            if query['constraint']:
                q.set_constraint(ConditionModel.objects.get(pk=int(query['constraint'])).get_string())
            queries.append(q)
    elif query['source'] == 'drive':
        metadata = drive.get_metadata(query['identifier'], user_settings)
        if metadata['mimeType'] == 'application/vnd.google-apps.folder':
            q = "(mimeType = 'application/vnd.google-apps.fusiontable' or fileExtension='csv') " \
                "and trashed = false and '%s' in parents" % str(query['identifier'])
            drive_files = drive.list_files(query=q, order_by='viewedByMeTime desc', files=True,
                                           user_settings=user_settings)
            for drive_file in drive_files:
                queries.append(Query(source=query['source'], identifier=drive_file['id'],
                                     description="%s%s" % (metadata['name'], drive_file['name'])))
        else:
            queries.append(Query(source=query['source'], identifier=metadata['id'], description=metadata['name']))
    elif query['source'] == 'combiner':
        combiner = CombinerModel.objects.get(pk=int(query['identifier']))
        start = localtime(combiner.start).strftime("%a, %d %b %Y - %I:%M:%S %p") if combiner.start else None
        end = localtime(combiner.start).strftime("%a, %d %b %Y - %I:%M:%S %p") if combiner.end else None
        desc = "Start: %s and End: %s" % (start, end)
        queries.append(Query(source=query['source'], identifier=combiner.flow.name, description=desc))
    elif query['source'] == 'galileo':
        q = Query(source=query['source'], identifier=query['identifier'], description=None)
        polygon_name = None
        if query.get('spatial', None):
            polygon = PolygonModel.objects.get(pk=int(query['spatial']))
            q.set_spatial_property(jsonpickle.decode(polygon.json))
            polygon_name = polygon.name
        year = query['year'] if query.get('year', None) else 'xxxx'
        month = query['month'] if query.get('month', None) else 'xx'
        day = query['day'] if query.get('day', None) else 'xx'
        hour = query['hour'] if query.get('hour', None) else 'xx'
        q.set_temporal_property('%s-%s-%s-%s' % (year, month, day, hour))
        where = None
        if query.get('constraint', None):
            condition = ConditionModel.objects.get(pk=int(query['constraint']))
            q.set_constraint(condition.get_json())
            where = condition.get_string()
        response = requests.post(master_settings.WEBSERVICE_HOST + "/blocks", json=q.__dict__)
        json_response = jsonpickle.decode(response.text)
        blocks = 0
        if query['runType'] == 'for':
            for group in json_response["result"]:
                blocks += len(json_response["result"][group])
            q.polygon = polygon_name
            q.where = where
            q.desc = "%d blocks" % blocks
            queries.append(q)
        else:
            for group in json_response["result"]:
                blocks = len(json_response["result"][group])
                q_dash = Query(source=query['source'], identifier=query['identifier'], description="%d blocks" % blocks)
                q_dash.set_spatial_property(q.spatial)
                q_dash.set_temporal_property(group[:group.rfind("-")])
                q_dash.set_attribute_filter('x__spatial__x', 9, '=', group[group.rfind("-") + 1:])
                q_dash.set_constraint(q.constraint)
                q_dash.polygon = polygon_name
                q_dash.where = where
                queries.append(q_dash)
    return queries


def find_pipelines(workflow):
    # TODO: Change the code to get the pipelines correctly - handling rhomboids
    # elements is already a topologically sorted list
    elements = list(workflow.elements)
    pipelines = []
    for element in elements:
        if isinstance(element, Component):
            if len(element.sys_parents) + len(element.sys_combiners) > 1:
                pipelines.append([element])
            else:
                if element.is_root:
                    pipelines.append([element])
                else:
                    for pipeline in pipelines:
                        for parent in pipeline:
                            if parent.id in element.sys_parents or parent.id in element.sys_combiners:
                                pipeline.append(element)
                                break
                        else:
                            continue
                        break
        else:
            pipelines.append([element])
    return pipelines


def fetch_data_from_galileo(assistant, pipeline, history, query_dict, data_source):
    query = Query.from_json(query_dict) if isinstance(query_dict, dict) else query_dict
    logger.debug("requesting galileo to address the query for workflow %d" % history.id)
    response = requests.post(master_settings.WEBSERVICE_HOST + "/featureset", json=query_dict)
    json_response = jsonpickle.decode(response.text)
    query.set_results(json_response)
    data_source.query = jsonpickle.encode(query)
    data_source.save()
    assistant.add_pipeline(history=history, pipeline=pipeline)


class SchedulerAssistant(Thread):
    def __init__(self, scheduler, supervisor):
        super(SchedulerAssistant, self).__init__()
        self.scheduler = scheduler
        self.supervisor = supervisor
        self.queue = Queue.Queue()
        self.__lock = threading.Condition()
        self.terminated = False

    def add_pipeline(self, history, pipeline):
        self.__lock.acquire()
        self.queue.put((history, pipeline))
        self.__lock.release()

    def terminate(self):
        self.terminated = True

    def is_terminated(self):
        return self.terminated

    def run(self):
        while not self.terminated:
            history, pipeline = self.queue.get()
            if history is None:
                break
            element = pipeline[0]
            try:
                if isinstance(element, Component) and element.is_root:
                    data_source = DataSourceModel.objects.get(history=history, target_id=element.id)
                    query_dict = jsonpickle.decode(data_source.query)
                    query = Query.from_json(query_dict) if isinstance(query_dict, dict) else query_dict
                    destinations = {}
                    if data_source.source == 'galileo':
                        if query.results is None or 'hostFileSize' not in query.results:
                            # async_req = threading.Thread(target=fetch_data_from_galileo,
                            #                              args=(self, pipeline, history, query_dict, data_source))
                            # async_req.start()
                            fetch_data_from_galileo(self, pipeline, history, query_dict, data_source)
                            continue
                        else:
                            json_response = query.results
                        all_workers = self.supervisor.get_all_workers()
                        workers = []
                        for host, file_size in json_response['hostFileSize'].items():
                            destinations[host] = file_size
                            for worker, worker_repr in all_workers:
                                if host == worker:
                                    workers.append((str(worker), int(worker_repr.port)))
                                    break
                        hostname, destination, wait = self.supervisor.find_best_destination(
                            history.user.username, destinations)
                        json_response["workers"] = workers
                        query.set_results(json_response)
                    else:
                        workers = self.supervisor.get_worker_names()
                        for worker in workers:
                            destinations[worker] = 10000000  # 10MB file size for unknown
                        hostname, destination, wait = self.supervisor.find_best_destination(
                            history.user.username, destinations)

                    if wait:
                        logger.info('deferring pipeline %d of workflow %d' % (element.id, history.id))
                        self.add_pipeline(history, pipeline)
                        continue

                    target_history = PipelineScheduler.build_target_history(
                        history=history, target=element, hostname=hostname)

                    targets = [Target(name=str(Component.__name__).lower() + "-%d" % element.id,
                                      query=query, target_input=None, target_type=Component.__name__,
                                      element=element, history=target_history)]
                    self.supervisor.make_assignment(hostname, history.user.username, history.id)
                    if len(pipeline) > 1:
                        for next_element in pipeline[1:]:
                            targets.append(
                                PipelineScheduler.build_target(history=history, element=next_element,
                                                               hostname=hostname))
                    settings = get_user_settings(history.user)
                    pid = history.id
                    uname = history.user.username
                    messaging.push(destination, messaging.Request(
                        messaging.RequestType.PIPELINE, messaging.PipelineRequest(pid, uname, targets, settings)))

                elif isinstance(element, Combiner):
                    combiner_flow = WorkflowModel.objects.get(pk=element.flow_id)
                    finished_runs = HistoryModel.objects.filter(flow=combiner_flow, status="Finished",
                                                                user=history.user)
                    if element.start is not None:
                        finished_runs = finished_runs.filter(start__gte=element.start)
                    if element.end is not None:
                        finished_runs = finished_runs.filter(finish__lte=element.end)
                    finished_runs = finished_runs.order_by('pk')
                    parent_keys = ["component-" + str(combiner_flow.component_id)]
                    local_pickles, global_pickles = {parent_keys[-1]: []}, {parent_keys[-1]: []}
                    destinations = {}
                    for run in finished_runs:
                        thm = TargetHistoryModel.objects.get(history=run,
                                                             target_id=combiner_flow.component_id)
                        local_pickles[parent_keys[-1]].append(str(thm.local_pickle))
                        global_pickles[parent_keys[-1]].append(str(thm.global_pickle))
                        pickle_size = destinations.get(thm.hostname, 0)
                        destinations[thm.hostname] = pickle_size + thm.pickle_size
                    hostname, destination, wait = self.supervisor.find_best_destination(
                        history.user.username, destinations)

                    if wait:
                        logger.info('deferring pipeline %d of workflow %d' % (element.id, history.id))
                        self.add_pipeline(history, pipeline)
                        continue

                    target_history = PipelineScheduler.build_target_history(
                        history=history, target=element, hostname=hostname)
                    targets = [Target(name=str(Combiner.__name__).lower() + "-%d" % element.id, query=None,
                                      target_input=TargetInput(
                                          parents=parent_keys, local_pickles=local_pickles,
                                          global_pickles=global_pickles),
                                      target_type=Combiner.__name__, element=element,
                                      history=target_history)]
                    self.supervisor.make_assignment(hostname, history.user.username, history.id)
                    if len(pipeline) > 1:
                        for element in pipeline[1:]:
                            targets.append(
                                PipelineScheduler.build_target(history=history, element=element,
                                                               hostname=hostname))
                    settings = get_user_settings(history.user)
                    pid = history.id
                    uname = history.user.username
                    messaging.push(destination,
                                   messaging.Request(messaging.RequestType.PIPELINE,
                                                     messaging.PipelineRequest(pid, uname, targets, settings)))

                else:
                    parents = pipeline[0].sys_parents[:]
                    parents.extend(pipeline[0].sys_combiners)
                    destinations = {}
                    for parent in parents:
                        parent_target_history = TargetHistoryModel.objects.filter(
                            history_id=history.id, target_id=parent).first()
                        if not parent_target_history or parent_target_history.status != 'Finished':
                            self.add_pipeline(history, pipeline)
                            break
                        else:
                            hostname = parent_target_history.hostname
                            pickle_size = destinations.get(hostname, 0)
                            destinations[hostname] = pickle_size + parent_target_history.pickle_size
                    else:
                        uname = history.user.username
                        hostname, destination, wait = self.supervisor.find_best_destination(
                            uname, destinations)
                        if wait:
                            logger.info('deferring pipeline %d of workflow %d' % (element.id, history.id))
                            self.add_pipeline(history, pipeline)
                            continue
                        targets = []
                        for element in pipeline:
                            targets.append(
                                PipelineScheduler.build_target(history=history, element=element,
                                                               hostname=hostname))
                        self.supervisor.make_assignment(hostname, history.user.username, history.id)
                        settings = get_user_settings(history.user)
                        pid = history.id
                        messaging.push(destination,
                                       messaging.Request(messaging.RequestType.PIPELINE,
                                                         messaging.PipelineRequest(pid, uname, targets, settings)))
            except Exception as e:
                logger.error("Something went wrong while processing the target. Details - %s" % e.message)
                exc_trace = traceback.format_exc()
                logger.error(exc_trace)
                thm = TargetHistoryModel.objects.filter(history=history, target_id=element.id).first()
                thm.status = "Failed"
                thm.save()
                FlowStatusModel(history_id=int(history.id), title="Component Failed", target_id=int(element.id),
                                result="failure", description=exc_trace, element=element.name).save()
                self.scheduler.add_event(history.id)
                self.supervisor.remove_assignment(thm.hostname, history.user.username, history.id)
                # self.scheduler.increment_qsize()
        return


class PipelineScheduler(Thread):
    def __init__(self, qsize, supervisor):
        super(PipelineScheduler, self).__init__()
        self.hostname = socket.getfqdn()
        self.deferred_queue = collections.deque()
        self.__event_queue = Queue.Queue()
        self.ready_queue = collections.deque()
        self.primary_queue = collections.deque()
        self.__secondary_queue = {}
        self.vacancy = qsize
        self.supervisor = supervisor
        self.lock = threading.Condition()
        self.__assistant = None
        self.__paused = False
        self.__waiting = False

    def add_event(self, hid):
        self.__event_queue.put(hid)

    def pause(self):
        self.__paused = True
        if self.__assistant and not self.__assistant.is_terminated():
            self.__assistant.terminate()
            self.__assistant.add_pipeline(history=None, pipeline=None)

    def resume(self, vacancy):
        self.__paused = False
        self.vacancy = vacancy
        self.__assistant = SchedulerAssistant(scheduler=self, supervisor=self.supervisor)
        self.__assistant.start()
        self.__resume_workflows()
        self.awake()
        # self.__assistant.start()

    def is_paused(self):
        return self.__paused

    def is_waiting(self):
        return self.__waiting

    def increment_qsize(self, increment=1):
        self.lock.acquire()
        self.vacancy += increment
        self.lock.release()

    def decrement_qsize(self, decrement=1):
        self.lock.acquire()
        self.vacancy -= decrement
        self.lock.release()

    def awake(self):
        self.lock.acquire()
        self.lock.notify()
        self.lock.release()

    @staticmethod
    def build_target_history(history, target, hostname):
        thm = TargetHistoryModel.objects.filter(history_id=history.id, target_id=target.id).first()
        if thm is None:
            thm = TargetHistoryModel(history=history, target_id=target.id, hostname=hostname, status="Scheduled")
            thm.save()
        else:
            thm.hostname = hostname
            thm.save()
        return TargetHistory(history_id=history.id, user_id=history.user.username, flow_id=history.flow.id,
                             flow_name=history.flow.name, target_id=target.id, status=thm.status,
                             timezone=master_settings.TIME_ZONE, user_email=history.user.email)

    @staticmethod
    def build_target(history, element, hostname):
        parent_keys = []
        local_pickles = {}
        global_pickles = {}
        if isinstance(element, Component):
            for parent in element.sys_parents:
                parent_keys.append('component-' + str(parent))
                target_history = TargetHistoryModel.objects.filter(history_id=history.id, target_id=parent).first()
                local_pickles[parent_keys[-1]] = []
                global_pickles[parent_keys[-1]] = []
                if target_history and target_history.local_pickle and target_history.global_pickle:
                    local_pickles[parent_keys[-1]].append(str(target_history.local_pickle))
                    global_pickles[parent_keys[-1]].append(str(target_history.global_pickle))
            for combiner in element.sys_combiners:
                parent_keys.append('combiner-' + str(combiner))
                target_history = TargetHistoryModel.objects.filter(history_id=history.id, target_id=combiner).first()
                local_pickles[parent_keys[-1]] = []
                global_pickles[parent_keys[-1]] = []
                if target_history and target_history.local_pickle and target_history.global_pickle:
                    local_pickles[parent_keys[-1]].append(str(target_history.local_pickle))
                    global_pickles[parent_keys[-1]].append(str(target_history.global_pickle))
        target_input = TargetInput(parents=parent_keys, local_pickles=local_pickles, global_pickles=global_pickles)
        return Target(name=str(element.__class__.__name__).lower() + "-" + str(element.id),
                      query=None, target_input=target_input, target_type=element.__class__.__name__, element=element,
                      history=PipelineScheduler.build_target_history(
                          history=history, target=element, hostname=hostname))

    def __resume_workflows(self):
        try:
            self.ready_queue = collections.deque()
            self.primary_queue = collections.deque()
            logger.info("attempting to resume workflows")
            histories = HistoryModel.objects.exclude(status__in=[
                "Pending", "Finished", "Failed"]).order_by('priority', 'created')
            logger.info("found " + str(len(histories)) + " unfinished workflows")
            global_settings = get_global_settings()
            for history in histories:
                thms = TargetHistoryModel.objects.filter(history=history).exclude(status="Finished")
                for thm in thms:
                    FlowStatusModel.objects.filter(history=history, target=thm.target).delete()
                thms.delete()
                logger.info(
                    "removed " + str(len(thms)) + " unfinished targets and their events for the workflow " + str(
                        history.flow.name))
                workflow = Workflow.load(history.local_pickle, history.global_pickle, global_settings)
                workflow.id = history.id
                workflow.pipelines = collections.deque(find_pipelines(workflow))
                history.status = 'Queued'
                history.save()
                self.primary_queue.append(workflow)
                # self.vacancy -= 1
            logger.info("Found %d resumable workflows. Added them to the primary queue. Vacancy = %d" % (len(
                self.primary_queue), self.vacancy))
        except Exception as e:
            logger.error("Some exception occurred while resuming the workflows. %s" % e.message)
            exc_message = traceback.format_exc()
            logger.error(exc_message)

    def __process_events(self):
        while True:
            try:
                hid = int(self.__event_queue.get_nowait())
                try:
                    if hid not in self.__secondary_queue:
                        continue
                    history = HistoryModel.objects.get(pk=hid)
                    workflow = self.__secondary_queue.get(hid)
                    pipelines = collections.deque([])
                    while len(workflow.pipelines) > 0:
                        pipeline = workflow.pipelines.popleft()
                        target_history = TargetHistoryModel.objects.filter(
                            history_id=history.id, target_id=pipeline[0].id).first()
                        if target_history:
                            if target_history.status == 'Failed' and history.status != 'Failed':
                                history.status = 'Failed'
                                history.finish = timezone.now()
                                history.save()
                                _thms = TargetHistoryModel.objects.filter(history=history)
                                for _thm in _thms:
                                    self.supervisor.remove_assignment(
                                        _thm.hostname, history.user.username, history.id)
                                self.__secondary_queue.pop(hid)
                                break
                            else:
                                if target_history.status == 'Finished':
                                    pipeline.pop(0)

                                if len(pipeline) > 0:
                                    pipelines.append(pipeline)
                                else:
                                    self.supervisor.remove_assignment(
                                        target_history.hostname, history.user.username, history.id)
                        else:
                            element = pipeline[0]
                            if isinstance(element, Component) and not element.is_root:
                                parents = element.sys_parents[:]
                                parents.extend(element.sys_combiners)
                                for parent in parents:
                                    parent_target_history = TargetHistoryModel.objects.filter(
                                        history_id=history.id, target_id=parent).first()
                                    if not parent_target_history or parent_target_history.status != 'Finished':
                                        break
                                else:
                                    TargetHistoryModel(history=history, target_id=pipeline[0].id,
                                                       hostname=self.hostname, status="Scheduled").save()
                                    self.__assistant.add_pipeline(history=history, pipeline=pipeline)
                    else:
                        if len(pipelines) > 0:
                            while len(pipelines) > 0:
                                workflow.pipelines.append(pipelines.popleft())
                        else:
                            history.status = 'Finished'
                            history.finish = timezone.now()
                            history.save()
                            self.__secondary_queue.pop(hid)
                except BaseException as e:
                    logger.error("Failed to process the event %d - %s" % (hid, e.message))
                    logger.error(traceback.format_exc())
            except Queue.Empty:
                break

    def run(self):
        last_user = 0
        self.__assistant = SchedulerAssistant(scheduler=self, supervisor=self.supervisor)
        self.__assistant.start()
        self.__resume_workflows()
        global_settings = get_global_settings()
        while True:
            try:
                self.lock.acquire()
                while self.is_paused():
                    self.__waiting = True
                    self.lock.wait()

                self.__waiting = False
                self.lock.release()

                users = User.objects.all().order_by('username')
                usernames = [user.username for user in users]
                pending_workflows = []
                pending_flow_count = 0
                queued_flow_count = HistoryModel.objects.filter(status='Queued').count()
                while queued_flow_count + pending_flow_count < self.vacancy:
                    no_more_flows = True
                    for index in range(last_user, last_user + len(users)):
                        user = users[index % len(users)]
                        user_history = HistoryModel.objects.filter(status='Pending', user=user).order_by(
                            '-priority', 'created').first()
                        if user_history is not None:
                            user_history.status = 'Queued'
                            user_history.start = timezone.now()
                            user_history.save()
                            pending_workflows.append(user_history)
                            pending_flow_count += 1
                            no_more_flows = False
                    if no_more_flows:
                        break

                pending_workflows.sort(key=lambda x: x.created)

                for history in pending_workflows:
                    workflow = Workflow.load(history.local_pickle, history.global_pickle, global_settings)
                    workflow.id = history.id
                    self.ready_queue.append(workflow)
                    # self.vacancy -= 1
                    try:
                        last_user = usernames.index(history.user.username)
                    except:
                        logger.error(
                            'User %s not found. Resetting the last user to zero.' % history.user.username)

                while self.ready_queue:
                    workflow = self.ready_queue.popleft()
                    workflow.pipelines = collections.deque(find_pipelines(workflow))
                    self.primary_queue.append(workflow)

                self.lock.acquire()
                if len(self.primary_queue) == 0:
                    logger.info("Scheduler is going to sleep")
                    self.lock.wait()  # Go to sleep until the Supervisor awakes
                    logger.info("Scheduler is back up and running")
                self.lock.release()

                self.__process_events()

                while self.primary_queue:
                    if self.is_paused():
                        break
                    workflow = self.primary_queue.popleft()
                    history = HistoryModel.objects.get(pk=workflow.id)
                    pipelines = collections.deque([])
                    while len(workflow.pipelines) > 0:
                        if self.is_paused():
                            break
                        pipeline = workflow.pipelines.popleft()
                        if (isinstance(pipeline[0], Component) and pipeline[0].is_root) or isinstance(
                                pipeline[0], Combiner):
                            thm = TargetHistoryModel(
                                history=history, target_id=pipeline[0].id, hostname=self.hostname, status="Scheduled")
                            thm.save()
                            self.__assistant.add_pipeline(history=history, pipeline=pipeline)
                        pipelines.append(pipeline)
                    else:
                        while len(pipelines) > 0:
                            workflow.pipelines.append(pipelines.popleft())
                        self.__secondary_queue[history.id] = workflow
                        # self.increment_qsize()
            except BaseException as e:
                logger.error(
                    "Some exception occurred in the scheduler - %s. Scheduler is still up and running." % e.message)
                exc_message = traceback.format_exc()
                logger.error(exc_message)


class SupervisorAssistant(Thread):
    def __init__(self, hostname, supervisor):
        super(SupervisorAssistant, self).__init__()
        self.supervisor = supervisor
        self.workers = Queue.Queue()
        self.hostname = hostname

    def add_worker(self, worker, address):
        self.workers.put((worker, address))

    def run(self):
        total_requests = 0
        update_count = 0
        snapshot_count = 0
        while True:
            worker, address = self.workers.get()
            total_requests += 1
            if total_requests % 50 == 0:
                logger.info("%s total requests = %d" % (self.hostname, total_requests))
            try:
                msg = messaging.recv(worker)
                if msg[messaging.Request.TYPE] == messaging.RequestType.CONFIG:
                    global_settings = get_global_settings()
                    response = messaging.SupervisorConfigResponse(container_size=master_settings.CONTAINER_SIZE_MB,
                                                                  global_settings=global_settings)
                    messaging.send(worker, response)
                    msg = messaging.recv(worker)
                    port_num = msg[messaging.Request.BODY][messaging.WorkerConfigResponse.PORT_NUMBER]
                    num_cores = msg[messaging.Request.BODY][messaging.WorkerConfigResponse.LOGICAL_CORES]
                    num_slots = msg[messaging.Request.BODY][messaging.WorkerConfigResponse.NUM_SLOTS]
                    available_mem = msg[messaging.Request.BODY][messaging.WorkerConfigResponse.AVAILABLE_MEMORY]
                    total_mem = msg[messaging.Request.BODY][messaging.WorkerConfigResponse.TOTAL_MEMORY]
                    pid = msg[messaging.Request.BODY][messaging.WorkerConfigResponse.PROCESS_ID]
                    host_name = socket.getfqdn(address[0])
                    self.supervisor.update_workers(
                        hostname=host_name, ipaddr=address[0], port=port_num, cores=num_cores, pid=pid,
                        available_mem=available_mem, total_mem=total_mem, slots=num_slots)
                elif msg[messaging.Request.TYPE] == messaging.RequestType.UPDATE:
                    update_count += 1
                    model = msg[messaging.Request.BODY][messaging.ModelUpdateRequest.MODEL]
                    update = msg[messaging.Request.BODY][messaging.ModelUpdateRequest.UPDATE]
                    if model == TargetHistory.__name__:
                        thm = TargetHistoryModel.objects.filter(history_id=int(update[TargetHistory.HISTORY_ID]),
                                                                target_id=int(update[TargetHistory.TARGET_ID])).first()
                        thm.status = update[TargetHistory.STATUS]
                        thm.save()
                        if thm.status == "Retry":
                            FlowStatusModel.objects.filter(history_id=int(update[TargetHistory.HISTORY_ID]),
                                                           target_id=int(update[TargetHistory.TARGET_ID])).delete()
                        history = HistoryModel.objects.get(id=thm.history_id)
                        if thm.status == 'Running' and history.status == 'Queued':
                            history.status = 'Running'
                            history.save()
                        elif thm.status == 'Failed':
                            history.status = 'Failed'
                            history.finish = timezone.now()
                            history.save()
                        self.supervisor.add_scheduler_event(history.id)
                        self.supervisor.awake_scheduler()
                    elif model == FlowStatus.__name__:
                        fsm = FlowStatusModel(
                            history_id=int(update[FlowStatus.HISTORY_ID]), title=update[FlowStatus.TITLE],
                            target_id=int(update[FlowStatus.TARGET_ID]), result=update[FlowStatus.RESULT],
                            description=update[FlowStatus.DESCRIPTION],
                            element=update[FlowStatus.ELEMENT])
                        thm = TargetHistoryModel.objects.filter(history_id=int(update[FlowStatus.HISTORY_ID]),
                                                                target_id=int(update[FlowStatus.TARGET_ID])).first()
                        if fsm.result == "Failed":
                            thm.status = fsm.result
                            thm.save()
                        if update[FlowStatus.LOCAL_PICKLE]:
                            fsm.pickle = update[FlowStatus.LOCAL_PICKLE]
                            thm.local_pickle = fsm.pickle
                        if update[FlowStatus.GLOBAL_PICKLE]:
                            fsm.gcs_pickle = update[FlowStatus.GLOBAL_PICKLE]
                            thm.global_pickle = fsm.gcs_pickle
                        if update[FlowStatus.PICKLE_SIZE]:
                            thm.pickle_size = long(update[FlowStatus.PICKLE_SIZE])
                        if update[FlowStatus.OUTPUT_TYPE]:
                            fsm.type = TypeModel.objects.filter(identifier=update[FlowStatus.OUTPUT_TYPE]).first()
                            thm.type = fsm.type
                        if update[FlowStatus.FUSION_TABLE_KEYS]:
                            fsm.ftkey = update[FlowStatus.FUSION_TABLE_KEYS]
                            thm.ftkey = fsm.ftkey
                        if update[FlowStatus.REFERENCE]:
                            fsm.ref = update[FlowStatus.REFERENCE]
                        fsm.save()
                        thm.save()
                elif msg[messaging.Request.TYPE] == messaging.RequestType.SNAPSHOT:
                    snapshot_count += 1
                    snapshot = msg[messaging.Request.BODY]
                    hostname = snapshot[messaging.WorkerSnapshotResponse.HOSTNAME]
                    utilization = snapshot[messaging.WorkerSnapshotResponse.UTILIZATION]
                    system_time = snapshot[messaging.WorkerSnapshotResponse.SYSTEM_TIME]
                    user_wr_ratio = snapshot[messaging.WorkerSnapshotResponse.USER_WR_RATIO]
                    if self.supervisor.is_recording():
                        tracked = self.supervisor.get_host_utilization(hostname)
                        if utilization > 0:
                            user_running = snapshot[messaging.WorkerSnapshotResponse.USER_RUNNING]
                            for user, stats in user_running.items():
                                num_processes = stats['num_processes']
                                cpu_percent = stats['cpu_percent']
                                mem_percent = stats['memory_percent']
                                ActivityTrackerModel(instant=system_time, hostname=hostname, tracked=tracked,
                                                     reported=utilization, username=user, processes=num_processes,
                                                     cpu=cpu_percent, memory=mem_percent,
                                                     json=jsonpickle.encode(snapshot)).save()
                        else:
                            ActivityTrackerModel(instant=system_time, hostname=hostname, tracked=tracked, reported=0,
                                                 username='system', processes=0, cpu=0, memory=0,
                                                 json=jsonpickle.encode(snapshot)).save()
                    self.supervisor.update_snapshot(hostname, utilization, user_wr_ratio)
                elif msg[messaging.Request.TYPE] == messaging.RequestType.EMAIL:
                    request = msg[messaging.Request.BODY]
                    from_ = request[messaging.WorkerEmailRequest.FROM]
                    sender = User.objects.filter(username=from_).first()
                    to = request[messaging.WorkerEmailRequest.TO]
                    subject = request[messaging.WorkerEmailRequest.SUBJECT]
                    plain = request[messaging.WorkerEmailRequest.PLAIN]
                    html = request[messaging.WorkerEmailRequest.HTML]
                    if sender is not None:
                        self.supervisor.send_email(
                            sender=sender.email, receivers=to, subject=subject, plain=plain, html=html)
            except:
                logger.error("Something went wrong while handling the message from worker")
                logger.error(traceback.format_exc())
            finally:
                worker.close()
                if update_count % 50 == 0:
                    logger.info("%s update requests = %d" % (self.hostname, update_count))
                if snapshot_count % 50 == 0:
                    logger.info("%s snapshot requests = %d" % (self.hostname, snapshot_count))


class NoWorkerFound(Exception):
    pass


class Singleton(type):
    """
    From the stackoverflow post
    http://stackoverflow.com/a/6798042/4582603
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Supervisor(Thread):
    __metaclass__ = Singleton

    def __init__(self):
        super(Supervisor, self).__init__()
        self.__expected_workers = []
        self.__expected_workers = master_settings.WORKERS
        self.__workers = {}
        self.__lock = threading.Condition()
        self.__scheduler = PipelineScheduler(qsize=0, supervisor=self)
        self.__scheduler_invoked = False
        self.__snapshots = {}
        self.__assignments = {}
        self.__record = False
        logger.info("Supervisor instantiated. Pipeline scheduler is not invoked (isAlive=%s)" % str(
            self.__scheduler.isAlive()))
        logger.info("Expected workers - %s " % self.__expected_workers)
        self.__assistants = {}
        # self.__assistant = SupervisorAssistant(supervisor=self)
        # logger.info("Assistant instantiated")

    def is_recording(self):
        return self.__record

    def record_activity(self):
        self.__record = True

    def stop_recording(self):
        self.__record = False

    def reset_assignments(self):
        self.__lock.acquire()
        for hostname in self.__expected_workers:
            self.__assignments[hostname] = set()
        self.__lock.release()

    def make_assignment(self, hostname, user, hid):
        self.__lock.acquire()
        self.__assignments[hostname].add("%s#%d" % (user, hid))
        self.__lock.release()

    def remove_assignment(self, hostname, user, hid):
        self.__lock.acquire()
        try:
            self.__assignments[hostname].remove("%s#%d" % (user, hid))
        except:
            pass
        self.__lock.release()

    def __start_scheduler(self):
        for hostname in self.__expected_workers:
            if hostname not in self.__workers:
                break
        else:
            if not self.__scheduler_invoked:
                self.__scheduler.start()
                self.__scheduler_invoked = True
                logger.info("All workers connected. Starting the pipeline scheduler")
                self.reset_assignments()
            if self.__scheduler.is_paused():
                logger.info("All workers connected. Resuming scheduler operations")
                vacancy = 0
                for worker, worker_repr in self.get_all_workers():
                    vacancy += worker_repr.slots
                self.__scheduler.resume(vacancy)
                self.reset_assignments()

    def update_workers(self, hostname, ipaddr, port, cores, available_mem, total_mem, pid, slots):
        self.__lock.acquire()
        if hostname in self.__workers:
            previous_slots = self.__workers[hostname].slots
            self.__scheduler.decrement_qsize(previous_slots)
        worker_repr = collections.namedtuple('WorkerRepr', [
            'address', 'port', 'cores', 'available', 'total', 'pid', 'slots'])
        self.__workers[hostname] = worker_repr(ipaddr, port, cores, available_mem, total_mem, pid, slots)
        self.__scheduler.increment_qsize(slots)
        self.__scheduler.awake()
        self.__lock.release()
        self.__start_scheduler()

    def update_snapshot(self, hostname, utilization, user_wr_ratio):
        try:
            self.__lock.acquire()
            self.__snapshots[hostname] = (utilization, user_wr_ratio)
        finally:
            self.__lock.release()

    def run(self):
        logger.info("Supervisor started")
        self.reset_assignments()
        import psutil
        master = psutil.Process(pid=os.getpid())
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('', master_settings.SUPERVISOR_PORT))
        server.listen(5)
        num_connections = 0
        while True:
            try:
                worker, address = server.accept()
                if address[0] not in self.__assistants:
                    self.__assistants[address[0]] = SupervisorAssistant(
                        supervisor=self, hostname=socket.getfqdn(address[0]))
                    logger.info("Starting a new assistant for address %s" % str(address[0]))
                    self.__assistants[address[0]].start()
                num_connections += 1
                if num_connections % 50 == 0:
                    logger.info("connections=%d, files=%d, threads=%d" % (
                        num_connections, master.num_fds(), master.num_threads()))
                self.__assistants[address[0]].add_worker(worker, address)
            except BaseException as e:
                logger.error("Master failed to accept connection - %s. Force terminating all the workers." % e.message)
                logger.error(traceback.format_exc())
                import remote
                workers = self.get_worker_names()
                ssh_user = master_settings.WORKER_SSH_USER
                ssh_port = master_settings.WORKER_SSH_PORT
                password = master_settings.WORKER_SSH_PASSWORD
                ssh_pkey = master_settings.WORKER_SSH_PRIVATE_KEY
                for worker in workers:
                    remote.force_stop_worker(hostname=worker, port=ssh_port, username=ssh_user,
                                             password=password, key_filename=ssh_pkey)
                    self.remove_worker(worker)
                break
        server.close()

    def await_connect(self, hostname, timeout=5):
        # default timeout is 5 seconds
        end_time = time.time() + timeout
        current_time = time.time()
        while current_time < end_time:
            workers = self.get_worker_names()
            if hostname in workers:
                return
            current_time = time.time()
        raise Exception("Worker %s failed to connect in %d seconds" % (hostname, timeout))

    def add_scheduler_event(self, hid):
        self.__scheduler.add_event(hid)

    def awake_scheduler(self):
        self.__scheduler.awake()

    def get_worker_names(self):
        self.__lock.acquire()
        worker_hosts = list(self.__workers.keys())
        self.__lock.release()
        return worker_hosts

    def get_all_workers(self):
        self.__lock.acquire()
        all_workers = self.__workers.items()
        self.__lock.release()
        return all_workers

    def get_worker_address(self, hostname):
        self.__lock.acquire()
        worker_repr = self.__workers[hostname]
        address = (worker_repr.address, worker_repr.port)
        self.__lock.release()
        return address

    def stop_worker(self, hostname):
        try:
            while not self.__scheduler.is_waiting():
                self.__scheduler.pause()
                self.__scheduler.awake()

            address = self.get_worker_address(hostname)
            request = messaging.Request(messaging.RequestType.TERMINATION)
            messaging.push(address, request)
            self.remove_worker(hostname=hostname)
        except BaseException as e:
            raise e

    def remove_worker(self, hostname):
        self.__lock.acquire()
        if hostname in self.__workers:
            num_slots = self.__workers[hostname].slots
            self.__scheduler.decrement_qsize(num_slots)
            self.__snapshots.pop(hostname, None)
            self.__workers.pop(hostname, None)
        self.__lock.release()

    def get_worker_snapshot(self, hostname):
        address = self.get_worker_address(hostname)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(address)
            request = messaging.Request(messaging.RequestType.SNAPSHOT)
            response = messaging.sendrecv(sock, request)
            return {'what': 'snapshot', 'result': response}
        except socket.error as se:
            return {'what': 'error', 'result': se.message}

    def get_snapshots(self):
        try:
            self.__lock.acquire()
            snapshots = {}
            for key in self.__snapshots:
                snapshots[key] = self.__snapshots[key]
            return snapshots
        finally:
            self.__lock.release()

    def get_assignments(self):
        try:
            self.__lock.acquire()
            assignments = {}
            for key in self.__assignments:
                assignments[key] = self.__assignments[key]
            return assignments
        finally:
            self.__lock.release()

    def get_host_utilization(self, host):
        try:
            self.__lock.acquire()
            return min(len(self.__assignments.get(host, [])) / float(self.__workers[host].slots), 1)
        except:
            return 0
        finally:
            self.__lock.release()

    def get_total_utilization(self):
        workers = self.get_all_workers()
        assignments = self.get_assignments()
        utilization = 0
        for host, worker_repr in workers:
            utilization += float(len(assignments.get(host, [])) / worker_repr.slots)
        total_utilization = utilization / len(workers)
        logger.info("Total cluster utilization: %.2f" % total_utilization)
        return total_utilization

    def send_email(self, sender, receivers, subject, plain, html):
        msg_root = MIMEMultipart('related')
        msg_root['Subject'] = "[Columbus] %s" % str(subject)
        msg_root['From'] = master_settings.EMAIL_SENDER
        # msg_root['To'] = receivers
        # Create message container - the correct MIME type is multipart/alternative.
        msg_alt = MIMEMultipart('alternative')
        msg_root.attach(msg_alt)
        part1 = MIMEText(plain, 'plain')
        msg_alt.attach(part1)
        with open("%s/templates/email.html" % master_settings.BASE_DIR, "r") as email_handle:
            content = str(email_handle.read()).replace("<%email-content%>", html)
            part2 = MIMEText(content, 'html')
            msg_alt.attach(part2)
            with open("%s/static/images/logo-wo.png" % master_settings.BASE_DIR, "rb") as logo_handle:
                logo = MIMEImage(logo_handle.read())
                logo.add_header('Content-ID', '<logo>')
                msg_root.attach(logo)
        msg_root.add_header("reply-to", sender)
        try:
            self.__lock.acquire()
            sendgrid = smtplib.SMTP(host=master_settings.EMAIL_HOST, port=master_settings.EMAIL_PORT)
            sendgrid.ehlo()
            if master_settings.EMAIL_USE_TLS:
                sendgrid.starttls()
                sendgrid.ehlo()
            sendgrid.login(user=master_settings.EMAIL_HOST_USER, password=master_settings.EMAIL_HOST_PASSWORD)
            # sendmail function takes 3 arguments: sender's address, recipient's address
            # and message to send - here it is sent as one string.
            sendgrid.sendmail(sender, receivers, msg_root.as_string())
            sendgrid.quit()
        finally:
            self.__lock.release()

    def find_best_destination(self, username, destinations):
        hosts = []
        # destinations must be a map of hostname:filesize key-value pairs
        snapshots = self.get_snapshots()
        assignments = self.get_assignments()
        workers = self.get_all_workers()
        utilization = {}
        names = []
        strategy = master_settings.PIPELINE_SCHEDULING_STRATEGY
        threshold = master_settings.HYBRID_SCHEDULING_WR_RATIO
        for host, worker_repr in workers:
            utilization[host] = len(assignments.get(host, [])) / worker_repr.slots
            names.append(host)
        if strategy == 'local':
            for host, pickle_size in destinations.items():
                snapshot = snapshots.get(host, (0, {}))
                hosts.append((host, snapshot[0], snapshot[1].get(username, 0), pickle_size))
        elif strategy == 'remote':
            no_vacancy = True
            for host, pickle_size in destinations.items():
                snapshot = snapshots.get(host, (0, {}))
                names.remove(host)
                hosts.append((host, snapshot[0], snapshot[1].get(username, 0), pickle_size))
                if snapshot[0] < 1:
                    no_vacancy = False
            if no_vacancy:
                for host in names:
                    snapshot = snapshots.get(host, (0, {}))
                    hosts.append((host, snapshot[0], snapshot[1].get(username, 0), 0))
        elif strategy == 'hybrid':
            no_vacancy = True
            for host, pickle_size in destinations.items():
                snapshot = snapshots.get(host, (0, {}))
                names.remove(host)
                hosts.append((host, snapshot[0], snapshot[1].get(username, 0), pickle_size))
                if snapshot[0] < 1 or snapshot[1].get(username, 0) <= threshold:
                    no_vacancy = False
            if no_vacancy:
                for host in names:
                    snapshot = snapshots.get(host, (0, {}))
                    hosts.append((host, snapshot[0], snapshot[1].get(username, 0), 0))
        hosts.sort(key=lambda x: (x[1], x[2], -x[3]))
        host_addr = self.get_worker_address(hosts[0][0])
        wait = hosts[0][1] >= 1 and hosts[0][2] > 0 if strategy == 'local' else \
            hosts[0][1] >= 1 if strategy == 'remote' else hosts[0][1] >= 1 and hosts[0][2] > threshold
        logger.info("best destination: %s, wait=%s" % (hosts[0], wait))
        return hosts[0][0], host_addr, wait
