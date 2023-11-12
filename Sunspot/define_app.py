from balsam.api import ApplicationDefinition, Site
import os
import re

site_name = "LlamaDemo"

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
        pattern = r"\*\* START " + protein + r" \*\*(.*?)\*\* END " + protein + r" \*\*"
        matches = re.findall(pattern, lines, re.DOTALL)
        if matches:
            return protein
        return None

    
    def read_output_log(self,protein):
        """
        Read output log file from protein directory
        """
        with open('./job.out',"r") as f:
            lines = f.readlines()
            lines = self.nested_lists_to_string(lines)
            found_protein = self.fetch_between_markers(lines, protein)
        return found_protein
            

    def return_job_data(self):
        """
        Captures output and returns to job data
        """
        #targets = self.job.tags['target']
        protein_list = self.job.get_parameters()['protein_list'].split(",")
        if protein_list:
            found_proteins_list = []
            for prot in protein_list:
                found_protein = self.read_output_log(prot)
                if found_protein:
                    found_proteins_list.append(found_protein)
            if len(found_proteins_list) == len(protein_list):
                self.job.state = "JOB_FINISHED"
                self.job.save()
        self.job.state = "RESTART_READY"
        self.job.save()

    def handle_error(self):
        print("Starting Handle Error block")
        self.return_job_data()

    def handle_timeout(self):
        print("Starting Handle Timeout block")
        self.return_job_data()

    def shell_preamble(self):
        return f'source /soft/datascience/conda-2023-01-31/miniconda3/bin/activate && conda activate /gila/Aurora_deployment/conda_env_llm/balsam_llama_env && source /gila/Aurora_deployment/70B-acc_fix_for_ppi/set_application_env.sh'

    command_template = "-env CCL_WORKER_AFFINITY {{CCL_GROUP}} -env MASTER_PORT {{MASTER_PORT}} --cpu-bind list:{{CPU_BIND_GROUP}} python3 -u /gila/Aurora_deployment/70B-acc_fix_for_ppi/intel-extension-for-transformers/examples/huggingface/pytorch/text-generation/inference/run_generation_with_deepspeed.py \
    -m /gila/Aurora_deployment/llama-2-hf/Llama-2-70b-chat-hf \
    --benchmark --num-iter 1 --num-warmup 1 --ipex --input-tokens=1024 --max-new-tokens=1024 --prompt {{prompt}} --protein-list {{protein_list}} && sleep 5"

LlamaBashApp.sync()

