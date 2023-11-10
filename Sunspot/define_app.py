from balsam.api import ApplicationDefinition, Site, site_config
import os
import re

site_name = "LlammaDemo"


class LlamaBashApp(ApplicationDefinition):
    site = site_name

    
    def shell_preamble(self):
        return f'source /soft/datascience/conda-2023-01-31/miniconda3/bin/activate && conda activate /gila/Aurora_deployment/conda_env_llm/balsam_llama_env && source /gila/Aurora_deployment/70B-acc_fix_for_ppi/set_application_env.sh'


    command_template = "-env CCL_WORKER_AFFINITY {{CCL_GROUP}} -env MASTER_PORT {{MASTER_PORT}} --cpu-bind list:{{CPU_BIND_GROUP}} python3 -u /gila/Aurora_deployment/70B-acc_fix_for_ppi/intel-extension-for-transformers/examples/huggingface/pytorch/text-generation/inference/run_generation_with_deepspeed.py \
    -m /gila/Aurora_deployment/llama-2-hf/Llama-2-70b-chat-hf \
    --benchmark --num-iter 1 --num-warmup 1 --ipex --input-tokens=1024 --max-new-tokens=1024 --prompt {{prompt}} --protein-list {{protein_list}} && sleep 5"

LlamaBashApp.sync()
