#!/bin/bash --login

#BATCH --ntasks-per-node=1
#SBATCH --job-name=dlg_with_monitor
#SBATCH --time=00:01:00

#--------------------------------------------------
# Generating the list of Prometheus targets.
#--------------------------------------------------

# Target listen port.
PORT=8000

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
LISTEN_ADDRESS="0.0.0.0:8000"
# Path to the Prometheus database.
DB_PATH="/tmp/vogarko-prometheus-data/"

COMMAND="$PROMETHEUS_APP --config.file=$CONFIG_FILE --web.listen-address=$LISTEN_ADDRESS --storage.tsdb.path=$DB_PATH"
# Enabling debug logging.
COMMAND="$COMMAND --log.level=debug"

echo $COMMAND
$COMMAND

