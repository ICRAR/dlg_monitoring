#!/bin/bash

# Path to the node exporter binary.
node_exporter="$HOME/node_exporter-0.16.0.linux-amd64/node_exporter"

# Run node exporter.
$node_exporter &

node_exporter_pid=$!

# Run DALiuGE (on the same node with node exporter).
"$@" &

dlg_pid=$!

wait $dlg_pid

kill $node_exporter_pid
wait $node_exporter_pid

echo "OLOLO"
