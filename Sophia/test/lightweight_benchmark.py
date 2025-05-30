#!/usr/bin/env python3
"""
Lightweight benchmark that tests parsing performance without loading large CSV files.
Focuses on the core text processing differences between serial and parallel approaches.
"""

import time
import subprocess
import os
import tempfile


def create_minimal_csv_files():
    """Create minimal CSV files for testing to avoid loading huge files."""
    
    # Create minimal proteins.csv
    proteins_content = """search_words
A1BG
A1CF
A2M
AAMP
AANAT
ABCA1
ABCB1
ABCC1
ACAA1
ACAD8"""
    
    # Create minimal big_table.csv  
    big_table_content = """col1,col2,score
A1BG,A1CF,100
A1CF,A2M,200
A2M,AAMP,300
AAMP,AANAT,400"""
    
    # Create minimal string.csv
    string_content = """col1,col2,score
A1BG,ABCA1,150
ABCA1,ABCB1,250
ABCB1,ABCC1,350
ABCC1,ACAA1,450"""
    
    # Write to temporary files
    temp_dir = "Sophia/test/temp_data"
    os.makedirs(temp_dir, exist_ok=True)
    
    with open(f"{temp_dir}/proteins.csv", "w") as f:
        f.write(proteins_content)
    
    with open(f"{temp_dir}/big_table.csv", "w") as f:
        f.write(big_table_content)
        
    with open(f"{temp_dir}/string.csv", "w") as f:
        f.write(string_content)
    
    return temp_dir


def time_parser_lightweight(parser_script, test_file, output_file, temp_data_dir, use_parallel=False):
    """Time a parser execution with minimal CSV files."""
    cmd = [
        "python", parser_script,
        "--batch-output", test_file,
        "--output-dot", output_file,
        "--proteins-csv", f"{temp_data_dir}/proteins.csv",
        "--big-table-csv", f"{temp_data_dir}/big_table.csv", 
        "--string-csv", f"{temp_data_dir}/string.csv"
    ]
    
    if use_parallel:
        cmd.extend(["--parallel", "--workers", "4"])
    
    parser_name = os.path.basename(parser_script)
    mode = "parallel" if use_parallel else "serial"
    print(f"⏱️  Running: {parser_name} ({mode})")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
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
        print("   ⏰ Timeout after 30 seconds")
        return 30, False, 0


def main():
    """Run lightweight benchmark."""
    print("🚀 LIGHTWEIGHT PARSER BENCHMARK")
    print("=" * 50)
    print("Using minimal CSV files to test core parsing logic")
    print()
    
    # Create minimal data files
    temp_data_dir = create_minimal_csv_files()
    print(f"📁 Created minimal test data in {temp_data_dir}")
    
    # Test configurations
    test_sizes = [
        (5, 1, "Tiny"),
        (10, 2, "Small"),
        (25, 2, "Medium"), 
        (50, 2, "Large"),
        (100, 3, "Very Large")
    ]
    
    results = []
    
    for proteins, iterations, size_name in test_sizes:
        print(f"\n📊 Testing {size_name}: {proteins} proteins x {iterations} iterations")
        print("-" * 45)
        
        # Generate test file
        test_file = f"Sophia/test/light_test_{proteins}p.jsonl"
        
        cmd = [
            "python", "Sophia/test/generate_fake_outputs.py",
            "--proteins-csv", f"{temp_data_dir}/proteins.csv",
            "--num-proteins", str(proteins),
            "--iterations", str(iterations),
            "--output-file", test_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to generate test data: {result.stderr}")
            continue
            
        # Count lines
        with open(test_file, 'r') as f:
            lines = sum(1 for _ in f)
        
        print(f"📝 Generated {lines:,} lines")
        
        # Test serial parser
        serial_time, serial_success, serial_interactions = time_parser_lightweight(
            "Sophia/parse_llm_output.py",
            test_file,
            f"Sophia/test/light_serial_{proteins}p.dot",
            temp_data_dir
        )
        
        # Test parallel parser (serial mode)
        parallel_serial_time, parallel_serial_success, _ = time_parser_lightweight(
            "Sophia/parse_llm_output_parallel.py",
            test_file,
            f"Sophia/test/light_parallel_serial_{proteins}p.dot",
            temp_data_dir
        )
        
        # Test parallel parser (parallel mode)
        parallel_time, parallel_success, parallel_interactions = time_parser_lightweight(
            "Sophia/parse_llm_output_parallel.py",
            test_file,
            f"Sophia/test/light_parallel_{proteins}p.dot",
            temp_data_dir,
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
        
        # Compare parallel script in serial vs parallel mode
        if parallel_serial_success and parallel_success:
            internal_speedup = parallel_serial_time / parallel_time
            internal_str = f"Serial→Parallel: {internal_speedup:.2f}x"
        else:
            internal_str = "N/A"
        
        results.append({
            'size': size_name,
            'lines': lines,
            'serial_time': serial_time,
            'parallel_serial_time': parallel_serial_time,
            'parallel_time': parallel_time,
            'speedup': speedup_str,
            'internal_speedup': internal_str,
            'interactions': serial_interactions
        })
        
        print(f"🏁 Results:")
        print(f"   Serial parser vs Parallel parser: {speedup_str}")
        print(f"   {internal_str}")
        
        # Cleanup test files
        for f in [test_file] + [f"Sophia/test/light_*_{proteins}p.dot"]:
            if os.path.exists(f):
                os.remove(f)
    
    # Summary table
    print("\n" + "=" * 80)
    print("LIGHTWEIGHT BENCHMARK SUMMARY")
    print("=" * 80)
    print(f"{'Size':<10} {'Lines':<6} {'Serial':<8} {'Par(Ser)':<8} {'Par(Par)':<8} {'Speedup':<12} {'Internal':<15}")
    print("-" * 80)
    
    for r in results:
        print(f"{r['size']:<10} {r['lines']:<6} {r['serial_time']:<8.3f} "
              f"{r['parallel_serial_time']:<8.3f} {r['parallel_time']:<8.3f} "
              f"{r['speedup']:<12} {r['internal_speedup']:<15}")
    
    # Analysis
    print("\n📋 ANALYSIS:")
    print("-" * 40)
    
    # Find crossover point
    crossover_found = False
    for r in results:
        if "faster" in r['speedup'] and "🚀" in r['speedup']:
            print(f"✅ Parallel becomes beneficial at {r['size']} size ({r['lines']} lines)")
            crossover_found = True
            break
    
    if not crossover_found:
        print("⚠️  No clear parallel advantage found in test range")
        print("⚠️  For these data sizes, serial parser is sufficient")
    
    print(f"\n🧹 Cleaning up temporary files...")
    import shutil
    shutil.rmtree(temp_data_dir)
    
    print("\n💡 Note: This test uses minimal CSV files. Real performance may differ")
    print("   with large validation databases due to I/O and memory effects.")


if __name__ == "__main__":
    main() 