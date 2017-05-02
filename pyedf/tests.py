import jsonpickle
import requests
from colorker.core import Query

GALILEO_SERVICE_HOST = 'http://tomcat.columbus.cs.colostate.edu/galileo-web-service'

polygons = [[{"lat": "40.597792003905454", "lon": "-104.77729797363281"},
             {"lat": "40.43545015171254", "lon": "-104.77729797363281"},
             {"lat": "40.43545015171254", "lon": "-105.10414123535156"},
             {"lat": "40.597792003905454", "lon": "-105.10414123535156"},
             {"lat": "40.597792003905454", "lon": "-104.77729797363281"}],

            [{"lat": "32.86574639547474", "lon": "-96.6851806640625"},
             {"lat": "32.699488680852674", "lon": "-96.6851806640625"},
             {"lat": "32.699488680852674", "lon": "-97.02713012695312"},
             {"lat": "32.86574639547474", "lon": "-97.02713012695312"},
             {"lat": "32.86574639547474", "lon": "-96.6851806640625"}],

            [{"lat": "42.35600690670568", "lon": "-71.02249145507812"},
             {"lat": "42.19291648699529", "lon": "-71.02249145507812"},
             {"lat": "42.19291648699529", "lon": "-71.36032104492188"},
             {"lat": "42.35600690670568", "lon": "-71.36032104492188"},
             {"lat": "42.35600690670568", "lon": "-71.02249145507812"}],

            [{"lat": "33.91829235152197", "lon": "-117.78305053710938"},
             {"lat": "33.75631505992706", "lon": "-117.78305053710938"},
             {"lat": "33.75631505992706", "lon": "-118.11676025390625"},
             {"lat": "33.91829235152197", "lon": "-118.11676025390625"},
             {"lat": "33.91829235152197", "lon": "-117.78305053710938"}],

            [{"lat": "39.8992015115692", "lon": "-104.76974487304688"},
             {"lat": "39.72989765591686", "lon": "-104.76974487304688"},
             {"lat": "39.72989765591686", "lon": "-105.11306762695312"},
             {"lat": "39.8992015115692", "lon": "-105.11306762695312"},
             {"lat": "39.8992015115692", "lon": "-104.76974487304688"}],

            [{"lat": "40.60196281341108", "lon": "-79.8101806640625"},
             {"lat": "40.43335959357837", "lon": "-79.8101806640625"},
             {"lat": "40.43335959357837", "lon": "-80.15213012695312"},
             {"lat": "40.60196281341108", "lon": "-80.15213012695312"},
             {"lat": "40.60196281341108", "lon": "-79.8101806640625"}],

            [{"lat": "30.40722867174157", "lon": "-81.56524658203125"},
             {"lat": "30.23652704486517", "lon": "-81.56524658203125"},
             {"lat": "30.23652704486517", "lon": "-81.91131591796875"},
             {"lat": "30.40722867174157", "lon": "-81.91131591796875"},
             {"lat": "30.40722867174157", "lon": "-81.56524658203125"}],

            [{"lat": "40.77742172100596", "lon": "-73.83224487304688"},
             {"lat": "40.608739823836984", "lon": "-73.83224487304688"},
             {"lat": "40.608739823836984", "lon": "-74.17625427246094"},
             {"lat": "40.77742172100596", "lon": "-74.17625427246094"},
             {"lat": "40.77742172100596", "lon": "-73.83224487304688"}],

            [{"lat": "42.00950942549377", "lon": "-87.54180908203125"},
             {"lat": "41.83785101947692", "lon": "-87.54180908203125"},
             {"lat": "41.83785101947692", "lon": "-87.88787841796875"},
             {"lat": "42.00950942549377", "lon": "-87.88787841796875"},
             {"lat": "42.00950942549377", "lon": "-87.54180908203125"}],

            [{"lat": "43.06437305188956", "lon": "-75.94024658203125"},
             {"lat": "42.89357335568508", "lon": "-75.94024658203125"},
             {"lat": "42.89357335568508", "lon": "-76.28631591796875"},
             {"lat": "43.06437305188956", "lon": "-76.28631591796875"},
             {"lat": "43.06437305188956", "lon": "-75.94024658203125"}]]

