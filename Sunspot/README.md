# Run Protein Protein Interaction using Balsam on Sunspot
We are using [Balsam](https://balsam.readthedocs.io/en/latest/) to run a Llama LLM on Sunspot for finding Protein Protein interaction.

Go to [notes for demo](./NOTES_FOR_DEMO.md) after this setup to run demo from a demo laptop. 

Begin by cloning this repo on Sunspot.

## Create site

First ensure you have environment variables for the http proxy set:
```bash
export HTTP_PROXY=http://proxy.alcf.anl.gov:3128
export HTTPS_PROXY=http://proxy.alcf.anl.gov:3128
export http_proxy=http://proxy.alcf.anl.gov:3128
export https_proxy=http://proxy.alcf.anl.gov:3128
```

Load conda module:
```bash
source /soft/datascience/conda-2023-01-31/miniconda3/bin/activate
conda activate /gila/Aurora_deployment/conda_env_llm/balsam_llama_env
```
Login
```bash
balsam login --force
```
Copy and paste the URL returned by the `balsam login` command in a browser and follow the instructions.  Note there is currently a bug in the command line prompt for login.  Ignore the warning messages.

Go to a location on `/gila`, e.g.
```bash
cd /gila/Aurora_deployment/anl_llama/demo
```

Once you are at the place on `/gila` where you want the site directory to be placed, create the site.
```bash
balsam site init -n LlamaDemo LlamaDemo
```

Follow the instructions at the prompt.  Select Sunspot for the machine.  Put in `Aurora_deployment` for your project.

## Activate site

Copy sample settings file to your site directory

```bash
cp /gila/Aurora_deployment/anl_llama/demo/balsam_ppi_llama/sample_settings.yml /gila/Aurora_deployment/anl_llama/demo/LlamaDemo
```

Look-up which reservation queue is active for the day.  Edit the `settings.yml` file you just copied.  Under `elastic` set `submit_queue: "<todays_reservation>"`.

Go to site directory and start site
```bash
cd /gila/Aurora_deployment/anl_llama/demo/LlamaDemo
balsam site start
```

Check that the site is "active", i.e. communicating with the Balsam server:
```bash
balsam site ls
```

Finally, create a directory under data which will be mounted on the demo laptop:
```bash
mkdir /gila/Aurora_deployment/anl_llama/demo/LlamaDemo/data/LlamaBashAppOutput
```
