from balsam.api import Job, Site, BatchJob
import os
import re
import time
import multiprocessing
from multiprocessing import Manager, Lock
import pandas as pd
import shutil

total_app_start = time.time()

llama_site_name = "Llamademo"
llama_site = Site.objects.get(llama_site_name)
queried_llama_job_ids = []
proteins_to_find = {}
app_path = os.getcwd()
proteins_file_path = os.path.join(app_path,"proteins.csv")
big_table_file_path = os.path.join(app_path,"big_table.csv")
string_file_path = os.path.join(app_path,"string.csv")
df = pd.read_csv(proteins_file_path)
bt = pd.read_csv(big_table_file_path)
bt = bt.reset_index(drop=True)
st = pd.read_csv(string_file_path)
st = st.reset_index(drop=True)
known_proteins = df['search_words'].tolist()


output_path = '/home/alien/Documents/code/mount_remote_system/data' #change
dot_file = '/home/alien/Documents/code/protein-graph-visualization-main/src/visg/static/data/interactions_full_run.dot' #change
#proteins_to_find = {folder: next(protein_batches) for folder in folders}
#output_path = '/Users/adityatanikanti/Codes/ten-iteration-per-protein/vLLMBashAppOutputFullten'
#dot_file = 'interactions_full_run.dot'

def proteins_to_process():
    llama_jobs_ready_for_polling = Job.objects.filter(site_id=llama_site.id, 
                                                    state=["CREATED","STAGED_IN","PREPROCESSED","RUNNING","JOB_FINISHED","RESTART_READY"])
    for j in llama_jobs_ready_for_polling:
            if j.id not in queried_llama_job_ids:
                print("Creating new polling job batch")
                protein_list = j.get_parameters()['protein_list'].split(",")
                directory = os.path.join(llama_site.path,
                                        "data",
                                        j.workdir)
                new_dir = os.path.join(output_path,directory.split("/")[-1])
                proteins_to_find[new_dir] = protein_list
    return proteins_to_find

def move_current_dot_to_backup():
    directory_for_previous_iterations = os.path.dirname(dot_file)
    # List all files in the backup directory
    files_in_backup_dir = [f for f in os.listdir(directory_for_previous_iterations) if os.path.isfile(os.path.join(directory_for_previous_iterations, f))]
    number_to_append = len(files_in_backup_dir) + 1
    file_to_move = dot_file
    new_file_name = f"{file_to_move.split('.')[0]}_{number_to_append}.{file_to_move.split('.')[-1]}"
    shutil.move(file_to_move, os.path.join(directory_for_previous_iterations, new_file_name)) 
    with open(dot_file, 'w') as out_f:
        out_f.write('digraph G {\n}')

def validate_and_generate_dot(protein1, protein2):
    edge = f"{protein1} -> {protein2}"
    if protein2 == None:
        return edge + ';\n'
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
    if (lpkg == -1 and stri == -1):
        new_content = edge + ' [color=red, penwidth=5.0];\n'
    elif (lpkg >= 1 and stri == 0):
        new_content = edge + ' [color=orange, penwidth=5.0];\n'
    elif (lpkg == -1 and stri > 0):
        new_content = edge + ' [color=blue, penwidth=2.0];\n'
    elif (lpkg > 500 and stri > 500):
        new_content = edge + ' [color=green, penwidth=2.0];\n'
    else:
        new_content = edge + ';\n'
        #print(new_content) # not found in either
    # master_dot[edge] = new_content
    # #return master_dot[edge]
    # return (interaction, master_dot[edge]) 
    print("Adding to dot file:",new_content)
    return new_content

def find_interactions(directory, proteins, known_proteins, interactions_dict):
    print(f"Checking directory: {directory}")  # Debugging print
    job_file = os.path.join(directory, 'job.out')
    proteins_to_find = set(proteins)  # Set of proteins to find interactions for.
    while proteins_to_find:
        if os.path.exists(job_file):
            with open(job_file, 'r') as file:
                content = file.read()
                proteins_found = set()  # Keep track of proteins found in this iteration.
                for protein in proteins_to_find:
                    print("Looking for protein:",protein)
                    pattern = r"\*\* START " + protein + r" \*\*(.*?)\*\* END " + protein + r" \*\*"
                    matches = re.findall(pattern, content, re.DOTALL)
                    if matches:
                        match_found = False
                        for match in matches:
                            for known_protein in known_proteins:
                                if re.search(r'\b' + re.escape(known_protein) + r'\b', match) and known_protein != protein:
                                    #edge = f"{protein_to_find} -> {other_protein}"
                                    match_found = True
                                    interaction = f"{protein} -> {known_protein}"
                                    interaction = validate_and_generate_dot(protein, known_protein)
                                    if interaction not in interactions_dict:
                                        interactions_dict[interaction] = True
                                        with open(dot_file, 'r') as file:
                                            content = file.read()
                                        # Check if the content is not empty and the last character is indeed a "}"
                                        if content and content[-1] == '}':
                                            # Remove the last character
                                            content = content[:-1]
                                            # Add the "interaction object" and the closing "}"
                                            content += f"{interaction}"
                                            content += "}"
                                            # Write the modified content back to the file
                                            with open(dot_file, 'w') as file:
                                                file.write(content)
                        if not match_found:
                            interaction = f"{protein} -> None;\n"
                            if interaction not in interactions_dict:
                                interactions_dict[interaction] = True
                                with open(dot_file, 'r') as file:
                                    content = file.read()
                                    # Check if the content is not empty and the last character is indeed a "}"
                                    if content and content[-1] == '}':
                                        # Remove the last character
                                        content = content[:-1]
                                        # Add the "interaction object" and the closing "}"
                                        content += f"{interaction}"
                                        content += "}"
                                        # Write the modified content back to the file
                                        with open(dot_file, 'w') as file:
                                            file.write(content)
                        proteins_found.add(protein)
                proteins_to_find -= proteins_found  # Remove found proteins from the search set.

        time.sleep(5)  # Wait for some time before checking again to reduce resource usage.

def main():
    # directories_with_proteins and known_proteins should be defined as before

    manager = Manager()
    interactions_dict = manager.dict() 
    lock = Lock()

    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    proteins_to_find = proteins_to_process()
    move_current_dot_to_backup()
    for directory, proteins in proteins_to_find.items():
        print(directory,">",proteins)
        result=pool.apply_async(find_interactions, args=([directory, proteins, known_proteins, interactions_dict]))
        result.get()
    pool.close()
    pool.join()
    print(f"Total time to finish processing {time.time() - total_app_start:.3f} secs")

if __name__ == "__main__":
    main()


