# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import datetime
from tank_vendor import shotgun_api3
import sgtk
logger = sgtk.platform.get_logger(__name__)

def create_human_readable_date(dt):
    """
    Return the date represented by the argument as a string, displaying recent
    dates as "Yesterday", "Today", or "Tomorrow".

    :param dt: The date convert to a string
    :type dt: :class:`datetime.date` or :class:`datetime.datetime`

    :returns: A String representing date appropriate for display
    """
    delta, date_str = None, None
    if isinstance(dt, datetime.datetime):
        delta = datetime.datetime.now(dt.tzinfo) - dt
    elif isinstance(dt, datetime.date):
        delta = datetime.date.today() - dt

    if delta:
        if delta.days == 1:
            date_str = "Yesterday"
        elif delta.days == 0:
            date_str = "Today"
        elif delta.days == -1:
            date_str = "Tomorrow"
        else:
            # use the locale appropriate date representation
            date_str = dt.strftime("%x")

    return date_str


def old_create_human_readable_timestamp(dt, postfix=""):
    """
    Return the time represented by the argument as a string where the date portion is
    displayed as "Yesterday", "Today", or "Tomorrow" if appropriate.

    By default just the date is displayed, but additional formatting can be appended
    by using the postfix argument.

    :param dt: The date and time to convert to a string
    :type dt: :class:`datetime.datetime` or float

    :param postfix: What will be displayed after the date portion of the dt argument
    :type postfix: A strftime style String

    :returns: A String representing dt appropriate for display
    """
    # shotgun_model converts datetimes to floats representing unix time so
    # handle that as a valid value as well
    #if isinstance(dt, float):

    dt = datetime.datetime.fromtimestamp(int(dt))
    #logger.debug(">>>>>>>>>> dt is: {}".format(dt))
    # get a relative date_str
    date_str = create_human_readable_date(dt)
    #logger.debug(">>>>>>>>>> date_str is: {}".format(date_str))
    # time_format = "{}{}".format(date_str, postfix)

    #return dt.strftime(time_format)
    return date_str

def create_human_readable_timestamp(dt):
    created_unixtime = int(dt)
    # logger.debug(">>>>>>>>>> dt is: {}".format(dt))
    """
    date_str = datetime.datetime.fromtimestamp(created_unixtime).strftime(
        "%m-%d-%y %H:%M:%S"
    )
    logger.debug(">>>>>>>>>> date_str 1 is: {}".format(date_str))
    """

    date_str = datetime.datetime.fromtimestamp(
        created_unixtime, shotgun_api3.sg_timezone.LocalTimezone()
    )
    #logger.debug(">>>>>>>>>> date_str 2 is: {}".format(date_str))
    return date_str

def create_publish_timestamp(dt):
    created_unixtime = int(dt)

    date_str = datetime.datetime.fromtimestamp(created_unixtime).strftime(
        "%m-%d-%y %H:%M:%S"
    )
    #logger.debug(">>>>>>>>>> date_str 1 is: {}".format(date_str))

    return date_str

def get_time_now():
    date_str = datetime.datetime.now()
    return date_str

