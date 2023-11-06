from ast import List
from balsam.api import Job, Site, BatchJob
import os
import pandas as pd
import time

total_app_start = time.time()

site_name = "polaris-site"
app_path = os.getcwd()
proteins_file_path = os.path.join(app_path,"proteins.csv")

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

        for index, start in enumerate(range(0, total_rows, batch_size)):
            end = start + batch_size
            batch = df.iloc[start:end]['search_words'].tolist()            
            yield index, ','.join(batch)

    def define_job(self):
        df = pd.read_csv(proteins_file_path)
        #df = df.iloc[0:99] #change this to run all
        jobs = [Job(app_id="vLLMBashApp",
            site_name=site_name,
            workdir=f'vLLMBashAppOutput/{n}',
            parameters={"prompt": f"'{self.prompt}'", "protein_list":batch, "num_iter":10},
            num_nodes=1,
            ranks_per_node=1,
            gpus_per_rank=4,
            tags={"target":batch},
            node_packing_count = 1 
        )for n, batch in self.get_word_batches(df,100)]
        jobs = Job.objects.bulk_create(jobs)
        return jobs


jobdefine = JobDefine()
jobs = jobdefine.define_job()
site = Site.objects.get(site_name)
#CHANGE THESE TO YOUR PROJECT/QUEUE
BatchJob.objects.create(
    site_id=site.id,
    num_nodes=10,
    wall_time_min=180,
    job_mode="mpi",
    project="datascience",
    queue="prod",
)
    

