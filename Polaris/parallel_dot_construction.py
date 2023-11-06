import csv
import os
import re
import multiprocessing
import pandas as pd

# Assuming the datasets 'bt' and 'st' used in the validate_and_generate_dot method 
# are read from CSVs or any other sources.
# bt = pd.read_csv('big_table.csv')
# st = pd.read_csv('string.csv')


app_path = os.getcwd()
proteins_file_path = os.path.join(app_path,"proteins.csv")
big_table_file_path = os.path.join(app_path,"big_table.csv")
string_file_path = os.path.join(app_path,"string.csv")
bt = pd.read_csv(big_table_file_path)
bt = bt.reset_index(drop=True)
st = pd.read_csv(string_file_path)
st = st.reset_index(drop=True)
master_dot = {}

with open('proteins.csv', 'r') as f:
    reader = csv.reader(f)
    words = set(row[0] for row in reader)

# parent_directory = "/grand/datascience/atanikanti/vllm_service/vllm-balsam/vllm_site/data/vLLMBashAppOutput"
output_path = os.path.join(app_path,"/data/vLLMBashAppOutput")
folders = [os.path.join(output_path, d) for d in os.listdir(output_path) if os.path.isdir(os.path.join(output_path, d))]

dot_file_path = os.path.join(app_path,"llama_predictions_polaris_parallel.dot")


def search_patterns_in_file(filepath, words):
    interactions = []
    matched_words = set()
    with open(filepath, 'r') as file:
        content = file.read()
        for word in words:
            pattern = r"\*\* START " + word + r" \*\*(.*?)\*\* END " + word + r" \*\*"
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                matched_words.add(word)  
                for other_word in words:
                    #if other_word in match and other_word != word:
                    if re.search(r'\b' + re.escape(other_word) + r'\b', match) and other_word != word:
                        interactions.append((word, other_word))
    return interactions, matched_words




def validate_and_generate_dot(interaction):
    protein1, protein2 = interaction
    edge = f"{protein1} -> {protein2}"
    # ... [rest of your validation method without the return part]
    if edge not in master_dot:
        if protein2 == None:
            return (interaction, edge + ';\n')
            #new_content = edge + ';'
            #master_dot[edge] = new_content
            #return new_content
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
    master_dot[edge] = new_content
    #return master_dot[edge]
    return (interaction, master_dot[edge]) 

def parallel_validate(interactions):
    pool = multiprocessing.Pool()
    results = pool.map(validate_and_generate_dot, interactions)
    pool.close()
    pool.join()
    return results



#parent_directory = "/grand/datascience/atanikanti/vllm_service/vllm-balsam/vllm_site/data/vLLMBashAppOutputFullten/0"
pool = multiprocessing.Pool()
results = []
for folder in folders:
    filepath = os.path.join(folder, 'job.out')
    if os.path.exists(filepath):
        results.append(pool.apply_async(search_patterns_in_file, args=(filepath, words)))

all_interactions = set()
all_matched_words = set()

for result in results:
    interactions, matched_words = result.get()
    all_interactions.update(interactions)
    all_matched_words.update(matched_words)

# Add words without interactions
for word in (words - all_matched_words):
    all_interactions.add((word, None))

# Sort interactions
sorted_interactions = sorted(all_interactions, key=lambda x: (x[0], x[1] if x[1] else ""))
print(sorted_interactions)

validated_interactions = parallel_validate(sorted_interactions)


with open(dot_file_path, 'w') as file:
    file.write('digraph G {\n')
    for index, (_, content) in enumerate(validated_interactions):
        sorted_validated_interactions = sorted(validated_interactions[:index], key=lambda x: (x[0][0], x[0][1] if x[0][1] else ""))
        for _, sorted_content in sorted_validated_interactions:
            file.write(sorted_content)
        validated_interactions = validated_interactions[index:]
    file.write('}\n')
