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

    def getSessionIDs(self):
        """
        Returns session IDs for a graph.
        """
        query = 'SHOW TAG VALUES FROM "' + self.graph_sha + '" WITH KEY = session_id'
        res = self.client.query(query)
        sessions = []
        values = _get_result_values(res)
        if values:
            for [s, session_id] in values:
                sessions.append(session_id)
        return sessions

    # TODO: Test the case when application started, but failed to finish - what is the result of query then?
    def getExecutionTime(self, session_id, app_key):
        """
        Returns application execution time. 
        Returns -1 if no data found.
        """
        query = "SELECT ELAPSED(value,1s) FROM \"" + self.graph_sha + "\" WHERE \"key\" = '" + app_key + "' AND session_id = '" + session_id + "'"
        res = self.client.query(query)
        values = _get_result_values(res)
        exec_time = -1
        if values:
            # TODO: Calculate average time among different oid.
            exec_time = values[0][1]
        return exec_time

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

    def get_average_execution_time(self, sessions, app_key):
        """
        Returns the average execution time, for a given application, among different sessions.
        """
        if (len(sessions) > 0):
            return 0.

        total_exec_time = 0.
        num_records = 0
        # Loop over all graph sessions, and calculate the total execution time.
        for session in sessions:
            exec_time = self.reader.getExecutionTime(session, app_key)
            if (exec_time >= 0):
            # A record found in the DB.
                total_exec_time += float(exec_time)
                num_records += 1
        if (num_records > 0):
            avg_exec_time = total_exec_time / float(num_records)
            return avg_exec_time
        else:
            # No records found in the DB.
            return 0.

    def translate_execution_time(self):
        """
        Parametrizes the application execution time in a graph.
        """
        sessions = self.reader.getSessionIDs()
        if (len(sessions) == 0):
            return False

        num_app = 0
        # Loop over graph applications, and parametrize the execution time.
        for jd in self.graph['nodeDataArray']:
            categoryType = jd['categoryType']
            if (categoryType == 'ApplicationDrop'):
                num_app += 1
                app_key = str(jd['key'])
                avg_exec_time = self.get_average_execution_time(sessions, app_key)

                if (avg_exec_time > 0.):
                    # Replace execution time in the graph.
                    filter(lambda x: x['name'] == 'execution_time', jd['fields'])[0]['value'] = str(int(avg_exec_time))

        print "Translated execution time for ", num_app, " applications, based on ", len(sessions), " sessions data."
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
