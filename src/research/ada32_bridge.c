/*
 * Ada32 Bridge - Simple C program to call Ada32.dll functions
 * Compile with: i686-w64-mingw32-gcc -o ada32_bridge.exe ada32_bridge.c
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaAssembleFragment_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaNormalizeAtomStream_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaDisassembleAtomStream_t)(void* input, int inputSize);
typedef int (__cdecl *AdaGetErrorText_t)(int errorCode, char* buffer, int bufferSize);
typedef int (__cdecl *AdaLookupAtomEnum_t)(const char* atomName);

int main(int argc, char* argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: ada32_bridge.exe <command> [args...]\n");
        return 1;
    }
    
    char* command = argv[1];
    
    // Load Ada32.dll
    HMODULE hDll = LoadLibrary("Ada32.dll");
    if (!hDll) {
        fprintf(stderr, "ERROR: Failed to load Ada32.dll\n");
        return 1;
    }
    
    // Get function pointers
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hDll, "AdaInitialize");
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(hDll, "AdaAssembleAtomStream");
    AdaAssembleFragment_t AdaAssembleFragment = (AdaAssembleFragment_t)GetProcAddress(hDll, "AdaAssembleFragment");
    AdaNormalizeAtomStream_t AdaNormalizeAtomStream = (AdaNormalizeAtomStream_t)GetProcAddress(hDll, "AdaNormalizeAtomStream");
    
    if (!AdaInitialize || !AdaAssembleAtomStream || !AdaNormalizeAtomStream) {
        fprintf(stderr, "ERROR: Failed to get Ada32.dll function pointers\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    // Initialize Ada32
    int init_result = AdaInitialize();
    if (init_result == 0) {
        fprintf(stderr, "ERROR: Ada32 initialization failed\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    if (strcmp(command, "test") == 0) {
        fprintf(stderr, "SUCCESS: Ada32.dll loaded and initialized\n");
        
        printf("\n=== Ada32 DLL Function Explorer ===\n");
        
        // Test AdaGetErrorText
        AdaGetErrorText_t AdaGetErrorText = (AdaGetErrorText_t)GetProcAddress(hDll, "AdaGetErrorText");
        if (AdaGetErrorText) {
            char buffer[256];
            memset(buffer, 0, sizeof(buffer));
            int result = AdaGetErrorText(0, buffer, sizeof(buffer));
            printf("AdaGetErrorText(0): result=%d, text='%s'\n", result, buffer);
            
            for (int i = 1; i <= 3; i++) {
                memset(buffer, 0, sizeof(buffer));
                result = AdaGetErrorText(i, buffer, sizeof(buffer));
                printf("AdaGetErrorText(%d): result=%d, text='%s'\n", i, result, buffer);
            }
        } else {
            printf("AdaGetErrorText: NOT FOUND\n");
        }
        
        // Test AdaLookupAtomEnum
        AdaLookupAtomEnum_t AdaLookupAtomEnum = (AdaLookupAtomEnum_t)GetProcAddress(hDll, "AdaLookupAtomEnum");
        if (AdaLookupAtomEnum) {
            const char* test_atoms[] = {"uni_start_stream", "uni_end_stream", "man_start_object", "invalid_atom", NULL};
            for (int i = 0; test_atoms[i] != NULL; i++) {
                int result = AdaLookupAtomEnum(test_atoms[i]);
                printf("AdaLookupAtomEnum('%s'): result=%d\n", test_atoms[i], result);
            }
        } else {
            printf("AdaLookupAtomEnum: NOT FOUND\n");
        }
        
        FreeLibrary(hDll);
        return 0;
    }
    
    if (strcmp(command, "disassemble") == 0) {
        if (argc < 3) {
            fprintf(stderr, "Usage: ada32_bridge.exe disassemble <input_file>\n");
            FreeLibrary(hDll);
            return 1;
        }
        
        char* input_file = argv[2];
        
        // Read input file
        FILE* fp = fopen(input_file, "rb");
        if (!fp) {
            fprintf(stderr, "ERROR: Cannot open input file: %s\n", input_file);
            FreeLibrary(hDll);
            return 1;
        }
        
        // Get file size
        fseek(fp, 0, SEEK_END);
        long input_size = ftell(fp);
        fseek(fp, 0, SEEK_SET);
        
        // Read file data
        char* input_data = malloc(input_size);
        fread(input_data, 1, input_size, fp);
        fclose(fp);
        
        // Get function pointer for disassemble
        AdaDisassembleAtomStream_t AdaDisassembleAtomStream = (AdaDisassembleAtomStream_t)GetProcAddress(hDll, "AdaDisassembleAtomStream");
        if (!AdaDisassembleAtomStream) {
            fprintf(stderr, "ERROR: Failed to get AdaDisassembleAtomStream function\n");
            free(input_data);
            FreeLibrary(hDll);
            return 1;
        }
        
        // Call Ada32 disassembly function
        int result = AdaDisassembleAtomStream(input_data, input_size);
        
        fprintf(stderr, "DEBUG_DISASSEMBLE: input_size=%ld, result=%d\n", input_size, result);
        fprintf(stderr, "SUCCESS: Disassembled %d bytes\n", result);
        
        free(input_data);
        FreeLibrary(hDll);
        return 0;
    }
    
    if (strcmp(command, "normalize") == 0) {
        if (argc < 3) {
            fprintf(stderr, "Usage: ada32_bridge.exe normalize <input_file>\n");
            FreeLibrary(hDll);
            return 1;
        }
        
        char* input_file = argv[2];
        
        // Read input file
        FILE* fp = fopen(input_file, "rb");
        if (!fp) {
            fprintf(stderr, "ERROR: Cannot open input file: %s\n", input_file);
            FreeLibrary(hDll);
            return 1;
        }
        
        // Get file size
        fseek(fp, 0, SEEK_END);
        long input_size = ftell(fp);
        fseek(fp, 0, SEEK_SET);
        
        // Read file data
        char* input_data = malloc(input_size + 1);
        fread(input_data, 1, input_size, fp);
        input_data[input_size] = '\0';
        fclose(fp);
        
        // Prepare output buffer
        int max_output_size = input_size * 4;
        char* output_data = malloc(max_output_size);
        int output_size = max_output_size;
        
        // Call Ada32 normalize function
        int result = AdaNormalizeAtomStream(input_data, input_size, output_data, &output_size);
        
        fprintf(stderr, "DEBUG: NORMALIZE input_size=%ld, max_output_size=%d, result=%d, output_size=%d\n", 
                input_size, max_output_size, result, output_size);
        
        if (result > 0) {
            // Write only the normalized binary data to stdout
            fwrite(output_data, 1, result, stdout);
            fflush(stdout);  // Ensure all data is written
            fprintf(stderr, "SUCCESS: Normalized %d bytes\n", result);
            
            free(input_data);
            free(output_data);
            FreeLibrary(hDll);
            return 0;
        } else {
            fprintf(stderr, "ERROR: Ada32 normalize failed with result: %d\n", result);
            free(input_data);
            free(output_data);
            FreeLibrary(hDll);
            return 1;
        }
    }
    
    if (strcmp(command, "fragment") == 0) {
        if (argc < 3) {
            fprintf(stderr, "Usage: ada32_bridge.exe fragment <input_file>\n");
            FreeLibrary(hDll);
            return 1;
        }
        
        char* input_file = argv[2];
        
        // Read input file
        FILE* fp = fopen(input_file, "rb");
        if (!fp) {
            fprintf(stderr, "ERROR: Cannot open input file: %s\n", input_file);
            FreeLibrary(hDll);
            return 1;
        }
        
        // Get file size
        fseek(fp, 0, SEEK_END);
        long input_size = ftell(fp);
        fseek(fp, 0, SEEK_SET);
        
        // Read file data
        char* input_data = malloc(input_size + 1);
        fread(input_data, 1, input_size, fp);
        input_data[input_size] = '\0';
        fclose(fp);
        
        // Prepare output buffer
        int max_output_size = input_size * 4;
        char* output_data = malloc(max_output_size);
        int output_size = max_output_size;
        
        // Call Ada32 fragment function
        int result = AdaAssembleFragment(input_data, input_size, output_data, &output_size);
        
        fprintf(stderr, "DEBUG_FRAGMENT: input_size=%ld, result=%d, output_size=%d\n", 
                input_size, result, output_size);
        
        if (result > 0) {
            // Extract the assembled binary data
            int actual_size = (result < output_size) ? result : output_size;
            fwrite(output_data, 1, actual_size, stdout);
            fflush(stdout);  // Ensure all data is written
            fprintf(stderr, "SUCCESS: Fragment assembled %d bytes\n", actual_size);
            
            free(input_data);
            free(output_data);
            FreeLibrary(hDll);
            return 0;
        } else {
            fprintf(stderr, "ERROR: Ada32 fragment failed with result: %d\n", result);
            free(input_data);
            free(output_data);
            FreeLibrary(hDll);
            return 1;
        }
    }
    
    if (strcmp(command, "assemble") == 0) {
        if (argc < 3) {
            fprintf(stderr, "Usage: ada32_bridge.exe assemble <input_file>\n");
            FreeLibrary(hDll);
            return 1;
        }
        
        char* input_file = argv[2];
        
        // Read input file
        FILE* fp = fopen(input_file, "rb");
        if (!fp) {
            fprintf(stderr, "ERROR: Cannot open input file: %s\n", input_file);
            FreeLibrary(hDll);
            return 1;
        }
        
        // Get file size
        fseek(fp, 0, SEEK_END);
        long input_size = ftell(fp);
        fseek(fp, 0, SEEK_SET);
        
        // Read file data
        char* input_data = malloc(input_size + 1);
        fread(input_data, 1, input_size, fp);
        input_data[input_size] = '\0';
        fclose(fp);
        
        // Prepare output buffer
        int max_output_size = input_size * 4;
        char* output_data = malloc(max_output_size);
        int output_size = max_output_size;
        
        // Call Ada32 assembly function
        int result = AdaAssembleAtomStream(input_data, input_size, output_data, &output_size);
        
        // Write debug info to file (stderr gets lost in Wine crash)
        FILE* debug_fp = fopen("bridge_debug.txt", "w");
        if (debug_fp) {
            fprintf(debug_fp, "DEBUG: input_size=%ld, max_output_size=%d, result=%d, output_size=%d\n", 
                    input_size, max_output_size, result, output_size);
            fclose(debug_fp);
        }
        
        fprintf(stderr, "DEBUG: input_size=%ld, max_output_size=%d, result=%d, output_size=%d\n", 
                input_size, max_output_size, result, output_size);
        
        if (result > 0) {
            // Extract the assembled binary data
            // Use minimum of result and output_size as actual size (matching Windows interface)
            int actual_size = (result < output_size) ? result : output_size;
            fwrite(output_data, 1, actual_size, stdout);
            fflush(stdout);  // Ensure all data is written
            fprintf(stderr, "SUCCESS: Assembled %d bytes (result=%d, output_size=%d, actual=%d)\n", actual_size, result, output_size, actual_size);
            
            free(input_data);
            free(output_data);
            FreeLibrary(hDll);
            return 0;
        } else {
            fprintf(stderr, "ERROR: Ada32 assembly failed with result: %d\n", result);
            free(input_data);
            free(output_data);
            FreeLibrary(hDll);
            return 1;
        }
    }
    
    if (strcmp(command, "explore") == 0) {
        printf("=== Ada32 DLL Function Explorer ===\n");
        
        // Test AdaGetErrorText
        AdaGetErrorText_t AdaGetErrorText = (AdaGetErrorText_t)GetProcAddress(hDll, "AdaGetErrorText");
        if (AdaGetErrorText) {
            char buffer[256];
            memset(buffer, 0, sizeof(buffer));
            int result = AdaGetErrorText(0, buffer, sizeof(buffer));
            printf("AdaGetErrorText(0): result=%d, text='%s'\n", result, buffer);
            
            for (int i = 1; i <= 3; i++) {
                memset(buffer, 0, sizeof(buffer));
                result = AdaGetErrorText(i, buffer, sizeof(buffer));
                printf("AdaGetErrorText(%d): result=%d, text='%s'\n", i, result, buffer);
            }
        } else {
            printf("AdaGetErrorText: NOT FOUND\n");
        }
        
        // Test AdaLookupAtomEnum
        AdaLookupAtomEnum_t AdaLookupAtomEnum = (AdaLookupAtomEnum_t)GetProcAddress(hDll, "AdaLookupAtomEnum");
        if (AdaLookupAtomEnum) {
            const char* test_atoms[] = {"uni_start_stream", "uni_end_stream", "man_start_object", "invalid_atom", NULL};
            for (int i = 0; test_atoms[i] != NULL; i++) {
                int result = AdaLookupAtomEnum(test_atoms[i]);
                printf("AdaLookupAtomEnum('%s'): result=%d\n", test_atoms[i], result);
            }
        } else {
            printf("AdaLookupAtomEnum: NOT FOUND\n");
        }
        
        // Test AdaNormalizeAtomStream with simple input
        if (AdaNormalizeAtomStream) {
            const char* test_input = "uni_start_stream <00x>\nuni_end_stream <00x>";
            int input_size = strlen(test_input);
            int max_output_size = input_size * 4;
            char* output_data = malloc(max_output_size);
            int output_size = max_output_size;
            
            int result = AdaNormalizeAtomStream((void*)test_input, input_size, output_data, &output_size);
            printf("AdaNormalizeAtomStream: input_size=%d, result=%d, output_size=%d\n", input_size, result, output_size);
            
            if (result > 0) {
                printf("Output preview: ");
                int preview_size = (result < 50) ? result : 50;
                for (int i = 0; i < preview_size; i++) {
                    printf("%02x ", (unsigned char)output_data[i]);
                }
                printf("\n");
            }
            
            free(output_data);
        } else {
            printf("AdaNormalizeAtomStream: NOT FOUND\n");
        }
        
        // Test disassemble on golden file
        FILE* fp = fopen("golden_tests/32-105.str", "rb");
        if (fp) {
            fseek(fp, 0, SEEK_END);
            long file_size = ftell(fp);
            fseek(fp, 0, SEEK_SET);
            
            char* binary_data = malloc(file_size);
            fread(binary_data, 1, file_size, fp);
            fclose(fp);
            
            AdaDisassembleAtomStream_t AdaDisassembleAtomStream = (AdaDisassembleAtomStream_t)GetProcAddress(hDll, "AdaDisassembleAtomStream");
            if (AdaDisassembleAtomStream) {
                int result = AdaDisassembleAtomStream(binary_data, file_size);
                printf("AdaDisassembleAtomStream(golden): input_size=%ld, result=%d\n", file_size, result);
            }
            
            free(binary_data);
        }
        
        FreeLibrary(hDll);
        return 0;
    }
    
    fprintf(stderr, "ERROR: Unknown command: %s\n", command);
    FreeLibrary(hDll);
    return 1;
}