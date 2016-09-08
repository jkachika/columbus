import csv
import json
import re
import sys

import requests
import time
import threading

from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse
from django.http import JsonResponse
from django.http.response import HttpResponseRedirect
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import View
from googleapiclient import errors
from oauth2client.client import HttpAccessTokenRefreshError

from columbus.settings import *
from pyedf import bigquery
from pyedf import coreengine
from pyedf import fusiontables
from pyedf.drive import list_files
from pyedf.models import *
from pyedf.security import CredentialManager
from pyedf.utils import *


def verify(request):
    if request.method == 'POST':
        data = request.POST
        username = data.get('username')
        password = data.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                next = request.POST.get('next')
                if next is not None:
                    return HttpResponseRedirect(next)
                return HttpResponseRedirect('/home')
            else:
                params = dict(error="Account disabled! Please contact the administrator.")
                return render(request, 'login.html', params)
        else:
            params = dict(error="Incorrect username or password! Please try again.")
            return render(request, 'login.html', params)


class _LoggedInMixin(object):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(_LoggedInMixin, self).dispatch(*args, **kwargs)


class Login(View):
    def get(self, request):
        params = {}
        return render(request, 'login.html', params)

    def post(self, request):
        return self.get(request)


class Test(_LoggedInMixin, View):
    def get(self, request):
        params = {}
        return render(request, 'test.html', params)

    def post(self, request):
        return self.get(request)


class HistoryAsync(_LoggedInMixin, View):
    def get(self, request):
        what = request.GET.get('what', None)
        hid = int(request.GET.get('id', 0))
        if what == "status":
            history = HistoryModel.objects.get(pk=int(hid), user=self.request.user)
            end = localtime(history.finish).strftime(
                "%a, %d %b %Y - %I:%M:%S %p") if history.finish else 'Not available'
            duration = str(history.duration) + " seconds" if history.duration > 0 else "--"
            return JsonResponse(
                {'what': what, 'data': {'id': history.id, 'details': history.details, 'status': history.status,
                                        'end': end, 'duration': duration}})
        elif what == "find":
            histories = HistoryModel.objects.filter(pk__gt=int(hid), user=self.request.user).order_by('pk')
            if histories:
                history = histories[0]
                start = localtime(history.start).strftime(
                    "%a, %d %b %Y - %I:%M:%S %p") if history.start else 'Not available'
                end = localtime(history.finish).strftime(
                    "%a, %d %b %Y - %I:%M:%S %p") if history.finish else 'Not available'
                duration = str(history.duration) + " seconds" if history.duration > 0 else "--"
                return JsonResponse(
                    {'what': what, 'data': {'id': history.id, 'details': history.details, 'status': history.status,
                                            'end': end, 'duration': duration, 'source': history.source,
                                            'name': history.flow.name, 'start': start}})
            else:
                return JsonResponse({"what": what, "data": "none"})
        return JsonResponse({"what": "unknown", "data": "error"})


class History(_LoggedInMixin, View):
    def get(self, request):
        hopenid = request.GET.get('hopenid', 0)
        user = self.request.user
        histories = HistoryModel.objects.filter(user=user).order_by('-pk')[:50]  # retrieving last 50 records
        params = dict(histories=histories, hopenid=hopenid if histories else 0)
        return render(request, 'history.html', params)

    def post(self, request):
        return self.get(request)


class Home(_LoggedInMixin, View):
    def get(self, request):
        user = self.request.user
        polygons = PolygonModel.objects.filter(user=user)
        workflows = WorkflowModel.objects.filter(Q(user=user, ignore=False) |
                                                 Q(viewers=user)).distinct().order_by('name')
        sferror = request.session.get('sferror', None)
        request.session['sferror'] = None
        params = dict(polygons=polygons, workflows=workflows, error=sferror)
        return render(request, 'bqhome.html', params)

    def post(self, request):
        return self.get(request)


class NLHome(View):
    def get(self, request):
        page = request.GET.get('page', None)
        if page not in ['overview', 'usage', 'publications', 'releases', 'people']:
            page = 'nlhome'
        params = {}
        return render(request, str(page) + '.html', params)


# get the status of the flow requested
class PeekFlow(_LoggedInMixin, View):
    def get(self, request):
        hid = request.GET.get('flowid', None)
        fsid = request.GET.get('fsid', None)
        if hid is None or fsid is None:
            return JsonResponse({'status': 'error', 'message': 'Both flow id and flow status id are required'})
        history = HistoryModel.objects.get(pk=int(hid))
        if not history:
            return JsonResponse(
                {'status': 'error', 'message': 'No flow in progress for the id provided(' + hid + ')'})
        try:
            timeout = 60
            statuses = FlowStatusModel.objects.filter(pk__gt=int(fsid), history=history).order_by('pk')
            while not statuses and timeout > 0 and history.status not in ["Finished", "Failed"]:
                time.sleep(5)
                timeout -= 5
                history.refresh_from_db()
                statuses = FlowStatusModel.objects.filter(pk__gt=int(fsid), history=history).order_by('pk')
            if not statuses and timeout == 0 and history.status not in ["Finished", "Failed"]:
                raise Exception("Timed out waiting for the status")
            results = []
            if statuses:
                for status in statuses:
                    results.append(dict(id=status.id, title=status.title, description=status.description,
                                        result=status.result, ref=status.ref if status.ref is not None else "",
                                        element=status.element, flowid=history.id,
                                        type=status.type.identifier if status.type else "",
                                        ftkey=status.ftkey if status.ftkey is not None else "",
                                        timestamp=localtime(status.timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]))
            if history.status == 'Finished':
                return JsonResponse({'status': 'finished', 'message': results})
            elif history.status == 'Failed':
                return JsonResponse({'status': 'failure', 'message': results})
            else:
                return JsonResponse({'status': 'success', 'message': results})
        except Exception as e:
            return JsonResponse({'status': 'timeout', 'message': e.message})


