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
import threading
from prometheus_client import start_http_server, Gauge

# A port number of the server to expose the metrics.
METRIC_SERVER_PORT = 8000
# A prefix for metric names.
METRIC_NAME_PREFIX = 'DALiuGE_'
# Metric description.
METRIC_DESCRIPTION = 'DALiuGE drop events'

class listener(object):
    """
    A listener class for pulling DALiuGE drop events to Prometheus database.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self.gauge_metric = None
        # Start up the server to expose the metrics.
        start_http_server(METRIC_SERVER_PORT)

    def handleEvent(self, event):
        with self._lock:
            if (self.gauge_metric == None):
                # Create a metric.
                metric_name = METRIC_NAME_PREFIX + event.session_id.replace(".", "_")
                self.gauge_metric = Gauge(
                    metric_name,
                    METRIC_DESCRIPTION,
                    ['oid', 'name'])
                print "Created a Prometheus metric with name ", metric_name

        if (event.type == 'execStatus'):
        # An event from application drop received.
            _oid = event.oid
            _name = event.name
            print "Handling the event with oid =", _oid
            #
            if (event.execStatus == 1):
            # Started.
                self.gauge_metric.labels(oid=_oid, name=_name).set(1.0)
            elif (event.execStatus == 2):
            # Finished.
                self.gauge_metric.labels(oid=_oid, name=_name).set(0.0)

