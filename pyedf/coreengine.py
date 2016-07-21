import collections
import math
import json
import cPickle as pickle
import os
import re
import shutil
import threading
from operator import itemgetter

import cachetools

from django.utils import timezone
from django.utils.timezone import localtime
from django.contrib.auth.models import User
from geojson import FeatureCollection, Feature

from columbus.settings import USER_DIRPATH, USER_GCSPATH
from pyedf import bigquery
from pyedf import fusiontables
from pyedf.models import ComponentModel, TypeModel
from pyedf.models import FlowStatusModel
from pyedf.models import HistoryModel
from pyedf.models import WorkflowModel
from pyedf.utils import info, caught
from pyedf.utils import json_serial
from pyedf.utils import log_n_suppress


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
        m = Combiner(id=combiner.id, name=combiner.name, flow_id=combiner.flow.id, code=combiner.code,
                     start=combiner.start, end=combiner.end, type=combiner.type.identifier,
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
    # with cloudstorage.open(pickle_path, 'r') as handle:
    try:
        info("reading from local disk")
        with open(pickle_path, 'rb') as handle:
            element = pickle.load(handle)
    except:
        info("local disk failed. copying file from cloud storage bucket to local disk")
        create_and_copy(gcs_pickle_path, pickle_path)
        with open(gcs_pickle_path, 'rb') as handle:
            element = pickle.load(handle)
    return element


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
    info('getting ' + what + ' for ftcindex - ' + str(ftcindex))
    if what == 'columns':
        return get_columns(element=element, ftcindex=ftcindex)
    elif what == 'data':
        direction = 'asc' if not desc else 'desc'
        columns = get_columns(element=element, ftcindex=ftcindex)
        if columns:
            csv = element.csv
            if element.sorted_key != columns[order_by] or element.sorted_dir != direction:
                info("sorting the data either because the direction changed or key changed")
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
            info("sorting the data either because the direction changed or key changed")
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
    # cloudstorage.delete(filename)
    # except cloudstorage.NotFoundError:
    #     pass
    except Exception as e:
        log_n_suppress(e)


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


class Component(object):
    def __init__(self, id, name, code, type, visualizer=False, root=False, parties=None):
        self.id = id  # id of the component
        self.name = name  # name of the component
        self.sys_parents = []
        self.sys_combiners = []
        self.sys_output = None
        self.sys_code = code
        self.type = type
        self.sorted_key = None
        self.sorted_dir = None
        self.is_root = root
        self.visualizer = visualizer
        self.parties = parties
        self.ftkey = None
        self.csv = None
        self.ftcindex = 0

    def serialize(self, directory, filename):
        if not os.path.exists(directory):
            os.makedirs(directory)
        # with cloudstorage.open(directory + '/' + filename, 'w', content_type='text/plain;charset=UTF-8',
        #                        options={'x-goog-acl': 'project-private'}) as handle:
        with open(directory + '/' + filename, 'wb') as handle:
            pickle.dump(self, handle)

    def to_json(self):
        return json.dumps(self, default=lambda o: json_serial(o), sort_keys=True)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and other.id == self.id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return 'component-' + str(self.id)

    def __repr__(self):
        return 'cid-' + str(self.id)


class Workflow(object):
    def __init__(self, id, name, flow_id, component_id, user):
        self.id = id  # id of the workflow instance
        self.flow_id = flow_id  # id of the workflow model
        self.name = name
        self.timestamp = timezone.now()
        self.user = user
        verify_flow(component_id)
        self.elements = collections.deque(linearize_flow(component_id))


class Combiner(object):
    def __init__(self, id, name, flow_id, code, type, is_static=False, start=None, end=None, visualizer=False,
                 parties=None):
        self.id = id
        self.name = name
        self.flow_id = flow_id
        self.sys_code = code
        self.static = is_static
        self.start = start
        self.end = end
        self.type = type
        self.visualizer = visualizer
        self.parties = parties
        self.sys_output = None
        self.sorted_key = None
        self.sorted_dir = None
        self.ftkey = None
        self.csv = None
        self.ftcindex = 0

    def serialize(self, directory, filename):
        if not os.path.exists(directory):
            os.makedirs(directory)
        # with cloudstorage.open(directory + '/' + filename, 'w', content_type='text/plain;charset=UTF-8',
        #                        options={'x-goog-acl': 'project-private'}) as handle:
        with open(directory + '/' + filename, 'wb') as handle:
            pickle.dump(self, handle)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and other.id == self.id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return 'combiner-' + str(self.id)

    def __repr__(self):
        return 'mid-' + str(self.id)


class EngineResource(object):
    def __init__(self, source, details, data):
        self.source = source
        self.details = details
        self.sys_output = data
        self.type = 'csv'
        self.sorted_key = None
        self.sorted_dir = None
        self.csv = None
        self.ftcindex = 0

    def serialize(self, directory, filename):
        if not os.path.exists(directory):
            os.makedirs(directory)
        # with cloudstorage.open(directory + '/' + filename, 'w', content_type='text/plain;charset=UTF-8',
        #                        options={'x-goog-acl': 'project-private'}) as handle:
        with open(directory + '/' + filename, 'wb') as handle:
            pickle.dump(self, handle)

    @staticmethod
    def load(flow_status):
        # with cloudstorage.open(filename, 'r') as handle:
        local_pickle = flow_status.pickle
        gcs_pickle = flow_status.gcs_pickle
        try:
            with open(local_pickle, 'rb') as handle:
                element = pickle.load(handle)
        except:
            create_and_copy(gcs_pickle, local_pickle)
            with open(gcs_pickle, 'rb') as handle:
                element = pickle.load(handle)
        return element


def __serialize_bigquery_request(source, identifier, history, feature, primitive, constraint=None):
    description = 'Finding the values of ' + str(feature) + '.'
    description += ' This request will create multiple workflows.'
    FlowStatusModel(history=history, title='Identifying feature', description=description, result='Success',
                    timestamp=timezone.now(), element='Pre-Processing').save()
    tmp = bigquery.get_distinct_feature(feature=feature, qualified_table_name=identifier,
                                        where=constraint.get_string() if constraint else None, sync=True)
    distinct = [row[0]["v"] for row in tmp["rows"]]
    for index, distinct_value in enumerate(distinct):
        if index == 0:
            execute_flow(source=source, identifier=identifier, history=history, feature=feature,
                         primitive=primitive, op="=", value=str(distinct_value), constraint=constraint)
        else:
            new_history = HistoryModel(user=history.user, start=timezone.now(), flow=history.flow,
                                       source=history.source, details="uninitialized", status="Queued")
            new_history.save()
            execute_flow(source=source, identifier=identifier, history=new_history, feature=feature,
                         primitive=primitive, op="=", value=str(distinct_value), constraint=constraint)


def __fetch_raw_data(element, source, identifier, history, feature=None, primitive=None, op=None, value=None,
                     constraint=None):
    if source == 'bigquery':
        if primitive == 9:  # 9 indicates a String
            value = "'" + str(value) + "'"
        if constraint is not None:
            history.details = str(feature) + str(op) + str(
                value) + " where " + constraint.get_string() + " on " + str(identifier)
            where = "(" + str(feature) + str(op) + str(value) + ") AND " + constraint.get_string()
        else:
            history.details = str(feature) + str(op) + str(value) + " on " + str(identifier)
            where = "(" + str(feature) + str(op) + str(value) + ")"
        history.save()
        FlowStatusModel(history=history, title='Fetching Data',
                        description=('Requesting bigquery to obtain the data based on the mentioned criteria - ' +
                                     history.details),
                        result="Pending", timestamp=timezone.now(), element=element.name).save()
        bq_output = bigquery.select_star(qualified_table_name=identifier, where=where, sync=True)
        csv = []
        fields = [field["name"] for field in bq_output['fields']]
        for row in bq_output['rows']:
            row_dict = {}
            for index, cell in enumerate(row):
                row_dict[fields[index]] = cell["v"]
            csv.append(row_dict)
        return csv


def __verify_output(element_type, __output__, element, history):
    try:
        FlowStatusModel(history=history, title='Verifying Output',
                        description='checking the output of ' + element.name + ' for its output type.',
                        result='Pending', timestamp=timezone.now(), element=element.name).save()
        if element.type == 'ftc':
            if not isinstance(__output__, FeatureCollection):
                raise Exception("Output type mismatch: expected a geojson feature collection")
        elif element.type == 'mftc':
            if not isinstance(__output__, list):
                raise Exception("Output type mismatch: expected a list of geojson feature collections")
            for ftc in __output__:
                if not isinstance(ftc, FeatureCollection):
                    raise Exception("Output type mismatch: expected a list of geojson feature collections")
        elif element.type == 'csv':
            if not isinstance(__output__, list):
                raise Exception("Output type mismatch: expected a list of dictionaries")
            for row in __output__:
                if not isinstance(row, dict):
                    raise Exception("Output type mismatch: expected a list of dictionaries")
        elif element.type == 'ft':
            if not isinstance(__output__, Feature):
                raise Exception("Output type mismatch: expected a geojson feature")
        else:
            if not isinstance(__output__, list):
                raise Exception("Output type mismatch: expected a list")

        FlowStatusModel(history=history, title='Verification Completed',
                        description=element.name + '\'s output matches with it\'s type.',
                        result='Success', timestamp=timezone.now(), element=element.name).save()

    except BaseException as e:
        log_n_suppress(e)
        FlowStatusModel(history=history, title='Verification Failed',
                        description='The output of ' + element.name + ' does not match it\'s output type.',
                        result='Failed', timestamp=timezone.now(), element=element.name).save()
        raise Exception(str(element_type) + ' <b>' + element.name + '</b> Failed - ' + e.message)


def __execute_code(__code__, __name__, __input__):
    scope = dict(locals(), **globals())
    exec (compile(__code__, __name__ + '.py', 'exec'), scope)
    return scope.get("__output__", __input__)


def __execute_element(element_type, _input, element, history):
    try:
        history.status = 'In Progress'
        history.save()
        FlowStatusModel(title='Executing ' + str(element_type),
                        description='Executing the code for ' + str(element_type).lower() + ' -  ' + element.name + '.',
                        result='Pending', element=element.name, history=history,
                        timestamp=timezone.now()).save()
        element.sys_output = __execute_code(__code__=element.sys_code, __name__=element.name, __input__=_input)
        __verify_output(element_type=element_type, __output__=element.sys_output, element=element, history=history)
        filekey = "c" if isinstance(element, Component) else "m"
        info("Is element " + str(element.name) + " having type " + str(element.type) + " visualizer? - " + str(
            element.visualizer))
        if element.visualizer:
            admin = User.objects.filter(is_superuser=True).order_by('email').first().email
            if element.type == 'ftc':
                ft_name = re.sub('[^a-zA-Z0-9]', '-', element.name)
                ft_name = ft_name + "-h" + str(history.id) + filekey + str(element.id)
                ftkey = fusiontables.create_ft_from_ftc(name=ft_name, description=history.details,
                                                        ftc=element.sys_output, parties=element.parties, admin=admin)
                element.ftkey = ftkey
            elif element.type == 'mftc':
                __output__ = element.sys_output
                ftkeys = []
                for index, ftc in enumerate(__output__):
                    ft_name = re.sub('[^a-zA-Z0-9]', '-', element.name)
                    ft_name += "-h" + str(history.id) + filekey + str(element.id) + "-ftc-" + ftc.get('id', str(index))
                    ftkey = fusiontables.create_ft_from_ftc(name=ft_name, description=history.details, ftc=ftc,
                                                            parties=element.parties, admin=admin)
                    ftkeys.append(ftkey)
                element.ftkey = ",".join(ftkeys)
        directory = USER_DIRPATH + history.user.username + "/pickles"
        gcs_directory = USER_GCSPATH + history.user.username + "/pickles"
        fileref = ("component-" if isinstance(element, Component) else "combiner-") + str(element.id)
        filename = "h" + str(history.id) + filekey + str(element.id) + ".pickle"
        element.serialize(directory=directory, filename=filename)  # pickling to local disk
        element.serialize(directory=gcs_directory, filename=filename)  # pickling to cloud for fault tolerance
        pickle_name = directory + "/" + filename
        gcs_pickle_name = gcs_directory + "/" + filename
        type_model = TypeModel.objects.get(identifier=element.type)
        FlowStatusModel(history=history, title=str(element_type) + ' Executed',
                        description=element.name + ' executed successfully.',
                        result='Success', timestamp=timezone.now(), ref=fileref,
                        element=element.name, pickle=pickle_name, gcs_pickle=gcs_pickle_name, type=type_model,
                        ftkey=element.ftkey).save()
    except BaseException as e:
        log_n_suppress(e)
        FlowStatusModel(history=history, title='Execution Failed',
                        description=element.name + ' failed to execute. Reason - ' + e.message,
                        result='Failed', timestamp=timezone.now(), element=element.name).save()
        raise Exception(str(element_type) + ' <b>' + element.name + '</b> Failed - ' + e.message)


def execute_flow(source, identifier, history, feature=None, primitive=None, op=None, value=None, constraint=None):
    try:
        if source == 'bigquery' and op is None:
            __serialize_bigquery_request(source=source, identifier=identifier, history=history, feature=feature,
                                         primitive=primitive, constraint=constraint)
            return
        history.status = 'Started'
        history.save()
        FlowStatusModel(title='Flow Verification', description='Verifiying the workflow for cycles.',
                        result='Pending', element="Pre-Processing", history=history, timestamp=timezone.now()).save()
        workflow = Workflow(id=history.id, name=history.flow.name, flow_id=history.flow.id,
                            component_id=history.flow.component.id, user=history.user.username)
        FlowStatusModel(title='Flow Created', description='Workflow instantiated and component chain created',
                        result='Success', element="Pre-Processing", history=history, timestamp=timezone.now()).save()
        while len(workflow.elements) != 0:
            element = workflow.elements.popleft()
            if isinstance(element, Component) and element.is_root:
                __input__ = __fetch_raw_data(element=element, source=source, identifier=identifier, history=history,
                                             feature=feature, primitive=primitive, op=op, value=value,
                                             constraint=constraint)
                directory = USER_DIRPATH + history.user.username + "/pickles"
                gcs_directory = USER_GCSPATH + history.user.username + "/pickles"
                filename = "h" + str(history.id) + "e" + str(element.id) + ".pickle"
                engine_res = EngineResource(source=source, details=history.details, data=__input__)
                engine_res.serialize(directory=directory, filename=filename)
                engine_res.serialize(directory=gcs_directory, filename=filename)
                pickle_name = directory + "/" + filename
                gcs_pickle_name = gcs_directory + "/" + filename
                FlowStatusModel(history=history, title='Fetch Completed',
                                description='Obtained ' + str(len(__input__)) + ' rows of data',
                                result='Success', timestamp=timezone.now(), ref="engine-" + str(element.id),
                                element="Pre-Processing", pickle=pickle_name, gcs_pickle=gcs_pickle_name,
                                type=TypeModel.objects.get(identifier='csv')).save()
                __execute_element(element_type="Component", _input=__input__, element=element, history=history)
            elif isinstance(element, Combiner):
                wmodel = WorkflowModel.objects.get(pk=element.flow_id)
                current_time = localtime(timezone.now()).strftime("%a, %d %b %Y - %I:%M:%S %p")
                if source == 'combiner' and history.details == 'uninitialized':
                    history.details = "Combined instances of " + wmodel.name + " as of " + current_time
                history.status = 'In Progress'
                history.save()
                ref = "component-" + str(wmodel.component.id)
                if element.start is not None and element.end is not None:
                    local_start = localtime(element.start).strftime("%a, %d %b %Y - %I:%M:%S %p")
                    local_end = localtime(element.end).strftime("%a, %d %b %Y - %I:%M:%S %p")
                    FlowStatusModel(title='Combining Data',
                                    description='Considering only the instances of ' + wmodel.name + ' between ' + str(
                                        local_start) + ' and ' + str(local_end),
                                    result='Pending', element=element.name, history=history,
                                    timestamp=timezone.now()).save()
                    histories = list(HistoryModel.objects.filter(flow_id=wmodel.id, start__gte=element.start,
                                                                 start__lte=element.end, status="Finished",
                                                                 user=history.user).order_by('pk'))
                elif element.start is not None:
                    local_start = localtime(element.start).strftime("%a, %d %b %Y - %I:%M:%S %p")
                    FlowStatusModel(title='Combining Data',
                                    description='Considering only the instances of ' + wmodel.name + ' after ' + str(
                                        local_start),
                                    result='Pending', element=element.name, history=history,
                                    timestamp=timezone.now()).save()
                    histories = list(HistoryModel.objects.filter(flow_id=wmodel.id, start__gte=element.start,
                                                                 status="Finished", user=history.user).order_by('pk'))
                elif element.end is not None:
                    local_end = localtime(element.end).strftime("%a, %d %b %Y - %I:%M:%S %p")
                    FlowStatusModel(title='Combining Data',
                                    description='Considering only the instances of ' + wmodel.name + ' before ' + str(
                                        local_end),
                                    result='Pending', element=element.name, history=history,
                                    timestamp=timezone.now()).save()
                    histories = list(HistoryModel.objects.filter(flow_id=wmodel.id, start__lte=element.end,
                                                                 status="Finished", user=history.user).order_by('pk'))
                else:
                    FlowStatusModel(title='Combining Data',
                                    description='Considering all the finished instances of ' + wmodel.name,
                                    result='Pending', element=element.name, history=history,
                                    timestamp=timezone.now()).save()
                    histories = list(HistoryModel.objects.filter(flow_id=wmodel.id, status="Finished",
                                                                 user=history.user).order_by('pk'))

                __input__, __output__ = [], None
                if not histories:
                    desc = 'Failed to combine the data because there are no instances for the workflow - ' + wmodel.name
                    FlowStatusModel(title='Combining Failed',
                                    description=desc, result='Failed', element=element.name, history=history,
                                    timestamp=timezone.now()).save()
                    raise ValueError("No instances found for '" + wmodel.name + "'")

                for past_history in histories:
                    statuses = list(FlowStatusModel.objects.filter(history=past_history, ref=ref))
                    for status in statuses:
                        if status.pickle is None:
                            FlowStatusModel(title='Combining Failed',
                                            description='Failed to combine the data because the output of  ' + ref + ' is missing',
                                            result='Failed', element=element.name, history=history,
                                            timestamp=timezone.now()).save()
                            raise ValueError(
                                "No pickle found for the reference '" + ref + "' of workflow " + wmodel.name)
                        compel = EngineResource.load(status)
                        __input__.append(compel.sys_output)

                FlowStatusModel(title='Combining Completed',
                                description=('Output of all the ' + wmodel.name + ' instances are combined. '
                                             'Gathered output of ' + str(len(__input__)) + ' instance(s).'),
                                result='Success', element=element.name, history=history,
                                timestamp=timezone.now()).save()
                __execute_element(element_type="Combiner", _input=__input__, element=element, history=history)
            else:
                # element is a non-root component
                FlowStatusModel(title='Gathering Input',
                                description='Collecting the output of all parents and combiners of this component',
                                result='Pending', element=element.name, history=history,
                                timestamp=timezone.now()).save()
                __input__, __output__ = {}, None
                __input__['ftkey'] = {}
                for parent in element.sys_parents:
                    statuses = list(FlowStatusModel.objects.filter(history=history, ref="component-" + str(parent)))
                    if not statuses:
                        FlowStatusModel(title='Gathering Failed',
                                        description='No output found for the component -  ' + element.name + '.',
                                        result='Failed', element=element.name, history=history,
                                        timestamp=timezone.now()).save()
                        raise ValueError("No output found for the component - " + element.name)
                    for status in statuses:
                        if status.pickle is None:
                            FlowStatusModel(title='Gathering Failed',
                                            description='Failed to gather input because the output of component-' + str(
                                                parent) + ' is missing.',
                                            result='Failed', element=element.name, history=history,
                                            timestamp=timezone.now()).save()
                            raise ValueError("No pickle found for the reference 'component-" + str(parent) + "'")
                        compel = EngineResource.load(status)
                        __input__['component-' + str(parent)] = compel.sys_output
                        if compel.ftkey is not None:
                            __input__["ftkey"]['component-' + str(parent)] = compel.ftkey

                for combiner in element.sys_combiners:
                    statuses = list(FlowStatusModel.objects.filter(history=history, ref="combiner-" + str(combiner)))
                    if not statuses:
                        FlowStatusModel(title='Gathering Failed',
                                        description='No output found for the combiner -  ' + element.name + '.',
                                        result='Failed', element=element.name, history=history,
                                        timestamp=timezone.now()).save()
                        raise ValueError("No output found for the combiner - " + element.name)
                    for status in statuses:
                        if status.pickle is None:
                            FlowStatusModel(title='Gathering Failed',
                                            description='Failed to gather input because the output of combiner-' + str(
                                                combiner) + ' is missing.',
                                            result='Failed', element=element.name, history=history,
                                            timestamp=timezone.now()).save()
                            raise ValueError("No pickle found for the reference 'combiner-" + str(combiner) + "'")
                        combel = EngineResource.load(status)
                        __input__['combiner-' + str(combiner)] = combel.sys_output
                        if combel.ftkey is not None:
                            __input__["ftkey"]['combiner-' + str(combiner)] = combel.ftkey
                info("component's input - " + str(__input__.keys()))
                FlowStatusModel(title='Gathering Completed',
                                description='The output of all parents and combiners of this component has been collected',
                                result='Success', element=element.name, history=history,
                                timestamp=timezone.now()).save()
                __execute_element(element_type="Component", _input=__input__, element=element, history=history)

        history.finish = timezone.now()
        history.duration = int((history.finish - history.start).seconds)
        history.status = "Finished"
        history.save()
        FlowStatusModel(history=history, title='Flow Completed',
                        description=history.flow.name + ' executed successfully.',
                        result='Success', timestamp=history.finish, element='Post-Processing').save()
    except BaseException as e:
        log_n_suppress(e)
        history.finish = timezone.now()
        history.duration = int((history.finish - history.start).seconds)
        history.status = "Failed"
        history.save()
        FlowStatusModel(history=history, title='Flow Failed',
                        description=history.flow.name + ' failed to execute. Reason - ' + e.message,
                        result='Failed', timestamp=timezone.now(), element='Post-Processing').save()
