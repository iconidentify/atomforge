/*
 * Minimal test to restore working Ada32.dll functionality
 * Based on our previous successful approach
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int size, void* output, int* outSize);

int main() {
    printf("🔧 Minimal Ada32.dll Test - Restoring Functionality\n");
    printf("==================================================\n");
    
    // Load Ada32.dll from root directory (like our working setup)
    HMODULE ada32 = LoadLibraryA("Ada32.dll");
    if (!ada32) {
        printf("❌ Failed to load Ada32.dll from current directory\n");
        return 1;
    }
    
    printf("✅ Ada32.dll loaded successfully\n");
    
    // Get functions
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(ada32, "AdaInitialize");
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(ada32, "AdaAssembleAtomStream");
    
    if (!AdaInitialize || !AdaAssembleAtomStream) {
        printf("❌ Required functions not found\n");
        FreeLibrary(ada32);
        return 1;
    }
    
    printf("✅ Functions found\n");
    
    // Initialize
    int init_result = AdaInitialize();
    printf("AdaInitialize(): %d\n", init_result);
    
    if (init_result != 1) {
        printf("❌ Initialization failed\n");
        FreeLibrary(ada32);
        return 1;
    }
    
    printf("✅ Ada32 initialized\n");
    
    // Test with our known working file
    FILE* fp = fopen("tests/fixtures/clean_32-105.txt", "r");
    if (!fp) {
        printf("❌ Cannot open tests/fixtures/clean_32-105.txt\n");
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
    
    printf("✅ Read %ld bytes from clean_32-105.txt\n", input_size);
    
    // Try compilation
    char output_buffer[1024];
    int output_size = sizeof(output_buffer);
    
    printf("🔄 Attempting compilation...\n");
    int result = AdaAssembleAtomStream(input_data, (int)input_size, output_buffer, &output_size);
    
    printf("AdaAssembleAtomStream result: %d\n", result);
    printf("Output size: %d\n", output_size);
    
    if (result == 0 && output_size > 0) {
        printf("🎉🎉🎉 SUCCESS! Compilation working!\n");
        printf("Generated %d bytes (expected ~413)\n", output_size);
        
        // Save result
        FILE* out_fp = fopen("RESTORED_WORKING_OUTPUT.str", "wb");
        if (out_fp) {
            fwrite(output_buffer, 1, output_size, out_fp);
            fclose(out_fp);
            printf("💾 Saved output to RESTORED_WORKING_OUTPUT.str\n");
        }
        
        // Show header
        printf("Header: ");
        for (int i = 0; i < 16; i++) {
            printf("%02x ", (unsigned char)output_buffer[i]);
        }
        printf("\n");
        
    } else {
        printf("❌ Compilation failed - result: %d, size: %d\n", result, output_size);
    }
    
    free(input_data);
    FreeLibrary(ada32);
    
    return (result == 0 && output_size > 0) ? 0 : 1;
}