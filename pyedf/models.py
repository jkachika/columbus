import logging
import traceback

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.timezone import localtime

logger = logging.getLogger(__name__)


# Create your models here.
class ConditionModel(models.Model):
    class Meta:
        db_table = 'all_conditions'

    name = models.CharField(max_length=1000)
    user = models.ForeignKey('auth.User')
    time = models.DateTimeField(db_column='created_on', default=timezone.now)
    type = models.CharField(max_length=100)
    source = models.CharField(max_length=1000, default="unknown")
    table = models.CharField(max_length=1000)

    def get_condition(self):
        if self.type == 'complex':
            return ComplexConditionModel.objects.get(pk=self.id)
        return SimpleConditionModel.objects.get(pk=self.id)

    def get_string(self):
        return str(self.get_condition())

    def get_json(self):
        return self.get_condition().json()


class SimpleConditionModel(ConditionModel):
    class Meta:
        db_table = 'simple_conditions'

    key = models.OneToOneField(ConditionModel, primary_key=True, db_column='conditions_pk', parent_link=True)
    feature = models.CharField(max_length=255)
    op = models.CharField(max_length=10)
    value = models.CharField(max_length=255)
    primitive = models.SmallIntegerField(default=9)  # 9 represents a STRING data type in galileo

    def json(self):
        # do not change key values - this is same as in galileo
        return {"feature": self.feature, "op": self.op, "value": self.value, "primitive": self.primitive}

    def __str__(self):
        if self.primitive != 9:
            return "(" + self.feature + " " + self.op + " " + self.value + ")"
        return "(" + self.feature + " " + self.op + " '" + self.value + "')"


class ComplexConditionModel(ConditionModel):
    class Meta:
        db_table = 'complex_conditions'

    key = models.OneToOneField(ConditionModel, primary_key=True, db_column='conditions_pk', parent_link=True)
    left = models.ForeignKey('ConditionModel', on_delete=models.CASCADE, related_name='left_condition')
    joint = models.CharField(max_length=100)
    right = models.ForeignKey('ConditionModel', on_delete=models.CASCADE, related_name='right_condition')

    @staticmethod
    def verify_and(condition):
        if isinstance(condition, ComplexConditionModel):
            if condition.joint != "and":
                raise ValueError("Invalid expression. Must be in disjunctive normal form")
            ComplexConditionModel.verify_and(condition.left.get_condition())
            ComplexConditionModel.verify_and(condition.right.get_condition())

    @staticmethod
    def verify_or(condition):
        if isinstance(condition, ComplexConditionModel):
            if condition.joint == "and":
                ComplexConditionModel.verify_and(condition.left.get_condition())
                ComplexConditionModel.verify_and(condition.right.get_condition())
            else:
                ComplexConditionModel.verify_or(condition.left.get_condition())
                ComplexConditionModel.verify_or(condition.right.get_condition())

    @staticmethod
    def validate(condition):
        if condition.joint == "and":
            ComplexConditionModel.verify_and(condition)
        else:
            ComplexConditionModel.verify_or(condition)

    def json(self):
        # do not change key values - this is same as in galileo
        left_cond = ComplexConditionModel.objects.get(
            pk=self.left.id) if self.left.type == 'complex' else SimpleConditionModel.objects.get(pk=self.left.id)
        right_cond = ComplexConditionModel.objects.get(
            pk=self.right.id) if self.right.type == 'complex' else SimpleConditionModel.objects.get(pk=self.right.id)
        return {"left": left_cond.json(), "joint": self.joint, "right": right_cond.json()}

    def __str__(self):
        left_cond = ComplexConditionModel.objects.get(
            pk=self.left.id) if self.left.type == 'complex' else SimpleConditionModel.objects.get(pk=self.left.id)
        right_cond = ComplexConditionModel.objects.get(
            pk=self.right.id) if self.right.type == 'complex' else SimpleConditionModel.objects.get(pk=self.right.id)
        return "(" + str(left_cond) + " " + self.joint + " " + str(right_cond) + ")"


