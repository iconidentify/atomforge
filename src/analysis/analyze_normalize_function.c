/*
 * Detailed analysis of AdaNormalizeAtomStream function
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaNormalizeAtomStream_t)(const char* input, int inputSize, void* output, int* outputSize);
typedef const char* (__cdecl *AdaGetErrorText_t)(void);

int main() {
    printf("=== Detailed Analysis of AdaNormalizeAtomStream ===\n");
    
    HMODULE hStarAda32 = LoadLibrary("star_us_50_32/ADA32.DLL");
    if (!hStarAda32) {
        printf("❌ Failed to load star Ada32\n");
        return 1;
    }
    
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hStarAda32, "AdaInitialize");
    AdaNormalizeAtomStream_t AdaNormalizeAtomStream = (AdaNormalizeAtomStream_t)GetProcAddress(hStarAda32, "AdaNormalizeAtomStream");
    AdaGetErrorText_t AdaGetErrorText = (AdaGetErrorText_t)GetProcAddress(hStarAda32, "AdaGetErrorText");
    
    if (!AdaInitialize || !AdaNormalizeAtomStream) {
        printf("❌ Functions not available\n");
        FreeLibrary(hStarAda32);
        return 1;
    }
    
    // Initialize
    int init_result = AdaInitialize();
    printf("AdaInitialize: %d\n", init_result);
    
    // Load test data
    FILE* fp = fopen("clean_32-105.txt", "r");
    if (!fp) {
        printf("❌ Cannot load test file\n");
        FreeLibrary(hStarAda32);
        return 1;
    }
    
    fseek(fp, 0, SEEK_END);
    long input_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    
    char* input_text = malloc(input_size + 1);
    fread(input_text, 1, input_size, fp);
    input_text[input_size] = 0;
    fclose(fp);
    
    printf("Input: %ld bytes\n", input_size);
    printf("First 100 chars: '%.100s'\n", input_text);
    
    // Test different buffer sizes to understand output
    printf("\n=== Testing Different Buffer Sizes ===\n");
    
    int test_sizes[] = {1000, 2000, 4000, 8000, 16000};
    for (int i = 0; i < 5; i++) {
        int buffer_size = test_sizes[i];
        char* test_buffer = malloc(buffer_size);
        int test_output_size = buffer_size;
        
        printf("\nTesting with %d-byte buffer:\n", buffer_size);
        
        int result = AdaNormalizeAtomStream(input_text, (int)input_size, test_buffer, &test_output_size);
        printf("  Result: %d, Output size: %d\n", result, test_output_size);
        
        if (AdaGetErrorText) {
            const char* error = AdaGetErrorText();
            if (error && strlen(error) > 0) {
                printf("  Error: '%s'\n", error);
            }
        }
        
        if (result > 0 && test_output_size > 0 && test_output_size <= buffer_size) {
            printf("  ✅ Success! Actual output: %d bytes\n", test_output_size);
            
            // Show first 100 bytes as hex
            printf("  First 100 bytes (hex): ");
            for (int j = 0; j < 100 && j < test_output_size; j++) {
                printf("%02x ", (unsigned char)test_buffer[j]);
                if ((j + 1) % 16 == 0) printf("\n                           ");
            }
            printf("\n");
            
            // Show first 100 bytes as text
            printf("  First 100 bytes (text): '");
            for (int j = 0; j < 100 && j < test_output_size; j++) {
                if (test_buffer[j] >= 32 && test_buffer[j] <= 126) {
                    printf("%c", test_buffer[j]);
                } else {
                    printf(".");
                }
            }
            printf("'\n");
            
            // Save this result
            char filename[256];
            sprintf(filename, "test_output/normalize_%d_bytes.dat", test_output_size);
            FILE* save_fp = fopen(filename, "wb");
            if (save_fp) {
                fwrite(test_buffer, 1, test_output_size, save_fp);
                fclose(save_fp);
                printf("  💾 Saved to %s\n", filename);
            }
            
            // Check if this could be our target format
            if (test_output_size == 356) {
                printf("  🏆 PERFECT SIZE! This might be our target!\n");
                
                // Check for FDO format
                if (test_output_size >= 2 && 
                    (unsigned char)test_buffer[0] == 0x40 && 
                    (unsigned char)test_buffer[1] == 0x01) {
                    printf("  🎯 FDO FORMAT DETECTED!\n");
                }
            }
            
            break; // Found working size, no need to test larger ones
        }
        
        free(test_buffer);
    }
    
    // Test with different input types
    printf("\n=== Testing Different Input Types ===\n");
    
    // Test 1: Try with compiled Ada32 output as input
    FILE* ada32_fp = fopen("test_output/clean_AdaAssembleAtomStream.str", "rb");
    if (ada32_fp) {
        printf("\nTesting with Ada32 compiled output as input:\n");
        
        fseek(ada32_fp, 0, SEEK_END);
        int ada32_size = ftell(ada32_fp);
        fseek(ada32_fp, 0, SEEK_SET);
        
        char* ada32_data = malloc(ada32_size);
        fread(ada32_data, 1, ada32_size, ada32_fp);
        fclose(ada32_fp);
        
        printf("  Ada32 input: %d bytes\n", ada32_size);
        
        char normalize_output[4096];
        int normalize_size = sizeof(normalize_output);
        
        int ada32_result = AdaNormalizeAtomStream((const char*)ada32_data, ada32_size, normalize_output, &normalize_size);
        printf("  Result: %d, Output size: %d\n", ada32_result, normalize_size);
        
        if (ada32_result > 0 && normalize_size > 0) {
            if (normalize_size == 356) {
                printf("  🏆 ADA32 INPUT PRODUCES 356 BYTES!\n");
                printf("  🎯 This might be the compression we need!\n");
                
                FILE* compressed_fp = fopen("test_output/ada32_normalized_356.str", "wb");
                if (compressed_fp) {
                    fwrite(normalize_output, 1, normalize_size, compressed_fp);
                    fclose(compressed_fp);
                    printf("  💾 Saved potential compressed result\n");
                }
                
                // Compare with golden file
                FILE* golden_fp = fopen("golden_tests/32-105.str", "rb");
                if (golden_fp) {
                    fseek(golden_fp, 0, SEEK_END);
                    int golden_size = ftell(golden_fp);
                    fseek(golden_fp, 0, SEEK_SET);
                    
                    if (golden_size == 356) {
                        char* golden_data = malloc(golden_size);
                        fread(golden_data, 1, golden_size, golden_fp);
                        
                        int matches = 0;
                        for (int k = 0; k < 356; k++) {
                            if (normalize_output[k] == golden_data[k]) matches++;
                        }
                        
                        printf("  📊 Golden comparison: %d/356 matches (%.1f%%)\n", 
                               matches, (float)matches/356*100);
                        
                        if (matches == 356) {
                            printf("  🎉🎉🎉 PERFECT MATCH! FOUND THE COMPRESSION! 🎉🎉🎉\n");
                        }
                        
                        free(golden_data);
                    }
                    fclose(golden_fp);
                }
            }
        }
        
        free(ada32_data);
    }
    
    free(input_text);
    FreeLibrary(hStarAda32);
    return 0;
}