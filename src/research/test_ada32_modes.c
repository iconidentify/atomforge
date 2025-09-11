/*
 * Test different Ada32.dll calling modes to find production format
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaInitializeWithFlags_t)(int flags);
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int inputSize, void* output, int* outputSize);

int main() {
    printf("=== Testing Ada32.dll Different Calling Modes ===\n");
    
    HMODULE hDll = LoadLibrary("Ada32.dll");
    if (!hDll) {
        fprintf(stderr, "Failed to load Ada32.dll\n");
        return 1;
    }
    
    // Get functions
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hDll, "AdaInitialize");
    AdaInitializeWithFlags_t AdaInitializeWithFlags = (AdaInitializeWithFlags_t)GetProcAddress(hDll, "AdaInitializeWithFlags");
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(hDll, "AdaAssembleAtomStream");
    
    printf("AdaInitialize: %s\n", AdaInitialize ? "✅" : "❌");
    printf("AdaInitializeWithFlags: %s\n", AdaInitializeWithFlags ? "✅" : "❌");
    printf("AdaAssembleAtomStream: %s\n", AdaAssembleAtomStream ? "✅" : "❌");
    
    if (!AdaAssembleAtomStream) {
        printf("Cannot test without AdaAssembleAtomStream\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    // Read test input
    const char* test_input = "uni_start_stream <00x>\nman_start_object <independent, \"Test\">\nmat_object_id <32-1>\nuni_end_stream <00x>";
    int input_size = strlen(test_input);
    
    printf("\nInput: %s\n", test_input);
    printf("Input size: %d bytes\n\n", input_size);
    
    // Test different initialization modes
    int init_modes[] = {0, 1, 2, 3, 4, 5, 0x100, 0x200, 0x400, 0x1000};
    int num_modes = sizeof(init_modes) / sizeof(init_modes[0]);
    
    for (int mode = 0; mode < num_modes + 1; mode++) {
        printf("=== Test %d ===\n", mode);
        
        if (mode == 0) {
            // Standard initialization
            if (AdaInitialize) {
                int result = AdaInitialize();
                printf("AdaInitialize(): %d\n", result);
            }
        } else if (mode <= num_modes && AdaInitializeWithFlags) {
            // Initialize with different flags
            int flag = init_modes[mode - 1];
            int result = AdaInitializeWithFlags(flag);
            printf("AdaInitializeWithFlags(%d): %d\n", flag, result);
        } else {
            continue;
        }
        
        // Test different buffer sizes that might trigger production mode
        int buffer_sizes[] = {356, 512, 1024};
        int num_sizes = sizeof(buffer_sizes) / sizeof(buffer_sizes[0]);
        
        for (int i = 0; i < num_sizes; i++) {
            int max_output_size = buffer_sizes[i];
            char* output_data = malloc(max_output_size);
            int output_size = max_output_size;
            
            int result = AdaAssembleAtomStream(test_input, input_size, output_data, &output_size);
            
            printf("  Buffer %d: result=%d, output_size=%d", max_output_size, result, output_size);
            
            if (result == 0 && output_size > 0) {
                // Check for FDO header
                if (output_size >= 2 && (unsigned char)output_data[0] == 0x40 && (unsigned char)output_data[1] == 0x01) {
                    printf(" -> 🎯 FDO FORMAT!");
                    if (output_size == 356) {
                        printf(" 🎉 PRODUCTION SIZE!");
                    }
                } else {
                    printf(" -> bytes: ");
                    int show = (output_size > 8) ? 8 : output_size;
                    for (int j = 0; j < show; j++) {
                        printf("%02x ", (unsigned char)output_data[j]);
                    }
                }
            }
            printf("\n");
            
            free(output_data);
        }
        
        printf("\n");
    }
    
    FreeLibrary(hDll);
    return 0;
}