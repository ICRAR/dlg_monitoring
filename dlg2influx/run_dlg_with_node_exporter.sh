#!/bin/bash

# Path to the node exporter binary.
node_exporter="$HOME/node_exporter-0.16.0.linux-amd64/node_exporter"

# Run node exporter.
$node_exporter &
node_exporter_pid=$!

# Run DALiuGE (on the same node with node exporter).
"$@" &
dlg_pid=$!

# TODO: Workaround, before proper stopping of DALiuGE gets implemened.
sleep 60
kill -9 $dlg_pid

kill $node_exporter_pid
