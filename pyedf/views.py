import csv
import itertools
import json
import re
import sys
import threading
import time
import traceback as tb
from datetime import datetime as dt

import jsonpickle
import psutil
import requests
from colorker.service import bigquery, drive, fusiontables, gee
from colorker.utils import caught, deep_update
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.http import HttpResponse
from django.http import JsonResponse
from django.http.response import HttpResponseRedirect
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import View
from googleapiclient import errors
from oauth2client.client import HttpAccessTokenRefreshError, flow_from_clientsecrets, FlowExchangeError

from columbus import settings
from columbus.settings import *
from pyedf import coreengine
from pyedf.models import *
import remote

USER_SETTINGS = "user_settings"
logger = logging.getLogger(__name__)


def verify(request):
    if request.method == 'POST':
        data = request.POST
        username = data.get('username')
        password = data.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                user_settings = deep_update(coreengine.get_global_settings(), coreengine.get_user_settings(username))
                request.session[USER_SETTINGS] = user_settings
                next = data.get('next', None)
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
        params = {'next': request.GET.get('next', None)}
        return render(request, 'login.html', params)

    def post(self, request):
        return self.get(request)


class Test(_LoggedInMixin, View):
    def get(self, request):
        params = {}
        return render(request, 'test.html', params)

    def post(self, request):
        return self.get(request)


class Galileo(_LoggedInMixin, View):
    def get(self, request):
        params = {}
        return render(request, 'galileo-overview.html', params)

    def post(self, request):
        return self.get(request)


# class HistoryAsync(_LoggedInMixin, View):
#     def get(self, request):
#         what = request.GET.get('what', None)
#         hid = int(request.GET.get('id', 0))
#         if what == "status":
#             history = HistoryModel.objects.get(pk=int(hid), user=self.request.user)
#             end = localtime(history.finish).strftime(
#                 "%a, %d %b %Y - %I:%M:%S %p") if history.finish else 'Not available'
#             duration = str(history.duration) + " seconds" if history.duration > 0 else "--"
#             return JsonResponse(
#                 {'what': what, 'data': {'id': history.id, 'status': history.status,
#                                         'end': end, 'duration': duration}})
#         elif what == "find":
#             histories = HistoryModel.objects.filter(pk__gt=int(hid), user=self.request.user).order_by('pk')
#             if histories:
#                 history = histories[0]
#                 start = localtime(history.start).strftime(
#                     "%a, %d %b %Y - %I:%M:%S %p") if history.start else 'Not available'
#                 end = localtime(history.finish).strftime(
#                     "%a, %d %b %Y - %I:%M:%S %p") if history.finish else 'Not available'
#                 duration = str(history.duration) + " seconds" if history.duration > 0 else "--"
#                 return JsonResponse(
#                     {'what': what, 'data': {'id': history.id, 'status': history.status,
#                                             'end': end, 'duration': duration,
#                                             'name': history.flow.name, 'start': start}})
#             else:
#                 return JsonResponse({"what": what, "data": "none"})
#         return JsonResponse({"what": "unknown", "data": "error"})


class History(_LoggedInMixin, View):
    def get(self, request):
        try:
            hopenid = int(request.GET.get('hopenid', 0))
            if hopenid == 0:
                raise Exception("No instance id provided to view the details of the same.")
            user = self.request.user
            history = HistoryModel.objects.get(user=user, pk=hopenid)
            if history and history.status in ['Running', 'Finished', 'Failed']:
                params = dict(history=history)
                return render(request, 'history.html', params)
            else:
                raise Exception("Either you do not have permission or the instance has not yet started")
        except Exception as e:
            request.session['history_error'] = e.message
            return HttpResponseRedirect('/dashboard')

    def post(self, request):
        return self.get(request)


class Importer(_LoggedInMixin, View):
    def post(self, request):
        try:
            data = request.POST
            ft_name = str(data.get('ft-name', None))
            name_field = str(data.get('name-field', None))
            geometry_field = str(data.get('geometry-field', None))
            if ft_name and name_field and geometry_field:
                polygons = fusiontables.get_polygons_from_ft(
                    table_id=ft_name, name_attr=name_field, geometry_attr=geometry_field,
                    user_settings=self.request.session[USER_SETTINGS])
                for polygon in polygons:
                    PolygonModel(user=self.request.user, name=polygon['name'],
                                 json=jsonpickle.encode(polygon['geometry'], unpicklable=False)).save()
            request.session['showform'] = 'other'
            return JsonResponse({'what': 'import', 'result': 'success', 'message': 'Import successful'})
        except BaseException as e:
            logger.error(traceback.format_exc())
            return JsonResponse({'what': 'import', 'result': 'failure', 'message': e.message})


