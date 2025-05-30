# Protein-Protein Interaction Discovery Pipeline

A comprehensive pipeline for discovering protein-protein interactions using Large Language Models (LLMs) with vLLM batch API processing.

## Overview

This pipeline generates prompts for protein interaction discovery, processes them through vLLM batch API, and parses the responses to extract and visualize protein interaction networks.

## Features

- **Batch Prompt Generation**: Creates vLLM-compatible JSONL prompts with configurable iterations
- **Optimized Parsing**: Both serial and parallel parsers with performance optimizations
- **Network Visualization**: Generates color-coded DOT files for network analysis
- **Validation Integration**: Cross-references predictions with existing databases
- **Performance Benchmarking**: Comprehensive testing infrastructure

## Quick Start

1. **Generate batch prompts:**
   ```bash
   python generate_batch_prompts.py --proteins-csv data/proteins.csv --output prompts.jsonl
   ```

2. **Submit to vLLM batch API** (external step)

3. **Parse responses and generate network:**
   ```bash
   # For small datasets (< 5,000 responses)
   python parse_llm_output.py --batch-output responses.jsonl --output-dot network.dot
   
   # For large datasets (≥ 5,000 responses)  
   python parse_llm_output_parallel.py --batch-output responses.jsonl --output-dot network.dot --parallel
   ```

## Files

### Core Pipeline
- `generate_batch_prompts.py` - Generate vLLM batch prompts
- `parse_llm_output.py` - Optimized serial parser 
- `parse_llm_output_parallel.py` - Enhanced parallel parser
- `requirements.txt` - Python dependencies

### Testing & Benchmarking
- `test/generate_fake_outputs.py` - Generate test data
- `test/core_benchmark.py` - Algorithm performance testing
- `test/lightweight_benchmark.py` - Minimal dependency benchmarking
- `test/benchmark_parsers.py` - Full-scale performance comparison
- `test/quick_benchmark.py` - Fast comparison testing
- `test/demo.sh` - Complete pipeline demonstration

### Documentation
- `PERFORMANCE_ANALYSIS.md` - Comprehensive performance analysis
- `test/README.md` - Testing infrastructure documentation

## Performance Characteristics

### Serial vs Parallel Parsing

**Use Serial Parser (`parse_llm_output.py`) when:**
- Processing < 5,000 responses
- Working with small to medium datasets
- Prioritizing simplicity and lower memory usage

**Use Parallel Parser (`parse_llm_output_parallel.py`) when:**
- Processing ≥ 5,000 responses  
- Working with large-scale datasets
- CPU cores are available for parallel processing

### Benchmarking Results

Based on comprehensive testing:

| Data Size | Best Parser | Performance Gain |
|-----------|-------------|------------------|
| < 1,000 lines | Serial | 2-7x faster |
| 1,000-5,000 lines | Serial | 1-3x faster |
| ≥ 5,000 lines | Parallel | 1.3x+ faster |

See `PERFORMANCE_ANALYSIS.md` for detailed analysis.

## Network Visualization

The pipeline generates color-coded DOT files with the following scheme:

- 🔴 **Red**: Novel LLM predictions (not in validation databases)
- 🟠 **Orange**: Found in big_table.csv only
- 🔵 **Blue**: Found in string.csv only  
- 🟢 **Green**: High confidence (found in both databases with high scores)
- ⚫ **Black**: Default (found in databases with lower scores)

## Configuration

### Prompt Generation Options
```bash
python generate_batch_prompts.py \
  --proteins-csv data/proteins.csv \
  --output batch_prompts.jsonl \
  --iterations 3 \
  --model-name "meta-llama/Meta-Llama-3.1-8B-Instruct"
```

### Parser Options
```bash
python parse_llm_output_parallel.py \
  --batch-output responses.jsonl \
  --output-dot network.dot \
  --proteins-csv data/proteins.csv \
  --big-table-csv data/big_table.csv \
  --string-csv data/string.csv \
  --parallel \
  --workers 4
```

## Data Requirements

- `data/proteins.csv` - List of proteins to analyze
- `data/big_table.csv` - Validation database (optional)
- `data/string.csv` - STRING database export (optional)

## Testing

Run the test suite:
```bash
# Quick performance comparison
python test/quick_benchmark.py

# Comprehensive algorithm testing
python test/core_benchmark.py

# Lightweight benchmarking (minimal dependencies)
python test/lightweight_benchmark.py

# Complete pipeline demo
bash test/demo.sh
```

## Installation

```bash
pip install -r requirements.txt
```

## Dependencies

- pandas - Data manipulation
- Standard library: json, re, argparse, multiprocessing, time

## Architecture

The pipeline follows a modular architecture:

1. **Input Layer**: Protein datasets and configuration
2. **Generation Layer**: vLLM prompt creation
3. **Processing Layer**: LLM batch API (external)
4. **Parsing Layer**: Response extraction and validation
5. **Output Layer**: Network visualization and analysis

## Contributing

The pipeline includes comprehensive testing infrastructure. When contributing:

1. Run benchmarks to ensure performance is maintained
2. Add tests for new functionality
3. Update documentation for user-facing changes

## License

This project is part of the BALSAM protein-protein interaction research pipeline. 