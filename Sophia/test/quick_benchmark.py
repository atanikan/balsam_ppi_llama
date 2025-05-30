#!/usr/bin/env python3
"""
Quick benchmark script for comparing parser performance.
Uses smaller datasets for faster testing.
"""

import time
import subprocess
import os


def time_parser(parser_script, test_file, output_file, use_parallel=False):
    """Time a parser execution."""
    cmd = ["python", parser_script, "--batch-output", test_file, "--output-dot", output_file]
    
    if use_parallel:
        cmd.extend(["--parallel", "--workers", "4"])
    
    print(f"⏱️  Running: {os.path.basename(parser_script)} {'(parallel)' if use_parallel else '(serial)'}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        end_time = time.time()
        
        if result.returncode == 0:
            # Extract interactions count
            interactions = 0
            for line in result.stdout.split('\n'):
                if "Total unique interactions:" in line:
                    interactions = int(line.split(':')[1].strip().replace(',', ''))
                    break
            
            execution_time = end_time - start_time
            print(f"   ✅ Success: {execution_time:.3f}s, {interactions:,} interactions")
            return execution_time, True, interactions
        else:
            print(f"   ❌ Failed: {result.stderr}")
            return 0, False, 0
            
    except subprocess.TimeoutExpired:
        print("   ⏰ Timeout after 60 seconds")
        return 60, False, 0


def main():
    """Run quick benchmark."""
    print("🚀 QUICK PARSER BENCHMARK")
    print("=" * 50)
    
    # Generate test data
    test_sizes = [
        (20, 2, "Small"),
        (50, 2, "Medium"), 
        (100, 2, "Large")
    ]
    
    results = []
    
    for proteins, iterations, size_name in test_sizes:
        print(f"\n📊 Testing {size_name}: {proteins} proteins x {iterations} iterations")
        print("-" * 40)
        
        # Generate test file
        test_file = f"Sophia/test/quick_test_{proteins}p.jsonl"
        
        cmd = [
            "python", "Sophia/test/generate_fake_outputs.py",
            "--num-proteins", str(proteins),
            "--iterations", str(iterations),
            "--output-file", test_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to generate test data")
            continue
            
        # Count lines
        with open(test_file, 'r') as f:
            lines = sum(1 for _ in f)
        
        print(f"📝 Generated {lines:,} lines")
        
        # Test serial parser
        serial_time, serial_success, serial_interactions = time_parser(
            "Sophia/parse_llm_output.py",
            test_file,
            f"Sophia/test/quick_serial_{proteins}p.dot"
        )
        
        # Test parallel parser (serial mode)
        parallel_serial_time, parallel_serial_success, _ = time_parser(
            "Sophia/parse_llm_output_parallel.py",
            test_file,
            f"Sophia/test/quick_parallel_serial_{proteins}p.dot"
        )
        
        # Test parallel parser (parallel mode)
        parallel_time, parallel_success, parallel_interactions = time_parser(
            "Sophia/parse_llm_output_parallel.py",
            test_file,
            f"Sophia/test/quick_parallel_{proteins}p.dot",
            use_parallel=True
        )
        
        # Calculate speedup
        if serial_success and parallel_success and serial_time > 0:
            speedup = serial_time / parallel_time
            if speedup > 1.1:
                speedup_str = f"{speedup:.2f}x faster 🚀"
            elif speedup < 0.9:
                speedup_str = f"{1/speedup:.2f}x slower 🐌"
            else:
                speedup_str = f"~same speed ≈"
        else:
            speedup_str = "N/A"
        
        results.append({
            'size': size_name,
            'lines': lines,
            'serial_time': serial_time,
            'parallel_time': parallel_time,
            'speedup': speedup_str,
            'interactions': serial_interactions
        })
        
        print(f"🏁 Parallel vs Serial: {speedup_str}")
        
        # Cleanup
        for f in [test_file, f"Sophia/test/quick_*_{proteins}p.dot"]:
            if os.path.exists(f):
                os.remove(f)
    
    # Summary table
    print("\n" + "=" * 60)
    print("QUICK BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"{'Size':<8} {'Lines':<8} {'Serial':<10} {'Parallel':<10} {'Result':<15}")
    print("-" * 60)
    
    for r in results:
        print(f"{r['size']:<8} {r['lines']:<8} {r['serial_time']:<10.3f} "
              f"{r['parallel_time']:<10.3f} {r['speedup']:<15}")
    
    print("\n💡 Tip: Run 'python Sophia/test/benchmark_parsers.py' for comprehensive testing")


if __name__ == "__main__":
    main() 