class TypeModel(models.Model):
    class Meta:
        db_table = 'supported_types'

    name = models.CharField(max_length=255)
    identifier = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return "{id: %d, name: %s, identifier: %s}" % (self.id, self.name, self.identifier)


class TargetModel(models.Model):
    class Meta:
        db_table = 'all_targets'

    name = models.CharField(max_length=255)
    description = models.CharField(max_length=1000)
    type = models.ForeignKey('TypeModel', null=True)
    target_type = models.CharField(max_length=50)
    output = models.TextField(db_column='output_desc')
    code = models.TextField()
    user = models.ForeignKey('auth.User')
    time = models.DateTimeField(db_column='created_on', default=timezone.now)
    visualizer = models.BooleanField(default=False)
    ignore = models.BooleanField(default=False)
    parties = models.ManyToManyField('auth.User', db_table='target_parties', symmetrical=False,
                                     related_name='parties')
    viewers = models.ManyToManyField('auth.User', db_table='target_viewers', symmetrical=False,
                                     related_name='viewers')


class ParentComponentsModel(models.Model):
    class Meta:
        db_table = 'parent_components'

    component = models.ForeignKey('ComponentModel', to_field='key', db_column='component_id',
                                  related_name='child_component')
    parent = models.ForeignKey('ComponentModel', to_field='key', db_column='parent_id',
                               related_name='parent_component')


class ParentCombinersModel(models.Model):
    class Meta:
        db_table = 'parent_combiners'

    component = models.ForeignKey('ComponentModel', to_field='key', db_column='component_id')
    combiner = models.ForeignKey('CombinerModel', to_field='key', db_column='combiner_id')


