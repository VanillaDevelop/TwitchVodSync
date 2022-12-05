import datetime


def append_timestamps(report_start, fights):
    """
    For a list of fights (dict), append formatted strings of the start and end of the encounter
    :param report_start: The startTime (epoch) of the report
    :param fights: A list of fights (dict)
    :return: None. The operation is in-place.
    """
    for fight in fights:
        start = datetime.datetime.fromtimestamp(float(report_start)/1000 + float(fight['startTime'])/1000)
        end = datetime.datetime.fromtimestamp(float(report_start)/1000 + float(fight['endTime'])/1000)
        fight['timestampStart'] = start.strftime("%H:%M:%S")
        fight['timestampEnd'] = end.strftime("%H:%M:%S")


def timestamp_to_string(timestamp):
    """
    Returns an epoch timestamp as a formatted string
    :param timestamp: The timestamp to convert
    :return: A string of the date and time represented within the epoch timestamp.
    """
    return datetime.datetime.fromtimestamp(float(timestamp)/1000).strftime("%Y-%m-%d %H:%M:%S")