class Dashboard(_LoggedInMixin, View):
    def get(self, request):
        error = request.session.get('history_error', None)
        request.session['history_error'] = None
        q = request.GET.get('q', 'all')
        from_ = int(request.GET.get('from', 0))
        what = request.GET.get('get', 'n')
        from_ = from_ - 1 if what == 'p' else from_
        records = int(request.GET.get('r', 50))
        statuses = {}
        users = []
        if q == 'retry':
            hid = request.GET.get('id', 0)
            rh = HistoryModel.objects.filter(pk=int(hid), user=self.request.user).first()
            if rh is not None:
                FlowStatusModel.objects.filter(history=rh).delete()
                TargetHistoryModel.objects.filter(history=rh).delete()
                rh.status = 'Pending'
                rh.start = None
                rh.finish = None
                rh.save()
                coreengine.Supervisor().awake_scheduler()
        if q == 'delete':
            hid = request.GET.get('id', 0)
            rh = HistoryModel.objects.filter(pk=int(hid), user=self.request.user).first()
            if rh is not None:
                fsms = FlowStatusModel.objects.filter(history=rh)
                for fsm in fsms:
                    if fsm.ftkey:
                        try:
                            fusiontables.delete_table(fsm.ftkey, request.session[USER_SETTINGS])
                        except:
                            logger.error("Failed to delete fusion table %s" % str(fsm.ftkey))
                    if fsm.gcs_pickle:
                        pickle = str(fsm.gcs_pickle).split('#')
                        try:
                            gee.delete_object(bucket=pickle[0], filename=pickle[1],
                                              user_settings=self.request.session[USER_SETTINGS])
                        except:
                            logger.error("Failed to delete gcs pickle %s" % str(fsm.gcs_pickle))
                fsms.delete()
                TargetHistoryModel.objects.filter(history=rh).delete()
                DataSourceModel.objects.filter(history=rh).delete()
                rh.delete()
        workflows = HistoryModel.objects.filter(user=self.request.user)
        user_flows = HistoryModel.objects.filter(~Q(user=self.request.user))
        statuses["all"] = workflows.count()
        flow_groups = workflows.values('status').annotate(num_status=Count('status'))
        for group in flow_groups:
            statuses[str(group['status']).lower()] = group['num_status']
        if q == 'pending':
            workflows = workflows.filter(status='Pending')
            user_flows = user_flows.filter(status='Pending')
        elif q == 'running':
            workflows = workflows.filter(status='Running')
            user_flows = user_flows.filter(status='Running')
        elif q == 'queued':
            workflows = workflows.filter(status='Queued')
            user_flows = user_flows.filter(status='Queued')
        elif q == 'finished':
            workflows = workflows.filter(status='Finished').order_by('-finish')
            user_flows = user_flows.filter(status='Finished')
        elif q == 'failed':
            workflows = workflows.filter(status='Failed')
            user_flows = user_flows.filter(status='Failed')
        else:
            q = 'all'
        other_user_flows = user_flows.count()
        total_flows = workflows.count() + user_flows.count()
        total = workflows.count()
        users.append([str(self.request.user.last_name), workflows.count(), max(total_flows, 1)])
        user_groups = user_flows.values('user__last_name').annotate(num_flows=Count('user')).order_by('-num_flows')[:3]
        for group in user_groups:
            users.append([str(group['user__last_name']), group['num_flows'], max(total_flows, 1)])
            other_user_flows -= group['num_flows']
        workflows = workflows[from_:min(from_ + records, total)] if what == 'n' else workflows[max(
            from_ - records, 0):from_]
        for workflow in workflows:
            sources = DataSourceModel.objects.filter(history_id=workflow.id)
            if sources:
                workflow.targets = dict()
                for source in sources:
                    workflow.targets[source.target.name] = jsonpickle.decode(source.query)
        users.append(['Others', other_user_flows, max(total_flows, 1)])
        start = from_ + 1 if what == 'n' else max(from_ - records, 0) + 1
        end = min(start + records - 1, total)
        params = dict(statuses=statuses, users=users, workflows=workflows, selected=q, start=start,
                      end=end, total=total, error=error)
        return render(request, 'dashboard.html', params)

    def post(self, request):
        return self.get(request)


