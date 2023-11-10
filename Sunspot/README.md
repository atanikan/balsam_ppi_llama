# Run Protein Protein Interaction using Balsam on Sunspot
We are using [Balsam](https://balsam.readthedocs.io/en/latest/) to run a Llama LLM on Sunspot for finding Protein Protein interaction.

Got to [notes for demo](./NOTES_FOR_DEMO.md) after this setup to run demo from a demo laptop. 

Begin by cloning this repo on Sunspot.

## Create site

Load conda module:
```bash
source /soft/datascience/conda-2023-01-31/miniconda3/bin/activate
conda activate /gila/Aurora_deployment/conda_env_llm/balsam_llama_env
```
Login
```bash
balsam login --force
```
Copy and paste the URL in a browser and follow the instructions.  Note there is currently a bug in the command line prompt for login.  Ignore the warning messages.

Create site
```bash
balsam site init -n LlamaDemo LlamaDemo
```
Follow the instructions at the prompt.  Select Sunspot for the machine.

## Activate site

Copy sample settings file to your site directory

```bash
cp balsam_ppi_llama/sample_settings.yml /path/to/your/site
```

Look-up which reservation queue is active for the day.  Edit the `settings.yml` file you just copied.  Under `elastic` set `submit_queue: "<todays_reservation>"`.

Go to site directory and start site
```bash
cd /path/to/your/site
balsam site start
```

Check that the site is "active", i.e. communicating with the Balsam server:
```bash
balsam site ls
```