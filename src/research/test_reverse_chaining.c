/*
 * Test reverse chaining: txt → AdaNormalizeAtomStream → AdaAssembleAtomStream
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(const char* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaNormalizeAtomStream_t)(const char* input, int inputSize, void* output, int* outputSize);
typedef const char* (__cdecl *AdaGetErrorText_t)(void);

int main() {
    printf("=== Testing Reverse Chaining ===\n");
    printf("Step 1: .txt → AdaNormalizeAtomStream → ~3186 bytes (expanded)\n");
    printf("Step 2: ~3186 bytes → AdaAssembleAtomStream → hopefully 356 bytes!\n\n");
    
    HMODULE hAda32 = LoadLibrary("Ada32.dll");
    if (!hAda32) {
        printf("❌ Failed to load Ada32.dll\n");
        return 1;
    }
    
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hAda32, "AdaInitialize");
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(hAda32, "AdaAssembleAtomStream");
    AdaNormalizeAtomStream_t AdaNormalizeAtomStream = (AdaNormalizeAtomStream_t)GetProcAddress(hAda32, "AdaNormalizeAtomStream");
    AdaGetErrorText_t AdaGetErrorText = (AdaGetErrorText_t)GetProcAddress(hAda32, "AdaGetErrorText");
    
    if (!AdaInitialize || !AdaAssembleAtomStream || !AdaNormalizeAtomStream) {
        printf("❌ Essential functions missing\n");
        FreeLibrary(hAda32);
        return 1;
    }
    
    // Initialize
    AdaInitialize();
    printf("✅ Ada32 initialized\n");
    
    // Load test data
    FILE* fp = fopen("clean_32-105.txt", "r");
    if (!fp) {
        printf("❌ Cannot load test file\n");
        FreeLibrary(hAda32);
        return 1;
    }
    
    fseek(fp, 0, SEEK_END);
    long input_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    char* input_text = malloc(input_size + 1);
    fread(input_text, 1, input_size, fp);
    input_text[input_size] = 0;
    fclose(fp);
    
    printf("✅ Loaded %ld bytes input\n", input_size);
    
    // Step 1: .txt → AdaNormalizeAtomStream (expand/normalize)
    printf("\n=== Step 1: Normalize/Expand ===\n");
    char* normalized = malloc(8192);  // Larger buffer for 3186+ bytes
    int normalizedSize = 8192;
    
    int normalize_result = AdaNormalizeAtomStream(input_text, (int)input_size, normalized, &normalizedSize);
    printf("AdaNormalizeAtomStream: result=%d, size=%d\n", normalize_result, normalizedSize);
    
    if (AdaGetErrorText) {
        const char* error = AdaGetErrorText();
        if (error && strlen(error) > 0) {
            printf("Error after Step 1: '%s'\n", error);
        }
    }
    
    if (normalizedSize > 0 && normalizedSize < 8192) {
        printf("✅ Step 1 Success: %d bytes normalized data\n", normalizedSize);
        
        // Show first part of normalized data
        printf("Normalized header: ");
        for (int i = 0; i < 16 && i < normalizedSize; i++) {
            printf("%02x ", (unsigned char)normalized[i]);
        }
        printf("\n");
        
        printf("Normalized text preview: '%.100s'\n", normalized);
        
        // Save intermediate result
        FILE* norm_fp = fopen("test_output/step1_normalized.dat", "wb");
        if (norm_fp) {
            fwrite(normalized, 1, normalizedSize, norm_fp);
            fclose(norm_fp);
            printf("💾 Saved Step 1 normalized result\n");
        }
        
        // Step 2: normalized → AdaAssembleAtomStream (compress)
        printf("\n=== Step 2: Assemble from Normalized Data ===\n");
        char final_output[1024];
        int finalSize = sizeof(final_output);
        
        int assemble_result = AdaAssembleAtomStream(normalized, normalizedSize, final_output, &finalSize);
        printf("AdaAssembleAtomStream: result=%d, size=%d\n", assemble_result, finalSize);
        
        if (AdaGetErrorText) {
            const char* error = AdaGetErrorText();
            if (error && strlen(error) > 0) {
                printf("Error after Step 2: '%s'\n", error);
            }
        }
        
        if (finalSize > 0) {
            printf("✅ Step 2 Success: %d bytes final output\n", finalSize);
            
            printf("Final header: ");
            for (int i = 0; i < 16 && i < finalSize; i++) {
                printf("%02x ", (unsigned char)final_output[i]);
            }
            printf("\n");
            
            if (finalSize == 356) {
                printf("🏆🏆🏆 BREAKTHROUGH! Got 356-byte target! 🏆🏆🏆\n");
                
                // Check for FDO format
                if (finalSize >= 2 && (unsigned char)final_output[0] == 0x40 && (unsigned char)final_output[1] == 0x01) {
                    printf("🎯 Perfect FDO format (40 01 header)!\n");
                } else if ((unsigned char)final_output[0] == 0x00 && (unsigned char)final_output[1] == 0x01) {
                    printf("📊 Raw format (00 01 header)\n");
                }
                
                // Save final result
                FILE* final_fp = fopen("test_output/REVERSE_CHAIN_SUCCESS.str", "wb");
                if (final_fp) {
                    fwrite(final_output, 1, finalSize, final_fp);
                    fclose(final_fp);
                    printf("💾 Saved reverse chain result\n");
                }
                
                // Compare with golden file
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
                            if (final_output[i] == golden_data[i]) matches++;
                        }
                        
                        printf("\n📊 Golden File Comparison:\n");
                        printf("Accuracy: %d/356 (%.1f%%)\n", matches, (float)matches/356*100);
                        
                        if (matches == 356) {
                            printf("🎉🎉🎉 PERFECT MATCH! REVERSE CHAINING IS THE SOLUTION! 🎉🎉🎉\n");
                            printf("🏆 COMPLETE .txt TO .str COMPILER ACHIEVED! 🏆\n");
                        } else if (matches > 300) {
                            printf("🎯 Very close! Only %d byte differences\n", 356 - matches);
                        }
                        
                        free(golden_data);
                    }
                    fclose(golden_fp);
                }
            } else if (finalSize == 413) {
                printf("⚠️  Got 413 bytes (standard format, not compressed)\n");
            } else {
                printf("📊 Got %d bytes (unexpected size)\n", finalSize);
            }
            
            // Save whatever we got
            FILE* result_fp = fopen("test_output/reverse_chain_result.str", "wb");
            if (result_fp) {
                fwrite(final_output, 1, finalSize, result_fp);
                fclose(result_fp);
                printf("💾 Saved reverse chain result (%d bytes)\n", finalSize);
            }
        } else {
            printf("❌ Step 2 failed or no output\n");
        }
    } else {
        printf("❌ Step 1 failed - no normalized data\n");
    }
    
    free(input_text);
    free(normalized);
    FreeLibrary(hAda32);
    
    printf("\n=== REVERSE CHAINING SUMMARY ===\n");
    printf("Tested: txt → normalize → assemble\n");
    printf("This approach could be the key to 356-byte compression!\n");
    
    return 0;
}