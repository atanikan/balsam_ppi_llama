from balsam.api import BatchJob, Job, Site
from balsam.config import ClientSettings
import os
import time
import pandas as pd
import re

# Test iteration number
test_iter = 0

# Site Names
polling_site_name = "llama-science"
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


def _make_polling_jobs_sequential(protein_list,directory="",nproc=1):
    polling_jobs = []
    
    parent_ids = []
    njobs = 0
    for protein in protein_list:
        job = Job(app_id="BatchPollingApp",
                site_name=polling_site_name,
                workdir=f'BatchPollingAppOutput/{protein}',
                parameters = {"directory":"/gila/Aurora_deployment/csimpson/balsam_ppi_llama/Sunspot/llama-science/data/LlamaBashAppOutput",
                            "protein":protein},
                tags={"target":protein,"app_type":"polling","test_iter":test_iter},
                parent_ids = parent_ids,
                node_packing_count=node_packing_count,
                threads_per_core=threads_per_core,
                )
        job.save()
        parent_ids = [job.id]
        polling_jobs.append(job)
        njobs += 1
        if njobs > nproc:
            njobs = 0
            parent_ids = []
        
    return polling_jobs

def _make_polling_jobs_bulk(protein_list,directory=""):
    polling_jobs = [Job(app_id="BatchPollingApp",
                site_name=polling_site_name,
                workdir=f'BatchPollingAppOutput/{protein}',
                parameters = {"directory":"/gila/Aurora_deployment/csimpson/balsam_ppi_llama/Sunspot/llama-science/data/LlamaBashAppOutput",
                            "protein":protein,"timeout":60},
                tags={"target":protein,"app_type":"polling","test_iter":test_iter},
                node_packing_count=node_packing_count,
                threads_per_core=threads_per_core,
                ) for protein in protein_list]
           
    polling_jobs = Job.objects.bulk_create(polling_jobs)
    return polling_jobs


def make_polling_jobs(protein_list,directory=""):
    nproc = n_polling_batch_jobs*node_packing_count
    if polling_type == "sequential":
        return _make_polling_jobs_sequential(protein_list,nproc=nproc)
    else:
        return _make_polling_jobs_bulk(protein_list)

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

polling_site = Site.objects.get(polling_site_name)
llama_site = Site.objects.get(name=llama_site_name)

llama_jobs = Job.objects.filter(site_id=llama_site.id)
total_llama_job_num = llama_jobs.count()

queried_llama_job_ids = []

client = ClientSettings.load_from_file().build_client()
llama_app_id = client.App.objects.filter(site_name=llama_site_name,name="LlamaBashApp")[0].id
jobs = []

while len(queried_llama_job_ids) < total_llama_job_num or len(jobs) > 0:

    new_polling_jobs = []

    llama_jobs_ready_for_polling = Job.objects.filter(site_id=llama_site.id, 
                                                state=["RUNNING","JOB_FINISHED","RESTART_READY"],
                                                #app_id=llama_app_id,
                                                tags={"app_type":"llama"})
    for j in llama_jobs_ready_for_polling:
        if j.id not in queried_llama_job_ids:
            print("Creating new polling job batch")
            protein_list = j.get_parameters()['protein_list'].split(",")
            new_polling_jobs = make_polling_jobs(j.get_parameters()['protein_list'].split(","))
            if len(queried_llama_job_ids) == 0 and not elastic:
                print("Starting Polling Process")
                for i in range(n_polling_batch_jobs):
                    BatchJob.objects.create(
                                        site_id=polling_site.id,
                                        num_nodes=1,
                                        filter_tags={"app_type":"polling","test_iter":test_iter},
                                        wall_time_min=walltime,
                                        job_mode="serial",
                                        queue=queue,
                                        project=project,
                                    )
            queried_llama_job_ids.append(j.id)
    jobs+=new_polling_jobs
    print("Waiting for new polling results")
    #for job in Job.objects.as_completed(jobs):
    
    for n,job in enumerate(jobs):
        if job.done():
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
            jobs.pop(n)
            break

    new_polling_jobs = []
print(f"Total time for a total of {count_prots} proteins to finish processing {time.time() - total_app_start:.3f} secs")
        

