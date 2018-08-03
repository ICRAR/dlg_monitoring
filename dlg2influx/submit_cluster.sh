#!/bin/bash --login

#SBATCH --ntasks-per-node=1
#SBATCH --job-name=daliuge
#SBATCH --time=00:02:00

#-------------------------------------------------
# Common parameters.
#-------------------------------------------------
# Path to a logical graph.
LOGICAL_GRAPH_PATH="~/dlg_monitoring/graphs/Vitaliy.graph"

# InfluxDB access parameters.
export INFLUXDB_HOST="ec2-54-159-33-236.compute-1.amazonaws.com"
export INFLUXDB_PORT="8086"
export INFLUXDB_NAME="daliuge"
export INFLUXDB_USER=""
export INFLUXDB_PASSWORD=""

#-------------------------------------------------
# Loading modules.
#-------------------------------------------------

module swap PrgEnv-cray PrgEnv-gnu
module load python/2.7.14
# The pip-installed mpi4py module in the virtual_env somehow does not work with the
# Magnus MPI environment, so we need to load the system mpi4py module, which means
# to load system python 2.7 module first to make sure everything is in 2.7
module load mpi4py

#--------------------------------------------------
# Runing DALiuGE.
#--------------------------------------------------

SID=$(date +"%Y-%m-%d_%H-%M-%S")
# Folder for storing logs.
LOG_DIR="./dlg-logs/"$SID

mkdir -p $LOG_DIR # To remove potential directory creation conflicts later.

# Defualt DALiuGE libs path.
DLG_DEFAULT_PATH="~/.dlg/lib"

# DALiuGE event listener. Default path is "~/.dlg/lib"
EVENT_LISTENER="dlg2influx.listener"

# Copy listener to DALiuGE libs folder.
cp ~/dlg_monitoring/dlg2influx/dlg2influx.py $DLG_DEFAULT_PATH

srun --export=all /home/vogarko/test_venv/bin/python -m dlg.deploy.pawsey.start_dfms_cluster -l $LOG_DIR -L $LOGICAL_GRAPH_PATH --event-listener=$EVENT_LISTENER

#-------------------------------------------------
echo "FINISHED!"



