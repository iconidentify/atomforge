/*
 * Simple test of reverse chaining concept
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(const char* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaNormalizeAtomStream_t)(const char* input, int inputSize, void* output, int* outputSize);

int main() {
    printf("=== Simple Reverse Chaining Test ===\n");
    
    HMODULE hAda32 = LoadLibrary("Ada32.dll");
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hAda32, "AdaInitialize");
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(hAda32, "AdaAssembleAtomStream");
    AdaNormalizeAtomStream_t AdaNormalizeAtomStream = (AdaNormalizeAtomStream_t)GetProcAddress(hAda32, "AdaNormalizeAtomStream");
    
    AdaInitialize();
    
    // Load input
    FILE* fp = fopen("clean_32-105.txt", "r");
    fseek(fp, 0, SEEK_END);
    long size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    char* input = malloc(size + 1);
    fread(input, 1, size, fp);
    input[size] = 0;
    fclose(fp);
    
    printf("Input: %ld bytes\n", size);
    
    // Step 1: txt → normalize
    char* normalized = malloc(8192);
    int norm_size = 8192;
    AdaNormalizeAtomStream(input, (int)size, normalized, &norm_size);
    printf("Step 1 - Normalized: %d bytes\n", norm_size);
    
    if (norm_size > 0 && norm_size < 8192) {
        // Step 2: normalized → assemble
        char final[1024];
        int final_size = 1024;
        AdaAssembleAtomStream(normalized, norm_size, final, &final_size);
        printf("Step 2 - Final: %d bytes\n", final_size);
        
        if (final_size == 356) {
            printf("🏆 SUCCESS! Got 356 bytes!\n");
            
            FILE* success_fp = fopen("test_output/reverse_success.str", "wb");
            if (success_fp) {
                fwrite(final, 1, final_size, success_fp);
                fclose(success_fp);
                printf("💾 Saved 356-byte result\n");
            }
            
            // Quick header check
            printf("Header: ");
            for (int i = 0; i < 8; i++) {
                printf("%02x ", (unsigned char)final[i]);
            }
            printf("\n");
            
        } else {
            printf("Got %d bytes (not 356)\n", final_size);
        }
    } else {
        printf("Step 1 failed: %d bytes\n", norm_size);
    }
    
    free(input);
    free(normalized);
    FreeLibrary(hAda32);
    return 0;
}