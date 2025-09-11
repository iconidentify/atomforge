#!/usr/bin/env python3
"""
Comprehensive Ada32.dll Function Test

This script will systematically test ALL Ada32.dll assembly functions
to determine which one produces the production binary format (356 bytes)
instead of the debug format (4,111 bytes).
"""

import subprocess
import os
import json

class Ada32FunctionTester:
    def __init__(self):
        self.functions_to_test = [
            'AdaAssembleAtomStream',     # Known: produces debug format
            'AdaAssembleFragment',       # Hypothesis: might produce production
            'AdaNormalizeAtomStream',    # Hypothesis: debug → production conversion
            'AdaAssembleArgument'        # Unknown: component-level assembly
        ]
        
        self.test_input = 'golden_tests/32-105.txt'
        self.expected_production_size = 356
        self.expected_debug_size = 4111
        
    def create_test_bridge(self):
        """Create a comprehensive C bridge to test all functions"""
        
        bridge_code = '''
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaAssembleFragment_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaNormalizeAtomStream_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaAssembleArgument_t)(void* input, int inputSize, void* output, int* outputSize);

int test_function(const char* func_name, void* func_ptr, const char* input_file) {
    FILE* fp = fopen(input_file, "rb");
    if (!fp) {
        fprintf(stderr, "ERROR: Cannot open %s\\n", input_file);
        return -1;
    }
    
    fseek(fp, 0, SEEK_END);
    long input_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    
    char* input_data = malloc(input_size + 1);
    fread(input_data, 1, input_size, fp);
    input_data[input_size] = '\\0';
    fclose(fp);
    
    int max_output_size = input_size * 4;
    char* output_data = malloc(max_output_size);
    int output_size = max_output_size;
    
    int result = 0;
    
    if (strcmp(func_name, "AdaAssembleAtomStream") == 0) {
        AdaAssembleAtomStream_t func = (AdaAssembleAtomStream_t)func_ptr;
        result = func(input_data, input_size, output_data, &output_size);
    } else if (strcmp(func_name, "AdaAssembleFragment") == 0) {
        AdaAssembleFragment_t func = (AdaAssembleFragment_t)func_ptr;
        result = func(input_data, input_size, output_data, &output_size);
    } else if (strcmp(func_name, "AdaNormalizeAtomStream") == 0) {
        AdaNormalizeAtomStream_t func = (AdaNormalizeAtomStream_t)func_ptr;
        result = func(input_data, input_size, output_data, &output_size);
    } else if (strcmp(func_name, "AdaAssembleArgument") == 0) {
        AdaAssembleArgument_t func = (AdaAssembleArgument_t)func_ptr;
        result = func(input_data, input_size, output_data, &output_size);
    }
    
    printf("%s: result=%d, output_size=%d\\n", func_name, result, output_size);
    
    if (result > 0) {
        // Write output to file for analysis
        char output_filename[256];
        sprintf(output_filename, "test_output/func_%s.str", func_name);
        FILE* out_fp = fopen(output_filename, "wb");
        if (out_fp) {
            int actual_size = (result < output_size) ? result : output_size;
            fwrite(output_data, 1, actual_size, out_fp);
            fclose(out_fp);
            printf("Wrote %d bytes to %s\\n", actual_size, output_filename);
            
            // Check if this looks like production format
            if (actual_size >= 4 && output_data[0] == 0x40 && output_data[1] == 0x01) {
                printf("🎯 BINARY FDO FORMAT DETECTED (starts with 40 01)\\n");
                if (actual_size < 1000) {
                    printf("🎉 POSSIBLE PRODUCTION FORMAT (small size: %d bytes)\\n", actual_size);
                } else {
                    printf("⚠️  DEBUG FORMAT (large size: %d bytes)\\n", actual_size);
                }
            }
        }
    }
    
    free(input_data);
    free(output_data);
    
    return result;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: comprehensive_test.exe <input_file>\\n");
        return 1;
    }
    
    char* input_file = argv[1];
    
    HMODULE hDll = LoadLibrary("Ada32.dll");
    if (!hDll) {
        fprintf(stderr, "ERROR: Failed to load Ada32.dll\\n");
        return 1;
    }
    
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hDll, "AdaInitialize");
    if (AdaInitialize) {
        int init_result = AdaInitialize();
        printf("AdaInitialize result: %d\\n", init_result);
    }
    
    printf("\\n=== Testing All Ada32.dll Assembly Functions ===\\n");
    
    void* functions[] = {
        GetProcAddress(hDll, "AdaAssembleAtomStream"),
        GetProcAddress(hDll, "AdaAssembleFragment"), 
        GetProcAddress(hDll, "AdaNormalizeAtomStream"),
        GetProcAddress(hDll, "AdaAssembleArgument")
    };
    
    const char* func_names[] = {
        "AdaAssembleAtomStream",
        "AdaAssembleFragment",
        "AdaNormalizeAtomStream", 
        "AdaAssembleArgument"
    };
    
    for (int i = 0; i < 4; i++) {
        printf("\\n--- Testing %s ---\\n", func_names[i]);
        if (functions[i]) {
            test_function(func_names[i], functions[i], input_file);
        } else {
            printf("%s: NOT FOUND\\n", func_names[i]);
        }
    }
    
    FreeLibrary(hDll);
    return 0;
}
'''
        
        with open('comprehensive_ada32_test.c', 'w') as f:
            f.write(bridge_code)
        
        print("✅ Created comprehensive test bridge")
        
    def compile_and_run_test(self):
        """Compile the test bridge and run it"""
        
        print("🔧 Compiling comprehensive test...")
        
        # Compile in Docker
        cmd = [
            'docker-compose', 'run', '--rm', 'ada32-wine', 
            'bash', '-c', 
            'cd /ada32_toolkit && i686-w64-mingw32-gcc -o comprehensive_test.exe comprehensive_ada32_test.c'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Compilation failed: {result.stderr}")
            return False
        
        print("✅ Compilation successful")
        
        # Run the test
        print("🧪 Running comprehensive Ada32.dll function test...")
        
        cmd = [
            'docker-compose', 'run', '--rm', 'ada32-wine',
            'bash', '-c',
            f'cd /ada32_toolkit && wine comprehensive_test.exe {self.test_input}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        print("Test output:")
        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)
        
        return True
        
    def analyze_results(self):
        """Analyze the output files to determine which function produces production format"""
        
        print("\n=== Analysis of Function Outputs ===")
        
        results = {}
        
        for func_name in self.functions_to_test:
            output_file = f'test_output/func_{func_name}.str'
            if os.path.exists(output_file):
                size = os.path.getsize(output_file)
                results[func_name] = size
                
                # Check first few bytes
                with open(output_file, 'rb') as f:
                    header = f.read(10)
                
                is_fdo = len(header) >= 2 and header[0] == 0x40 and header[1] == 0x01
                
                print(f"{func_name:25}: {size:4d} bytes - {'FDO format' if is_fdo else 'Unknown format'}")
                
                # Compare with expected sizes
                if size == self.expected_production_size:
                    print(f"🎯 {func_name}: MATCHES PRODUCTION SIZE ({size} bytes)!")
                elif size == self.expected_debug_size:
                    print(f"⚠️  {func_name}: Debug format ({size} bytes)")
                elif is_fdo and size < 1000:
                    print(f"✅ {func_name}: Possible production format ({size} bytes)")
                
            else:
                print(f"{func_name:25}: No output file generated")
                results[func_name] = 0
        
        print(f"\n🎯 TARGET: {self.expected_production_size} bytes (production format)")
        print(f"📊 CURRENT: {self.expected_debug_size} bytes (debug format)")
        
        return results
    
    def run_full_test(self):
        """Run the complete test suite"""
        print("🚀 Comprehensive Ada32.dll Function Analysis")
        print("=" * 60)
        
        # Create test bridge
        self.create_test_bridge()
        
        # Ensure output directory exists
        os.makedirs('test_output', exist_ok=True)
        
        # Compile and run
        if self.compile_and_run_test():
            # Analyze results
            results = self.analyze_results()
            
            print("\n🏆 CONCLUSION:")
            production_candidates = [func for func, size in results.items() 
                                   if size == self.expected_production_size]
            
            if production_candidates:
                print(f"✅ Found production format function(s): {', '.join(production_candidates)}")
            else:
                print("❌ No function produced the exact production format")
                print("   Additional investigation needed")
        
        return True

def main():
    tester = Ada32FunctionTester()
    tester.run_full_test()

if __name__ == "__main__":
    main()