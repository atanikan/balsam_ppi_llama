# Protein-Protein Interaction Analysis with Balsam on Polaris
Leverage the capabilities of [Balsam](https://balsam.readthedocs.io/en/latest/) to employ a [vLLM](https://vllm.readthedocs.io/) service API, utilizing Llama 70B for Protein-Protein Interaction (PPI) identification on Polaris. Balsam enables code execution on remote systems. This guide details the steps for setting up a Balsam site on Polaris and executing a vLLM service for PPI discovery.

## Prerequisites
- Clone this repository.
- Obtain the necessary validation files for PPI analysis from [this link](https://anl.box.com/s/nva3ypf5lpzk7oxz2efw4xd6dcug6j8s).

## Table of Contents
- [Setup vllm and balsam](#setup-vllm-and-balsam-environments)
- [Create Balsam Sites](#create-and-start-balsam-sites)
- [Run the Application](#execute-the-application-and-submit-jobs)

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

2. Review and adjust your [job-template.sh](job-template.sh) as demonstrated [here](job-template.sh). 

> **Note**: Balsam offers elastic queue features that adjust automatically based on job demand. Consult my [settings.yml](settings.yml) for configuration details.

> **Note**: For remote job submission, after configuring the Polaris site, install Balsam, vllm, and pandas locally (Python=3.9) to manage jobs and retrieve results from a remote location. You will select Local after `balsam site init`

### Execute the Application and Submit Jobs

Within the Polaris site:

1. Make sure the [csv files](https://anl.box.com/s/nva3ypf5lpzk7oxz2efw4xd6dcug6j8s) are placed in the directory from which you are operating the app and submitting jobs.

2. Update the conda environment in the [define_app.py](define_app.py) script within the `def shell_preamble` method to match your setup. Also ensure `command_template` references [vllm_batch.py](vllm_batch.py) appropriately.

> _Note:_ In the [define_jobs.py](define_jobs.py) script, modify `df = df.iloc[0:99]` to not process all 19k proteins. Also, currently, the application processes 100 proteins per instance. Adjust the batch size in `self.get_word_batches(df,100)` as required.

3. Finally run

```bash
python3 define_app.py
python3 define_jobs.py
```

> _Note:_ Use `qstat` and `balsam job ls` to check if the jobs are running and have finished. Other balsam commands are found in balsam [docs](https://balsam.readthedocs.io/en/latest/user-guide/jobs/).


4. Following job completion, select either [parallel_dot_construction.py](parallel_dot_construction.py) or [serial_dot_construction.py](serial_dot_construction.py) to process the output. Check that `output_path` and `dot_file_path` are set correctly.

```bash
python3 parallel_dot_construction.py
```
