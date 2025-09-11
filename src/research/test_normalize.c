#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaNormalizeAtomStream_t)(void* input, int inputSize, void* output, int* outputSize);

int main(int argc, char* argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: test_normalize.exe <input_file>\n");
        return 1;
    }
    
    HMODULE hDll = LoadLibrary("Ada32.dll");
    if (!hDll) {
        fprintf(stderr, "Failed to load Ada32.dll\n");
        return 1;
    }
    
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hDll, "AdaInitialize");
    if (AdaInitialize) AdaInitialize();
    
    AdaNormalizeAtomStream_t AdaNormalizeAtomStream = (AdaNormalizeAtomStream_t)GetProcAddress(hDll, "AdaNormalizeAtomStream");
    if (!AdaNormalizeAtomStream) {
        fprintf(stderr, "AdaNormalizeAtomStream not found\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    // Read input
    FILE* fp = fopen(argv[1], "rb");
    fseek(fp, 0, SEEK_END);
    long input_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    char* input_data = malloc(input_size + 1);
    fread(input_data, 1, input_size, fp);
    input_data[input_size] = '\0';
    fclose(fp);
    
    printf("Testing AdaNormalizeAtomStream\n");
    printf("Input size: %ld bytes\n", input_size);
    
    char output_data[65536];
    int output_size = sizeof(output_data);
    
    int result = AdaNormalizeAtomStream(input_data, input_size, output_data, &output_size);
    
    printf("Result: %d\n", result);
    printf("Output size: %d bytes\n", output_size);
    
    if (result == 0 && output_size > 0) {
        printf("First 16 bytes: ");
        int show_bytes = (output_size > 16) ? 16 : output_size;
        for (int i = 0; i < show_bytes; i++) {
            printf("%02x ", (unsigned char)output_data[i]);
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
        FILE* out_fp = fopen("test_output/normalize_result.str", "wb");
        if (out_fp) {
            fwrite(output_data, 1, output_size, out_fp);
            fclose(out_fp);
            printf("Saved to test_output/normalize_result.str\n");
        }
    } else if (result != 0) {
        printf("❌ Function failed with error %d\n", result);
    }
    
    free(input_data);
    FreeLibrary(hDll);
    return 0;
}