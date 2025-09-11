/*
 * Simple test of function chaining concept
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(const char* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaNormalizeAtomStream_t)(const char* input, int inputSize, void* output, int* outputSize);

int main() {
    printf("=== Simple Function Chaining Test ===\n");
    
    HMODULE hAda32 = LoadLibrary("Ada32.dll");
    if (!hAda32) {
        printf("❌ Failed to load Ada32.dll\n");
        return 1;
    }
    
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hAda32, "AdaInitialize");
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(hAda32, "AdaAssembleAtomStream");
    AdaNormalizeAtomStream_t AdaNormalizeAtomStream = (AdaNormalizeAtomStream_t)GetProcAddress(hAda32, "AdaNormalizeAtomStream");
    
    if (!AdaInitialize || !AdaAssembleAtomStream) {
        printf("❌ Functions missing\n");
        FreeLibrary(hAda32);
        return 1;
    }
    
    // Initialize
    AdaInitialize();
    printf("✅ Initialized\n");
    
    // Load test data
    FILE* fp = fopen("clean_32-105.txt", "r");
    fseek(fp, 0, SEEK_END);
    long input_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    char* input_text = malloc(input_size + 1);
    fread(input_text, 1, input_size, fp);
    input_text[input_size] = 0;
    fclose(fp);
    
    printf("✅ Loaded %ld bytes input\n", input_size);
    
    // Step 1: txt → AssembleAtomStream
    char raw[512];
    int rawSize = 512;
    AdaAssembleAtomStream(input_text, (int)input_size, raw, &rawSize);
    printf("Step 1: %d bytes raw binary\n", rawSize);
    
    if (rawSize == 413) {
        printf("✅ Step 1 produced expected 413 bytes\n");
        
        // Step 2: raw binary → NormalizeAtomStream  
        if (AdaNormalizeAtomStream) {
            char fdo[512];
            int fdoSize = 512;
            
            int normalize_result = AdaNormalizeAtomStream((const char*)raw, rawSize, fdo, &fdoSize);
            printf("Step 2: result=%d, size=%d\n", normalize_result, fdoSize);
            
            if (fdoSize == 356) {
                printf("🏆 SUCCESS! Got 356-byte result!\n");
                
                // Save result
                FILE* final_fp = fopen("test_output/chained_result.str", "wb");
                if (final_fp) {
                    fwrite(fdo, 1, fdoSize, final_fp);
                    fclose(final_fp);
                    printf("💾 Saved chained result\n");
                }
                
                // Quick comparison
                FILE* golden_fp = fopen("golden_tests/32-105.str", "rb");
                if (golden_fp) {
                    fseek(golden_fp, 0, SEEK_END);
                    int golden_size = ftell(golden_fp);
                    if (golden_size == 356) {
                        fseek(golden_fp, 0, SEEK_SET);
                        char* golden_data = malloc(356);
                        fread(golden_data, 1, 356, golden_fp);
                        
                        int matches = 0;
                        for (int i = 0; i < 356; i++) {
                            if (fdo[i] == golden_data[i]) matches++;
                        }
                        printf("Accuracy: %d/356 (%.1f%%)\n", matches, (float)matches/356*100);
                        
                        if (matches == 356) {
                            printf("🎉🎉🎉 PERFECT MATCH! 🎉🎉🎉\n");
                        }
                        
                        free(golden_data);
                    }
                    fclose(golden_fp);
                }
            } else if (fdoSize > 0) {
                printf("Got %d bytes (not 356)\n", fdoSize);
            } else {
                printf("❌ Step 2 failed\n");
            }
        } else {
            printf("❌ AdaNormalizeAtomStream not available\n");
        }
    } else {
        printf("❌ Step 1 produced %d bytes (not 413)\n", rawSize);
    }
    
    free(input_text);
    FreeLibrary(hAda32);
    return 0;
}