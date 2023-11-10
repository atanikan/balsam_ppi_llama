# To run the demo

## On Alienware laptop

1. Activate conda environment
```
conda activate myenv
```

2. Ensure you have `balsam login --force` to christines account

3. Ensure the site name is `Llamademo`. The queues names on the site are set as per the following on the following days

```bash
richp@uan-0001:~ $ TZ="America/Chicago" pbs_rstat
Resv ID         Queue         User     State             Start / Duration / End
-------------------------------------------------------------------------------
R5607178.amn-00 R5607178      atanikan RN          Today 13:30 / 14400 / Today 17:30
/home/alien/Documents/code/balsam_ppi_llama/Sunspot
R5607181.amn-00 R5607181      atanikan CO            Fri 11:00 / 14400 / Fri 15:00
R5607184.amn-00 R5607184      atanikan CO     Sun Nov 12 14:30 / 14400 / Sun Nov 12 18:30
R5607186.amn-00 R5607186      atanikan CO     Mon Nov 13 18:00 / 16200 / Mon Nov 13 22:30
R5607188.amn-00 R5607188      atanikan CO     Tue Nov 14 10:30 / 32400 / Tue Nov 14 19:30
R5607189.amn-00 R5607189      atanikan CO     Wed Nov 15 10:30 / 32400 / Wed Nov 15 19:30
R5607190.amn-00 R5607190      atanikan CO     Thu Nov 16 10:30 / 21600 / Thu Nov 16 16:30
```

4. Run define_app.py once

```
cd /home/alien/Documents/code/balsam_ppi_llama/Sunspot
python3 define_app.py
```

5. Run define_jobs.py

```
cd /home/alien/Documents/code/balsam_ppi_llama/Sunspot
python3 define_jobs.py
```

6. Before running build_dot_file.py ensure the path to dot file is `/home/alien/Documents/code/protein-graph-visualization-main/src/visg/static/data` and the fileystem is mounted and pointing correctly. This should be left running until it stops. If stopped and restarted it will rename the exisiting dot file at its location and create a new one from scratch.

```
sshfs -o cache=yes,kernel_cache,allow_other,default_permissions csimpson@sunspot.alcf.anl.gov:/lus/gila/projects/Aurora_deployment/anl_llama/demo/LlamaDemo/data/LlamaBashAppOutput ~/Documents/code/mount_remote_system/data
cd /home/alien/Documents/code/balsam_ppi_llama/Sunspot
python3 build_dot_file.py
```

7. Run visualization

``` 
cd ~/Documents/code/protein-graph-visualization-main/src
./start.sh
```

8. Open [http://127.0.0.1:5000/index](http://127.0.0.1:5000/index) on Chrome
