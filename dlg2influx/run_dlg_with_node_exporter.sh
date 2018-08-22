#!/bin/bash

# Run the node exporter.
$NODE_EXPORTER &
node_exporter_pid=$!

# Run DALiuGE (on the same node with node exporter).
"$@" &
dlg_pid=$!

# TODO: Workaround, before proper stopping of DALiuGE gets implemened.
sleep 90
kill -9 $dlg_pid

kill $node_exporter_pid
