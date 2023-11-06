# Protein-Protein Interaction Analysis with Balsam on Thetagpu & Polaris

Leverage the capabilities of [Balsam](https://balsam.readthedocs.io/en/latest/) to employ a vLLM service API, utilizing Llama 70B for Protein-Protein Interaction (PPI) identification on Polaris. Balsam enables code execution on remote systems. This guide details the steps for setting up a Balsam site on Polaris and executing a vLLM service for PPI discovery.

## Prerequisites
- Clone this repository.
- Obtain the necessary validation files for PPI analysis from [this link](https://anl.box.com/s/nva3ypf5lpzk7oxz2efw4xd6dcug6j8s).

## Table of Contents
- [Setup vllm and balsam](#setup-vllm-and-balsam-environments)
- [Create Balsam Sites](#create-balsam-sites-in-remote-or-local-and-start)
- [Run the Application](#run-the-app-and-submit-jobs)

### Setup vllm and Balsam Environments

Create a conda environment for vllm and Balsam on Polaris:

```bash
module load conda
conda create -n balsam-vllm-polaris python=3.9 -y
conda activate balsam-vllm-polaris
pip install --pre balsam
pip install vllm pandas
```

### Create and Start Balsam Sites

1. To establish a Balsam site on Polaris for job submission:

```bash
balsam login
balsam site init polaris-site
cd polaris-site
balsam site start
```

> **Note**: For remote job submission, after configuring the Polaris site, install Balsam, vllm, and pandas locally (Python=3.9) to manage jobs and retrieve results from a remote location.

2. Review and adjust your [job-template.sh](job-template.sh) as demonstrated [here](job-template.sh). 

> **Note**: Balsam offers elastic queue features that adjust automatically based on job demand. Consult my [settings.yml](settings.yml) for configuration details.

> **Note**: To submit jobs locally, modify the launcher settings in `settings.yml` by changing `mpi_app_launcher: balsam.platform.app_run.MPICHRun` to `mpi_app_launcher: balsam.platform.app_run.LocalAppRun`.

### Execute the Application and Submit Jobs

Within the Polaris site:

1. Make sure the [csv files](https://anl.box.com/s/nva3ypf5lpzk7oxz2efw4xd6dcug6j8s) are placed in the directory from which you are operating the app and submitting jobs. Subsequently run the following:

> **Note**: Below process will begin job submission. In the [define_jobs.py](define_jobs.py) script, modify `df = df.loc[0:999]` to not process all 19k proteins. Currently, the application processes 100 proteins per instance. Adjust the batch size in `self.get_word_batches(df,100)` as required.

> **Note**: Also, update the conda environment in the [define_app.py](define_app.py) script within the `shell_preamble` to match your setup and ensure it references [vllm_batch.py](vllm_batch.py) appropriately.

```bash
python3 define_app.py
python3 define_jobs.py
```

3. Following job completion, select either [parallel_dot_construction.py](parallel_dot_construction.py) or [serial_dot_construction.py](serial_dot_construction.py) to process the output. Check that `output_path` and `dot_file_path` are set correctly.

```bash
python3 parallel_dot_construction.py
```
