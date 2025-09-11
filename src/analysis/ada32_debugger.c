/*
 * Debug why Ada32.dll is failing on golden test files
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int size, void* output, int* outSize);
typedef int (__cdecl *AdaGetErrorText_t)(int code, char* buf, int bufSize);

int main(int argc, char* argv[]) {
    if (argc != 2) {
        printf("Usage: %s <input_file>\n", argv[0]);
        return 1;
    }
    
    printf("🔍 Debug Ada32.dll Issue\n");
    printf("========================\n");
    printf("Input: %s\n", argv[1]);
    
    // Load Ada32.dll
    HMODULE ada32 = LoadLibraryA("bin/dlls/Ada32.dll");
    if (!ada32) {
        printf("❌ Failed to load bin/dlls/Ada32.dll\n");
        return 1;
    }
    printf("✅ Ada32.dll loaded\n");
    
    // Get function pointers
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(ada32, "AdaInitialize");
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(ada32, "AdaAssembleAtomStream");
    AdaGetErrorText_t AdaGetErrorText = (AdaGetErrorText_t)GetProcAddress(ada32, "AdaGetErrorText");
    
    if (!AdaInitialize || !AdaAssembleAtomStream) {
        printf("❌ Required functions not found\n");
        FreeLibrary(ada32);
        return 1;
    }
    printf("✅ Functions found\n");
    
    // Initialize Ada32
    int init_result = AdaInitialize();
    printf("AdaInitialize(): %d\n", init_result);
    
    if (init_result != 1) {
        printf("❌ Initialization failed\n");
        FreeLibrary(ada32);
        return 1;
    }
    
    // Read input file
    FILE* fp = fopen(argv[1], "r");
    if (!fp) {
        printf("❌ Cannot open input file: %s\n", argv[1]);
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
    
    printf("✅ Read %ld bytes\n", input_size);
    
    // Show first few lines
    printf("\n📄 First 200 characters:\n");
    for (int i = 0; i < 200 && i < input_size; i++) {
        if (input_data[i] >= 32 && input_data[i] <= 126) {
            printf("%c", input_data[i]);
        } else if (input_data[i] == '\n') {
            printf("\\n\n");
        } else if (input_data[i] == '\r') {
            printf("\\r");
        } else {
            printf("[%02x]", (unsigned char)input_data[i]);
        }
    }
    printf("\n\n");
    
    // Try compilation
    printf("🔄 Attempting compilation...\n");
    char output_buffer[1024];
    int output_size = sizeof(output_buffer);
    
    int result = AdaAssembleAtomStream(input_data, (int)input_size, output_buffer, &output_size);
    printf("AdaAssembleAtomStream result: %d\n", result);
    printf("Output size: %d\n", output_size);
    
    // Get detailed error information
    if (result != 0) {
        printf("\n❌ Compilation failed with error code: %d\n", result);
        
        if (AdaGetErrorText) {
            char error_buffer[512] = {0};
            int error_result = AdaGetErrorText(result, error_buffer, sizeof(error_buffer));
            printf("AdaGetErrorText result: %d\n", error_result);
            printf("Error message: '%s'\n", error_buffer);
        }
        
        // Try common error codes
        printf("\nTesting common error codes:\n");
        for (int code = 0; code <= 10; code++) {
            if (AdaGetErrorText) {
                char test_buffer[256] = {0};
                AdaGetErrorText(code, test_buffer, sizeof(test_buffer));
                if (strlen(test_buffer) > 0) {
                    printf("  Code %d: '%s'\n", code, test_buffer);
                }
            }
        }
    } else {
        printf("✅ Compilation successful! %d bytes generated\n", output_size);
        
        // Show output header
        printf("Output header: ");
        for (int i = 0; i < 16 && i < output_size; i++) {
            printf("%02x ", (unsigned char)output_buffer[i]);
        }
        printf("\n");
    }
    
    free(input_data);
    FreeLibrary(ada32);
    
    return 0;
}