from balsam.api import BatchJob, Job, Site
from balsam.config import ClientSettings
import os
import time
import pandas as pd
import re

# Test iteration number
test_iter = 2

# Site Names
polling_site_name = "llama-polling"
llama_site_name = "llama-science"

# If you are running your polling from the same site as the llama jobs,
# choose the queue and walltime; this will run one polling process per cpu core.
if polling_site_name == llama_site_name:
    node_packing_count = 104
    threads_per_core = 1
    n_polling_batch_jobs = 1
    queue = "debug"
    project = "Aurora_deployment"
    walltime = 60
# If you are running your polling from a local site on Sunspot, set how many
# processes you want polling by n_polling_batch_jobs.  
else:
    node_packing_count = 1
    threads_per_core = 1
    n_polling_batch_jobs = 4
    queue = "local"
    project = "local"
    walltime = 720


# Sequential will 
polling_type = "sequential"
elastic = False


total_app_start = time.time()

print("Starting polling")

app_path = os.getcwd()
proteins_file_path = os.path.join(app_path,"proteins.csv")
big_table_file_path = os.path.join(app_path,"big_table.csv")
string_file_path = os.path.join(app_path,"string.csv")
bt = pd.read_csv(big_table_file_path)
bt = bt.reset_index(drop=True)
st = pd.read_csv(string_file_path)
st = st.reset_index(drop=True)
df = pd.read_csv(proteins_file_path)

print("Read input files")

# The path to the dot file
dot_file_path = os.path.join(app_path,"llama_predictions.dot")
# Check if the file exists
if not os.path.exists(dot_file_path):
    # Create the file with the default content
    with open(dot_file_path, 'w') as file:
        file.write('digraph G {\n}')

print("Created dot file")

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
        #print("dot content:",new_content)
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
monitor_start_time = time.time()
monitor_interval = 30
count_prots = 0

polling_site = Site.objects.get(polling_site_name)
llama_site = Site.objects.get(name=llama_site_name)

llama_jobs = Job.objects.filter(site_id=llama_site.id)
total_llama_job_num = llama_jobs.count()

queried_llama_job_ids = []
jobs = []
finished_proteins = []

while len(queried_llama_job_ids) < total_llama_job_num or len(jobs) > 0:

    new_polling_jobs = []

    # Query for llama jobs that are running, partially run, or finished
    llama_jobs_ready_for_polling = Job.objects.filter(site_id=llama_site.id, 
                                                state=["RUNNING","JOB_FINISHED","RESTART_READY"],
                                                tags={"app_type":"llama"})
    
    # Loop over llama jobs and create a polling job for each that will look for finished proteins
    for j in llama_jobs_ready_for_polling:
        if j.id not in queried_llama_job_ids:
            print("Creating new polling job batch")
            protein_list = j.get_parameters()['protein_list'].split(",")
            
            directory = os.path.join(llama_site.path,
                                     "data",
                                     j.workdir)

            new_polling_job = Job(app_id="MultiProteinBatchPollingApp",
                          site_name=polling_site_name,
                          workdir=f"MultiBatchPollingAppOutput/{j.id}/0",
                          parameters = {"protein_list":protein_list,
                                        "directory":directory},
                          tags={"app_type":"multi_polling","test_iter":test_iter,"target_batch":j.id},
                            node_packing_count=node_packing_count,
                )
            new_polling_job.save()
            
            new_polling_jobs.append(new_polling_job)

            # Create a batch job to run polling if this is the first iteration and elastic queueing is not enabled
            if len(queried_llama_job_ids) == 0 and not elastic:
                print("Starting Polling Process")
                for i in range(n_polling_batch_jobs):
                    BatchJob.objects.create(
                                        site_id=polling_site.id,
                                        num_nodes=1,
                                        filter_tags={"app_type":"multi_polling","test_iter":test_iter},
                                        wall_time_min=walltime,
                                        job_mode="serial",
                                        queue=queue,
                                        project=project,
                                    )
            queried_llama_job_ids.append(j.id)
    jobs+=new_polling_jobs


    # Add polling jobs auto created by postprocessing hook of previous polling jobs
    for llama_id in queried_llama_job_ids:
        auto_polling_jobs = Job.objects.filter(site_id=polling_site.id, 
                                                state=["PREPROCESSED","RUNNING","JOB_FINISHED","RESTART_READY"],
                                                tags={"app_type":"multi_polling","target_batch":llama_id})

        job_ids = [j.id for j in jobs]
        for aj in auto_polling_jobs:
            # Only include jobs that have not yet found a protein and isn't already being monitored
            if "found_protein" not in aj.data.keys():
                jobs.append(aj)
            elif aj.id not in job_ids:
                if aj.data["found_protein"] not in finished_proteins:
                    jobs.append(aj)

    print(f"Tracking {len(jobs)} polling jobs")
    time.sleep(monitor_interval)
    #for job in Job.objects.as_completed(jobs):
    
    # Loop over polling jobs
    for n,job in enumerate(jobs):
        if job.done() and "found_protein" in job.data.keys():
            protein = job.data['found_protein']
            try:
                output = job.result()
                output = output.decode('utf-8')
            except Exception as e:
                print(f"Results could not be pulled for job {job.id} for protein {protein}")
                print(f"Exception: {e}")
                continue
           
            finished_proteins.append(protein) # add protein to list of finished proteins
            
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
            jobs.pop(n) # Remove polling job from list of jobs to monitor
            break

    new_polling_jobs = []
print(f"Finished {len(finished_proteins)} proteins")
print(f"Total time for a total of {count_prots} proteins to finish processing {time.time() - total_app_start:.3f} secs")
        

