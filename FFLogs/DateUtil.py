import datetime


def append_timestamps(report_start, fights):
    for fight in fights:
        start = datetime.datetime.fromtimestamp(float(report_start)/1000 + float(fight['startTime'])/1000)
        end = datetime.datetime.fromtimestamp(float(report_start)/1000 + float(fight['endTime'])/1000)
        fight['timestampStart'] = start.strftime("%H:%M:%S")
        fight['timestampEnd'] = end.strftime("%H:%M:%S")


def timestamp_to_string(timestamp):
    return datetime.datetime.fromtimestamp(float(timestamp)/1000).strftime("%Y-%m-%d %H:%M:%S")