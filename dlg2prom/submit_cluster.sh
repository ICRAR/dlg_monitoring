#!/bin/bash --login

#SBATCH --ntasks-per-node=1
#SBATCH --job-name=daliuge
#SBATCH --time=00:01:00

#-------------------------------------------------
# Loading modules.
#-------------------------------------------------

module swap PrgEnv-cray PrgEnv-gnu
module load python/2.7.10
# the pip-installed mpi4py module in the virtual_env somehow does not work with the
# Magnus MPI environment, so we need to load the system mpi4py module, which means
# to load system python 2.7 module first to make sure everything is in 2.7
module load mpi4py

#--------------------------------------------------
# Generating the list of Prometheus targets.
#--------------------------------------------------

# Target listen port.
PORT=8080

#SLURM_JOB_NODELIST='nid000[11-13]'
echo $SLURM_JOB_NODELIST
HOSTS=$(scontrol show hostnames $SLURM_JOB_NODELIST)
TARGETS=($HOSTS)

hostspec=()
for host in ${TARGETS[*]}
do
    hostspec+=("'$host:$PORT'")
done

TARGETS_STRING=$(echo "${hostspec[*]}" | sed 's/ /, /g')

echo $TARGETS_STRING

#---------------------------------------------------
# Generating Prometheus config file.
#---------------------------------------------------

CONFIG_FILE_TEMPLATE="./prometheus_dlg_template.yml"
CONFIG_FILE="./prometheus_dlg.yml"
# Data scraping interval.
INTERVAL="1s"

sed "s/__TARGETS__/$TARGETS_STRING/;s/__INTERVAL__/$INTERVAL/g" $CONFIG_FILE_TEMPLATE > $CONFIG_FILE

#---------------------------------------------------
# Running Prometheus server.
#---------------------------------------------------

# Path to Prometheus application.
PROMETHEUS_APP="./prometheus-2.3.1.linux-amd64/prometheus"
# Prometheus server listen address.
PROMETHEUS_LISTEN_ADDRESS="0.0.0.0:8080"
# Path to the Prometheus database.
PROMETHEUS_DB_PATH="/tmp/vogarko-prometheus-data/"

COMMAND="$PROMETHEUS_APP --config.file=$CONFIG_FILE --web.listen-address=$PROMETHEUS_LISTEN_ADDRESS --storage.tsdb.path=$PROMETHEUS_DB_PATH"
# Enabling debug logging.
COMMAND="$COMMAND --log.level=debug"

echo $COMMAND
$COMMAND &

prometheus_pid=$!
echo "PID=$prometheus_pid"

#--------------------------------------------------
# Runing DALiuGE.
#--------------------------------------------------

SID=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_DIR="/tmp/vogarko-dlg-logs/"$SID
# Path to logical graph.
LOGICAL_GRAPH_PATH="./dlg_monitoring/dlg2prom/tests/Vitaliy.graph"

mkdir -p $LOG_DIR # To remove potential directory creation conflicts later.

# Prometheus listener. Default path is "~/.dlg/lib"
PROMETHEUS_LISTENER="dlg2prom.listener"

srun --export=all /home/vogarko/test_venv/bin/python -m dlg.deploy.pawsey.start_dfms_cluster -l $LOG_DIR -L $LOGICAL_GRAPH_PATH --event-listener=$PROMETHEUS_LISTENER &

#-------------------------------------------------
sleep 40
kill $prometheus_pid
wait $prometheus_pid
ls $PROMETHEUS_DB_PATH

echo "FINISHED!"

# Copy Prometheus DB to home directory.
cp -r $PROMETHEUS_DB_PATH $HOME


