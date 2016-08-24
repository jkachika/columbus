import logging
import traceback as tb
from datetime import datetime as dt

import numpy
import math

logger = logging.getLogger(__name__)


def caught(try_function, *args):
    try:
        try_function(*args)
        return False
    except BaseException:
        return True


def log_n_raise(e, msg=None):
    logger.error(tb.format_exc())
    if msg is not None:
        raise Exception(msg)
    raise Exception(e.message)


def log_n_suppress(e):
    trace = tb.format_exc()
    logger.error(trace)
    logger.error(e.message)
    if "exec (compile(__code__, __name__ + '.py', 'exec'), scope)" in str(trace):
        sub_trace = str(trace).split("exec (compile(__code__, __name__ + '.py', 'exec'), scope)")[-1]
        sub_trace = sub_trace.replace('<module>', 'module').replace('\n', '<br/>')
        return e.message + '<br/><b>Trace:</b>' + sub_trace.strip()
    return e.message


def debug(message):
    logger.debug(message)


def info(message):
    logger.info(message)


def error(message):
    logger.error(message)


def warn(message):
    logger.warn(message)


def is_number(s):
    return False if caught(float, s) else True


# finds the mean of a feature collection for a given property
def mean(prop, ftc):
    features = ftc['features']
    result = [(float(feature['properties'][prop]) if is_number(feature['properties'][prop]) and not math.isnan(
        float(feature['properties'][prop])) else 0.0) for feature in features]
    return numpy.mean(numpy.array(result))


# finds the standard deviation of a feature collection for a given property
def std(prop, ftc):
    features = ftc['features']
    result = [(float(feature['properties'][prop]) if is_number(feature['properties'][prop]) and not math.isnan(
        float(feature['properties'][prop])) else 0.0) for feature in features]
    return numpy.std(numpy.array(result))


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code.
       Add other types that are not serializable
       :param obj: The object that needs to be serialized
       :return: json serialization of the given object
    """
    if isinstance(obj, dt):
        s = obj.strftime('%Y-%m-%d %H:%M:%S.%f')
        tail = s[-7:]
        f = round(float(tail), 3)
        temp = "%.3f" % f
        return "%s%s" % (s[:-7], temp[1:])
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    raise TypeError("Type not serializable")


class Dict(dict):
    """dot.notation access to dictionary attributes"""

    def __getattr__(self, attr):
        return self.get(attr, None)

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
