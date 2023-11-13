# To run the demo

## On Sunspot

1.  The queues names on Sunspot are set as per the following on the following days

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
You must go to your site on Sunspot and in the `settings.yml` file under `elastic` set submit_queue: "<todays_reservation>".

Start the site with `balsam site start` from within the site directory or if it is already active, restart it with `balsam site sync`.

## On Alienware laptop
1. Open a terminal.  Mount your site's data directory onto the demo laptop:
```bash
sshfs -o cache=yes,kernel_cache,allow_other,default_permissions <YOUR_USER_NAME>@sunspot.alcf.anl.gov:/lus/gila/projects/Aurora_deployment/anl_llama/demo/LlamaDemo/data/LlamaBashAppOutput ~/Documents/code/mount_remote_system/data
```
You will be asked for your credentials twice, once for bastion, once for Sunspot.

2. Open a new tab in the terminal (Shift+Ctrl+t).  Activate conda environment and start the viz.
```
conda activate myenv
cd ~/Documents/code/protein-graph-visualization-main/src
./start.sh
```
Leave this running.

3. Open another tab in the terminal.  Activate your conda environment and validate your credentials with the balsam service on the laptop:
```bash
conda activate myenv
balsam login --force
```

4. In the same tab, go to the code for starting balsam jobs on Sunspot
```bash
cd ~/Documents/code/balsam_ppi_llama/Sunspot
```
   Edit `define_app.py` and `define_jobs.py` to include your site name.
5. The demo is set up to run 300 proteins on 3 nodes by default.  To run the full set of proteins, in `define_jobs.py` look for the line [df = df.loc[0:299]](https://github.com/atanikan/balsam_ppi_llama/blob/58c52a43aa6b8c63606ef7d88c7b2e450e467831/Sunspot/define_jobs.py#L59C9-L59C27) in the function `define_job` and comment it out.

6. Start the run_all.sh script.  This will start the Balsam jobs and a script to pull data through the mount to the laptop:
```bash
./run_all.sh
```
Leave this running in the terminal.

7. Open [http://127.0.0.1:5000/index](http://127.0.0.1:5000/index) on Chrome.
8. You can set the viz to full screen with `F11` and then reload with `Shift+Ctrl+r`.
9. If the workflow completes, you can restart it by executing `run_all.sh` again.

You will have at this point 3 terminal tabs open, one running the viz server, one running the script pulling data through the mount, and one where you can check the tunnel status.  You may also want a fourth terminal on Sunspot to check the queue or deal with site issues.

## Shutdown

1. Stop the viz server by going to the terminal where it is running and hit `Ctrl+c`.  Close the chrome window.
2. Stop the script pulling data through the mount by going to the terminal where it is running and hit `Ctrl+c`.
3. Go to a terminal on Sunspot.  Go to your site, remove the app, and stop the site.
   ```bash
   cd /gila/Aurora_deployment/anl_llama/demo/LlamaDemo
   balsam app rm -n LlamaBashApp
   balsam site stop
   ```
4. Remove any running jobs from the queue
   ```bash
   qdel <pbs_job_id>
   ```
