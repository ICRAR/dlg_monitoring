## Usage (on a cluster):

*1. Install InfluxDB client:*  
pip install influxdb

*2. Install DALiuGE:*  
pip install git+https://github.com/ICRAR/daliuge

*3. Submit the Slurm script:*  
sbatch -N 2 -p debugq ~/dlg_monitoring/dlg2influx/submit_cluster.sh


