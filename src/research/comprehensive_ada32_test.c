
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
        fprintf(stderr, "ERROR: Cannot open %s\n", input_file);
        return -1;
    }
    
    fseek(fp, 0, SEEK_END);
    long input_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    
    char* input_data = malloc(input_size + 1);
    fread(input_data, 1, input_size, fp);
    input_data[input_size] = '\0';
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
    
    printf("%s: result=%d, output_size=%d\n", func_name, result, output_size);
    
    if (result > 0) {
        // Write output to file for analysis
        char output_filename[256];
        sprintf(output_filename, "test_output/func_%s.str", func_name);
        FILE* out_fp = fopen(output_filename, "wb");
        if (out_fp) {
            int actual_size = (result < output_size) ? result : output_size;
            fwrite(output_data, 1, actual_size, out_fp);
            fclose(out_fp);
            printf("Wrote %d bytes to %s\n", actual_size, output_filename);
            
            // Check if this looks like production format
            if (actual_size >= 4 && output_data[0] == 0x40 && output_data[1] == 0x01) {
                printf("🎯 BINARY FDO FORMAT DETECTED (starts with 40 01)\n");
                if (actual_size < 1000) {
                    printf("🎉 POSSIBLE PRODUCTION FORMAT (small size: %d bytes)\n", actual_size);
                } else {
                    printf("⚠️  DEBUG FORMAT (large size: %d bytes)\n", actual_size);
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
        fprintf(stderr, "Usage: comprehensive_test.exe <input_file>\n");
        return 1;
    }
    
    char* input_file = argv[1];
    
    HMODULE hDll = LoadLibrary("Ada32.dll");
    if (!hDll) {
        fprintf(stderr, "ERROR: Failed to load Ada32.dll\n");
        return 1;
    }
    
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hDll, "AdaInitialize");
    if (AdaInitialize) {
        int init_result = AdaInitialize();
        printf("AdaInitialize result: %d\n", init_result);
    }
    
    printf("\n=== Testing All Ada32.dll Assembly Functions ===\n");
    
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
        printf("\n--- Testing %s ---\n", func_names[i]);
        if (functions[i]) {
            test_function(func_names[i], functions[i], input_file);
        } else {
            printf("%s: NOT FOUND\n", func_names[i]);
        }
    }
    
    FreeLibrary(hDll);
    return 0;
}
