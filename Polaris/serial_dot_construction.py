import os
import pandas as pd
import re
app_path = os.getcwd()
proteins_file_path = os.path.join(app_path,"proteins.csv")
big_table_file_path = os.path.join(app_path,"big_table.csv")
string_file_path = os.path.join(app_path,"string.csv")
bt = pd.read_csv(big_table_file_path)
bt = bt.reset_index(drop=True)
st = pd.read_csv(string_file_path)
st = st.reset_index(drop=True)
df = pd.read_csv(proteins_file_path)
master_dot = {}
# The path to the dot file
dot_file_path = os.path.join(app_path,"llama_predictions_polaris.dot")
output_path = os.path.join(app_path,"/data/vLLMBashAppOutput")
def flatten(lst):
    """
    Recursively flatten a nested list.
    """
    flat_list = []
    for item in lst:
        if isinstance(item, list):
            flat_list.extend(flatten(item))
        else:
            flat_list.append(item)
    return flat_list

def nested_lists_to_string(nested_list):
    """
    Convert a nested list into a single string with spaces between items.
    """
    flat_list = flatten(nested_list)
    return ' '.join(map(str, flat_list))

def validate_and_generate_dot(protein1, protein2, edge):
    if edge not in master_dot:
        if protein2 == None:
            new_content = edge + ';\n'
            master_dot[edge] = new_content
            return
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
        print(new_content) # not found in either
        master_dot[edge] = new_content
        # with open(dot_file_path, 'w') as file:
        #     file.write(new_content)

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

def construct_dot(directory):
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            if "job.out" in filename:
                filepath = os.path.join(dirpath, filename)
                with open(filepath, 'r',encoding='utf8', errors='ignore') as f:
                    lines = f.readlines()
                    #lines = self.fetch_between_markers(lines, protein)
                    lines = nested_lists_to_string(lines)
                    for n,protein in enumerate(df['search_words']): 
                        pattern = r'\*\* START ' + re.escape(protein) + r' \*\*.*\*\* END ' + re.escape(protein) + r' \*\*'
                        match = re.search(pattern, lines, re.DOTALL)
                        #match = re.search(r'START.*END', lines, re.DOTALL)
                        if match:
                            between_markers = match.group()
                            if len(between_markers)>0:
                                filtered_proteins = find_filtered_proteins(protein,between_markers)
                                if filtered_proteins:
                                    for prot in filtered_proteins:
                                        edge = f"{protein} -> {prot}"
                                        validate_and_generate_dot(protein,prot,edge)
                                else:
                                    edge = f"{protein} -> NONE" 
                                    validate_and_generate_dot(protein,None,edge)

construct_dot(output_path)
# Check if the file exists
with open(dot_file_path, 'w') as file:
    dot_vals = 'digraph G {'
    for value in master_dot.values():
        dot_vals = dot_vals + value
    dot_vals = dot_vals + '}'
    file.write(dot_vals)

