/*
 * Ada32 Production Format Test - Find the real compiler function
 * This will test all assembly functions with the same input to see which produces 356 bytes
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaAssembleFragment_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaNormalizeAtomStream_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaAssembleArgument_t)(void* input, int inputSize, void* output, int* outputSize);

void test_function(const char* func_name, void* func_ptr, const char* input_data, int input_size) {
    if (!func_ptr) {
        printf("❌ %s: Function not found\n", func_name);
        return;
    }
    
    printf("\n🧪 Testing %s...\n", func_name);
    
    // Prepare large output buffer
    int max_output_size = input_size * 8;
    char* output_data = malloc(max_output_size);
    int output_size = max_output_size;
    
    int result = 0;
    
    // Call the appropriate function
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
    
    printf("   Function result: %d\n", result);
    printf("   Output size: %d bytes\n", output_size);
    
    if (result > 0) {
        // Use the smaller of result or output_size as actual size
        int actual_size = (result < output_size) ? result : output_size;
        
        // Check if this looks like binary FDO format
        if (actual_size >= 2 && (unsigned char)output_data[0] == 0x40 && (unsigned char)output_data[1] == 0x01) {
            printf("   ✅ Binary FDO format detected (40 01 header)\n");
            
            // Check size category
            if (actual_size < 500) {
                printf("   🎯 PRODUCTION SIZE RANGE (%d bytes)\n", actual_size);
                if (actual_size == 356) {
                    printf("   🎉 EXACT MATCH: 356 BYTES - THIS IS THE PRODUCTION COMPILER!\n");
                }
            } else if (actual_size > 3000) {
                printf("   📝 Debug format size (%d bytes)\n", actual_size);
            } else {
                printf("   ❓ Intermediate size (%d bytes)\n", actual_size);
            }
            
            // Save output for analysis
            char output_filename[256];
            sprintf(output_filename, "test_%s.str", func_name);
            FILE* out_fp = fopen(output_filename, "wb");
            if (out_fp) {
                fwrite(output_data, 1, actual_size, out_fp);
                fclose(out_fp);
                printf("   💾 Saved to %s\n", output_filename);
                
                // Show first few bytes
                printf("   🔍 First 16 bytes: ");
                for (int i = 0; i < 16 && i < actual_size; i++) {
                    printf("%02x ", (unsigned char)output_data[i]);
                }
                printf("\n");
            }
        } else {
            printf("   ❌ Not binary FDO format\n");
        }
    } else {
        printf("   ❌ Function call failed\n");
    }
    
    free(output_data);
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: ada32_production_test.exe <input_file>\n");
        return 1;
    }
    
    char* input_file = argv[1];
    
    printf("🚀 Ada32.dll Production Format Search\n");
    printf("=====================================\n");
    printf("Target: Find function that produces 356-byte format\n");
    printf("Input: %s\n", input_file);
    
    // Load Ada32.dll
    HMODULE hDll = LoadLibrary("bin/dlls/Ada32.dll");
    if (!hDll) {
        fprintf(stderr, "❌ Failed to load Ada32.dll\n");
        return 1;
    }
    
    // Initialize Ada32
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hDll, "AdaInitialize");
    if (AdaInitialize) {
        int init_result = AdaInitialize();
        printf("Ada32 initialization: %d\n", init_result);
    } else {
        printf("❌ AdaInitialize not found\n");
    }
    
    // Read input file
    FILE* fp = fopen(input_file, "rb");
    if (!fp) {
        fprintf(stderr, "❌ Cannot open input file: %s\n", input_file);
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
    
    // Get all function pointers
    void* funcs[] = {
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
    
    // Test each function
    for (int i = 0; i < 4; i++) {
        test_function(func_names[i], funcs[i], input_data, input_size);
    }
    
    printf("\n🎯 ANALYSIS COMPLETE\n");
    printf("Look for the function that produced exactly 356 bytes!\n");
    
    free(input_data);
    FreeLibrary(hDll);
    return 0;
}
