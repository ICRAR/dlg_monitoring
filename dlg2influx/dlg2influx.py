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
from influxdb import InfluxDBClient

# Name of environment variables.
host_env = 'INFLUXDB_HOST'
port_env = 'INFLUXDB_PORT'
dbname_env = 'INFLUXDB_NAME'
user_env = 'INFLUXDB_USER'
password_env = 'INFLUXDB_PASSWORD'
graph_sha_env = 'GRAPH_SHA'

class listener(object):
    """
    A listener class for storing DALiuGE drop events to InfluxDB database.
    """
    def __init__(self):
        # Retrieve database info from environment variables.
        host = os.getenv(host_env, 'localhost')
        port = os.getenv(port_env, 8086)
        dbname = os.getenv(dbname_env, 'daliuge')
        user = os.getenv(user_env, '')
        password = os.getenv(password_env, '')

        """Instantiate the connection to the InfluxDB client."""
        self.client = InfluxDBClient(host, port, user, password, dbname)

        #self.graph_sha = os.getenv(graph_sha_env, None)
        self.graph_sha = os.getenv(graph_sha_env, 'test')

    def handleEvent(self, event):
        if (self.graph_sha is not None):
            if (event.type == 'execStatus'):
            # An event from application drop received.
                oid = event.oid
                name = event.name
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

                # Create measurement data.
                json_body = [
                    {
                        "measurement": measurement_name,
                        "tags": {
                            "session_id": session_id,
                            "oid": oid,
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