class PeekFlowData(_LoggedInMixin, View):
    def get(self, request):
        # hid = int(request.GET.get('flowid', None))
        fsid = int(request.GET.get('fsid', None))
        what = request.GET.get('what', None)
        ftcindex = int(request.GET.get('ftcindex', 0))

        if what == 'columns':
            result = coreengine.get_output(fsid=fsid, what=what, ftcindex=ftcindex)
            return JsonResponse({'what': what, 'result': result})
        elif what == 'data':
            draw = request.POST.get('draw', 1)
            start = int(request.POST.get('start', 0))
            length = int(request.POST.get('length', 10))
            orderby = int(request.POST.get('order[0][column]', 0))
            orderdir = request.POST.get('order[0][dir]', 'asc')
            output = coreengine.get_output(fsid=fsid, what=what, ftcindex=ftcindex, order_by=orderby,
                                           desc=True if orderdir == 'desc' else False)
            records = len(output)
            if len(output) != 0:
                result = output[start:(start + length)]
                return JsonResponse({'draw': draw, 'recordsTotal': records, 'recordsFiltered': records,
                                     'data': result})
            return JsonResponse({'draw': draw, 'recordsTotal': 0, 'recordsFiltered': 0,
                                 'data': []})
        elif what == 'ftc':
            result = coreengine.get_collections(fsid)
            return JsonResponse({'what': what, 'result': result})
        elif what == 'chart':
            fields = str(request.GET.get('fields', '')).split(',')
            output = coreengine.get_output(fsid=fsid, what=what, ftcindex=ftcindex, order_by=fields[0],
                                           desc=False, fields=fields)
            return JsonResponse({'what': what, 'result': output})
        return JsonResponse({'what': what, 'result': []})

    def post(self, request):
        return self.get(request)


class OAuth2Handler(_LoggedInMixin, View):
    def get(self, request):
        state = request.GET.get('state', None)
        code = request.GET.get('code', None)
        try:
            credentials = CredentialManager.get_drive_credentials(code)
            security = SecurityModel.objects.filter(user=self.request.user).first()
            if security:
                security.credentials = credentials.to_json()
            else:
                security = SecurityModel(user=self.request.user, credentials=credentials.to_json())
            security.save()
            return HttpResponseRedirect(state)
        except Exception as e:
            log_n_suppress(e)
            request.session['sferror'] = e.message
            return HttpResponseRedirect('/home')


class DatasourceAsync(_LoggedInMixin, View):
    def get(self, request):
        source = request.GET.get('source', None)
        if source == 'drive':
            security = SecurityModel.objects.filter(user=self.request.user).first()
            if security:
                run_type = request.GET.get('runtype', 'for')
                try:
                    result = list_files(security.credentials,
                                        query="mimeType = 'application/vnd.google-apps.fusiontable' or \
                                        mimeType = 'application/vnd.google-apps.folder' or fileExtension='csv' \
                                        and trashed = false" if run_type == 'for' else "mimeType = \
                                        'application/vnd.google-apps.folder' and trashed = false",
                                        order_by="viewedByMeTime desc", files=True if run_type == 'for' else False)
                    return JsonResponse({'what': 'files', 'result': result})
                except errors.HttpError, err:
                    if err.resp.status == 401:
                        return JsonResponse(
                            {'what': 'authorize', 'result': CredentialManager.get_drive_authorization_url('/home')})
                except HttpAccessTokenRefreshError as err:
                    return JsonResponse(
                        {'what': 'authorize', 'result': CredentialManager.get_drive_authorization_url('/home')})
                except Exception as e:
                    log_n_suppress(e)
                    return JsonResponse({'what': 'error', 'result': e.message})
            else:
                return JsonResponse(
                    {'what': 'authorize', 'result': CredentialManager.get_drive_authorization_url('/home')})
        return JsonResponse({'what': 'error', 'result': 'Unknown source specified - ' + str(source)})


