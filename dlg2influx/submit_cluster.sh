#!/bin/bash --login

#SBATCH --ntasks-per-node=1
#SBATCH --job-name=daliuge
#SBATCH --time=00:05:00

#-------------------------------------------------
# Setup parameters.
#-------------------------------------------------
# Python interpreter path.
python="$HOME/test_venv/bin/python"

# Path to a logical graph.
logical_graph="$HOME/dlg_monitoring/graphs/Vitaliy_scatter_long.graph"

# DALiuGE event listener.
dlg_listener="$HOME/dlg_monitoring/dlg2influx/dlg2influx.py" 
dlg_listener_class="dlg2influx.Listener"

# Graph parametrizer.
graph_parametrizer=$dlg_listener

# Path to the srun script.
srun_script="$HOME/dlg_monitoring/dlg2influx/run_dlg_with_node_exporter.sh"

# Path to the node exporter binary.
export NODE_EXPORTER="$HOME/node_exporter-0.16.0.linux-amd64/node_exporter"

#-------------------------------------------------
# InfluxDB parameters.
#-------------------------------------------------
# InfluxDB access parameters. (These are also used by the listener & parametrizer.)
export INFLUXDB_HOST="ec2-54-159-33-236.compute-1.amazonaws.com"
export INFLUXDB_PORT="8086"
export INFLUXDB_NAME="daliuge"
export INFLUXDB_USER=""
export INFLUXDB_PASSWORD=""

#-------------------------------------------------
# Prometheus parameters.
#-------------------------------------------------
# Target listen port. (Using the port exposed by the node exporter.)
prometheus_target_port=9100

# Path to the template config file.
prometheus_template_config="$HOME/dlg_monitoring/dlg2influx/prometheus_dlg_template.yml"

# Data scraping interval (sec).
prometheus_scraping_interval=5

# Path to Prometheus application.
prometheus_app="./prometheus-2.3.1.linux-amd64/prometheus"
# Prometheus server listen address.
prometheus_listen_address="0.0.0.0:8080"
# Path to the Prometheus database.
prometheus_db_path="/tmp/dlg-prometheus-data/"

#-------------------------------------------------
# Extract sha-value from the graph.
#-------------------------------------------------
sha=$(sed -r -n 's/.*"sha": *"([a-z0-9]+)".*/\1/p' $logical_graph)
echo "sha=$sha"

export GRAPH_SHA=$sha

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
# Generating the list of Prometheus targets.
#--------------------------------------------------
#SLURM_JOB_NODELIST='nid000[11-13]'
echo $SLURM_JOB_NODELIST
hosts=$(scontrol show hostnames $SLURM_JOB_NODELIST)
targets=($hosts)

hostspec=()
for host in ${targets[*]}
do
    hostspec+=("'$host:$prometheus_target_port'")
done

prometheus_targets=$(echo "${hostspec[*]}" | sed 's/ /, /g')

echo $prometheus_targets

#---------------------------------------------------
# Generating Prometheus config file.
#---------------------------------------------------
# Prometheus database credentials.
prometheus_db_name=$INFLUXDB_NAME
prometheus_user=$INFLUXDB_USER
prometheus_password=$INFLUXDB_PASSWORD

remote_write_url="http://${INFLUXDB_HOST}:${INFLUXDB_PORT}/api/v1/prom/write?u=${prometheus_user}\\&p=${prometheus_password}\\&db=${prometheus_db_name}"

# Auto-generated config file path.
prometheus_config="$HOME/prometheus_dlg.yml"

# Generate the Prometheus config file from a template.
_sed_cmd="
s/__TARGETS__/$prometheus_targets/
s#__REMOTE_WRITE_URL__#$remote_write_url#
s/__INTERVAL__/${prometheus_scraping_interval}s/g"

sed "$_sed_cmd" $prometheus_template_config > $prometheus_config

#---------------------------------------------------
# Running Prometheus server.
#---------------------------------------------------
mkdir -p $prometheus_db_path

run_command="$prometheus_app --config.file=$prometheus_config --web.listen-address=$prometheus_listen_address --storage.tsdb.path=$prometheus_db_path"

# Enabling debug logging.
run_command="$run_command --log.level=debug"

echo $run_command
$run_command &

prometheus_pid=$!

#-----------------------------------------------------
# Translate LG to PLG (Parametrized Logical Graph).
#-----------------------------------------------------
temp_dir="./tmp"
sid=$(date +"%Y-%m-%d_%H-%M-%S")
mkdir -p $temp_dir
parametrized_graph="$temp_dir/PLG_${sid}.graph"

$python $graph_parametrizer -L $logical_graph -o $parametrized_graph

#--------------------------------------------------
# Runing DALiuGE.
#--------------------------------------------------
sid=$(date +"%Y-%m-%d_%H-%M-%S")
# Folder for storing logs.
dlg_log_dir="$HOME/dlg-logs/"$sid

mkdir -p $dlg_log_dir # To remove potential directory creation conflicts later.

# Defualt DALiuGE lib path.
dlg_lib_path="$HOME/.dlg/lib"

# Copy event listener to DALiuGE libs folder.
cp $dlg_listener $dlg_lib_path

srun --export=all $srun_script $python -m dlg.deploy.pawsey.start_dfms_cluster -l $dlg_log_dir -L $parametrized_graph --event-listener=$dlg_listener_class

echo "Finished srun!"

#-------------------------------------------------
# Kill Prometheus server (forcing it to write/flush the data).
kill $prometheus_pid
wait $prometheus_pid

echo "Finished all!"



