#!/bin/bash
# Demonstration script for the protein interaction pipeline

echo "====================================================="
echo "PROTEIN INTERACTION DISCOVERY PIPELINE DEMO"
echo "====================================================="

# Step 1: Generate batch prompts
echo "Step 1: Generating batch prompts for 5 proteins..."
python Sophia/generate_batch_prompts.py \
    --max-proteins 5 \
    --iterations 2 \
    --output-file Sophia/test/demo_prompts.jsonl

echo ""
echo "Step 2: Generating fake LLM responses for testing..."
python Sophia/test/generate_fake_outputs.py \
    --num-proteins 5 \
    --iterations 2 \
    --output-file Sophia/test/demo_responses.jsonl

echo ""
echo "Step 3: Parsing LLM responses and generating DOT file..."
python Sophia/parse_llm_output.py \
    --batch-output Sophia/test/demo_responses.jsonl \
    --output-dot Sophia/test/demo_interactions.dot \
    --verbose

echo ""
echo "Step 4: Showing first few lines of generated files..."
echo "-----------------------------------------------------"
echo "Generated prompts (first 2 lines):"
head -2 Sophia/test/demo_prompts.jsonl | jq -r '.body.messages[1].content'

echo ""
echo "Generated DOT interactions (first 10 lines):"
head -10 Sophia/test/demo_interactions.dot

echo ""
echo "====================================================="
echo "DEMO COMPLETE!"
echo "====================================================="
echo "Files generated:"
echo "  - Sophia/test/demo_prompts.jsonl (batch prompts for vLLM)"
echo "  - Sophia/test/demo_responses.jsonl (fake LLM responses)"
echo "  - Sophia/test/demo_interactions.dot (protein network visualization)"
echo ""
echo "To visualize the network:"
echo "  dot -Tpng Sophia/test/demo_interactions.dot -o Sophia/test/demo_network.png"
echo ""
echo "For real usage, submit demo_prompts.jsonl to your vLLM"
echo "batch API, then use the parser on the real responses." 