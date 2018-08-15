#
#    ICRAR - International Centre for Radio Astronomy Research
#    (c) UWA - The University of Western Australia, 2016
#    Copyright by UWA (in the framework of the ICRAR)
#    All rights reserved
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston,
#    MA 02111-1307  USA
#
import os
import optparse
import json
from influxdb import InfluxDBClient

# Names of environment variables.
host_env = 'INFLUXDB_HOST'
port_env = 'INFLUXDB_PORT'
dbname_env = 'INFLUXDB_NAME'
user_env = 'INFLUXDB_USER'
password_env = 'INFLUXDB_PASSWORD'
graph_sha_env = 'GRAPH_SHA'

DEFAULT_DB_NAME='daliuge'

def _get_result_values(result):
    """
    Returns key-value table from the raw InfluxDB query result.
    """
    if 'series' in result.raw:
        return result.raw['series'][0]['values']
    else:
        return []

def _get_graph_sha():
    return os.getenv(graph_sha_env, 'test')

class Reader(object):
    """
    A class that reads graph data from InfluxDB database.
    """
    def __init__(self, graph_sha):
        self.graph_sha = graph_sha
        # Connect to the InfluxDB client.
        try:
            self.client = Connector().connect(False)
        except Exception as e:
            print e

    def _get_value_list(self, values):
        """
        Returns value list from a query result (key-value) table.
        """
        list = []
        if values:
            for [key, value] in values:
                list.append(value)
        return list

    def getSessionIDs(self):
        """
        Returns session IDs for a graph.
        """
        query = 'SHOW TAG VALUES FROM "' + self.graph_sha + '" WITH KEY = session_id'
        res = self.client.query(query)
        values = _get_result_values(res)
        sessions = self._get_value_list(values)
        return sessions

    def getOIDs(self, app_key):
        """
        Returns application OIDs for a given application in a graph.
        """
        query = 'SHOW TAG VALUES FROM "' + self.graph_sha + '" WITH KEY = oid WHERE "key" = \'' + app_key + "'"
        res = self.client.query(query)
        values = _get_result_values(res)
        oids = self._get_value_list(values)
        return oids

    def getExecutionTime(self, session_id, app_key, oid):
        """
        Returns application execution time.
        Returns None if no data found.
        """
        query = "SELECT ELAPSED(value,1s) FROM \"" + self.graph_sha \
                + "\" WHERE \"key\" = '" + app_key  + "'" \
                + " AND session_id = '" + session_id + "'" \
                + " AND oid = '" + oid + "'"
        res = self.client.query(query)
        values = _get_result_values(res)

        if values:
            exec_time = values[0][1]
            return exec_time
        else:
            # No records found.
            return None

class Listener(object):
    """
    A listener class for storing DALiuGE drop events to InfluxDB database.
    """
    def __init__(self):
        # Connect to the InfluxDB client.
        try:
            self.client = Connector().connect(True)
        except Exception as e:
            print e

        self.graph_sha = _get_graph_sha()
        print "Graph sha =", self.graph_sha

    def handleEvent(self, event):
        """
        This function gets called by DALiuGE events.
        """
        if (event.type == 'execStatus'):
        # An event from application drop received.
            oid = event.oid
            print "Handling the event with oid =", oid
            # Calculate the event status.
            value = -1
            if (event.execStatus == 1):
            # Event started.
                value = 1
            elif (event.execStatus == 2):
            # Event finished.
                value = 0

            measurement_name = self.graph_sha
            session_id = event.session_id
            key = event.lg_key
            name = event.name

            # Create measurement data.
            json_body = [
                {
                    "measurement": measurement_name,
                    "tags": {
                        "session_id": session_id,
                        "oid": oid,
                        "key": key,
                        "name": name
                    },
                    "fields": {
                        "value": value
                    }
                }
            ]

            try:
                # Write data to the database.
                self.client.write_points(json_body)
            except Exception as e:
                print e

