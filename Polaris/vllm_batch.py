from vllm import LLM, SamplingParams
import ray
from argparse import ArgumentParser
import time

def main():
    total_start_time = time.time()
    parser = ArgumentParser()
    parser.add_argument('--protein-list', default='RAD51', type=str)
    parser.add_argument('--num-iter', default=10, type=int)
    parser.add_argument('--prompt', default='You are a helpful assistant. We are interested in protein interactions.  Based on the documents you have been trained with, can you provide any information on which proteins might interact with', type=str)
    args = parser.parse_args()
    ray.init(_temp_dir='/tmp')
    list_prompts = []
    if args.protein_list:
        protein_list = args.protein_list
        protein_list = protein_list.split(",")
        for protein in protein_list:
            protein = protein.strip()
            prompt = args.prompt + " " + protein
            list_prompts.append(prompt)
    print("List of prompts>>", list_prompts)
    model_start_time = time.time()
    sampling_params = SamplingParams(max_tokens=1024)
    llm = LLM(model="meta-llama/Llama-2-70b-chat-hf",tokenizer='hf-internal-testing/llama-tokenizer',tensor_parallel_size=4,download_dir='/grand/datascience/atanikanti/vllm_service/',seed=123321213)
    print("Time for model initialisation: Time: %.6f sec" % (time.time() - model_start_time))
    print("Starting to generate")
    return_out = []
    for i in range(args.num_iter):
        iteration_start_time = time.time()
        outputs = llm.generate(list_prompts, sampling_params)
        # Print the outputs.
        for output in outputs:
            prompt = output.prompt
            generated_text = output.outputs[0].text
            protein = output.prompt.split()[-1]
            print(f"** START {protein} **")
            print(f"Prompt: {prompt!r}") 
            print(f"Generated text: {generated_text!r}")
            print(f"** END {protein} **")
            return_out.append(generated_text)
        print("Iteration: %d, Time: %.6f sec" % (i, time.time() - iteration_start_time))
        # get the end time
    # get the execution time
    print("Time for full app Time: %.6f sec" % (time.time() - total_start_time))

    return return_out

if __name__=="__main__":
    main()
