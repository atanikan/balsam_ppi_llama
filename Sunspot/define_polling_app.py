from balsam.api import ApplicationDefinition, BatchJob, Job, Site
import os
import time
import pandas as pd
import re

site_name = "llama-polling"

class BatchPollingApp(ApplicationDefinition):
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

    def run(self, directory, protein, timeout=20*60):
        """
            Monitors and extracts content between ** START {pattern} ** and ** END {pattern} ** from all files in a directory.
            Parameters:
                directory (str): The path of the directory to monitor and search in.
                pattern (str): The pattern to search between.
                timeout (int, optional): Time in seconds to monitor the directory. Defaults to 15*60 seconds (15 minutes).
            Returns:
                list: A list of strings, where each string is the content between ** START {pattern} ** and ** END {pattern} **.
                    Returns an empty list if the pattern is not found within the timeout.
        """
        print("Polling at", directory, protein, timeout)
        end_time = time.time() + timeout
        #result = {'interacting_proteins':None,
        # #           'output_logs':None}
        results = []
        # while time.time() < end_time:
        #     # Walk through the directory
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                with open(filepath, 'r',encoding='utf8', errors='ignore') as f:
                    lines = f.readlines()
                    #lines = self.fetch_between_markers(lines, protein)
                    lines = self.nested_lists_to_string(lines)
                    pattern = r'\*\* START ' + re.escape(protein) + r' \*\*.*\*\* END ' + re.escape(protein) + r' \*\*'
                    match = re.search(pattern, lines, re.DOTALL)
                    #match = re.search(r'START.*END', lines, re.DOTALL)
                    if match:
                        between_markers = match.group()
                        print("between markers>>",between_markers)
                        if len(between_markers)>0:
                            results = between_markers
                            #results = unicode(results, errors='ignore')
                            return results.encode('utf-8')
        self.job.state = "RUN_ERROR"
        self.job.save()                                          
                #results.append(filepath)
        return results

BatchPollingApp.sync()

    

