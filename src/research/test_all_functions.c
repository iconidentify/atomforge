#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaAssembleFragment_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaNormalizeAtomStream_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaAssembleArgument_t)(void* input, int inputSize, void* output, int* outputSize);

int main(int argc, char* argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: test_all.exe <input_file>\n");
        return 1;
    }
    
    // Load and initialize
    HMODULE hDll = LoadLibrary("Ada32.dll");
    if (!hDll) {
        fprintf(stderr, "Failed to load Ada32.dll\n");
        return 1;
    }
    
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hDll, "AdaInitialize");
    if (AdaInitialize) AdaInitialize();
    
    // Get all functions
    void* functions[] = {
        GetProcAddress(hDll, "AdaAssembleAtomStream"),
        GetProcAddress(hDll, "AdaAssembleFragment"),
        GetProcAddress(hDll, "AdaNormalizeAtomStream"),
        GetProcAddress(hDll, "AdaAssembleArgument")
    };
    
    const char* names[] = {
        "AdaAssembleAtomStream",
        "AdaAssembleFragment", 
        "AdaNormalizeAtomStream",
        "AdaAssembleArgument"
    };
    
    // Read input
    FILE* fp = fopen(argv[1], "rb");
    fseek(fp, 0, SEEK_END);
    long input_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    char* input_data = malloc(input_size + 1);
    fread(input_data, 1, input_size, fp);
    input_data[input_size] = '\0';
    fclose(fp);
    
    printf("Testing all Ada32 functions with clean input:\n");
    printf("Input size: %ld bytes\n\n", input_size);
    
    for (int i = 0; i < 4; i++) {
        printf("=== Testing %s ===\n", names[i]);
        
        if (!functions[i]) {
            printf("Function not found\n\n");
            continue;
        }
        
        char output_data[65536];
        int output_size = sizeof(output_data);
        int result = 0;
        
        if (i == 0) {
            AdaAssembleAtomStream_t func = (AdaAssembleAtomStream_t)functions[i];
            result = func(input_data, input_size, output_data, &output_size);
        } else if (i == 1) {
            AdaAssembleFragment_t func = (AdaAssembleFragment_t)functions[i];
            result = func(input_data, input_size, output_data, &output_size);
        } else if (i == 2) {
            AdaNormalizeAtomStream_t func = (AdaNormalizeAtomStream_t)functions[i];
            result = func(input_data, input_size, output_data, &output_size);
        } else if (i == 3) {
            AdaAssembleArgument_t func = (AdaAssembleArgument_t)functions[i];
            result = func(input_data, input_size, output_data, &output_size);
        }
        
        printf("Result: %d\n", result);
        printf("Output size: %d bytes\n", output_size);
        
        if (result == 0 && output_size > 0) {
            printf("First 16 bytes: ");
            int show_bytes = (output_size > 16) ? 16 : output_size;
            for (int j = 0; j < show_bytes; j++) {
                printf("%02x ", (unsigned char)output_data[j]);
            }
            printf("\n");
            
            // Check for FDO header
            if (output_size >= 2 && (unsigned char)output_data[0] == 0x40 && (unsigned char)output_data[1] == 0x01) {
                printf("🎯 FDO FORMAT DETECTED!\n");
                if (output_size == 356) {
                    printf("🎉 EXACT PRODUCTION SIZE MATCH!\n");
                }
            }
            
            // Save output
            char filename[256];
            sprintf(filename, "test_output/clean_%s.str", names[i]);
            FILE* out_fp = fopen(filename, "wb");
            if (out_fp) {
                fwrite(output_data, 1, output_size, out_fp);
                fclose(out_fp);
                printf("Saved to %s\n", filename);
            }
        } else if (result != 0) {
            printf("❌ Function failed with error %d\n", result);
        }
        
        printf("\n");
    }
    
    free(input_data);
    FreeLibrary(hDll);
    return 0;
}