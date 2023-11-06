from balsam.api import ApplicationDefinition, Site, site_config
import os
import re
site_name = "polaris-site"
app_path = os.getcwd()
proteins_file_path = os.path.join(app_path,"proteins.csv")
import pandas as pd
df = pd.read_csv(proteins_file_path, names=['search_words'])

class vLLMBashApp(ApplicationDefinition):
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
        #match = re.search(r'START.*END', lines, re.DOTALL)
        if not match:
            return None
        between_markers = match.group()
        # Search for the desired word in the extracted content
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
    
    def shell_preamble(self):
        return f'module load conda && conda activate balsam-vllm-polaris-conda-env'

    command_template = "python3 /grand/datascience/vllm_batch.py --protein-list {{protein_list}} --prompt {{prompt}} --num-iter {{num_iter}}"

vLLMBashApp.sync()
