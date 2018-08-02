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
from influxdb import InfluxDBClient

host = 'localhost'
port = 8086

dbname = 'daliuge'
user = ''
password = ''

class listener(object):
    """
    A listener class for storing DALiuGE drop events to InfluxDB database.
    """
    def __init__(self):
        """Instantiate the connection to the InfluxDB client."""
        protocol = 'json'
        self.client = InfluxDBClient(host, port, user, password, dbname)

    def handleEvent(self, event):
        if (event.type == 'execStatus'):
        # An event from application drop received.
            oid = event.oid
            name = event.name
            print "Handling the event with oid =", oid
            #
            value = -1
            if (event.execStatus == 1):
            # Started.
                value = 1
            elif (event.execStatus == 2):
            # Finished.
                value = 0
            # Create measurement data.
            json_body = [
                {
                    "measurement": event.session_id.replace(".", "_"),
                    "tags": {
                        "oid": oid,
                        "name": name
                    },
                    "fields": {
                        "value": value
                    }
                }
            ]
            # Write data to the database.
            self.client.write_points(json_body)