timestamps = ["2012-11-19-xx", "2013-10-07-xx", "2016-06-01-xx", "2015-05-29-xx", "2012-12-12-xx",
              "2013-09-18-xx", "2014-10-09-xx", "2016-05-31-xx", "2013-10-21-xx", "2012-12-03-xx"]

months = ["2012-11-xx-xx", "2013-10-xx-xx", "2016-06-xx-xx", "2015-05-xx-xx", "2012-12-xx-xx",
          "2013-09-xx-xx", "2014-10-xx-xx", "2016-05-xx-xx", "2014-09-xx-xx", "2013-05-xx-xx"]

spatial_years = ["2015-xx-xx-xx", "2016-xx-xx-xx", "2016-xx-xx-xx", "2015-xx-xx-xx", "2014-xx-xx-xx",
                 "2016-xx-xx-xx", "2016-xx-xx-xx", "2016-xx-xx-xx", "2014-xx-xx-xx", "2014-xx-xx-xx"]

spatial_days = ["2013-10-09-xx", "2016-01-27-xx", "2013-03-13-xx", "2015-04-17-xx", "2012-12-05-xx",
                "2016-05-19-xx", "2015-05-07-xx", "2015-06-19-xx", "2014-09-17-xx", "2014-02-03-xx"]

spatial_months = ["2013-10-xx-xx", "2016-01-xx-xx", "2013-03-xx-xx", "2015-04-xx-xx", "2012-11-xx-xx",
                  "2015-08-xx-xx", "2015-05-xx-xx", "2015-06-xx-xx", "2014-09-xx-xx", "2014-02-xx-xx"]


def galileo_spatial_tests(identifier):
    for index, polygon in enumerate(polygons):
        q = Query(source="galileo", identifier=identifier, description="spatial query test")
        q.set_spatial_property(polygon)
        response = requests.post("%s/featureset" % GALILEO_SERVICE_HOST, json=q.__dict__)
        json_response = jsonpickle.decode(response.text)
        print "sp%d,%s,%d,%d,%s" % (index, str(json_response["filesystem"]), int(json_response["totalProcessingTime"]),
                                    int(json_response["totalResultSize"]), str(json_response["elapsedTime"])[:-2])


def galileo_temporal_day_tests(identifier, interactive=True):
    for index, timestamp in enumerate(timestamps):
        q = Query(source="galileo", identifier=identifier, description="temporal query test")
        q.set_temporal_property(timestamp)
        if interactive:
            q.set_results("true")
        response = requests.post("%s/featureset" % GALILEO_SERVICE_HOST, json=q.__dict__)
        json_response = jsonpickle.decode(response.text)
        print "td%d,%s,%d,%d,%s" % (index, str(json_response["filesystem"]), int(json_response["totalProcessingTime"]),
                                    int(json_response["totalResultSize"]), str(json_response["elapsedTime"])[:-2])


def galileo_temporal_month_tests(identifier):
    for index, month in enumerate(months):
        q = Query(source="galileo", identifier=identifier, description="temporal query test")
        q.set_temporal_property(month)
        response = requests.post("%s/featureset" % GALILEO_SERVICE_HOST, json=q.__dict__)
        json_response = jsonpickle.decode(response.text)
        print "tm%d,%s,%d,%d,%s" % (index, str(json_response["filesystem"]), int(json_response["totalProcessingTime"]),
                                    int(json_response["totalResultSize"]), str(json_response["elapsedTime"])[:-2])


def galileo_spatio_temporal_years(identifier):
    for index, polygon in enumerate(polygons):
        q = Query(source="galileo", identifier=identifier, description="temporal query test")
        q.set_spatial_property(polygon)
        q.set_temporal_property(spatial_years[index])
        response = requests.post("%s/featureset" % GALILEO_SERVICE_HOST, json=q.__dict__)
        json_response = jsonpickle.decode(response.text)
        print "st%d,%s,%d,%d,%s" % (index, str(json_response["filesystem"]), int(json_response["totalProcessingTime"]),
                                    int(json_response["totalResultSize"]), str(json_response["elapsedTime"])[:-2])


