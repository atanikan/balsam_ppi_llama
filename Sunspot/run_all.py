from define_app import LlamaBashApp
from define_jobs import JobDefine
from local_dot_construction import LocalDotConstruction
from balsam.api import Job, Site, BatchJob
import os
import pandas as pd
import multiprocessing
import time
from collections import OrderedDict

app_start_time = time.time()

llama_site_name = "sunspot-site"
app_path = os.getcwd()
proteins_file_path = os.path.join(app_path,"proteins.csv")
big_table_file_path = os.path.join(app_path,"big_table.csv")
string_file_path = os.path.join(app_path,"string.csv")
bt = pd.read_csv(big_table_file_path)
bt = bt.reset_index(drop=True)
st = pd.read_csv(string_file_path)
st = st.reset_index(drop=True)
check_unique_interaction = {}
df = pd.read_csv(proteins_file_path)
proteins_list = df['search_words'].tolist()
write_lock = multiprocessing.Lock()
llamabashapp = LlamaBashApp()
llamabashapp.sync()

define_jobs = JobDefine()
jobs = define_jobs.define_job()
llama_site = Site.objects.get(llama_site_name)
BatchJob.objects.create(
    site_id=llama_site.id,
    num_nodes=3,
    wall_time_min=120,
    job_mode="mpi",
    project="Aurora_deployment",
    queue="debug",
    filter_tags={"app_type":"llama"}
)     

llama_site = Site.objects.get(name=llama_site_name)
llama_jobs = Job.objects.filter(site_id=llama_site.id)
total_llama_job_num = llama_jobs.count()

queried_llama_job_ids_count = 0
while queried_llama_job_ids_count < total_llama_job_num:
    llama_jobs_finished = Job.objects.filter(site_id=llama_site.id, state=["JOB_FINISHED"], tags={"app_type":"llama"})
    queried_llama_job_ids_count = len(llama_jobs_finished)
    local_dot = LocalDotConstruction('/data','llama_predictions.dot')
    local_dot.run()

print(f"Total time for to finish processing {time.time() - app_start_time:.3f} secs")


