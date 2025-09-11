/*
 * Refined Ada32.dll chaining with correct binary input signatures and flags
 */
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int size, void* output, int* outSize);
typedef int (__cdecl *AdaNormalizeAtomStream_t)(void* input, int size, void* output, int* outSize);
typedef int (__cdecl *AdaNormalizeAtomStreamFlags_t)(void* input, int size, void* output, int* outSize, int flags);
typedef int (__cdecl *AdaGetErrorText_t)(int code, char* buf, int bufSize);
typedef const char* (__cdecl *AdaGetErrorTextSimple_t)(void);

int main() {
    printf("=== Refined Ada32.dll Chaining with Binary Signatures ===\n");
    
    HMODULE ada32 = LoadLibraryA("Ada32.dll");
    if (!ada32) {
        printf("❌ Failed to load Ada32.dll\n");
        return 1;
    }
    
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(ada32, "AdaInitialize");
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(ada32, "AdaAssembleAtomStream");
    AdaNormalizeAtomStream_t AdaNormalizeAtomStream = (AdaNormalizeAtomStream_t)GetProcAddress(ada32, "AdaNormalizeAtomStream");
    AdaGetErrorText_t AdaGetErrorText = (AdaGetErrorText_t)GetProcAddress(ada32, "AdaGetErrorText");
    AdaGetErrorTextSimple_t AdaGetErrorTextSimple = (AdaGetErrorTextSimple_t)GetProcAddress(ada32, "AdaGetErrorText");
    
    printf("Function availability:\n");
    printf("  AdaInitialize: %s\n", AdaInitialize ? "✅" : "❌");
    printf("  AdaAssembleAtomStream: %s\n", AdaAssembleAtomStream ? "✅" : "❌");
    printf("  AdaNormalizeAtomStream: %s\n", AdaNormalizeAtomStream ? "✅" : "❌");
    printf("  AdaGetErrorText: %s\n", AdaGetErrorText ? "✅" : "❌");
    
    if (!AdaInitialize || !AdaAssembleAtomStream || !AdaNormalizeAtomStream) {
        printf("❌ Essential functions missing\n");
        FreeLibrary(ada32);
        return 1;
    }
    
    // Initialize Ada32
    printf("\n=== Initialization ===\n");
    int init_result = AdaInitialize();
    printf("AdaInitialize(): %d\n", init_result);
    
    if (init_result != 1) {
        char errBuf[256] = {0};
        if (AdaGetErrorText) {
            AdaGetErrorText(0, errBuf, 256);
            printf("Init failed: %s\n", errBuf);
        }
        FreeLibrary(ada32);
        return 1;
    }
    
    // Load test input
    printf("\n=== Loading Input ===\n");
    FILE* fp = fopen("clean_32-105.txt", "r");
    if (!fp) {
        printf("❌ Cannot open clean_32-105.txt\n");
        FreeLibrary(ada32);
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
    
    // Step 1: Text → AdaAssembleAtomStream → 413-byte binary
    printf("\n=== Step 1: Assemble to Binary ===\n");
    char raw[512] = {0};
    int rawSize = 512;
    
    int assemble_result = AdaAssembleAtomStream(input_text, (int)input_size, raw, &rawSize);
    printf("AdaAssembleAtomStream: result=%d, size=%d\n", assemble_result, rawSize);
    
    if (assemble_result != 0) {
        char errBuf[256] = {0};
        if (AdaGetErrorText) {
            AdaGetErrorText(assemble_result, errBuf, 256);
            printf("Assemble failed: %s\n", errBuf);
        } else if (AdaGetErrorTextSimple) {
            const char* error = AdaGetErrorTextSimple();
            if (error) printf("Error: %s\n", error);
        }
        FreeLibrary(ada32);
        return 1;
    }
    
    if (rawSize <= 0) {
        printf("❌ No binary output from Step 1\n");
        FreeLibrary(ada32);
        return 1;
    }
    
    printf("✅ Step 1 Success: %d bytes binary\n", rawSize);
    printf("Binary header: ");
    for (int i = 0; i < 16 && i < rawSize; i++) {
        printf("%02x ", (unsigned char)raw[i]);
    }
    printf("\n");
    
    // Save intermediate result
    FILE* raw_fp = fopen("test_output/refined_step1_binary.dat", "wb");
    if (raw_fp) {
        fwrite(raw, 1, rawSize, raw_fp);
        fclose(raw_fp);
        printf("💾 Saved Step 1 binary result\n");
    }
    
    // Step 2: Binary → AdaNormalizeAtomStream → Compressed binary
    printf("\n=== Step 2: Normalize Binary (Standard Signature) ===\n");
    char fdo[512] = {0};
    int fdoSize = 512;
    
    int normalize_result = AdaNormalizeAtomStream(raw, rawSize, fdo, &fdoSize);
    printf("AdaNormalizeAtomStream: result=%d, size=%d\n", normalize_result, fdoSize);
    
    char errBuf[256] = {0};
    if (AdaGetErrorText) {
        AdaGetErrorText(normalize_result, errBuf, 256);
        printf("Normalize error: '%s'\n", errBuf);
    } else if (AdaGetErrorTextSimple) {
        const char* error = AdaGetErrorTextSimple();
        if (error && strlen(error) > 0) {
            printf("Error: '%s'\n", error);
        }
    }
    
    if (fdoSize == 356) {
        printf("🏆🏆🏆 SUCCESS! Got 356-byte FDO format! 🏆🏆🏆\n");
        
        printf("FDO header: ");
        for (int i = 0; i < 16; i++) {
            printf("%02x ", (unsigned char)fdo[i]);
        }
        printf("\n");
        
        // Check format
        if (fdoSize >= 2 && (unsigned char)fdo[0] == 0x40 && (unsigned char)fdo[1] == 0x01) {
            printf("🎯 Perfect FDO format (40 01 header)!\n");
        }
        
        // Save result
        FILE* fdo_fp = fopen("test_output/REFINED_FDO_SUCCESS.str", "wb");
        if (fdo_fp) {
            fwrite(fdo, 1, fdoSize, fdo_fp);
            fclose(fdo_fp);
            printf("💾 Saved FDO result\n");
        }
        
        // Compare with golden
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
                
                printf("📊 Golden comparison: %d/356 (%.1f%%)\n", matches, (float)matches/356*100);
                if (matches == 356) {
                    printf("🎉🎉🎉 PERFECT MATCH! COMPILER COMPLETE! 🎉🎉🎉\n");
                }
                
                free(golden_data);
            }
            fclose(golden_fp);
        }
    } else if (fdoSize > 0) {
        printf("⚠️  Got %d bytes (not 356)\n", fdoSize);
        
        // Save whatever we got
        FILE* result_fp = fopen("test_output/refined_normalize_result.dat", "wb");
        if (result_fp) {
            fwrite(fdo, 1, fdoSize, result_fp);
            fclose(result_fp);
            printf("💾 Saved normalize result (%d bytes)\n", fdoSize);
        }
    } else {
        printf("❌ Step 2 failed or no output\n");
    }
    
    // Step 3: Test with Flags Parameter (if standard signature didn't work)
    if (fdoSize != 356) {
        printf("\n=== Step 3: Testing Flags Parameter ===\n");
        
        for (int flag = 0; flag <= 2; flag++) {
            fdoSize = 512;
            memset(fdo, 0, 512);
            
            // Try signature with flags: AdaNormalizeAtomStream(input, size, output, outputSize*, flags)
            int flag_result = ((AdaNormalizeAtomStreamFlags_t)AdaNormalizeAtomStream)(raw, rawSize, fdo, &fdoSize, flag);
            
            printf("Flag=%d: result=%d, size=%d", flag, flag_result, fdoSize);
            
            if (AdaGetErrorText) {
                memset(errBuf, 0, 256);
                AdaGetErrorText(flag_result, errBuf, 256);
                printf(", error='%s'", errBuf);
            }
            printf("\n");
            
            if (fdoSize == 356) {
                printf("🏆 SUCCESS with flag=%d! Got 356 bytes!\n", flag);
                
                // Check format
                if (fdoSize >= 2 && (unsigned char)fdo[0] == 0x40 && (unsigned char)fdo[1] == 0x01) {
                    printf("🎯 FDO format confirmed!\n");
                }
                
                // Save flagged result
                char flag_filename[256];
                sprintf(flag_filename, "test_output/FLAGGED_SUCCESS_%d.str", flag);
                FILE* flag_fp = fopen(flag_filename, "wb");
                if (flag_fp) {
                    fwrite(fdo, 1, fdoSize, flag_fp);
                    fclose(flag_fp);
                    printf("💾 Saved flagged result\n");
                }
                
                break; // Found working flag
            } else if (flag_result > 0 && fdoSize > 0) {
                printf("  → Produced %d bytes\n", fdoSize);
            }
        }
    }
    
    // Cleanup
    free(input_text);
    FreeLibrary(ada32);
    
    printf("\n=== REFINED CHAINING SUMMARY ===\n");
    printf("Tested proper binary signatures and flags parameters\n");
    printf("This approach should achieve 356-byte compression if the functions support it\n");
    
    return 0;
}