class Translator(object):
    """
    A translator class for parametrizing logical graph parameters.
    """
    def __init__(self, graph, graph_sha):
        self.graph = graph
        self.graph_sha = graph_sha
        self.reader = Reader(graph_sha)

    def get_average_execution_time(self, app_key, sessions, oids):
        """
        Returns the average execution time, for a given application, among different sessions and OIDs.
        """
        if (len(sessions) == 0 or len(oids) == 0):
            return 0.

        total_exec_time = 0.
        num_records = 0
        # Loop over all graph sessions, and calculate the total execution time.
        for session in sessions:
            for oid in oids:
                exec_time = self.reader.getExecutionTime(session, app_key, oid)
                if (exec_time is not None):
                # A record found in the DB.
                    total_exec_time += float(exec_time)
                    num_records += 1
        if (num_records > 0):
            avg_exec_time = total_exec_time / float(num_records)
            return avg_exec_time
        else:
            # No records found in the DB.
            return None

    def translate_execution_time(self):
        """
        Parametrizes the application execution time in a graph.
        """
        sessions = self.reader.getSessionIDs()
        if (len(sessions) == 0):
            return False

        num_app_translated = 0
        # Loop over graph applications, and parametrize the execution time.
        for jd in self.graph['nodeDataArray']:
            categoryType = jd['categoryType']
            if (categoryType == 'ApplicationDrop' or categoryType == 'GroupComponent'):
            # This is an application or application group node.
                app_key = str(jd['key'])
                oids = self.reader.getOIDs(app_key)
                avg_exec_time = self.get_average_execution_time(app_key, sessions, oids)
                print 'key, avg_exec_time =', app_key, avg_exec_time

                is_group = (categoryType == 'GroupComponent')
                field_name = ''
                if is_group:
                    field_name = 'appFields'
                else:
                    field_name = 'fields'

                if (avg_exec_time is not None):
                    fields = jd[field_name]
                    exec_time_field = filter(lambda x: x['name'] == 'execution_time', fields)

                    # Replace execution time in the graph.
                    num_app_translated += 1
                    new_value = int(avg_exec_time)
                    exec_time_field[0]['value'] = str(new_value)

        print "Translated execution time for ", num_app_translated, " applications, based on ", len(sessions), " sessions data."
        return True

class Connector(object):
    """
    A class responsible for connection to InfluxDB database.
    """
    def __init__(self):
        self.host = os.getenv(host_env, 'localhost')
        self.port = os.getenv(port_env, 8086)
        self.dbname = os.getenv(dbname_env, DEFAULT_DB_NAME)
        self.user = os.getenv(user_env, '')
        self.password = os.getenv(password_env, '')

    @staticmethod
    def check_db_exists(client, dbname):
        """ Check if the database exists."""
        try:
            res = client.query("SHOW DATABASES")
            db_exist = ([dbname] in _get_result_values(res))
            return db_exist
        except Exception as e:
            print e

    def connect(self, create_new_db = False):
        """Instantiate the connection to the InfluxDB client."""
        client = InfluxDBClient(self.host, self.port, self.user, self.password, self.dbname)

        # Check if the database exists.
        db_exist = self.check_db_exists(client, self.dbname)

        if db_exist:
            print "Connected to InfluxDB database: ", self.dbname
        else:
            print "Could not find the InfluxDB database: ", self.dbname
            if create_new_db:
                # Create a new database.
                print "Creating a new database."
                client.create_database(dbname)

        return client

def translate_lg_to_plg():
    """
    Parametrizes logical graph essentially translating LG to PLG (parametrized logical graph).
    """
    parser = optparse.OptionParser()
    parser.add_option("-L", "--logical-graph", action="store", type="string",
                      dest="logical_graph", help="The filename of the logical graph to parametrize", default=None)

    parser.add_option("-o", "--output-graph", action="store", type="string",
                      dest="output_graph", help="The filename of the output parametrized logical graph", default=None)

    (options, _) = parser.parse_args()

    if bool(options.logical_graph) == False:
        parser.error("A logical graph filename must be specified")

    if bool(options.output_graph) == False:
        parser.error("An output graph filename must be specified")

    lg_path = options.logical_graph
    if lg_path and not os.path.exists(lg_path):
        parser.error("Cannot locate graph file at '{0}'".format(lg_path))

    f = open(lg_path)
    with f:
        lg = json.load(f)

    graph_sha = _get_graph_sha()
    translator = Translator(lg, graph_sha)
    translator.translate_execution_time()

    # Write the parametrized logical graph.
    with open(options.output_graph, 'w') as outfile:
        json.dump(lg, outfile)

    print "Translated LG to PLG and wrote the result to: ", options.output_graph

if __name__ == '__main__':
    translate_lg_to_plg()
