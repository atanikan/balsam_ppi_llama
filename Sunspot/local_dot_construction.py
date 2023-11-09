import csv
import os
import re
import multiprocessing
import pandas as pd
from balsam.api import BatchJob, Job, Site
from balsam.config import ClientSettings
from argparse import ArgumentParser
import time
import itertools
from collections import OrderedDict


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


class LocalDotConstruction:
    def __init__(self, output_file, output_path) -> None:
        self.output_file = output_file
        self.output_path = output_path

    # Function to extract numerical value from folder name for sorting
    def extract_number(self, folder_name):
        match = re.search(r'\d+', folder_name)
        return int(match.group()) if match else None
    
    def get_word_batches(self, df, batch_size=100):
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
            
            for start in range(0, total_rows, batch_size):
                end = min(start + batch_size, total_rows)
                ordered_set = OrderedDict.fromkeys(df.iloc[start:end]['search_words'])
                yield list(ordered_set.keys())
                # batch_set = set(batch)
                # yield batch_set
    
    def worker_main(self, queue, output_file, write_lock):
        while True:
            folder, proteins_to_find = queue.get()
            if folder is None:
                break  # Exit signal
            _, found_proteins = self.search_patterns_in_file(folder, proteins_to_find, output_file, write_lock)
            queue.put((folder, proteins_to_find - set(list(found_proteins.values()))))

    
    def run(self):
        folders = [os.path.join(self.output_path, d) for d in os.listdir(self.output_path) if os.path.isdir(os.path.join(self.output_path, d))]
        folders = sorted(folders, key=self.extract_number)
        #proteins_to_find = {folder: frozenset(list(get_word_batches(df,100))) for folder in folders}
        #proteins_to_find = {folder: set(itertools.chain(*get_word_batches(df,100))) for folder in folders}
        protein_batches = self.get_word_batches(df,100)
        proteins_to_find = {folder: next(protein_batches) for folder in folders}

        # Create a manager for shared state between processes
        manager = multiprocessing.Manager()
        queue = manager.Queue()

        # Start worker processes
        num_workers = multiprocessing.cpu_count()
        workers = []
        for _ in range(num_workers):
            p = multiprocessing.Process(target=self.worker_main, args=(queue, self.output_file, write_lock))
            p.start()
            workers.append(p)
            queue.put((None, None))  # Queue "poison pills" to signal process termination

        # Initial population of the queue
        for folder in folders:
            queue.put((folder, proteins_to_find[folder]))

        # Collect results
        remaining_proteins = set(proteins_list)
        while remaining_proteins:
            folder, _ = queue.get()
            for folder in folders:
                if proteins_to_find[folder]:  # If there are proteins left to find in this folder
                    queue.put((folder, proteins_to_find[folder]))
                else:
                    remaining_proteins = remaining_proteins.difference(proteins_to_find[folder])  # Update the set of remaining proteins
            time.sleep(5)  # Check every 5 seconds

        # Signal workers to exit
        for _ in workers:
            queue.put((None, None))

        # Wait for all workers to finish
        for p in workers:
            p.join()

        print("All proteins found.")


    def search_patterns_in_file(self, folder, proteins_to_find, output_file, write_lock):
        file_path = os.path.join(folder, 'job.out')
        # interactions = []
        # matched_words = set()
        try:
            with open(file_path, 'r') as file:
                content = file.read()
                for protein_to_find in proteins_to_find:
                    pattern = r"\*\* START " + protein_to_find + r" \*\*(.*?)\*\* END " + protein_to_find + r" \*\*"
                    matches = re.findall(pattern, content, re.DOTALL)
                    for match in matches:
                        for other_protein in proteins_list:
                            #if other_word in match and other_word != word:
                            if re.search(r'\b' + re.escape(other_protein) + r'\b', match) and other_protein != protein_to_find:
                                edge = f"{protein_to_find} -> {other_protein}"
                                if edge not in check_unique_interaction:
                                    interaction = self.validate_and_generate_dot(protein_to_find, other_protein)
                                    check_unique_interaction[edge] = protein_to_find
                                    with write_lock:
                                        with open(output_file, 'a') as out_f:
                                            out_f.write(interaction)
        except FileNotFoundError:
            pass  # File might not exist yet
        return folder, check_unique_interaction

    def validate_and_generate_dot(self, protein1, protein2):
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
        print("new>>>",new_content)
        return new_content

    
                


    # def main():
    #     # parser = ArgumentParser()
    #     # parser.add_argument('--output-path', default='/Users/adityatanikanti/Codes/ten-iteration-per-protein/vLLMBashAppOutputFullten/', type=str)
    #     # parser.add_argument('--dot-file', default='llama_predictions.dot', type=str)
    #     # args = parser.parse_args()
    #     # output_path = args.output_path
    #     # output_file = args.dot_file
        

# if __name__ == "__main__":
#     main()
   