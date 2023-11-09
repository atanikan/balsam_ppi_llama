from ast import List
from balsam.api import Job, Site, BatchJob
import os
import pandas as pd
import time

total_app_start = time.time()

site_name = "sunspot-site"
app_path = os.getcwd()
proteins_file_path = os.path.join(app_path,"proteins.csv")

# Split the values into groups
CCL_WORKER_GROUPS = [
    [1, 9, 17, 25],
    [33, 41, 53, 61],
    [69, 77, 85, 93]
]

CPU_BIND_GROUPS = [
    ["2-4", "106-108:10-12", "114-116:18-20", "122-124:26-28", "130-132"],
    ["34-36", "138-140:42-44", "146-148:54-56", "158-160:62-64", "166-168"],
    ["70-72", "174-176:78-80", "182-184:86-88", "190-192:94-96", "198-200"]
]


class JobDefine():
    def __init__(self) -> None:
        self.prompt = f"You are playing the role of a helpful assistant. We are interested in protein interactions.  Based on the documents you have been trained with, can you provide any information on which proteins might interact with"
    

    def get_word_batches(self, df, batch_size=5):
        """
        Yield batches of words from the dataframe as comma-separated strings along with cyclic permutations of CCL_WORKER_AFFINITY and cpu-bind values.

        Parameters:
        - df: DataFrame containing the words.
        - column_name: Name of the column containing the words.
        - batch_size: Size of each batch (default: 5).

        Returns:
        - Iterator yielding the batch index, comma-separated word batches, CCL_WORKER_AFFINITY, and cpu-bind values.
        """
        total_rows = df.shape[0]
        group_len = len(CCL_WORKER_GROUPS)
        
        for index, start in enumerate(range(0, total_rows, batch_size)):
            end = start + batch_size
            batch = df.iloc[start:end]['search_words'].tolist()
            
            ccl_group = CCL_WORKER_GROUPS[index % group_len]
            cpu_bind_group = CPU_BIND_GROUPS[index % group_len]
            
            yield index, ','.join(batch), ccl_group, cpu_bind_group

    def define_job(self):
        df = pd.read_csv(proteins_file_path)
        # df.drop(0, inplace=True)
        df = df.loc[0:299] #change this to run all
        jobs = [Job(app_id="LlamaBashApp",
            site_name=site_name,
            workdir=f'LlamaBashAppOutput/{n}',
            parameters={"prompt": f"'{self.prompt}'", "MASTER_PORT": 29600+n, "protein_list":batch, "CCL_GROUP":','.join(map(str, ccl)), "CPU_BIND_GROUP":','.join(cpu_bind)},
            num_nodes=1,
            ranks_per_node=4,
            gpus_per_rank=1,
            tags={"target":batch},
            node_packing_count = 1 #change this to set number of jobs in parallel on same node; set to 3 once fixed
        )for n, batch, ccl, cpu_bind in self.get_word_batches(df,100)] #Runs in batches of 100 proteins
        #for n,word in enumerate(df['search_words'])]
        jobs = Job.objects.bulk_create(jobs)
        return jobs

jobdefine = JobDefine()
jobs = jobdefine.define_job()
site = Site.objects.get(site_name)
BatchJob.objects.create(
    site_id=site.id,
    num_nodes=3,
    wall_time_min=120,
    job_mode="mpi",
    project="Aurora_deployment",
    queue="workq"
)