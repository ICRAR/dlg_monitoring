#!/bin/bash --login

#SBATCH --ntasks-per-node=1
#SBATCH --job-name=daliuge
#SBATCH --time=00:02:00

#-------------------------------------------------
# Main parameters.
#-------------------------------------------------

# Python interpreter path.
PYTHON="/home/vogarko/test_venv/bin/python"

# Path to a logical graph.
LOGICAL_GRAPH_PATH="$HOME/dlg_monitoring/graphs/Vitaliy_long.graph"

# InfluxDB access parameters.
export INFLUXDB_HOST="ec2-54-159-33-236.compute-1.amazonaws.com"
export INFLUXDB_PORT="8086"
export INFLUXDB_NAME="daliuge"
export INFLUXDB_USER=""
export INFLUXDB_PASSWORD=""

# DALiuGE event listener.
EVENT_LISTENER_PATH="$HOME/dlg_monitoring/dlg2influx/dlg2influx.py" 
EVENT_LISTENER_CLASS="dlg2influx.Listener"

# Graph parametrizer.
PARAMETRIZER_PATH=$EVENT_LISTENER_PATH

#-------------------------------------------------
# Extract sha-value from the graph.
#-------------------------------------------------
SHA=$(sed -r -n 's/.*"sha": *"([a-z0-9]+)".*/\1/p' $LOGICAL_GRAPH_PATH)
echo "SHA=$SHA"
export GRAPH_SHA=$SHA

#-------------------------------------------------
# Loading modules.
#-------------------------------------------------

module swap PrgEnv-cray PrgEnv-gnu
module load python/2.7.14
# The pip-installed mpi4py module in the virtual_env somehow does not work with the
# Magnus MPI environment, so we need to load the system mpi4py module, which means
# to load system python 2.7 module first to make sure everything is in 2.7
module load mpi4py

#-----------------------------------------------------
# Translate LG to PLG (Parametrized Logical Graph).
#-----------------------------------------------------
$PYTHON $PARAMETRIZER_PATH

#--------------------------------------------------
# Runing DALiuGE.
#--------------------------------------------------

SID=$(date +"%Y-%m-%d_%H-%M-%S")
# Folder for storing logs.
LOG_DIR="$HOME/dlg-logs/"$SID

mkdir -p $LOG_DIR # To remove potential directory creation conflicts later.

# Defualt DALiuGE lib path.
DLG_LIB_PATH="$HOME/.dlg/lib"

# Copy event listener to DALiuGE libs folder.
cp $EVENT_LISTENER_PATH $DLG_LIB_PATH

srun --export=all $PYTHON -m dlg.deploy.pawsey.start_dfms_cluster -l $LOG_DIR -L $LOGICAL_GRAPH_PATH --event-listener=$EVENT_LISTENER_CLASS

#-------------------------------------------------
echo "FINISHED!"



