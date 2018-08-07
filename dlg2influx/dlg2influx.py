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

class Reader(object):
    """
    A class that reads graph data from InfluxDB database.
    """
    def __init__(self, sha):
        self.sha = sha
        # Connect to the InfluxDB client.
        self.client = connect_to_db()

        dbname = get_db_name()
        # Check if the database exists.
        db_exist = check_db_exists(self.client, dbname)

        if db_exist:
            print "Connected to InfluxDB database: ", dbname
        else:
            print "Could not connect to InfluxDB database: ", dbname

    def queryData(self):
        """
        Read data from InfluxDB.
        """
        print "Called queryData() for sha =", self.sha

class Listener(object):
    """
    A listener class for storing DALiuGE drop events to InfluxDB database.
    """
    def __init__(self):
        # Connect to the InfluxDB client.
        self.client = connect_to_db()

        try:
            dbname = get_db_name()
            # Check if the database exists.
            db_exist = check_db_exists(self.client, dbname)

            if db_exist:
                print "Connected to InfluxDB database: ", dbname
            else:
                # Create a new database.
                print "Could not find InfluxDB database. Creating a new database."
                self.client.create_database(dbname)
        except Exception as e:
            print e

        self.graph_sha = get_graph_sha()
        print "Graph sha =", self.graph_sha

    def handleEvent(self, event):
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

def get_graph_sha():
    return os.getenv(graph_sha_env, 'test')

def get_db_name():
    return os.getenv(dbname_env, DEFAULT_DB_NAME)

def connect_to_db():
    """Instantiate the connection to the InfluxDB client."""
    # Retrieve database connection parameters from environment variables.
    host = os.getenv(host_env, 'localhost')
    port = os.getenv(port_env, 8086)
    dbname = get_db_name()
    user = os.getenv(user_env, '')
    password = os.getenv(password_env, '')

    client = InfluxDBClient(host, port, user, password, dbname)
    return client

def check_db_exists(client, dbname):
    """ Check if the database exists."""
    try:
        res = client.query("show databases")
        db_exist = ([dbname] in res.raw['series'][0]['values'])
        return db_exist
    except Exception as e:
        print e

def translate_lg_to_plg():
    """
    Parametrizes logical graph essentially translating LG to PLG (parametrized logical graph).
    """
    parser = optparse.OptionParser()
    parser.add_option("-L", "--logical-graph", action="store", type="string",
                      dest="logical_graph", help="The filename of the logical graph to parametrize", default=None)

    (options, _) = parser.parse_args()

    if bool(options.logical_graph) == False:
        parser.error("A logical graph filename must be specified")

    lg_path = options.logical_graph
    if lg_path and not os.path.exists(lg_path):
        parser.error("Cannot locate graph file at '{0}'".format(lg_path))

    f = open(lg_path)
    with f:
        lg = json.load(f)
        print lg

    sha = get_graph_sha()
    reader = Reader(sha)
    reader.queryData()

if __name__ == '__main__':
    translate_lg_to_plg()