class Download(_LoggedInMixin, View):
    def get(self, request):
        hid = int(request.GET.get('flowid', None))
        fsid = int(request.GET.get('fsid', None))
        ftcindex = int(request.GET.get('ftcindex', 0))
        history = HistoryModel.objects.get(pk=hid)
        details = str(history.details) if len(str(history.details)) < 50 else str(history.details)[:50]
        filename = re.sub('[^a-zA-Z0-9]', '-', details) + ".csv"
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="' + filename + '"'
        writer = csv.writer(response)
        output = coreengine.get_output(fsid=fsid, what='download', ftcindex=ftcindex)
        for row in output:
            writer.writerow(row)
        return response


class DeleteAsync(_LoggedInMixin, View):
    def get(self, request):
        what = request.GET.get('what', None)
        id = request.GET.get('id', None)
        if what is not None and id is not None:
            id = int(id)
            if what == "history":
                history = HistoryModel.objects.get(pk=id, user=self.request.user)
                statuses = FlowStatusModel.objects.filter(history=history)
                delete_success = True
                for status in statuses:
                    if status.ftkey:
                        try:
                            fusiontables.delete_table(status.ftkey)
                        except:
                            delete_success = False
                            break
                if delete_success:
                    for status in statuses:
                        if status.pickle:
                            coreengine.delete_pickle(status.pickle)
                            coreengine.delete_pickle(status.gcs_pickle)
                    if statuses:
                        statuses.delete()
                    if history:
                        history.delete()
                    return JsonResponse({'what': what, 'result': "success"})
                else:
                    return JsonResponse({'what': what, 'result': "error"})
        return JsonResponse({'what': "unknown", 'result': "error"})


class BuildChain(_LoggedInMixin, View):
    def get(self, request):
        compid = int(request.GET.get('compid', 0))
        return JsonResponse(
            {'result': 'error' if caught(coreengine.verify_flow, compid) else str(
                coreengine.linearize_flow(compid)) if compid != 0 else 'error'})


class StartFlow(_LoggedInMixin, View):
    def post(self, request):
        try:
            data = request.POST
            choice = data.get('datasource', None)
            flow = data.get('workflow', None)
            if choice is None or flow is None:
                raise Exception('Datasource and Workflow must be specified in order to start a flow.')

            workflow = WorkflowModel.objects.get(pk=int(flow))
            if choice == 'bigquery':
                bq_table = data.get('bq-table', None)
                feature = data.get('bq-feature-label', None)
                feature_type = int(data['bq-feature-type'])
                if bq_table is None or feature is None:
                    raise ValueError("Table and feature names are required to start the flow")
                run_type = data.get('run-type', 'for-each')
                op, value, constraint = None, None, None
                if run_type == "for":
                    op = data.get('bq-feature-op', None)
                    value = data.get('bq-feature-value', None)
                    if op is None or value is None:
                        raise ValueError("Operator and value are required to start the flow")
                if data.get('bq-constraint', None):
                    constraint = ConditionModel.objects.get(pk=int(data["bq-constraint"]))
                history = HistoryModel(user=self.request.user, start=timezone.now(), flow=workflow, source=choice,
                                       details="uninitialized", status="Queued")
                history.save()
                user_thread = threading.Thread(target=coreengine.execute_flow,
                                               args=(choice, bq_table, history, feature, feature_type,
                                                     op, value, constraint))
                user_thread.setName(self.request.user.username + '/tmp/hid' + str(history.id))
                user_thread.setDaemon(True)
                user_thread.start()
            elif choice == 'combiner':
                title = data.get('combiner-title', '')
                history = HistoryModel(user=self.request.user, start=timezone.now(), flow=workflow, source=choice,
                                       details="uninitialized" if len(title.strip()) == 0 else title.strip(),
                                       status="Queued")
                history.save()
                user_thread = threading.Thread(target=coreengine.execute_flow, args=(choice, None, history))
                user_thread.setName(self.request.user.username + '/tmp/hid' + str(history.id))
                user_thread.setDaemon(True)
                user_thread.start()
            elif choice == 'drive':
                drive_id = data.get('gd-identifier', None)
                history = HistoryModel(user=self.request.user, start=timezone.now(), flow=workflow, source=choice,
                                       details="uninitialized", status="Queued")
                history.save()
                user_thread = threading.Thread(target=coreengine.execute_flow, args=(choice, drive_id, history))
                user_thread.setName(self.request.user.username + '/tmp/hid' + str(history.id))
                user_thread.setDaemon(True)
                user_thread.start()
            else:
                raise Exception('Invalid datasource selection')
            return HttpResponseRedirect('/history/?hopenid=' + str(history.id))
        except Exception as e:
            log_n_suppress(e)
            request.session['sferror'] = e.message
            return HttpResponseRedirect('/home')


class CodeReader(_LoggedInMixin, View):
    def get(self, request):
        cid = request.GET.get('componentid', 0)
        mid = request.GET.get('combinerid', 0)
        if cid != 0:
            component = ComponentModel.objects.get(pk=int(cid))
            return HttpResponse(component.code)
        if mid != 0:
            combiner = CombinerModel.objects.get(pk=int(mid))
            return HttpResponse(combiner.code)
        return HttpResponse('')


