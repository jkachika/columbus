from django import template

register = template.Library()


@register.filter(name='list_parents_id')
def list_parents_id(component):
    """
    :param component: instance of ComponentModel
    :return: list of parents' id values
    """
    result = ''
    for parent in component.parents.all():
        result += str(parent.id) + ","
    return result[:-1]


@register.filter(name='list_combiners_id')
def list_combiners_id(component):
    """
    :param component: instance of ComponentModel
    :return: list of parents' id values
    """
    result = ''
    for combiner in component.combiners.all():
        result += str(combiner.id) + ","
    return result[:-1]


@register.filter(name='list_parents_name')
def list_parents_name(component):
    """
    :param component: instance of ComponentModel
    :return: list of parents' name values
    """
    result = ''
    for parent in component.parents.all():
        result += str(parent.name) + ","
    return result[:-1]


@register.filter(name='list_combiners_name')
def list_combiners_name(component):
    """
    :param component: instance of ComponentModel
    :return: list of parents' name values
    """
    result = ''
    for combiner in component.combiners.all():
        result += str(combiner.name) + ","
    return result[:-1]


@register.filter(name='list_parents_output')
def list_parents_output(component):
    """
    :param component: instance of ComponentModel
    :return: list of parents' output values
    """
    result = ''
    for parent in component.parents.all():
        result += str(parent.name) + " - [" + str(parent.output) + "]\n"
    return result[:-1]


@register.filter(name='list_parents_type')
def list_parents_type(component):
    """
    :param component: instance of ComponentModel
    :return: list of parents' type values
    """
    result = ''
    for parent in component.parents.all():
        result += str(parent.name) + " - " + str(parent.type.name) + "\n"
    return result[:-1]


@register.filter(name='list_parties')
def list_parties(component):
    """
    :param component: instance of ComponentModel
    :return: list of user id values.
    """
    result = ''
    for party in component.parties.all():
        result = result + str(party.id) + ","
    return result[:-1]


@register.filter(name='list_viewers')
def list_viewers(workflow):
    """
    :param workflow: instance of WorkflowModel
    :return: list of user id values.
    """
    return ",".join([str(viewer.id) for viewer in workflow.viewers.all()])


@register.filter(name='str_condition')
def str_condition(condition):
    """
    Returns the string representation of a condition object.
    :param condition: a condition object
    :return: string representation of the object
    """
    return str(condition.get_condition())


@register.filter(name='string')
def string(obj):
    """
    Returns the string representation of the object
    :param obj: any object
    :return: string
    """
    return str(obj)


@register.filter(name='target_names')
def target_names(targets, separator):
    return separator.join([target['name'] for target in targets])


@register.filter(name='compute_gb')
def compute_gb(value):
    return "%.2f" % (float(value)/(1024 * 1024 * 1024))


@register.filter(name='compute_mb')
def compute_mb(value):
    return "%.2f" % (float(value)/(1024 * 1024))