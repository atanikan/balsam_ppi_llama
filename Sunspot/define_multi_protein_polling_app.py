from balsam.api import ApplicationDefinition, BatchJob, Job, Site
import os
import time
import pandas as pd
import re

site_name = "llama-science"

class MultiProteinBatchPollingApp(ApplicationDefinition):
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
    
    def handle_error(self):
        self.job.state = "RESTART_READY"
        self.job.save()

    def postprocess(self):
        
        parameters = self.job.get_parameters()

        stdout_file = "./job.out"
        found_protein = ""
        with open(stdout_file,"r") as f:
            while found_protein == "":
                line = f.readline()
                if "Found protein" in line:
                    line_list = line.split()
                    found_protein = line_list[-1]

        
        self.job.data = {"found_protein":found_protein}

        protein_list = parameters["protein_list"]
        new_protein_list = protein_list.copy()
        if found_protein in new_protein_list:
            new_protein_list.remove(found_protein)

        if len(new_protein_list) > 0:

            new_params = self.job.get_parameters()
            new_params["protein_list"] = new_protein_list
           
            new_tags = self.job.tags

            previous_workdir = str(self.job.workdir)
            previous_workdir_list = previous_workdir.split("/")
            workdir_iter = int(previous_workdir_list[-1])+1
            new_workdir = "/".join(previous_workdir_list[0:-1]+[str(workdir_iter)])

            new_job = Job.objects.create(app_id=self.job.app_id,
                          site_name=site_name,
                          workdir=new_workdir,
                          parameters = new_params,
                          tags=new_tags,
                            node_packing_count=self.job.node_packing_count,
                )
            new_job.save()
            print(f"Postprocess created next job id={new_job.id}\n")
        else:
            print(f"Postprocess did not create new polling job\n")
        self.job.state = "POSTPROCESSED"


    def run(self, directory, protein_list, timeout=60*60):
        """
            Monitors and extracts content between ** START {pattern} ** and ** END {pattern} ** from all files in a directory.
            Parameters:
                directory (str): The path of the directory to search for results.
                protein_list (list): The list of proteins to look for
                timeout (int, optional): Time in seconds to monitor the directory. Defaults to 60*60 seconds (1 hour).
            Returns:
                list: A list of strings, where each string is the content between ** START {pattern} ** and ** END {pattern} **.
                    Returns an empty list if the pattern is not found within the timeout.
        """
        
        
        end_time = time.time() + timeout
       
        results = []
        while time.time() < end_time and len(results) == 0:
            for protein in protein_list:
                # Walk through the directory
                for dirpath, dirnames, filenames in os.walk(directory):
                    for filename in filenames:
                        if filename == "job.out":
                            filepath = os.path.join(dirpath, filename)
                            with open(filepath, 'r',encoding='utf8', errors='ignore') as f:
                                lines = f.readlines()
                                #lines = self.fetch_between_markers(lines, protein)
                                lines = self.nested_lists_to_string(lines)
                                
                                pattern = r'\*\* START ' + re.escape(protein) + r' \*\*.*\*\* END ' + re.escape(protein) + r' \*\*'
                                match = re.search(pattern, lines, re.DOTALL)
                                #match = re.search(r'START.*END', lines, re.DOTALL)
                                if match:
                                    print(f"Found protein {protein}")
                                    print("Polling at", directory, protein, timeout)
                                    between_markers = match.group()
                                    print("between markers>>",between_markers)
                                    if len(between_markers)>0:
                                        print("returning results")
                                        results = between_markers
                                        return results.encode('utf-8')
        self.job.state = "RUN_ERROR"
        self.job.save()                                          
                 
        return results

MultiProteinBatchPollingApp.sync()

    