def galileo_spatio_temporal_months(identifier):
    for index, polygon in enumerate(polygons):
        q = Query(source="galileo", identifier=identifier, description="temporal query test")
        q.set_spatial_property(polygon)
        q.set_temporal_property(spatial_months[index])
        response = requests.post("%s/featureset" % GALILEO_SERVICE_HOST, json=q.__dict__)
        json_response = jsonpickle.decode(response.text)
        print "sm%d,%s,%d,%d,%s" % (index, str(json_response["filesystem"]), int(json_response["totalProcessingTime"]),
                                    int(json_response["totalResultSize"]), str(json_response["elapsedTime"])[:-2])


def galileo_spatio_temporal_days(identifier, interactive=False):
    for index, polygon in enumerate(polygons):
        q = Query(source="galileo", identifier=identifier, description="temporal query test")
        q.set_spatial_property(polygon)
        q.set_temporal_property(spatial_days[index])
        if interactive:
            q.set_results("true")
        response = requests.post("%s/featureset" % GALILEO_SERVICE_HOST, json=q.__dict__)
        json_response = jsonpickle.decode(response.text)
        print "sd%d,%s,%d,%d,%s" % (index, str(json_response["filesystem"]), int(json_response["totalProcessingTime"]),
                                    int(json_response["totalResultSize"]), str(json_response["elapsedTime"])[:-2])


def find_most_spatial_days(identifier):
    for index, polygon in enumerate(polygons):
        q = Query(source="galileo", identifier=identifier, description="spatial query test")
        q.set_spatial_property(polygon)
        response = requests.post("%s/featureset" % GALILEO_SERVICE_HOST, json=q.__dict__)
        json_response = jsonpickle.decode(response.text)
        max_key, max_rows, max_processing_time = None, 0, 0
        result = json_response["result"]
        for key in result:
            result_size = 0
            processing_time = 0
            for item in result[key]:
                result_size += item["resultSize"]
                processing_time = max(processing_time, item["processingTime"])
            if result_size > max_rows:
                max_rows = result_size
                max_key = key
                max_processing_time = processing_time
        print "sp%d,%s,%d,%d" % (index, max_key, max_rows, max_processing_time)


paperPolygon = [{"lat": "33.68206818063879", "lon": "-117.982177734375"},
                    {"lat": "33.87725673930016", "lon": "-118.421630859375"},
                    {"lat": "34.2435947296974", "lon": "-118.21975708007812"},
                    {"lat": "34.24245948736849", "lon": "-117.85308837890625"},
                    {"lat": "33.99119576995599", "lon": "-117.520751953125"}]

