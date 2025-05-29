# Protein-Protein Interaction Batch Prompt Generator

This directory contains scripts for generating batch API prompts to query Large Language Models about protein-protein interactions and parsing the results to create protein interaction networks.

## File Organization

### Main Pipeline Files
- `generate_batch_prompts.py` - Generate batch prompts for vLLM
- `parse_llm_output.py` - Parse LLM responses (optimized)
- `parse_llm_output_parallel.py` - Parse LLM responses (parallel processing)
- `requirements.txt` - Python dependencies
- `README.md` - This documentation

### Test Directory (`test/`)
- `generate_fake_outputs.py` - Generate fake LLM responses for testing
- `demo.sh` - Complete pipeline demonstration
- `README.md` - Test-specific documentation
- Test data files (`.jsonl`, `.dot`)

## Workflow Overview

1. **Generate batch prompts** using `generate_batch_prompts.py`
2. **Submit to vLLM batch API** for processing
3. **Parse results** using `parse_llm_output.py` to create DOT network files

## Quick Start

### Generate Prompts
```bash
python Sophia/generate_batch_prompts.py --max-proteins 100 --iterations 3
```

### Parse Results (after getting LLM responses)
```bash
python Sophia/parse_llm_output.py --batch-output your_responses.jsonl --verbose
```

### Run Demo/Test
```bash
bash Sophia/test/demo.sh
```

## Scripts

### 1. `generate_batch_prompts.py` - Prompt Generator

Reads protein names from a CSV file and generates JSONL format prompts suitable for vLLM batch API processing.

#### Features

- Reads protein names from `data/proteins.csv`
- Generates multiple iterations per protein to reduce hallucination
- Outputs JSONL format compatible with vLLM batch API
- Focused prompts designed for easy parsing
- Optimized for generating protein names that exist in your dataset

#### Arguments

- `--input-file`: Path to proteins CSV file (default: `data/proteins.csv`)
- `--output-file`: Output JSONL file path (default: `protein_interaction_batch_prompts.jsonl`)
- `--iterations`: Number of iterations per protein (default: 3)
- `--max-proteins`: Limit number of proteins to process (for testing)
- `--model`: Model name for batch requests (default: `meta-llama/Meta-Llama-3.1-8B-Instruct`)
- `--max-tokens`: Maximum tokens per response (default: 1000)

### 2. `parse_llm_output.py` - Output Parser

Parses the LLM batch output, extracts protein interactions, validates them against your protein dataset, and generates a DOT file using the same color scheme as `parallel_dot_construction.py`.

#### Features

- Parses vLLM batch API output JSONL files
- Extracts protein names that match your `proteins.csv` dataset
- Validates interactions against `big_table.csv` and `string.csv`
- Optimized with O(1) database lookups and efficient I/O
- Generates DOT files with color-coded confidence levels

#### Arguments

- `--batch-output`: Path to vLLM batch output JSONL file (required)
- `--proteins-csv`: Path to proteins.csv file (default: `data/proteins.csv`)
- `--big-table-csv`: Path to big_table.csv file (default: `data/big_table.csv`)
- `--string-csv`: Path to string.csv file (default: `data/string.csv`)
- `--output-dot`: Output DOT file path (default: `llm_protein_interactions.dot`)
- `--verbose`: Print detailed statistics

### 3. `parse_llm_output_parallel.py` - Parallel Parser

Enhanced version with optional parallel processing for large batch files.

#### Additional Arguments

- `--parallel`: Use parallel processing for large files
- `--workers`: Number of worker processes (default: CPU count, max 8)
- `--batch-size`: Lines per batch for parallel processing (default: 1000)

## Performance Guidance

| File Size | Recommended Parser | Expected Speedup |
|-----------|-------------------|------------------|
| < 10,000 lines | `parse_llm_output.py` | Good enough |
| 10,000 - 100,000 lines | `parse_llm_output_parallel.py` | 2-4x faster |
| > 100,000 lines | `parse_llm_output_parallel.py --parallel` | 3-8x faster |

## Color Scheme Legend

When viewing the generated DOT file:

- **Red edges**: Novel LLM predictions (not in existing databases)
- **Orange edges**: Confirmed by big_table.csv only
- **Blue edges**: Confirmed by string.csv only  
- **Green edges**: High confidence (confirmed by both databases)
- **Black edges**: Low confidence interactions

## Example Usage

### Basic Workflow
```bash
# 1. Generate prompts
python Sophia/generate_batch_prompts.py --max-proteins 50

# 2. Submit to vLLM batch API (external step)

# 3. Parse results
python Sophia/parse_llm_output.py --batch-output results.jsonl --verbose

# 4. Visualize
dot -Tpng llm_protein_interactions.dot -o protein_network.png
```

### Large File Processing
```bash
python Sophia/parse_llm_output_parallel.py \
    --batch-output large_results.jsonl \
    --parallel \
    --workers 6 \
    --verbose
```

## Requirements

- Python 3.7+
- pandas
- Standard library modules (argparse, json, os, pathlib, re)
- Graphviz (for visualization)

Install requirements:
```bash
pip install -r Sophia/requirements.txt
```

## Testing

See `test/README.md` for testing instructions and demo usage.

## Next Steps

After generating the DOT file, you can:
1. Visualize it using Graphviz tools
2. Analyze the network properties
3. Focus on red edges for novel discoveries
4. Cross-reference green edges for validation 