from balsam.api import ApplicationDefinition, Site, site_config
import os
import re
import pandas as pd

site_name = "LlamaDemo"
app_path = os.getcwd()
proteins_file_path = os.path.join(app_path,"proteins.csv")
df = pd.read_csv(proteins_file_path, names=['search_words'])

class LlamaBashApp(ApplicationDefinition):
    site = site_name
    def flatten(self, lst):
        """
        Recursively flatten a nested list.
        """
        flat_list = []
        for item in lst:
            if isinstance(item, list):
                flat_list.extend(self.flatten(item))
            else:
                flat_list.append(item)
        return flat_list

    def nested_lists_to_string(self,nested_list):
        """
        Convert a nested list into a single string with spaces between items.
        """
        flat_list = self.flatten(nested_list)
        return ' '.join(map(str, flat_list))
    
    def fetch_between_markers(self, lines, protein):
        """
        Look for protein between start and end
        """
        # Extract content between first START and last END
        pattern = r'\*\* START ' + re.escape(protein) + r' \*\*.*\*\* END ' + re.escape(protein) + r' \*\*'
        match = re.search(pattern, lines, re.DOTALL)
        if not match:
            return None
        between_markers = match.group()
        return between_markers
    
    def read_output_log(self,protein):
        """
        Read output log file from protein directory
        """
        workdir = self.job.resolve_workdir(site_config.data_path)
        with open(os.path.join(app_path,f"{workdir}/job.out"),"r") as f:
            lines = f.readlines()
            lines = self.nested_lists_to_string(lines)
            lines = self.fetch_between_markers(lines, protein)
        return lines
    
    def find_filtered_proteins(self, protein):
        """
        Finds all the proteins that interact with target
        """
        filtered_proteins = []

        lines = self.read_output_log(protein)
        # Loop through the words in the DataFrame

        for word in df['search_words']:
            if protein != word:
                word_match = re.search(r'\b' + re.escape(word) + r'\b', lines)
                if word_match:
                    filtered_proteins.append(word)
        return filtered_proteins

    def return_job_data(self):
        """
        Captures output and returns to job data
        """
        targets = self.job.tags['target']
        target_list = targets.split(",")
        for targ in target_list:
            filtered_proteins = self.find_filtered_proteins(targ)
            if filtered_proteins:
                interacting_proteins = list(set(filtered_proteins))
            else:
                interacting_proteins = "None Found"
                print("interacting_proteins not found",interacting_proteins,"for target",targ)
        self.job.state = "JOB_FINISHED"
        self.job.save()

    def handle_error(self):
        print("Starting Handle Error block")
        self.return_job_data()

    def handle_timeout(self):
	print("Starting Handle Timeout block")
        # Sorry, not retrying slow runs:
	self.return_job_data()

    def shell_preamble(self):
        return f'source /soft/datascience/conda-2023-01-31/miniconda3/bin/activate && conda activate /gila/Aurora_deployment/conda_env_llm/balsam_llama_env && source /gila/Aurora_deployment/70B-acc_fix_for_ppi/set_application_env.sh'

    command_template = "-env CCL_WORKER_AFFINITY {{CCL_GROUP}} -env MASTER_PORT {{MASTER_PORT}} --cpu-bind list:{{CPU_BIND_GROUP}} python3 -u /gila/Aurora_deployment/70B-acc_fix_for_ppi/intel-extension-for-transformers/examples/huggingface/pytorch/text-generation/inference/run_generation_with_deepspeed.py \
    -m /gila/Aurora_deployment/llama-2-hf/Llama-2-70b-chat-hf \
    --benchmark --num-iter 1 --num-warmup 1 --ipex --input-tokens=1024 --max-new-tokens=1024 --prompt {{prompt}} --protein-list {{protein_list}} && sleep 5"

LlamaBashApp.sync()