def process_all_queries():
    for _ in range(5):
        galileo_spatial_tests(identifier="picarro-gh4-ng2")
        galileo_temporal_day_tests(identifier="picarro-gh4-ng2")
        galileo_temporal_month_tests(identifier="picarro-gh4-ng2")
        galileo_spatio_temporal_years(identifier="picarro-gh4-ng2")
        galileo_spatio_temporal_days(identifier="picarro-gh4-ng2")
        galileo_spatio_temporal_months(identifier="picarro-gh4-ng2")

        galileo_spatial_tests(identifier="picarro-gh5-ng2")
        galileo_temporal_day_tests(identifier="picarro-gh5-ng2")
        galileo_temporal_month_tests(identifier="picarro-gh5-ng2")
        galileo_spatio_temporal_years(identifier="picarro-gh5-ng2")
        galileo_spatio_temporal_days(identifier="picarro-gh5-ng2")
        galileo_spatio_temporal_months(identifier="picarro-gh5-ng2")

        galileo_spatial_tests(identifier="picarro-gh3-ng2")
        galileo_temporal_day_tests(identifier="picarro-gh3-ng2")
        galileo_temporal_month_tests(identifier="picarro-gh3-ng2")
        galileo_spatio_temporal_years(identifier="picarro-gh3-ng2")
        galileo_spatio_temporal_days(identifier="picarro-gh3-ng2")
        galileo_spatio_temporal_months(identifier="picarro-gh3-ng2")

        galileo_spatial_tests(identifier="picarro-gh4-ng1")
        galileo_temporal_day_tests(identifier="picarro-gh4-ng1")
        galileo_temporal_month_tests(identifier="picarro-gh4-ng1")
        galileo_spatio_temporal_years(identifier="picarro-gh4-ng1")
        galileo_spatio_temporal_days(identifier="picarro-gh4-ng1")
        galileo_spatio_temporal_months(identifier="picarro-gh4-ng1")

        galileo_spatial_tests(identifier="picarro-gh4-ng4")
        galileo_temporal_day_tests(identifier="picarro-gh4-ng4")
        galileo_temporal_month_tests(identifier="picarro-gh4-ng4")
        galileo_spatio_temporal_years(identifier="picarro-gh4-ng4")
        galileo_spatio_temporal_days(identifier="picarro-gh4-ng4")
        galileo_spatio_temporal_months(identifier="picarro-gh4-ng4")


workers = ['aries.c.columbus-csu.internal', 'taurus.c.columbus-csu.internal', 'gemini.c.columbus-csu.internal',
           'cancer.c.columbus-csu.internal', 'leo.c.columbus-csu.internal', 'virgo.c.columbus-csu.internal',
           'libra.c.columbus-csu.internal', 'scorpio.c.columbus-csu.internal', 'sagittarius.c.columbus-csu.internal',
           'capricorn.c.columbus-csu.internal', 'aquarius.c.columbus-csu.internal', 'pisces.c.columbus-csu.internal']


def massage_scheduling_results(filename, username='system', strategy=None):
    with open(filename, 'r') as handle:
        all_records = handle.readlines()
    print "records=%d" % len(all_records)
    header = all_records[0]
    host_utilization = dict()
    last_instant = 0
    columns = all_records[1].split(',')
    strategy = columns[0] if strategy is None else strategy
    filesystem = columns[1]

    with open("../data/%s-%s-all.csv" % (filesystem, strategy if username == 'system' else username), 'w') as handle:
        handle.write(header)
        for record in all_records[1:]:
            columns = record.split(',')
            instant = int(columns[2])
            columns[5] = username if username != 'system' else columns[5]
            host = columns[3]
            if last_instant != 0 and instant != last_instant:
                for worker in workers:
                    line = host_utilization.get(worker, ['0', username, '0', '0.0', '0.0\n'])
                    handle.write("%s,%s,%d,%s,%s" % (strategy, filesystem, last_instant, worker, ",".join(line)))
            last_instant = instant
            host_utilization[host] = columns[4:]
        for worker in workers:
            line = host_utilization.get(worker, ['0', username, '0', '0.0', '0.0\n'])
            handle.write("%s,%s,%d,%s,%s" % (strategy, filesystem, last_instant, worker, ",".join(line)))


if __name__ == "__main__":
    process_all_queries()
    massage_scheduling_results('../data/gh4ng1-jcharles.csv', 'jcharles')
    massage_scheduling_results('../data/gh4ng1-joe.csv', 'joe')
    massage_scheduling_results('../data/gh4ng1-sangmi.csv', 'sangmi')
    massage_scheduling_results('../data/gh4ng1-max.csv', 'max')
    massage_scheduling_results('../data/gh4ng1-remote.csv', strategy='remote')
    massage_scheduling_results('../data/gh4ng1-hybrid.csv', strategy='hybrid')
    massage_scheduling_results('../data/gh4ng1-local.csv', strategy='local')

    massage_scheduling_results('../data/gh4ng1-hybrid2.csv', strategy='hybrid2')
    massage_scheduling_results('../data/gh4ng1-hybrid3.csv', strategy='hybrid3')
    massage_scheduling_results('../data/gh4ng1-remote2.csv', strategy='remote2')
