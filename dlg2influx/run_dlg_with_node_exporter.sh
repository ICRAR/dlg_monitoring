#!/bin/bash

# Run the node exporter.
$NODE_EXPORTER &
node_exporter_pid=$!

# Run DALiuGE (on the same node with node exporter).
"$@"

kill $node_exporter_pid