class ControlPanel(_LoggedInMixin, View):
    def get(self, request):
        if not self.request.user.is_superuser:
            return HttpResponseRedirect('/home')
        cp_error = self.request.session.get('controlpanel.actionfailure', None)
        self.request.session['controlpanel.actionfailure'] = None
        q = request.GET.get('q', None)
        if q is None:
            supervisor = coreengine.Supervisor()
            connected_workers = supervisor.get_all_workers()
            expected_workers = list(settings.WORKERS)
            workers = []
            for hostname, worker_repr in connected_workers:
                if hostname in expected_workers:
                    expected_workers.remove(hostname)
                    workers.append((hostname, worker_repr))
            for hostname in expected_workers:
                workers.append((hostname, None))
            params = dict(workers=workers, container_size_mb=settings.CONTAINER_SIZE_MB, cp_error=cp_error,
                          is_recording=supervisor.is_recording())
            return render(request, 'control-panel.html', params)
        else:
            if q == 'snapshot':
                host = request.GET.get('host', None)
                supervisor = coreengine.Supervisor()
                if host is None:
                    return JsonResponse({'what': 'error', 'result': 'hostname is required to get the snapshot'})
                else:
                    snapshot = supervisor.get_worker_snapshot(host)
                return JsonResponse(snapshot)
            return JsonResponse({'what': 'error', 'result': 'Query not supported - %s' % q})

    def post(self, request):
        if not self.request.user.is_superuser:
            return JsonResponse(
                {'what': 'error', 'message': '''Unauthorized access. You do not have sufficient privileges
                to perform this action. If you believe that this is an error, please contact the administrator.
                If you\'re the administrator you must know what to do.'''})
        data = request.POST
        action = data.get('worker-action', 'unknown')
        expected_workers = list(settings.WORKERS)
        selected_workers = []
        for worker in expected_workers:
            if data.get("%s.cb" % worker, None):
                selected_workers.append(worker)
        master_port = settings.SUPERVISOR_PORT
        ssh_user = settings.WORKER_SSH_USER
        ssh_port = settings.WORKER_SSH_PORT
        password = settings.WORKER_SSH_PASSWORD
        ssh_pkey = settings.WORKER_SSH_PRIVATE_KEY
        venv_path = settings.WORKER_VIRTUAL_ENV
        supervisor = coreengine.Supervisor()
        messages = []
        if action == 'start-recording':
            supervisor.record_activity()
        elif action == 'stop-recording':
            supervisor.stop_recording()
        else:
            for worker in selected_workers:
                try:
                    if action == 'start':
                        remote.start_worker(hostname=worker, master_port=master_port, virtualenv=venv_path,
                                            port=ssh_port, username=ssh_user, password=password, key_filename=ssh_pkey)
                        supervisor.await_connect(worker)
                    elif action == 'force-stop':
                        remote.force_stop_worker(hostname=worker, port=ssh_port, username=ssh_user,
                                                 password=password, key_filename=ssh_pkey)
                        supervisor.remove_worker(worker)
                    elif action == 'install':
                        remote.install_worker(hostname=worker, virtualenv=venv_path, upgrade=False, port=ssh_port,
                                              username=ssh_user, password=password, key_filename=ssh_pkey)
                    elif action == 'upgrade':
                        remote.install_worker(hostname=worker, virtualenv=venv_path, upgrade=True, port=ssh_port,
                                              username=ssh_user, password=password, key_filename=ssh_pkey)
                    elif action == 'install-prerequisites':
                        remote.install_prerequisites(hostname=worker, port=ssh_port, username=ssh_user,
                                                     password=password, key_filename=ssh_pkey)
                    elif action == 'stop':
                        supervisor.stop_worker(worker)
                    else:
                        return JsonResponse({'what': 'error', 'result': 'unknown action command: %s' % action})
                except BaseException as e:
                    logger.error("Failed to perform the action '%s' on host %s" % (action, worker))
                    logger.error(traceback.format_exc())
                    messages.append("Failed to perform the action '%s' on host %s. Reason: %s" % (
                        action, worker, e.message))
        if len(messages) > 0:
            self.request.session['controlpanel.actionfailure'] = "\n".join(messages)
            return JsonResponse({'what': action,
                                 'result': 'Action failed on some or all of the workers.'})
        return JsonResponse({'what': action, 'result': 'Action performed successfully'})


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
            history.refresh_from_db()
            statuses = FlowStatusModel.objects.filter(pk__gt=int(fsid), history=history).order_by('pk')
            if statuses:
                results = []
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
            else:
                return JsonResponse({'status': 'wait', 'message': 'No new events found for the selected instance'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': e.message})


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


class OAuth2Handler(_LoggedInMixin, View):
    def get_drive_credentials(self, authorization_code):
        """Exchange an authorization code for OAuth 2.0 credentials.

        Args:
          authorization_code: Authorization code to exchange for OAuth 2.0
                              credentials.
        Returns:
          oauth2client.client.OAuth2Credentials instance.
        Raises:
          CodeExchangeException: an error occurred.
        """
        oauth2_callback = "%s://%s/oauth2callback" % (self.request.scheme, self.request.get_host())
        scopes = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/fusiontables']
        flow = flow_from_clientsecrets(GD_CREDENTIALS, ' '.join(scopes))
        flow.redirect_uri = oauth2_callback
        try:
            credentials = flow.step2_exchange(authorization_code)
            return credentials
        except FlowExchangeError, error:
            logging.error('An error occurred: %s', error)
            raise CodeExchangeException(None)

    def get(self, request):
        state = request.GET.get('state', None)
        code = request.GET.get('code', None)
        try:
            credentials = self.get_drive_credentials(code)
            security = ClientSecurityModel.objects.filter(user=self.request.user).first()
            if security:
                security.credentials = credentials.to_json()
            else:
                security = ClientSecurityModel(user=self.request.user, credentials=credentials.to_json())
            security.service = 'drive'
            security.save()
            username = self.request.user.username
            user_settings = deep_update(coreengine.get_global_settings(), coreengine.get_user_settings(username))
            request.session[USER_SETTINGS] = user_settings
            return HttpResponseRedirect(state)
        except Exception as e:
            logger.error(tb.format_exc())
            request.session['sferror'] = e.message
            return HttpResponseRedirect('/home')


class DatasourceAsync(_LoggedInMixin, View):
    def get_drive_auth_url(self, state):
        """Retrieve the authorization URL.
        Args:
          state: State for the authorization URL.
        Returns:
          Authorization URL to redirect the user to.
        """
        oauth2_callback = "%s://%s/oauth2callback" % (self.request.scheme, self.request.get_host())
        logger.info("oauth2callback: %s" % oauth2_callback)
        scopes = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/fusiontables']
        flow = flow_from_clientsecrets(GD_CREDENTIALS, scope=' '.join(scopes), redirect_uri=oauth2_callback)
        flow.params['access_type'] = 'offline'
        flow.params['approval_prompt'] = 'force'
        flow.params['state'] = state
        return flow.step1_get_authorize_url()

    def get(self, request):
        source = request.GET.get('source', None)
        if source == 'drive':
            security = ClientSecurityModel.objects.filter(user=self.request.user).first()
            if security:
                run_type = request.GET.get('runtype', 'for')
                try:
                    result = drive.list_files(
                        query="mimeType = 'application/vnd.google-apps.fusiontable' or \
                                mimeType = 'application/vnd.google-apps.folder' or fileExtension='csv' \
                                and trashed = false" if run_type == 'for' else "mimeType = \
                                'application/vnd.google-apps.folder' and trashed = false",
                        order_by="viewedByMeTime desc", files=True if run_type == 'for' else False,
                        user_settings=request.session[USER_SETTINGS])
                    return JsonResponse({'what': 'files', 'result': result})
                except errors.HttpError, err:
                    if err.resp.status == 401:
                        return JsonResponse(
                            {'what': 'authorize', 'result': self.get_drive_auth_url('/home')})
                except HttpAccessTokenRefreshError:
                    return JsonResponse(
                        {'what': 'authorize', 'result': self.get_drive_auth_url('/home')})
                except Exception as e:
                    logger.error(tb.format_exc())
                    return JsonResponse({'what': 'error', 'result': e.message})
            else:
                return JsonResponse(
                    {'what': 'authorize', 'result': self.get_drive_auth_url('/home')})
        elif source == 'workflow':
            flow_id = request.GET.get('id', None)
            if flow_id is None:
                return JsonResponse({'what': 'error', 'result': 'No flow id specified'})
            workflow = WorkflowModel.objects.get(pk=int(flow_id))
            try:
                result = coreengine.get_target_dictionaries(workflow.component_id, root=True)
                return JsonResponse({'what': 'components', 'result': result})
            except Exception as e:
                logger.error(tb.format_exc())
                return JsonResponse({'what': 'error', 'result': e.message})
        return JsonResponse({'what': 'error', 'result': 'Unknown source specified - ' + str(source)})


class Download(_LoggedInMixin, View):
    def get(self, request):
        hid = int(request.GET.get('flowid', None))
        fsid = int(request.GET.get('fsid', None))
        ftcindex = int(request.GET.get('ftcindex', 0))
        history = HistoryModel.objects.get(pk=hid)
        details = "%s-%d-%d-%d" % (history.flow.name, hid, fsid, ftcindex)
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
                            fusiontables.delete_table(status.ftkey, request.session[USER_SETTINGS])
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


class WorkflowReview(_LoggedInMixin, View):
    def get(self, request):
        try:
            instances = request.session.get('review-instances', None)
            if instances is None:
                return HttpResponseRedirect('/home')
            return render(request, 'review.html', instances)
        except Exception as e:
            logger.error(tb.format_exc())
            request.session['sferror'] = e.message
            return HttpResponseRedirect('/home')

    def post(self, request):
        try:
            instances = request.session.get('review-instances', None)
            if instances is None:
                raise Exception("No instances found for the chosen workflow.")
            return render(request, 'review.html', instances)
        except Exception as e:
            logger.error(tb.format_exc())
            request.session['sferror'] = e.message
            return HttpResponseRedirect('/home')


def create_workflow_instances(indices, data, instances, user, local_pickle, global_pickle, flow):
    for i in indices:
        if data.get('i%d-select' % i, None):
            priority = int(data.get('i%d-priority', 3))
            history = HistoryModel(user=user, local_pickle=local_pickle, global_pickle=global_pickle,
                                   priority=priority, flow=flow)
            history.save()
            instance = instances['instances']['i%d' % i]
            for part in instance:
                q = part['query']
                for target in part['targets']:
                    DataSourceModel(source=q['source'], identifier=q['identifier'], query=jsonpickle.encode(q),
                                    target_id=int(target['id']), history_id=history.id).save()


class WorkflowGenerator(_LoggedInMixin, View):
    def get(self, request):
        return HttpResponseRedirect('/home')

    def post(self, request):
        try:
            instances = request.session.get('review-instances', None)
            if instances is None:
                raise Exception("No instances found for the chosen workflow.")
            data = self.request.POST
            flow_id = instances['flow_id']
            user = self.request.user
            flow = WorkflowModel.objects.get(pk=int(flow_id))
            picklable_flow = coreengine.Workflow(id=0, name=flow.name, flow_id=flow.id, component_id=flow.component_id,
                                                 user=user.username)
            millis = int(round(time.time() * 1000))
            directory = "%s/%s/pickles/proto/wid%d" % (USER_DIRPATH, picklable_flow.user, flow.id)
            filename = "wid%dt%d.pickle" % (flow.id, millis)
            response = picklable_flow.serialize(directory, filename, request.session[USER_SETTINGS])
            local_pickle = "%s/%s" % (directory, filename)
            global_pickle = "%s#%s" % (response['bucket'], response['name'])

            per_thread_max = 25
            if instances['instance_count'] <= per_thread_max:
                create_workflow_instances(range(instances['instance_count']), data, instances,
                                          user, local_pickle, global_pickle, flow)
            else:
                instance_count = instances['instance_count']
                num_threads, threads = instance_count // per_thread_max, []
                for i in range(num_threads):
                    indices = range(i * per_thread_max,
                                    (i + 1) * per_thread_max if i < num_threads - 1 else max(
                                        (i + 1) * per_thread_max, instance_count))
                    t = threading.Thread(target=create_workflow_instances,
                                         args=(indices, data, instances, user, local_pickle, global_pickle, flow))
                    t.start()
                    threads.append(t)
                for thread in threads:
                    thread.join()
            request.session['review-instances'] = None
            coreengine.Supervisor().awake_scheduler()
            return JsonResponse({"what": "instances", "result": "success"})
        except Exception as e:
            logger.error(tb.format_exc())
            return JsonResponse({"what": "error", "result": "failure", "message": e.message})


class StartFlow(_LoggedInMixin, View):
    def post(self, request):
        try:
            data = request.POST
            flow_choices = data.get('flowChoices', None)
            if flow_choices is None:
                raise Exception("No flow sources found. Please try again")
            frozen_choices = jsonpickle.decode(flow_choices)
            workflow = WorkflowModel.objects.get(pk=int(frozen_choices['workflow']))
            root_components = coreengine.get_target_dictionaries(workflow.component_id, root=True)
            for root_component in root_components:
                if root_component not in frozen_choices['components']:
                    raise Exception("List of root components for the flow %s was compromised." % workflow.name)
                if str(root_component["id"]) not in frozen_choices['frozen']:
                    raise Exception("Component %s is missing the data source." % str(root_component["name"]))

            def find_cycle(frozen_source, all_frozen_components):
                if int(frozen_source['component']) in all_frozen_components:
                    raise Exception("Cyclic dependency exists among the data sources of the components")
                else:
                    all_frozen_components.append(int(frozen_source['component']))
                    if frozen_choices['frozen'][str(frozen_source['component'])]['source'] == 'component':
                        find_cycle(frozen_choices['frozen'][str(frozen_source['component'])], all_frozen_components)

            def find_component(frozen_source):
                if frozen_choices['frozen'][str(frozen_source['component'])]['source'] == 'component':
                    find_component(frozen_choices['frozen'][str(frozen_source['component'])])
                return str(frozen_source['component'])

            actual_sources = {}
            for frozen_comp in frozen_choices['frozen']:
                if frozen_choices['frozen'][frozen_comp]['source'] == 'component':
                    find_cycle(frozen_choices['frozen'][frozen_comp], [])
                else:
                    actual_sources[frozen_comp] = frozen_choices['frozen'][frozen_comp]
                    actual_sources[frozen_comp]['targets'] = set()
                    actual_sources[frozen_comp]['targets'].add(frozen_comp)

            for frozen_comp in frozen_choices['frozen']:
                if frozen_choices['frozen'][frozen_comp]['source'] == 'component':
                    comp = find_component(frozen_choices['frozen'][frozen_comp])
                    actual_sources[comp]['targets'].add(frozen_comp)

            all_targets = coreengine.get_target_dictionaries(workflow.component_id)
            all_targets_dict = {}
            combiner_count = 0
            for target in all_targets:
                all_targets_dict[str(target['id'])] = target
                if target['type'] == 'combiner':
                    combiner_count += 1
                    actual_sources[target['id']] = {'source': 'combiner', 'identifier': target['id'],
                                                    'targets': [target['id']]}
            root_count = len(root_components)
            non_root_count = len(all_targets) - combiner_count - root_count

            instances = dict(flow_id=workflow.id, flow_name=workflow.name, root=root_count, non_root=non_root_count,
                             combiners=combiner_count, total=len(all_targets), sources=len(actual_sources),
                             all_targets=all_targets_dict)
            source_id = 0
            total_instances = 1
            for key in actual_sources:
                queries = coreengine.serialize_query(actual_sources[key], self.request.session[USER_SETTINGS])
                queries_json = [query.__dict__ for query in queries]
                total_instances *= len(queries)
                if total_instances > 10000:
                    raise Exception(("Request resulting in too many instances (>10000) of the selected workflow. "
                                     "Consider changing the criteria for data sources."))
                instances['source-%d' % source_id] = dict(targets=list(actual_sources[key]['targets']),
                                                          queries=queries_json)
                source_id += 1

            instances['instance_count'] = total_instances

            sources = ['source-%d' % i for i in range(instances['sources'])]
            query_lists = [range(len(instances[source]['queries'])) for source in sources]
            instances['instances'] = dict()
            for i, product in enumerate(itertools.product(*query_lists)):
                indices = list(product)
                instances['instances']["i%d" % i] = list()
                for j, query_index in enumerate(indices):
                    targets = []
                    for target_id in instances['source-%d' % j]['targets']:
                        targets.append(instances['all_targets'][str(target_id)])
                    instances['instances']["i%d" % i].append(
                        dict(targets=targets, query=instances['source-%d' % j]['queries'][query_index]))
            request.session['review-instances'] = instances
            return JsonResponse({'what': 'instances', 'result': 'success'})
        except BaseException as e:
            logger.error(tb.format_exc())
            message = str(e.message)
            if isinstance(e, KeyError):
                message += " is missing in the sources."
            return JsonResponse({'what': "error", 'message': message})


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
            logger.error(e.message)
            logger.error(tb.format_exc())
            raise e


class WorkspaceAsync(_LoggedInMixin, View):
    def get(self, request):
        user = self.request.user
        name = request.GET.get('name', None)
        if name == 'constraint':
            table = request.GET.get('table', None)
            source = request.GET.get('source', None)
            conditions = ConditionModel.objects.filter(user=user, table=table, source=source).order_by('-time')
            result = []
            for condition in conditions:
                result.append(dict(id=condition.id, name=condition.name, expression=condition.get_string(),
                                   table=condition.table, source=condition.source,
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
                                                     table=data['constraint-table'], source=data['constraint-source'])
                else:
                    condition = ComplexConditionModel(name=data['constraint-name'], user=user, time=timezone.now(),
                                                      type='complex', left_id=int(data['constraint-left']),
                                                      joint=data['joint'], right_id=int(data['constraint-right']),
                                                      table=data['constraint-table'], source=data['constraint-source'])
                    if caught(ComplexConditionModel.validate, condition):
                        return JsonResponse({"result": "error",
                                             "message": "Invalid constraint. Must be in disjunctive normal form."})
                    if condition.left.source != condition.right.source:
                        return JsonResponse({"result": "error", "message": ("Invalid constraint. Both left and right "
                                                                            "constraints must be from same source.")})
                condition.save()
                message = dict(id=condition.id, name=condition.name, expression=str(condition),
                               source=condition.source, table=condition.table,
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
                                ParentComponentsModel(component_id=component.id, parent_id=int(result[1])).save()
                                # component.parents.add(ComponentModel.objects.get(pk=int(result[1])))
                            else:
                                ParentCombinersModel(component_id=component.id, combiner_id=int(result[1])).save()
                                # component.combiners.add(CombinerModel.objects.get(pk=int(result[1])))

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
                        logger.error(tb.format_exc())
                        raise type(e)(str(sys.exc_info()[1]) + '\n' + repr(sys.exc_info()[1]))

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
                        logger.error(tb.format_exc())
                        raise type(e)(str(sys.exc_info()[1]) + '\n' + repr(sys.exc_info()[1]))

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
        drive_service = ServerSecurityModel.objects.filter(user=self.request.user, service='drive').first()
        bigquery_service = ServerSecurityModel.objects.filter(user=self.request.user, service='bigquery').first()
        earthengine_service = ServerSecurityModel.objects.filter(user=self.request.user, service='earthengine').first()
        storage_service = ServerSecurityModel.objects.filter(user=self.request.user, service='storage').first()
        params = {"drive": drive_service, "bigquery": bigquery_service, "earthengine": earthengine_service,
                  "storage": storage_service}
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
            drive_service = ServerSecurityModel.objects.filter(user=self.request.user, service='drive').first()
            bigquery_service = ServerSecurityModel.objects.filter(user=self.request.user, service='bigquery').first()
            earthengine_service = ServerSecurityModel.objects.filter(user=self.request.user,
                                                                     service='earthengine').first()
            storage_service = ServerSecurityModel.objects.filter(user=self.request.user, service='storage').first()
            if drive_service and data.get('drive-key', ''):
                drive_service.credentials = data.get('drive-key', '')
                drive_service.save()
            elif data.get('drive-key', ''):
                drive_service = ServerSecurityModel(service='drive', user=user, credentials=data.get('drive-key', ''))
                drive_service.save()

            if bigquery_service and data.get('bigquery-key', ''):
                bigquery_service.credentials = data.get('bigquery-key', '')
                bigquery_service.save()
            elif data.get('bigquery-key', ''):
                bigquery_service = ServerSecurityModel(
                    service='bigquery', user=user, credentials=data.get('bigquery-key', ''))
                bigquery_service.save()

            if earthengine_service and data.get('ee-key', ''):
                earthengine_service.credentials = data.get('ee-key', '')
                earthengine_service.bucket = data.get('ee-bucket', '')
                earthengine_service.save()
            elif data.get('ee-key', ''):
                earthengine_service = ServerSecurityModel(
                    service='earthengine', user=user, credentials=data.get('ee-key', ''),
                    bucket=data.get('ee-bucket', ''))
                earthengine_service.save()

            if storage_service and data.get('gcs-key', ''):
                storage_service.credentials = data.get('gcs-key', '')
                storage_service.bucket = data.get('gcs-bucket', '')
                storage_service.save()
            elif data.get('gcs-key', ''):
                storage_service = ServerSecurityModel(service='storage', user=user, credentials=data.get('gcs-key', ''),
                                                      bucket=data.get('gcs-bucket', ''))
                storage_service.save()

            params = dict(info="Details successfully updated.", drive=drive_service, bigquery=bigquery_service,
                          earthengine=earthengine_service, storage=storage_service)
            if data.get('pwd') is not None and len(data.get('pwd')) > 0:
                if data.get('rpwd') is None or len(data.get('rpwd')) == 0:
                    params = dict(error="Passwords did not match. Please try again!", drive=drive_service,
                                  bigquery=bigquery_service, earthengine=earthengine_service, storage=storage_service)
                    return render(request, 'account.html', params)
                user.set_password(data.get('pwd'))
                params = dict(info="Details successfully updated. For security reasons, please login again!",
                              drive=drive_service, bigquery=bigquery_service, earthengine=earthengine_service,
                              storage=storage_service)
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
                logger.error(tb.format_exc())
                raise e
        else:
            response = requests.post(WEBSERVICE_HOST + "/featureset",
                                     json={"polygon": json.loads(request.body)})
        return HttpResponse(response.text)


class GalileoService(_LoggedInMixin, View):
    def get(self, request):
        route = request.GET.get("route", None)
        if route is None:
            return JsonResponse({"what": "error", "result": "Invalid request. No route specified"})
        else:
            response = dict(what="error", reason="unsupported operation", request=route)
            if route == "filesystem":
                query = request.GET.get("q", "names")
                if query == "names":
                    response = request.session.get("galileo#filesystem?names", None)
                    if response is None:
                        service = WEBSERVICE_HOST + "/filesystem?names&timezone=" + str(TIME_ZONE)
                        response = jsonpickle.decode(requests.get(service).text)["result"]
                        request.session["galileo#filesystem?names"] = response
                    return JsonResponse({"what": "filesystem#names", "result": response})
                elif query == "overview":
                    name = request.GET.get("name", None)
                    response = request.session.get("galileo#filesystem?overview&name=" + str(name), None)
                    if response is None:
                        service = WEBSERVICE_HOST + "/filesystem?overview&name=" + str(name) + "&timezone=" + str(
                            TIME_ZONE)
                        response = jsonpickle.decode(requests.get(service).text)["result"]
                        request.session["galileo#filesystem?overview&name=" + str(name)] = response
                    return JsonResponse({"what": "filesystem#overview", "result": response})
            elif route == "features":
                fsname = request.GET.get("fsname", None)
                if fsname:
                    response = request.session.get("galileo#features?fsname=" + str(fsname), None)
                    if response is None:
                        service = WEBSERVICE_HOST + "/features?filesystem=" + str(fsname)
                        response = jsonpickle.decode(requests.get(service).text)["result"]
                        request.session["galileo#features?fsname=" + str(fsname)] = response
                    return JsonResponse({"what": "filesystem#overview", "result": response})
            if "error" == response.get("what", None):
                return JsonResponse({"what": "error", "result": response.get("reason"),
                                     "request": response.get("request")})
            return JsonResponse(response)

    def post(self, request):
        route = request.GET.get("route", None)
        return JsonResponse({"what": "error", "result": "Unsupported opertaions for the route " + str(route)})


class BigqueryService(_LoggedInMixin, View):
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
                        features = bigquery.get_features(table, request.session[USER_SETTINGS])
                        request.session[table + BQ_FEATURES_SUFFIX] = {'what': service, 'result': features}
                    return JsonResponse(request.session.get(table + BQ_FEATURES_SUFFIX))
                return JsonResponse({'what': service, 'result': []})
            elif service == 'tables':
                if request.session.get(BQ_TABLES, None) is None:
                    response = bigquery.get_all_tables(request.session[USER_SETTINGS])
                    request.session[BQ_TABLES] = {'what': service, 'result': response}
                return JsonResponse(request.session[BQ_TABLES])
            elif service == 'distinct':
                feature = request.GET.get('feature', None)
                table = request.GET.get('table', None)
                if feature and table:
                    if request.session.get(table + "#distinct#" + feature, None) is None:
                        response = bigquery.get_distinct_feature(feature, table, request.session[USER_SETTINGS])
                        request.session[table + "#distinct#" + feature] = {'what': service, 'result': response}
                    return JsonResponse(request.session.get(table + "#distinct#" + feature))
                return JsonResponse({'what': service, 'result': {}})
            elif service == 'first':
                feature = request.GET.get('feature', None)
                table = request.GET.get('table', None)
                if feature and table:
                    if request.session.get(table + "#first#" + feature, None) is None:
                        response = bigquery.get_first_feature(feature, table, request.session[USER_SETTINGS])
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
                        logger.error(tb.format_exc())
                        raise e
                else:
                    try:
                        if service == 'localities':
                            response = requests.get(WEBSERVICE_HOST + "/locality?names")
                        elif service == 'locality':
                            city = request.GET.get('city', None)
                            if city is not None:
                                response = requests.get(WEBSERVICE_HOST + "/locality?featureset&locality=" + city)
                    except Exception as e:
                        logger.error(tb.format_exc())
                        raise e
        if response is not None:
            return HttpResponse(response)
        else:
            return HttpResponse('Invalid Service Request. Please check and try again')
