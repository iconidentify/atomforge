#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int inputSize, void* output, int* outputSize);

int main(int argc, char* argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: simple_test.exe <input_file>\n");
        return 1;
    }
    
    // Load Ada32.dll
    HMODULE hDll = LoadLibrary("Ada32.dll");
    if (!hDll) {
        fprintf(stderr, "Failed to load Ada32.dll\n");
        return 1;
    }
    
    // Initialize
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hDll, "AdaInitialize");
    if (AdaInitialize) {
        int init_result = AdaInitialize();
        printf("AdaInitialize: %d\n", init_result);
    }
    
    // Get function
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(hDll, "AdaAssembleAtomStream");
    if (!AdaAssembleAtomStream) {
        fprintf(stderr, "AdaAssembleAtomStream not found\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    // Read input
    FILE* fp = fopen(argv[1], "rb");
    if (!fp) {
        fprintf(stderr, "Cannot open %s\n", argv[1]);
        FreeLibrary(hDll);
        return 1;
    }
    
    fseek(fp, 0, SEEK_END);
    long input_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    
    char* input_data = malloc(input_size + 1);
    fread(input_data, 1, input_size, fp);
    input_data[input_size] = '\0';
    fclose(fp);
    
    printf("Input size: %ld bytes\n", input_size);
    
    // Try different output buffer sizes
    int buffer_sizes[] = {4096, 8192, 16384, 32768, 65536};
    int num_sizes = sizeof(buffer_sizes) / sizeof(buffer_sizes[0]);
    
    for (int i = 0; i < num_sizes; i++) {
        int max_output_size = buffer_sizes[i];
        char* output_data = malloc(max_output_size);
        int output_size = max_output_size;
        
        printf("\n=== Testing with %d byte buffer ===\n", max_output_size);
        
        int result = AdaAssembleAtomStream(input_data, input_size, output_data, &output_size);
        
        printf("Result: %d (0x%x)\n", result, result);
        printf("Output size: %d bytes\n", output_size);
        
        if (result > 0) {
            // Look at first 16 bytes
            printf("First 16 bytes: ");
            int show_bytes = (output_size > 16) ? 16 : output_size;
            for (int j = 0; j < show_bytes; j++) {
                printf("%02x ", (unsigned char)output_data[j]);
            }
            printf("\n");
            
            // Check for FDO header
            if (output_size >= 2 && (unsigned char)output_data[0] == 0x40 && (unsigned char)output_data[1] == 0x01) {
                printf("FDO format detected!\n");
                
                // Save this one
                char filename[256];
                sprintf(filename, "test_output/ada32_result_%d.str", max_output_size);
                FILE* out_fp = fopen(filename, "wb");
                if (out_fp) {
                    fwrite(output_data, 1, output_size, out_fp);
                    fclose(out_fp);
                    printf("Saved to %s\n", filename);
                }
            }
        }
        
        free(output_data);
    }
    
    free(input_data);
    FreeLibrary(hDll);
    return 0;
}