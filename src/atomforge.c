/*
 * Flexible Ada32 Compiler - Works with any input file
 * Now that we know Ada32.dll needs GIDINFO.INF and Ada.bin
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int size, void* output, int* outSize);

int main(int argc, char* argv[]) {
    if (argc != 3) {
        printf("Usage: %s <input.txt> <output.bin>\n", argv[0]);
        return 1;
    }
    
    const char* input_file = argv[1];
    const char* output_file = argv[2];
    
    printf("🔧 Flexible Ada32 Compiler\n");
    printf("Input: %s\n", input_file);
    printf("Output: %s\n", output_file);
    
    // Load Ada32.dll
    HMODULE ada32 = LoadLibraryA("Ada32.dll");
    if (!ada32) {
        printf("❌ Failed to load Ada32.dll\n");
        return 1;
    }
    
    // Get functions
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(ada32, "AdaInitialize");
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(ada32, "AdaAssembleAtomStream");
    
    if (!AdaInitialize || !AdaAssembleAtomStream) {
        printf("❌ Required functions not found\n");
        FreeLibrary(ada32);
        return 1;
    }
    
    // Initialize
    int init_result = AdaInitialize();
    if (init_result != 1) {
        printf("❌ Initialization failed: %d\n", init_result);
        FreeLibrary(ada32);
        return 1;
    }
    
    // Read input file
    FILE* fp = fopen(input_file, "r");
    if (!fp) {
        printf("❌ Cannot open input file: %s\n", input_file);
        FreeLibrary(ada32);
        return 1;
    }
    
    fseek(fp, 0, SEEK_END);
    long input_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    
    char* input_data = malloc(input_size + 1);
    fread(input_data, 1, input_size, fp);
    input_data[input_size] = 0;
    fclose(fp);
    
    printf("✅ Read %ld bytes from %s\n", input_size, input_file);
    
    // Compile
    char output_buffer[8192];  // Larger buffer for bigger files
    int output_size = sizeof(output_buffer);
    
    int result = AdaAssembleAtomStream(input_data, (int)input_size, output_buffer, &output_size);
    
    if (result == 0 && output_size > 0) {
        // Save output
        FILE* out_fp = fopen(output_file, "wb");
        if (out_fp) {
            fwrite(output_buffer, 1, output_size, out_fp);
            fclose(out_fp);
            printf("✅ Success: %d bytes -> %s\n", output_size, output_file);
        } else {
            printf("❌ Cannot write output file: %s\n", output_file);
            result = 1;
        }
    } else {
        printf("❌ Compilation failed - result: %d, size: %d\n", result, output_size);
    }
    
    free(input_data);
    FreeLibrary(ada32);
    
    return (result == 0 && output_size > 0) ? 0 : 1;
}