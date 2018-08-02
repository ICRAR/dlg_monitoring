## Usage (on a cluster):

*1. Install Prometheus client:*  
pip install prometheus_client

*2. Install DALiuGE:*  
pip install git+https://github.com/ICRAR/daliuge

*3. Submit the Slurm script, e.g. as:*  
sbatch -N 2 -p debugq submit_cluster.sh

## Test Run (on a local PC):

*1. Install Prometheus client:*  
pip install prometheus_client

*2. Run Prometheus db server (with a path to config file specified), e.g.:*  
~/prometheus-2.3.1.linux-amd64/prometheus --config.file=$HOME/dlg_monitoring/dlg2prom/tests/prometheus.yml

*3. Run DALiuGE node manager with this listener:*  
dlg nm -P 9000 -v --event-listener=dlg2prom.listener --dlg-path=~/dlg_monitoring/dlg2prom

*4. Translate and submit a graph to the DALiuGE node manager:*  
dlg unroll-and-partition -L ~/dlg_monitoring/graphs/Vitaliy.graph | dlg submit -p 9000