class ComponentModel(TargetModel):
    class Meta:
        # overriding the default table name with the following name
        db_table = 'all_components'
        verbose_name = 'all_components'
        get_latest_by = 'time'

    key = models.OneToOneField(TargetModel, primary_key=True, db_column='targets_pk', parent_link=True)
    parents = models.ManyToManyField('ComponentModel', through=ParentComponentsModel,
                                     symmetrical=False, related_name='parent_components')
    combiners = models.ManyToManyField('CombinerModel', through=ParentCombinersModel,
                                       symmetrical=False, related_name='parent_combiners')
    root = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        try:
            super(ComponentModel, self).save(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise Exception("Something went wrong while saving the component. Details - %s" % e.message)

    def __str__(self):
        return "{id: %s, name: %s, user: %s, time: %s}" % (
            self.id, self.name, self.user, self.time)


class CombinerModel(TargetModel):
    class Meta:
        db_table = 'all_combiners'

    key = models.OneToOneField(TargetModel, primary_key=True, db_column='targets_pk', parent_link=True)
    flow = models.ForeignKey('WorkflowModel')
    start = models.DateTimeField(null=True)
    end = models.DateTimeField(null=True)

    def save(self, *args, **kwargs):
        try:
            super(CombinerModel, self).save(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise Exception("Something went wrong while saving the combiner. Details - %s" % e.message)

    def __str__(self):
        return "{id: %s, name: %s, user: %s, time: %s, flow: %s}" % (
            self.id, self.name, self.user.username, self.time, self.flow)


class WorkflowModel(models.Model):
    class Meta:
        # overriding the default table name with the following name
        db_table = 'all_workflows'
        verbose_name = 'all_workflows'
        get_latest_by = 'time'

    name = models.CharField(max_length=255)
    description = models.CharField(max_length=2500)
    component = models.ForeignKey('ComponentModel', to_field='key', db_column='component_id')
    chain = models.CharField(max_length=3000, null=True, default=None)
    type = models.CharField(max_length=50, default='basic')
    auto_run = models.CharField(max_length=50, default='none')
    user = models.ForeignKey('auth.User')
    sharing = models.BooleanField(default=False)
    viewers = models.ManyToManyField('auth.User', db_table='workflow_viewers', symmetrical=False,
                                     related_name='workflow_viewers')
    time = models.DateTimeField(db_column='created_on', default=timezone.now)
    ignore = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        try:
            super(WorkflowModel, self).save(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise Exception("Something went wrong while saving the workflow. Details - %s" % e.message)

    def __str__(self):
        return "{id: %s, name: %s, user: %s, time: %s, type: %s}" % (
            self.id, self.name, self.user, self.time, self.type)


class AutoFlowModel(WorkflowModel):
    class Meta:
        db_table = 'auto_workflows'

    key = models.OneToOneField(WorkflowModel, primary_key=True, db_column='workflow_pk', parent_link=True)
    source = models.CharField(max_length=100, default="bigquery")
    identifier = models.CharField(max_length=1000)
    feature = models.CharField(max_length=255, null=True)
    op = models.CharField(max_length=50, null=True)
    value = models.CharField(max_length=1000, null=True)
    since = models.CharField(max_length=50, default='beginning')
    condition = models.ForeignKey('ConditionModel', null=True, on_delete=models.SET_NULL)
    schedule = models.ForeignKey('ScheduleModel', null=True, on_delete=models.SET_NULL)
    run_count = models.PositiveIntegerField(default=0)
    last_run = models.DateTimeField(null=True)
    run_status = models.CharField(max_length=100, null=True)

    def save(self, *args, **kwargs):
        try:
            super(AutoFlowModel, self).save(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise Exception("Something went wrong while saving the auto-workflow. Details - %s" % e.message)

    def __str__(self):
        return "{id: %s, name: %s, user: %s, time: %s, type: %s, auto-run: %s}" % (
            self.id, self.name, self.user, self.time, self.type, self.auto_run)


class DataSourceModel(models.Model):
    class Meta:
        db_table = 'flow_sources'

    source = models.CharField(db_column='data_source', max_length=100)
    identifier = models.CharField(max_length=1000)
    query = models.TextField()
    target = models.ForeignKey('TargetModel', db_index=True)
    history = models.ForeignKey('HistoryModel', db_index=True)


class TargetHistoryModel(models.Model):
    class Meta:
        db_table = 'targets_history'

    history = models.ForeignKey('HistoryModel', db_index=True)
    target = models.ForeignKey('TargetModel', db_index=True)
    # status can be Scheduled, Queued, Running, Finished, Failed, Retry
    status = models.CharField(max_length=100)
    timestamp = models.DateTimeField(default=timezone.now)
    local_pickle = models.CharField(max_length=1000, null=True)
    global_pickle = models.CharField(max_length=1000, null=True)
    ftkey = models.CharField(max_length=2500, null=True)
    type = models.ForeignKey('TypeModel', on_delete=models.SET_NULL, null=True)
    hostname = models.CharField(max_length=255)
    pickle_size = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        try:
            super(TargetHistoryModel, self).save(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise Exception("Something went wrong while saving the target history. Details - %s" % e.message)

    def __str__(self):
        return "{flow_id: %s, target_id: %s, status: %s, timestamp: %s}" % (
            self.history_id, self.target_id, self.status, self.timestamp)


class HistoryModel(models.Model):
    class Meta:
        db_table = 'user_history'

    user = models.ForeignKey('auth.User', db_index=True)
    created = models.DateTimeField(db_column='created_on', default=timezone.now)
    local_pickle = models.CharField(max_length=1000, null=True)
    global_pickle = models.CharField(max_length=1000, null=True)
    priority = models.SmallIntegerField(default=3, db_index=True)
    start = models.DateTimeField(db_column='started_on', null=True)
    finish = models.DateTimeField(db_column='finished_on', null=True)
    flow = models.ForeignKey('WorkflowModel')
    status = models.CharField(max_length=100, default='Pending', db_index=True)

    @property
    def duration(self):
        if self.start is None or self.finish is None:
            return 0
        execution_time = self.finish - self.start
        return execution_time.seconds

    # status should be one of Pending, Queued, Running, Failed, Finished

    def save(self, *args, **kwargs):
        try:
            super(HistoryModel, self).save(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise Exception("Something went wrong while saving the history. Details - %s" % e.message)

    def __str__(self):
        return "{id: %s, user: %s, time: %s, flow: %s, status: %s}" % (
            self.id, self.user.username, self.created, self.flow.name, self.status)


class FlowStatusModel(models.Model):
    class Meta:
        db_table = 'flow_status'

    history = models.ForeignKey('HistoryModel', db_index=True)
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=10000)
    result = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)
    ref = models.CharField(max_length=100, null=True)
    target = models.ForeignKey('TargetModel', db_index=True)
    element = models.CharField(max_length=1000)
    pickle = models.CharField(max_length=1000, null=True)
    gcs_pickle = models.CharField(max_length=1000, null=True)
    type = models.ForeignKey('TypeModel', on_delete=models.SET_NULL, null=True)
    ftkey = models.CharField(max_length=2500, null=True)  # fusion table key if the associated element is a visualizer

    def save(self, *args, **kwargs):
        try:
            super(FlowStatusModel, self).save(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise Exception("Something went wrong while saving the flow status. Details - %s" % e.message)

    def __str__(self):
        return "{flow_id: %s, target_id: %s, title: %s, result: %s, timestamp: %s}" % (
            self.history_id, self.target, self.title, self.result, self.timestamp)


class ActivityTrackerModel(models.Model):
    class Meta:
        db_table = 'activity_tracker'

    time = models.DateTimeField(db_column='created_on', default=timezone.now, db_index=True)
    instant = models.PositiveIntegerField(db_column='instant_sec')
    hostname = models.CharField(max_length=500, db_index=True)
    tracked = models.FloatField()
    reported = models.FloatField()
    username = models.CharField(max_length=100, db_index=True)
    processes = models.SmallIntegerField(db_column='num_processes')
    cpu = models.FloatField(db_column='cpu_percent')
    memory = models.FloatField(db_column='memory_percent')
    json = models.TextField()

    def save(self, *args, **kwargs):
        try:
            super(ActivityTrackerModel, self).save(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise Exception("Something went wrong while saving the activity. Details - %s" % e.message)

    def __str__(self):
        return "{id: %d, instant: %d, hostname: %s, utilization: %.2f, user: %s, num_processes: %d, cpu%%: %.2f, " \
               "memory%%: %.2f}" % (
                   self.id, self.instant, self.hostname, self.utilization, self.username, self.processes,
                   self.cpu, self.memory)


class PolygonModel(models.Model):
    class Meta:
        db_table = 'user_polygon'

    user = models.ForeignKey('auth.User')
    name = models.CharField(max_length=100)
    json = models.TextField()
    time = models.DateTimeField(db_column='created_on', default=timezone.now)

    def save(self, *args, **kwargs):
        try:
            super(PolygonModel, self).save(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise Exception("Something went wrong while saving the polygon. Details - %s" % e.message)

    def __str__(self):
        return "{id: %s, name: %s, user: %s, json: %s, time: %s}" % (
            self.id, self.name, self.user.username, self.json, self.time)


class ScheduleModel(models.Model):
    class Meta:
        db_table = 'all_schedules'

    name = models.CharField(max_length=100)
    user = models.ForeignKey('auth.User')
    time = models.DateTimeField(db_column='created_on', default=timezone.now)
    start = models.DateTimeField()
    repeat = models.CharField(max_length=50)
    custom_count = models.PositiveIntegerField(default=0)
    custom_repeat = models.CharField(max_length=50, null=True)
    custom_week = models.CharField(max_length=255, null=True)
    end = models.CharField(max_length=50, default="none")
    until = models.DateTimeField(null=True)
    count = models.PositiveIntegerField(null=True)

    def save(self, *args, **kwargs):
        try:
            super(ScheduleModel, self).save(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise Exception("Something went wrong while saving the schedule. Details - %s" % e.message)

    def __str__(self):
        start = localtime(self.start).strftime("%a, %d %b %Y at %I:%M %p")
        if self.repeat == 'none':
            return "Starts on or after %s and does not repeat."
        if self.repeat != 'custom' and self.end == 'count':
            return "Starts on or after %s and repeats %s for %d times." % (start, self.repeat, self.count)
        if self.repeat != 'custom' and self.end == 'date':
            until = localtime(self.until).strftime("%a, %d %b %Y, %I:%M %p")
            return "Starts on or after %s and repeats %s until %s." % (start, self.repeat, until)
        if self.repeat != 'custom' and self.end == 'forever':
            return "Starts on or after %s and repeats %s, forever." % (start, self.repeat)
        if self.repeat == 'custom' and self.end == 'count':
            if self.custom_repeat != 'week':
                return "Starts on or after %s and repeats every %d %s(s) for %d times." % (
                    start, self.custom_count, self.custom_repeat, self.count)
            return "Starts on or after %s and repeats every %d %s(s) on %s for %d times." % (
                start, self.custom_count, self.custom_repeat, self.custom_week, self.count)
        if self.repeat == 'custom' and self.end == 'date':
            until = localtime(self.until).strftime("%a, %d %b %Y, %I:%M %p")
            if self.custom_repeat != 'week':
                return "Starts on or after %s and repeats every %d %s(s) until %s." % (
                    start, self.custom_count, self.custom_repeat, until)
            return "Starts on or after %s and repeats every %d %s(s) on %s until %s." % (
                start, self.custom_count, self.custom_repeat, self.custom_week, until)
        if self.repeat == 'custom' and self.end == 'forever':
            if self.custom_repeat != 'week':
                return "Starts on or after %s and repeats every %d %s(s), forever." % (
                    start, self.custom_count, self.custom_repeat)
            return "Starts on or after %s and repeats every %d %s(s) on %s, forever." % (
                start, self.custom_count, self.custom_repeat, self.custom_week)


class ClientSecurityModel(models.Model):
    class Meta:
        db_table = 'oauth_credentials'

    user = models.ForeignKey('auth.User')
    service = models.CharField(max_length=100)
    credentials = models.CharField(max_length=2000)

    def save(self, *args, **kwargs):
        try:
            super(ClientSecurityModel, self).save(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise Exception("Something went wrong while saving the auth credentials. Details - %s" % e.message)


class ServerSecurityModel(models.Model):
    class Meta:
        db_table = 'service_account_credentials'

    user = models.ForeignKey('auth.User')
    service = models.CharField(max_length=100)
    credentials = models.TextField()
    bucket = models.CharField(max_length=1000, null=True)

    def save(self, *args, **kwargs):
        try:
            super(ServerSecurityModel, self).save(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise Exception("Something went wrong while saving the SA credentials. Details - %s" % e.message)


@receiver(post_save, sender=CombinerModel)
def combiner_updated(sender, instance, **kwargs):
    components = ComponentModel.objects.filter(combiners=instance)
    for component in components:
        if instance.ignore and not component.ignore:
            logger.info("setting ignore on component(" + str(component.id) + ") - " + component.name)
            component.ignore = True
            component.save()


@receiver(post_save, sender=ComponentModel)
def component_updated(sender, instance, **kwargs):
    workflows = WorkflowModel.objects.filter(component=instance)
    for workflow in workflows:
        if instance.ignore and not workflow.ignore:
            logger.info("setting ignore on workflow(" + str(workflow.id) + ") - " + workflow.name)
            workflow.ignore = True
            workflow.save()
    components = ComponentModel.objects.filter(parents=instance)
    for component in components:
        if instance.ignore and not component.ignore:
            logger.info("setting ignore on component(" + str(component.id) + ") - " + component.name)
            component.ignore = True
            component.save()


@receiver(post_save, sender=WorkflowModel)
def workflow_updated(sender, instance, **kwargs):
    combiners = CombinerModel.objects.filter(flow=instance)
    for combiner in combiners:
        if instance.ignore and not combiner.ignore:
            logger.info("setting ignore on combiner(" + str(combiner.id) + ") - " + combiner.name)
            combiner.ignore = True
            combiner.save()
