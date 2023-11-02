# Run Protein Protein Interaction using Balsam on Sunspot
We are using [Balsam](https://balsam.readthedocs.io/en/latest/) to run a Llama LLM on Sunspot for finding Protein Protein interaction.

## Prerequisites
1. Clone this repository
2. Download the validation files needed for running protein protein interaction from [here](https://anl.box.com/s/nva3ypf5lpzk7oxz2efw4xd6dcug6j8s) 

## Table of Contents

* [Setup Llama70B](#setup-llama70b-and-balsam-environments)
* [Create Balsam Site in remote and local](#create-balsam-sites-in-remote-or-local-and-start)
* [Run the app](#run-the-app-and-submit-jobs)

### Setup Llama70B and Balsam environments

Ensure the Llama70B conda environment is setup on Sunspot.

1. Either use existing conda environment.

```bash
source /soft/datascience/conda-2023-01-31/miniconda3/bin/activate
conda activate /gila/Aurora_deployment/conda_env_llm/balsam_llama_env
```

OR create conda environment from scratch for Llama70B and balsam

```bash
cd /gila/Aurora_deployment/70B-acc_fix_for_ppi/
source /soft/datascience/conda-2023-01-31/miniconda3/bin/activate
conda create -n anl_llma70_acc_fix python=3.9 --y
conda activate anl_llma70_acc_fix
source run_setup.sh
pip install --pre balsam
```

2. Install balsam and pandas locally as well (Python=3.9) to run jobs and poll results from remote location. Ensure the python version matches with the remote environment.

```bash
python3.9 -m venv env
source ~/env/bin/activate
pip install pandas
pip install --pre balsam
```

### Create Balsam Sites in remote or local and start

1. Create a balsam site on Sunspot and select Sunspot in order to submit jobs.
```bash
balsam login
balsam site init sunspot-site
cd sunspot-site
balsam site start
```

2. If you want to poll results back to local system, create a balsam site on your local system and select Local to run the polling job.
```bash
balsam login
balsam site init local-site
cd local-site
```
Before starting, change the launcher settings in `settings.yml` from `mpi_app_launcher: balsam.platform.app_run.MPICHRun` to `mpi_app_launcher: balsam.platform.app_run.LocalAppRun`

The file should now look like this

```bash
# Launcher settings
    ...
    mpi_app_launcher: balsam.platform.app_run.LocalAppRun
    local_app_launcher: balsam.platform.app_run.LocalAppRun
    ..
```

Finally start the site

```bash
balsam site start
```

### Run the app and submit jobs

1. This can be run inside Sunspot site. Ensure you have the [csv files](https://anl.box.com/s/nva3ypf5lpzk7oxz2efw4xd6dcug6j8s) and [set_application_env.sh](set_application_env.sh) file in the same site directory as to where you are running the app and submitting the jobs from 

```bash
python3 define_app.py
python3 define_jobs.py
```

> _Note:_ This should start submitting jobs. From the [define_jobs.py](define_jobs.py) file, change the `df = df.loc[0:999] #change this to run all` to fetch all 19k proteins. The app also as of now runs 100 proteins per instance. Change the batch size `self.get_word_batches(df,100)` to increase as needed. You can also make 3 instance run on one node by changing this `node_packing_count = 1 #change this to set number of jobs in parallel on same node; set to 3 once fixed` once it's fixed on Sunspot.

> _Note:_ Change the conda environment within the [define_app.py](define_app.py) in shell_preamble as well to your custom environment if needed.

2. Before you start running the polling app on your local system. Change the directory parameter inside [define_polling_app.py](define_polling_app.py) file to the path where [define_jobs.py](define_jobs.py) writes the output to.

```bash
jobs = [
    BatchPollingApp.submit(
        workdir=f'BatchPollingAppOutput/{protein}',
        directory="/gila/Aurora_deployment/atanikanti/LLM_service/balsam_service_ppi_llm_70B/balsam-llama-sunspot-site/data/LlamaBashAppOutput", #CHANGE THIS
        protein = protein,
        timeout=60,
        tags={"target":protein},
    )
    for n,protein in enumerate(df['search_words'].loc[0:999])
]
```

3. Run the polling app from within the local-site directory

```bash
python3 define_polling_app.py
```

> _Note:_ The Polling app should keep fetching results as they are generated remotely. Right now the polling app will create 1000 jobs one for each protein and poll each as and when it finds. Greater than 2000 proteins or jobs makes it slow.Change the `df['search_words'].loc[0:999]` as to poll more proteins

