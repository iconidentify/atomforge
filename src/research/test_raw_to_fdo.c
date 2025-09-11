/*
 * Test Ada32 functions for raw-to-FDO conversion
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaConvertToFDO_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaNormalizeAtomStream_t)(void* input, int inputSize, void* output, int* outputSize);

int main() {
    printf("=== Testing Ada32 Raw-to-FDO Conversion ===\n");
    
    HMODULE hDll = LoadLibrary("Ada32.dll");
    if (!hDll) {
        fprintf(stderr, "Failed to load Ada32.dll\n");
        return 1;
    }
    
    // Get functions
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hDll, "AdaInitialize");
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(hDll, "AdaAssembleAtomStream");
    AdaNormalizeAtomStream_t AdaNormalizeAtomStream = (AdaNormalizeAtomStream_t)GetProcAddress(hDll, "AdaNormalizeAtomStream");
    
    // Test possible conversion function names
    const char* conversion_functions[] = {
        "AdaConvertToFDO",
        "AdaFormatToFDO", 
        "AdaRawToFDO",
        "AdaAssembleToFDO",
        "AdaCompileToFDO",
        "AdaPackToFDO",
        "AdaConvertRaw",
        "AdaFormatRaw",
        "AdaProcessRaw"
    };
    
    printf("Looking for conversion functions:\n");
    void* conversion_func = NULL;
    const char* found_func_name = NULL;
    
    for (int i = 0; i < 9; i++) {
        void* func = GetProcAddress(hDll, conversion_functions[i]);
        printf("%-20s: %s\n", conversion_functions[i], func ? "✅ FOUND!" : "❌");
        if (func && !conversion_func) {
            conversion_func = func;
            found_func_name = conversion_functions[i];
        }
    }
    
    if (AdaInitialize) AdaInitialize();
    
    // Use our working raw output as test input
    FILE* fp = fopen("test_output/clean_AdaAssembleAtomStream.str", "rb");
    if (!fp) {
        printf("❌ Need raw Ada32 output file first\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    fseek(fp, 0, SEEK_END);
    long input_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    
    char* input_data = malloc(input_size);
    fread(input_data, 1, input_size, fp);
    fclose(fp);
    
    printf("\nUsing 413-byte raw Ada32 output as input (%ld bytes)\n", input_size);
    
    // Test AdaNormalizeAtomStream on the raw binary (not text)
    printf("\n=== Testing AdaNormalizeAtomStream on raw binary ===\n");
    char output_data[1024];
    int output_size = sizeof(output_data);
    
    int result = AdaNormalizeAtomStream(input_data, input_size, output_data, &output_size);
    printf("Result: %d, Output size: %d\n", result, output_size);
    
    if (result == 0 && output_size > 0) {
        printf("First 16 bytes: ");
        for (int i = 0; i < 16 && i < output_size; i++) {
            printf("%02x ", (unsigned char)output_data[i]);
        }
        printf("\n");
        
        // Check for FDO header
        if (output_size >= 2 && (unsigned char)output_data[0] == 0x40 && (unsigned char)output_data[1] == 0x01) {
            printf("🎯 SUCCESS: FDO FORMAT DETECTED!\n");
            if (output_size == 356) {
                printf("🎉 PERFECT: 356 BYTES - PRODUCTION FORMAT!\n");
            }
            
            // Save the result
            FILE* out_fp = fopen("test_output/converted_to_fdo.str", "wb");
            if (out_fp) {
                fwrite(output_data, 1, output_size, out_fp);
                fclose(out_fp);
                printf("💾 Saved to test_output/converted_to_fdo.str\n");
            }
        }
    }
    
    free(input_data);
    FreeLibrary(hDll);
    return 0;
}