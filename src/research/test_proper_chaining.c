/*
 * Test proper function chaining: txt → AdaAssembleAtomStream → AdaNormalizeAtomStream
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaTerminate_t)(void);
typedef const char* (__cdecl *AdaGetErrorText_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(const char* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaNormalizeAtomStream_t)(const char* input, int inputSize, void* output, int* outputSize);

int main() {
    printf("=== Testing Proper Function Chaining ===\n");
    printf("Step 1: .txt → AdaAssembleAtomStream → 413-byte raw\n");
    printf("Step 2: 413-byte raw → AdaNormalizeAtomStream → 356-byte FDO\n\n");
    
    HMODULE hAda32 = LoadLibrary("Ada32.dll");
    if (!hAda32) {
        printf("❌ Failed to load Ada32.dll\n");
        return 1;
    }
    
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hAda32, "AdaInitialize");
    AdaTerminate_t AdaTerminate = (AdaTerminate_t)GetProcAddress(hAda32, "AdaTerminate");
    AdaGetErrorText_t AdaGetErrorText = (AdaGetErrorText_t)GetProcAddress(hAda32, "AdaGetErrorText");
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(hAda32, "AdaAssembleAtomStream");
    AdaNormalizeAtomStream_t AdaNormalizeAtomStream = (AdaNormalizeAtomStream_t)GetProcAddress(hAda32, "AdaNormalizeAtomStream");
    
    printf("Function availability:\n");
    printf("  AdaInitialize: %s\n", AdaInitialize ? "✅" : "❌");
    printf("  AdaAssembleAtomStream: %s\n", AdaAssembleAtomStream ? "✅" : "❌");
    printf("  AdaNormalizeAtomStream: %s\n", AdaNormalizeAtomStream ? "✅" : "❌");
    printf("  AdaGetErrorText: %s\n", AdaGetErrorText ? "✅" : "❌");
    
    if (!AdaInitialize || !AdaAssembleAtomStream) {
        printf("❌ Essential functions missing\n");
        FreeLibrary(hAda32);
        return 1;
    }
    
    // Initialize Ada32
    printf("\n=== Initialization ===\n");
    int init_result = AdaInitialize();
    printf("AdaInitialize(): %d\n", init_result);
    
    if (init_result <= 0) {
        printf("❌ Initialization failed\n");
        FreeLibrary(hAda32);
        return 1;
    }
    
    // Load input text
    printf("\n=== Loading Input ===\n");
    FILE* fp = fopen("clean_32-105.txt", "r");
    if (!fp) {
        printf("❌ Cannot open clean_32-105.txt\n");
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
    
    printf("Loaded %ld bytes from clean_32-105.txt\n", input_size);
    
    // Step 1: .txt → AdaAssembleAtomStream → 413-byte raw
    printf("\n=== Step 1: Compile to Raw Binary ===\n");
    char raw[512];    // 413-byte output buffer
    int rawSize = 512;
    
    int assemble_result = AdaAssembleAtomStream(input_text, (int)input_size, raw, &rawSize);
    printf("AdaAssembleAtomStream: result=%d, size=%d\n", assemble_result, rawSize);
    
    if (AdaGetErrorText) {
        const char* error = AdaGetErrorText();
        if (error && strlen(error) > 0) {
            printf("Error after Step 1: '%s'\n", error);
        }
    }
    
    if (rawSize > 0 && rawSize < 512) {
        printf("✅ Step 1 Success: %d bytes of raw binary\n", rawSize);
        printf("Raw header: ");
        for (int i = 0; i < 16 && i < rawSize; i++) {
            printf("%02x ", (unsigned char)raw[i]);
        }
        printf("\n");
        
        // Save intermediate result
        FILE* raw_fp = fopen("test_output/step1_raw_binary.dat", "wb");
        if (raw_fp) {
            fwrite(raw, 1, rawSize, raw_fp);
            fclose(raw_fp);
            printf("💾 Saved Step 1 result\n");
        }
        
        // Step 2: 413-byte raw → AdaNormalizeAtomStream → 356-byte FDO
        printf("\n=== Step 2: Normalize Raw Binary to FDO ===\n");
        
        if (AdaNormalizeAtomStream) {
            char fdo[512];    // 356-byte target buffer
            int fdoSize = 512;
            
            // Try treating raw binary as text input to AdaNormalizeAtomStream
            int normalize_result = AdaNormalizeAtomStream((const char*)raw, rawSize, fdo, &fdoSize);
            printf("AdaNormalizeAtomStream: result=%d, size=%d\n", normalize_result, fdoSize);
            
            if (AdaGetErrorText) {
                const char* error = AdaGetErrorText();
                if (error && strlen(error) > 0) {
                    printf("Error after Step 2: '%s'\n", error);
                }
            }
            
            if (fdoSize == 356) {
                printf("🏆🏆🏆 SUCCESS! Got 356-byte FDO format! 🏆🏆🏆\n");
                
                printf("FDO header: ");
                for (int i = 0; i < 16; i++) {
                    printf("%02x ", (unsigned char)fdo[i]);
                }
                printf("\n");
                
                // Check for proper FDO format
                if (fdoSize >= 2 && (unsigned char)fdo[0] == 0x40 && (unsigned char)fdo[1] == 0x01) {
                    printf("🎯 Proper FDO format (40 01 header)!\n");
                }
                
                // Save final result
                FILE* fdo_fp = fopen("test_output/FINAL_FDO_RESULT.str", "wb");
                if (fdo_fp) {
                    fwrite(fdo, 1, fdoSize, fdo_fp);
                    fclose(fdo_fp);
                    printf("💾 Saved final FDO result\n");
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
                        for (int i = 0; i < 356; i++) {
                            if (fdo[i] == golden_data[i]) matches++;
                        }
                        
                        printf("\n📊 Golden File Comparison:\n");
                        printf("Accuracy: %d/356 (%.1f%%)\n", matches, (float)matches/356*100);
                        
                        if (matches == 356) {
                            printf("🎉🎉🎉 PERFECT MATCH! COMPILER IS COMPLETE! 🎉🎉🎉\n");
                        } else if (matches > 300) {
                            printf("🎯 Very close! Only %d differences\n", 356 - matches);
                        } else {
                            printf("❌ Significant differences\n");
                        }
                        
                        free(golden_data);
                    }
                    fclose(golden_fp);
                }
            } else if (normalize_result > 0 && fdoSize > 0) {
                printf("⚠️  Step 2 produced %d bytes (not 356)\n", fdoSize);
                
                // Save whatever we got
                FILE* result_fp = fopen("test_output/step2_normalize_result.dat", "wb");
                if (result_fp) {
                    fwrite(fdo, 1, fdoSize, result_fp);
                    fclose(result_fp);
                    printf("💾 Saved Step 2 result (%d bytes)\n", fdoSize);
                }
            } else {
                printf("❌ Step 2 failed or no output\n");
                
                // Try with flags parameter (common in AOL DLLs)
                printf("\n=== Testing with Flags Parameter ===\n");
                for (int flags = 0; flags <= 2; flags++) {
                    fdoSize = 512;
                    
                    // Try signature with flags: (input, inputSize, output, outputSize*, flags)
                    int flag_result = ((int (__cdecl *)(const char*, int, void*, int*, int))AdaNormalizeAtomStream)((const char*)raw, rawSize, fdo, &fdoSize, flags);
                    printf("AdaNormalizeAtomStream (flags=%d): result=%d, size=%d\n", flags, flag_result, fdoSize);
                    
                    if (flag_result > 0 && fdoSize == 356) {
                        printf("🏆 SUCCESS with flags=%d!\n", flags);
                        break;
                    }
                }
            }
        } else {
            printf("❌ AdaNormalizeAtomStream not available\n");
        }
    } else {
        printf("❌ Step 1 failed or no output\n");
    }
    
    // Cleanup
    if (AdaTerminate) {
        int term_result = AdaTerminate();
        printf("\nAdaTerminate(): %d\n", term_result);
    }
    
    free(input_text);
    FreeLibrary(hAda32);
    
    printf("\n=== SUMMARY ===\n");
    printf("Tested proper function chaining approach\n");
    printf("Key insight: Feed 413-byte binary to AdaNormalizeAtomStream\n");
    
    return 0;
}