class SavePolygon(_LoggedInMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            polygon = PolygonModel(name=data['name'], json=data['polygon'], time=timezone.now(), user=self.request.user)
            polygon.save()
            return JsonResponse({'id': polygon.id, 'name': polygon.name, 'json': data['polygon']})
        except Exception as e:
            log_n_raise(e)


class WorkspaceAsync(_LoggedInMixin, View):
    def get(self, request):
        user = self.request.user
        name = request.GET.get('name', None)
        if name == 'constraint':
            table = request.GET.get('table', None)
            conditions = ConditionModel.objects.filter(user=user, table=table).order_by('-time')
            result = []
            for condition in conditions:
                result.append(dict(id=condition.id, name=condition.name, expression=str(condition),
                                   table=condition.table,
                                   time=localtime(condition.time).strftime("%a, %d %b %Y - %I:%M:%S %p")))
            return JsonResponse({'what': name, 'result': result})
        return JsonResponse({'what': 'invalid', 'result': []})

    def post(self, request):
        user = self.request.user
        data = request.POST
        formtype = data['form-type']
        if formtype == 'constraint':
            try:
                if data['condition-type'] == 'simple':
                    datatypes = {1: int, 2: long, 3: float, 4: float, 9: str}
                    definitions = {1: "integer", 2: "integer", 3: "decimal number", 4: "decimal number", 9: "string"}
                    if caught(datatypes[int(data['feature-type'])], data["feature-value"]):
                        return JsonResponse({"result": "error", "message": "Invalid feature value, must be a(n) " +
                                                                           definitions[int(data['feature-type'])]})
                    condition = SimpleConditionModel(name=data['constraint-name'], user=user, time=timezone.now(),
                                                     type='simple', feature=data['feature-label'],
                                                     op=data["feature-op"], value=data["feature-value"],
                                                     primitive=int(data['feature-type']),
                                                     table=data['constraint-table'])
                else:
                    condition = ComplexConditionModel(name=data['constraint-name'], user=user, time=timezone.now(),
                                                      type='complex', left_id=int(data['constraint-left']),
                                                      joint=data['joint'], right_id=int(data['constraint-right']),
                                                      table=data['constraint-table'])
                    if caught(ComplexConditionModel.validate, condition):
                        return JsonResponse({"result": "error",
                                             "message": "Invalid constraint. Must be in disjunctive normal form."})
                condition.save()
                message = dict(id=condition.id, name=condition.name, expression=str(condition), table=condition.table,
                               time=localtime(condition.time).strftime("%a, %d %b %Y - %I:%M:%S %p"))
                return JsonResponse({"result": "success", "message": message})
            except Exception as e:
                return JsonResponse({"result": "error",
                                     "message": "Something went wrong while creating the constraint - " + e.message})
        elif formtype == 'schedule':
            try:
                tz = timezone.get_current_timezone()
                schedule = ScheduleModel(name=data['schedule-name'], user=user, time=timezone.now(),
                                         repeat=data['schedule-repeat'])
                schedule.start = tz.localize(dt.strptime(data['schedule-start'], '%m/%d/%Y %I:%M %p'))
                if schedule.repeat != 'none':
                    schedule.end = data['schedule-end']
                if schedule.repeat == 'custom':
                    schedule.custom_count = int(data['schedule-custom-count'])
                    schedule.custom_repeat = data['schedule-custom-repeat']
                if schedule.custom_repeat == 'week':
                    weekdays = data.getlist('schedule-week-repeat')
                    schedule.custom_week = ', '.join(weekdays)
                if schedule.end == 'date':
                    schedule.until = tz.localize(dt.strptime(data['schedule-until'], '%m/%d/%Y %I:%M %p'))
                elif schedule.end == 'count':
                    schedule.count = int(data['schedule-count'])
                schedule.save()
                message = dict(id=schedule.id, name=schedule.name, details=str(schedule),
                               time=localtime(schedule.time).strftime("%a, %d %b %Y - %I:%M:%S %p"))
                return JsonResponse({"result": "success", "message": message})
            except Exception as e:
                return JsonResponse({"result": "error",
                                     "message": "Something went wrong while creating the schedule - " + e.message})
        else:
            return JsonResponse({"result": "error", "message": "Invalid request."})


class Workspace(_LoggedInMixin, View):
    def get(self, request):
        user = self.request.user
        users = User.objects.filter(email__endswith='@gmail.com', is_staff=False, is_superuser=False).order_by(
            'first_name')
        allusers = User.objects.filter(is_staff=False, is_superuser=False).order_by('first_name')
        components = ComponentModel.objects.filter(Q(user=user, ignore=False) |
                                                   Q(viewers=user)).distinct().order_by('-time')
        combiners = CombinerModel.objects.filter(Q(user=user, ignore=False) |
                                                 Q(viewers=user)).distinct().order_by('-time')
        workflows = WorkflowModel.objects.filter(Q(user=user, ignore=False) |
                                                 Q(viewers=user)).distinct().order_by('-time')
        types = TypeModel.objects.all().order_by('name')
        polygons = PolygonModel.objects.filter(user=user).order_by('-time')
        conditions = ConditionModel.objects.filter(user=user).order_by('-time')
        schedules = ScheduleModel.objects.filter(user=user).order_by('-time')
        component_status = request.session.get('component', None)
        request.session['component'] = None
        workflow_status = request.session.get('workflow', None)
        request.session['workflow'] = None
        combiner_status = request.session.get('combiner', None)
        request.session['combiner'] = None
        formtype = request.session.get('showform', 'component')
        request.session['showform'] = None
        params = dict(components=components, workflows=workflows, combiners=combiners, users=users, allusers=allusers,
                      polygons=polygons, conditions=conditions, schedules=schedules, types=types, current_user=user,
                      cstatus=component_status, wstatus=workflow_status, mstatus=combiner_status, formtype=formtype)
        return render(request, 'workspace.html', params)

    def post(self, request):
        data = request.POST
        formtype = data['form-type']
        cerror, werror, merror = None, None, None
        user = self.request.user
        compid = int(data.get('compid', 0))
        wfid = int(data.get('wfid', 0))
        combid = int(data.get('combid', 0))
        if formtype == 'component':
            if data['action'] == 'create':
                try:
                    component = ComponentModel(user=user, name=data['cname'], description=data['cdesc'],
                                               time=timezone.now(), output=data['coutput'],
                                               visualizer=True if data.get('cvis', False) else False,
                                               root=True if data.get('croot', False) else False)
                    component.save()
                    if not component.root:
                        parents = data.getlist('cparent')
                        for parent in parents:
                            result = parent.split('-')
                            if result[0] == 'component':
                                component.parents.add(ComponentModel.objects.get(pk=int(result[1])))
                            else:
                                component.combiners.add(CombinerModel.objects.get(pk=int(result[1])))

                    if component.visualizer:
                        parties = data.getlist('cparties', None)
                        for party in parties:
                            component.parties.add(User.objects.get(pk=int(party)))

                    ctype = int(data['ctype'])
                    output_type = TypeModel.objects.get(pk=ctype)
                    component.type = output_type
                    compid = component.id
                    usercode = data['usercode']
                    usercode = "\n".join(usercode.split("\r\n"))
                    component.code = usercode
                    component.save()
                    try:
                        compile(usercode, data['cname'] + '.py', 'exec')
                    except BaseException as e:
                        log_n_raise(e, str(sys.exc_info()[1]) + '\n' + repr(sys.exc_info()[1]))

                    if component.visualizer and component.type.identifier not in ["ftc", "mftc"]:
                        raise ValueError(
                            "Visualization is only possible for output type Feature Collection or Multi Collection")

                    request.session['component'] = {'name': data['cname'],
                                                    'message': 'Component created successfully!'}
                    request.session['showform'] = 'component'
                except Exception as e:
                    logger.error(tb.format_exc())
                    cerror = 'Please correct the below errors: \n' + e.message
            elif data['action'] == 'delete':
                try:
                    component = ComponentModel.objects.get(pk=compid, user=user)
                    cname = component.name
                    component.ignore = True
                    component.save()
                    request.session['component'] = {'name': cname, 'message': 'Component deleted successfully!'}
                    request.session['showform'] = 'component'
                except Exception as e:
                    logger.error(tb.format_exc())
                    cerror = 'Please correct the below errors: \n' + e.message
            elif data['action'] == 'save':
                try:
                    component = ComponentModel.objects.get(pk=data['compid'], user=user)
                    component.name = data['cname']
                    component.description = data['cdesc']
                    component.time = timezone.now()
                    component.type = TypeModel.objects.get(pk=int(data['ctype']))
                    component.output = data['coutput']
                    component.visualizer = True if data.get('cvis', False) else False
                    if component.visualizer:
                        parties = data.getlist('cparties', None)
                        component.parties.clear()
                        for party in parties:
                            component.parties.add(User.objects.get(pk=int(party)))

                    usercode = data['usercode']
                    usercode = "\n".join(usercode.split("\r\n"))
                    component.code = usercode
                    component.save()
                    try:
                        compile(usercode, data['cname'] + '.py', 'exec')
                    except BaseException:
                        raise Exception(str(sys.exc_info()[1]) + '\n' + repr(sys.exc_info()[1]))

                    if component.visualizer and component.type.identifier not in ['ftc', 'mftc']:
                        raise ValueError(
                            "Visualization is only possible for output type Feature Collection or Multi Collection")

                    request.session['component'] = {'name': data['cname'],
                                                    'message': 'Component saved successfully!'}
                    request.session['showform'] = 'component'
                except Exception as e:
                    logger.error(tb.format_exc())
                    cerror = 'Please correct the below errors: \n' + e.message

        elif formtype == 'workflow':
            if data['action'] == 'create':
                try:
                    component = ComponentModel.objects.get(pk=data['wcomponents'])
                    workflow = WorkflowModel(user=user, name=data['wfname'], description=data['wfdesc'],
                                             time=timezone.now(), component=component,
                                             sharing=True if data.get('wshare', False) else False)
                    workflow.save()
                    wfid = workflow.id
                    coreengine.verify_flow(component.id)
                    chain = coreengine.linearize_flow(component.id)
                    workflow.chain = str(chain)
                    viewers = data.getlist('wviewers', None)
                    if workflow.sharing:
                        read_users = []
                        for viewer in viewers:
                            read_users.append(User.objects.get(pk=int(viewer)))
                        if read_users:
                            workflow.viewers.add(*read_users)
                            for element in chain:
                                if isinstance(element, coreengine.Component):
                                    ComponentModel.objects.get(pk=element.id).viewers.add(*read_users)
                                if isinstance(element, coreengine.Combiner):
                                    CombinerModel.objects.get(pk=element.id).viewers.add(*read_users)
                    workflow.save()
                    request.session['workflow'] = {'name': data['wfname'],
                                                   'message': 'Workflow created successfully!'}
                    request.session['showform'] = 'workflow'
                except Exception as e:
                    logger.error(tb.format_exc())
                    werror = 'Please correct the below errors: \n' + e.message

            elif data['action'] == 'delete':
                try:
                    workflow = WorkflowModel.objects.get(pk=wfid, user=user)
                    wfname = workflow.name
                    workflow.ignore = True
                    chain = coreengine.linearize_flow(workflow.component.id)
                    reversed_chain = chain[::-1]
                    read_users = workflow.viewers.all()
                    for read_user in read_users:
                        workflow_dependents = CombinerModel.objects.filter(user=read_user, flow=workflow)
                        if not workflow_dependents:
                            workflow.viewers.remove(read_user)
                        for element in reversed_chain:
                            if isinstance(element, coreengine.Component):
                                shared_component = ComponentModel.objects.get(pk=element.id)
                                component_dependents = ComponentModel.objects.filter(user=read_user,
                                                                                     parents=shared_component)
                                if not component_dependents:
                                    shared_component.viewers.remove(read_user)
                                else:
                                    break
                            if isinstance(element, coreengine.Combiner):
                                shared_combiner = CombinerModel.objects.get(pk=element.id)
                                combiner_dependents = ComponentModel.objects.filter(user=read_user,
                                                                                    combiners=shared_combiner)
                                if not combiner_dependents:
                                    shared_combiner.viewers.remove(read_user)
                                else:
                                    break
                    workflow.save()
                    request.session['workflow'] = {'name': wfname, 'message': 'Workflow deleted successfully!'}
                    request.session['showform'] = 'workflow'
                except Exception as e:
                    logger.error(tb.format_exc())
                    werror = 'Please correct the below errors: \n' + e.message

            elif data['action'] == 'save':
                try:
                    workflow = WorkflowModel.objects.get(pk=wfid, user=user)
                    workflow.name = data['wfname']
                    workflow.description = data['wfdesc']
                    workflow.time = timezone.now()
                    workflow.sharing = True if data.get('wshare', False) else False
                    chain = coreengine.linearize_flow(workflow.component.id)
                    reversed_chain = chain[::-1]
                    read_users = workflow.viewers.all()
                    for read_user in read_users:
                        workflow_dependents = CombinerModel.objects.filter(user=read_user, flow=workflow)
                        if not workflow_dependents:
                            workflow.viewers.remove(read_user)
                        for element in reversed_chain:
                            if isinstance(element, coreengine.Component):
                                shared_component = ComponentModel.objects.get(pk=element.id)
                                component_dependents = ComponentModel.objects.filter(user=read_user,
                                                                                     parents=shared_component)
                                if not component_dependents:
                                    shared_component.viewers.remove(read_user)
                                else:
                                    break
                            if isinstance(element, coreengine.Combiner):
                                shared_combiner = CombinerModel.objects.get(pk=element.id)
                                combiner_dependents = ComponentModel.objects.filter(user=read_user,
                                                                                    combiners=shared_combiner)
                                if not combiner_dependents:
                                    shared_combiner.viewers.remove(read_user)
                                else:
                                    break

                    viewers = data.getlist('wviewers', None)
                    if workflow.sharing:
                        read_users = []
                        for viewer in viewers:
                            read_users.append(User.objects.get(pk=int(viewer)))
                        if read_users:
                            workflow.viewers.add(*read_users)
                            for element in chain:
                                if isinstance(element, coreengine.Component):
                                    ComponentModel.objects.get(pk=element.id).viewers.add(*read_users)
                                if isinstance(element, coreengine.Combiner):
                                    CombinerModel.objects.get(pk=element.id).viewers.add(*read_users)
                    workflow.save()
                    request.session['workflow'] = {'name': data['wfname'], 'message': 'Workflow saved successfully!'}
                    request.session['showform'] = 'workflow'
                except Exception as e:
                    logger.error(tb.format_exc())
                    werror = 'Please correct the below errors: \n' + e.message

        elif formtype == 'combiner':
            if data['action'] == 'create':
                try:
                    tz = timezone.get_current_timezone()
                    start = data.get('mstart') if len(data.get('mstart', '')) != 0 else None
                    end = data.get('mend') if len(data.get('mend', '')) != 0 else None
                    combiner = CombinerModel(user=user, name=data['mname'], description=data['mdesc'],
                                             flow_id=int(data['mflow']), type_id=int(data['mtype']),
                                             output=data['moutput'],
                                             visualizer=True if data.get('mvis', False) else False)
                    combiner.start = tz.localize(dt.strptime(start, '%m/%d/%Y %I:%M %p')) if start is not None else None
                    combiner.end = tz.localize(dt.strptime(end, '%m/%d/%Y %I:%M %p')) if end is not None else None
                    combiner.save()
                    if combiner.visualizer:
                        parties = data.getlist('mparties', None)
                        for party in parties:
                            combiner.parties.add(User.objects.get(pk=int(party)))
                    combid = combiner.id
                    usercode = data['combinercode']
                    usercode = "\n".join(usercode.split("\r\n"))
                    combiner.code = usercode
                    combiner.save()
                    try:
                        compile(usercode, data['mname'] + '.py', 'exec')
                    except BaseException as e:
                        log_n_raise(e, str(sys.exc_info()[1]) + '\n' + repr(sys.exc_info()[1]))

                    if combiner.visualizer and combiner.type.identifier != 'ftc':
                        # Type is not feature collection(ftc), cannot be visualized.
                        raise ValueError(
                            "Visualization is only possible for output type Feature Collection having Point geometry.")

                    request.session['combiner'] = {'name': data['mname'],
                                                   'message': 'Combiner created successfully!'}
                    request.session['showform'] = 'combiner'
                except Exception as e:
                    logger.error(tb.format_exc())
                    merror = 'Please correct the below errors: \n' + e.message
            elif data['action'] == 'delete':
                try:
                    combiner = CombinerModel.objects.get(pk=combid, user=user)
                    mname = combiner.name
                    combiner.ignore = True
                    combiner.save()
                    request.session['combiner'] = {'name': mname, 'message': 'Combiner deleted successfully!'}
                    request.session['showform'] = 'combiner'
                except Exception as e:
                    logger.error(tb.format_exc())
                    merror = 'Please correct the below errors: \n' + e.message
            elif data['action'] == 'save':
                try:
                    tz = timezone.get_current_timezone()
                    start = data.get('mstart') if len(data.get('mstart', '')) != 0 else None
                    end = data.get('mend') if len(data.get('mend', '')) != 0 else None
                    combiner = CombinerModel.objects.get(pk=combid, user=user)
                    combiner.name = data['mname']
                    combiner.description = data['mdesc']
                    combiner.time = timezone.now()
                    combiner.start = tz.localize(dt.strptime(start, '%m/%d/%Y %I:%M %p')) if start is not None else None
                    combiner.end = tz.localize(dt.strptime(end, '%m/%d/%Y %I:%M %p')) if end is not None else None
                    combiner.type = TypeModel.objects.get(pk=int(data['mtype']))
                    combiner.output = data['moutput']
                    usercode = data['combinercode']
                    usercode = "\n".join(usercode.split("\r\n"))
                    combiner.code = usercode
                    combiner.visualizer = True if data.get('mvis', False) else False
                    if combiner.visualizer:
                        parties = data.getlist('mparties', None)
                        combiner.parties.clear()
                        for party in parties:
                            combiner.parties.add(User.objects.get(pk=int(party)))
                    combiner.save()
                    try:
                        compile(usercode, data['mname'] + '.py', 'exec')
                    except BaseException:
                        raise Exception(str(sys.exc_info()[1]) + '\n' + repr(sys.exc_info()[1]))

                    if combiner.visualizer and combiner.type.identifier != 'ftc':
                        # Type is not feature collection(ftc), cannot be visualized.
                        raise ValueError(
                            "Visualization is only possible for output type Feature Collection having Point geometry.")

                    request.session['combiner'] = {'name': data['mname'],
                                                   'message': 'Combiner saved successfully!'}
                    request.session['showform'] = 'combiner'
                except Exception as e:
                    logger.error(tb.format_exc())
                    merror = 'Please correct the below errors: \n' + e.message

        if cerror or werror or merror:
            components = ComponentModel.objects.filter(Q(user=user, ignore=False) |
                                                       Q(viewers=user)).distinct().order_by('-time')
            combiners = CombinerModel.objects.filter(Q(user=user, ignore=False) |
                                                     Q(viewers=user)).distinct().order_by('-time')
            workflows = WorkflowModel.objects.filter(Q(user=user, ignore=False) |
                                                     Q(viewers=user)).distinct().order_by('-time')
            users = User.objects.filter(email__endswith='@gmail.com', is_staff=False, is_superuser=False).order_by(
                'first_name')
            allusers = User.objects.filter(is_staff=False, is_superuser=False).order_by('first_name')
            polygons = PolygonModel.objects.filter(user=user).order_by('-time')
            conditions = ConditionModel.objects.filter(user=user).order_by('-time')
            schedules = ScheduleModel.objects.filter(user=user).order_by('-time')
            types = TypeModel.objects.all().order_by('name')
            params = dict(components=components, workflows=workflows, combiners=combiners, users=users,
                          allusers=allusers, current_user=user,
                          polygons=polygons, conditions=conditions, schedules=schedules, types=types, merror=merror,
                          cerror=cerror, werror=werror, copenid=compid, wopenid=wfid, mopenid=combid, formtype=formtype)
            return render(request, 'workspace.html', params)
        return redirect('/workspace')


class MyAccount(_LoggedInMixin, View):
    def get(self, request):
        params = {}
        return render(request, 'account.html', params)

    def post(self, request):
        params = {}
        return render(request, 'account.html', params)


class UpdateAccount(_LoggedInMixin, View):
    def post(self, request):
        if request.user.is_authenticated():
            user = request.user
            data = request.POST
            user.first_name = data.get('fname')
            user.last_name = data.get('lname')
            user.email = data.get('eaddress')
            params = dict(info="Details successfully updated.")
            if data.get('pwd') is not None and len(data.get('pwd')) > 0:
                if data.get('rpwd') is None or len(data.get('rpwd')) == 0:
                    params = dict(error="Passwords did not match. Please try again!")
                    return render(request, 'account.html', params)
                user.set_password(data.get('pwd'))
                params = dict(info="Details successfully updated. For security reasons, please login again!")
            user.save()
            return render(request, 'account.html', params)
        params = dict(error="Authentication failed. Please login again to make changes.")
        return render(request, 'account.html', params)


class Featureset(_LoggedInMixin, View):
    def post(self, request):
        if socket.gethostname() == 'Jo_SpectreX':
            import requesocks
            http_proxy = "socks5://127.0.0.1:2634"
            session = requesocks.session()
            session.proxies = {
                "http": http_proxy,
                "https": http_proxy
            }
            try:
                response = session.post(WEBSERVICE_HOST + "/featureset", data=json.dumps(
                    {"polygon": json.loads(request.body)}))
            except Exception as e:
                log_n_raise(e)
        else:
            response = requests.post(WEBSERVICE_HOST + "/featureset",
                                     json={"polygon": json.loads(request.body)})
        return HttpResponse(response.text)


class ColumbusService(_LoggedInMixin, View):
    def get(self, request):
        service = request.GET.get('name', None)
        response = None
        if service is not None:
            if service == 'features':
                # response = session.get(WEBSERVICE_HOST + "/features")
                table = request.GET.get('table', None)
                if table is not None:
                    features = request.session.get(table + BQ_FEATURES_SUFFIX, None)
                    if features is None:
                        features = bigquery.get_features(table)
                        request.session[table + BQ_FEATURES_SUFFIX] = {'what': service, 'result': features}
                    return JsonResponse(request.session.get(table + BQ_FEATURES_SUFFIX))
                return JsonResponse({'what': service, 'result': []})
            elif service == 'tables':
                if request.session.get(BQ_TABLES, None) is None:
                    response = bigquery.get_all_tables()
                    request.session[BQ_TABLES] = {'what': service, 'result': response}
                return JsonResponse(request.session[BQ_TABLES])
            elif service == 'distinct':
                feature = request.GET.get('feature', None)
                table = request.GET.get('table', None)
                if feature and table:
                    if request.session.get(table + "#distinct#" + feature, None) is None:
                        response = bigquery.get_distinct_feature(feature, table)
                        request.session[table + "#distinct#" + feature] = {'what': service, 'result': response}
                    return JsonResponse(request.session.get(table + "#distinct#" + feature))
                return JsonResponse({'what': service, 'result': {}})
            elif service == 'first':
                feature = request.GET.get('feature', None)
                table = request.GET.get('table', None)
                if feature and table:
                    if request.session.get(table + "#first#" + feature, None) is None:
                        response = bigquery.get_first_feature(feature, table)
                        request.session[table + "#first#" + feature] = {'what': service, 'result': response}
                    return JsonResponse(request.session.get(table + "#first#" + feature))
                return JsonResponse({'what': service, 'result': {}})
            else:
                if socket.gethostname() == 'Jo_SpectreX':
                    import requesocks
                    http_proxy = "socks5://127.0.0.1:2634"
                    session = requesocks.session()
                    session.proxies = {
                        "http": http_proxy,
                        "https": http_proxy
                    }
                    try:
                        if service == 'localities':
                            response = session.get(WEBSERVICE_HOST + "/locality?names")
                        elif service == 'locality':
                            city = request.GET.get('city', None)
                            if city is not None:
                                response = session.get(WEBSERVICE_HOST + "/locality?featureset&locality=" + city)
                    except Exception as e:
                        log_n_raise(e)
                else:
                    try:
                        if service == 'localities':
                            response = requests.get(WEBSERVICE_HOST + "/locality?names")
                        elif service == 'locality':
                            city = request.GET.get('city', None)
                            if city is not None:
                                response = requests.get(WEBSERVICE_HOST + "/locality?featureset&locality=" + city)
                    except Exception as e:
                        log_n_raise(e)
        if response is not None:
            return HttpResponse(response)
        else:
            return HttpResponse('Invalid Service Request. Please check and try again')
