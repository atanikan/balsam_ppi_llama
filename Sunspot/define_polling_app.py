from balsam.api import ApplicationDefinition, BatchJob, Job, Site
import os
import time
import pandas as pd
import re

site_name = "BatchPollingApp"
total_app_start = time.time()

app_path = os.getcwd()
proteins_file_path = os.path.join(app_path,"proteins.csv")
big_table_file_path = os.path.join(app_path,"big_table.csv")
string_file_path = os.path.join(app_path,"string.csv")
bt = pd.read_csv(big_table_file_path)
bt = bt.reset_index(drop=True)
st = pd.read_csv(string_file_path)
st = st.reset_index(drop=True)


# The path to the dot file
dot_file_path = os.path.join(app_path,"llama_predictions.dot")
# Check if the file exists
if not os.path.exists(dot_file_path):
    # Create the file with the default content
    with open(dot_file_path, 'w') as file:
        file.write('digraph G {\n}')


class BatchPollingApp(ApplicationDefinition):
    site = "BatchPollingApp"
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
df = pd.read_csv(proteins_file_path)
jobs = [
    BatchPollingApp.submit(
        workdir=f'BatchPollingAppOutput/{protein}',
        directory="/gila/Aurora_deployment/atanikanti/LLM_service/balsam_service_ppi_llm_70B/balsam-llama-sunspot-site/data/LlamaBashAppOutput", #CHANGE THIS
        protein = protein,
        timeout=60,
        tags={"target":protein},
    )
    for n,protein in enumerate(df['search_words'].loc[0:999])
]



site = Site.objects.get(site_name)
BatchJob.objects.create(
    site_id=site.id,
    num_nodes=1,
    wall_time_min=720,
    job_mode="serial",
    queue="local",
    project="local",
)



def validate_and_generate_dot(protein1, protein2, edge):
    # Now, open the file and read its contents
    content = None
    with open(dot_file_path, 'r') as file:
        content = file.read()   
    stri = -1
    lpkg = -1
    matches = bt[bt['col1'] == protein1 ]
    hit = matches[matches['col2'] == protein2]
    if not hit.empty:
        lpkg = hit['score'].astype(int).iloc[0]
    else:
        lpkg = -1
    st_matches = st[st['col1'] == protein1 ]
    tt_matches = st[st['col1'] == protein2 ]
    st_hit = st_matches[st_matches['col2'] == protein2]
    target = 0

    if not tt_matches.empty:
            target = target + 1

    stri = 0
            
    if( target == 0):
        #print("\t",protein2, "NOT FOUND in STRING")
        stri = -1
    elif (not st_hit.empty):
        #print("\t",protein1, "FOUND in STRING ---->",protein2,"with score", st_hit['score'].to_string(index=False))
        stri = st_hit['score'].astype(int).iloc[0]
    else:
        stri = 0

    #    print("\t",protein1,"->", protein2," lpkg:",lpkg, " str:",stri)
    if edge not in content:
        if (lpkg == -1 and stri == -1):
            new_content = content.replace('}', edge + ' [color=red, penwidth=5.0];\n}')
            print(protein1,"->", protein2,"[color=red, penwidth=5.0];") # not found in either
        elif (lpkg >= 1 and stri == 0):
            new_content = content.replace('}', edge + ' [color=orange, penwidth=5.0];\n}')
            print(protein1,"->", protein2,"[color=orange, penwidth=5.0];") #found in LPKG
        elif (lpkg == -1 and stri > 0):
            new_content = content.replace('}', edge + ' [color=blue, penwidth=2.0];\n}')
            print(protein1,"->", protein2,"[color=blue, penwidth=2.0];") #found in STRING
        elif (lpkg > 500 and stri > 500):
            new_content = content.replace('}', edge + ' [color=green, penwidth=2.0];\n}')
            print(protein1,"->", protein2,"[color=green, penwidth=2.0];") #strong support in both
        else:
            new_content = content.replace('}', edge + ';\n}')
            print(protein1,"->", protein2,";") #support in both
        print("dot content:",new_content)
        with open(dot_file_path, 'w') as file:
            file.write(new_content)

def find_filtered_proteins(protein,output):
    """
    Finds all the proteins that interact with target
    """
    filtered_proteins = []

    # Loop through the words in the DataFrame
    if output:
        for word in df['search_words']:
            if protein != word:
                word_match = re.search(r'\b' + re.escape(word) + r'\b', output)
                if word_match:
                    filtered_proteins.append(word)
    return filtered_proteins

job_start_time = time.time()
count_prots = 0
for job in Job.objects.as_completed(jobs):
    protein = job.tags['target']
    output = job.result()
    output = output.decode('utf-8')
    filtered_proteins = find_filtered_proteins(protein,output)
    with open("interactions.txt", "a") as f:
        if filtered_proteins:
            for prot in filtered_proteins:
                edge = f"{protein} -> {prot}"
                validate_and_generate_dot(protein,prot,edge)
                data = f"{edge}\n"
                f.write(data)
                f.flush()  # Force writing the data to the file immediately 
        else:
              edge = f"{protein} -> {None}" 
              validate_and_generate_dot(protein,"None",edge)
              data = f"{edge}\n"
              f.write(data)
              f.flush()  # Force writing the data to the file immediately
    print(f"Total time for {protein} to finish processing {time.time() - job_start_time:.3f} secs")
    job_start_time = time.time()
    count_prots = count_prots + 1
print(f"Total time for a total of {count_prots} proteins to finish processing {time.time() - total_app_start:.3f} secs")
    

