/*
 * Test the alternative Ada32.dll from star_us_50_32
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int size, void* output, int* outSize);
typedef int (__cdecl *AdaNormalizeAtomStream_t)(void* input, int size, void* output, int* outSize);
typedef int (__cdecl *AdaGetErrorText_t)(int code, char* buf, int bufSize);

int main() {
    printf("=== Testing Alternative Ada32.dll from star_us_50_32 ===\n");
    
    HMODULE ada32 = LoadLibraryA("star_us_50_32/Ada32.dll");
    if (!ada32) {
        printf("❌ Failed to load star_us_50_32/Ada32.dll\n");
        return 1;
    }
    
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(ada32, "AdaInitialize");
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(ada32, "AdaAssembleAtomStream");
    AdaNormalizeAtomStream_t AdaNormalizeAtomStream = (AdaNormalizeAtomStream_t)GetProcAddress(ada32, "AdaNormalizeAtomStream");
    AdaGetErrorText_t AdaGetErrorText = (AdaGetErrorText_t)GetProcAddress(ada32, "AdaGetErrorText");
    
    printf("Function availability:\n");
    printf("  AdaInitialize: %s\n", AdaInitialize ? "✅" : "❌");
    printf("  AdaAssembleAtomStream: %s\n", AdaAssembleAtomStream ? "✅" : "❌");
    printf("  AdaNormalizeAtomStream: %s\n", AdaNormalizeAtomStream ? "✅" : "❌");
    printf("  AdaGetErrorText: %s\n", AdaGetErrorText ? "✅" : "❌");
    
    if (!AdaInitialize || !AdaAssembleAtomStream) {
        printf("❌ Essential functions missing\n");
        FreeLibrary(ada32);
        return 1;
    }
    
    // Initialize
    int init_result = AdaInitialize();
    printf("\nAdaInitialize(): %d\n", init_result);
    
    if (init_result != 1) {
        printf("❌ Initialization failed\n");
        FreeLibrary(ada32);
        return 1;
    }
    
    // Load test input
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
    
    // Test AdaAssembleAtomStream
    printf("\n=== Testing AdaAssembleAtomStream ===\n");
    char raw[512] = {0};
    int rawSize = 512;
    
    int assemble_result = AdaAssembleAtomStream(input_text, (int)input_size, raw, &rawSize);
    printf("AdaAssembleAtomStream: result=%d, size=%d\n", assemble_result, rawSize);
    
    if (assemble_result == 0 && rawSize > 0) {
        printf("✅ Success: %d bytes\n", rawSize);
        printf("Header: ");
        for (int i = 0; i < 16; i++) {
            printf("%02x ", (unsigned char)raw[i]);
        }
        printf("\n");
        
        // Test AdaNormalizeAtomStream if available
        if (AdaNormalizeAtomStream) {
            printf("\n=== Testing AdaNormalizeAtomStream on Binary ===\n");
            char fdo[512] = {0};
            int fdoSize = 512;
            
            int normalize_result = AdaNormalizeAtomStream(raw, rawSize, fdo, &fdoSize);
            printf("AdaNormalizeAtomStream: result=%d, size=%d\n", normalize_result, fdoSize);
            
            if (fdoSize == 356) {
                printf("🏆🏆🏆 SUCCESS! Got 356-byte target! 🏆🏆🏆\n");
                
                // Check FDO format
                if (fdoSize >= 2 && (unsigned char)fdo[0] == 0x40 && (unsigned char)fdo[1] == 0x01) {
                    printf("🎯 Perfect FDO format (40 01 header)!\n");
                }
                
                // Save result
                FILE* star_fp = fopen("test_output/STAR_ADA32_SUCCESS.str", "wb");
                if (star_fp) {
                    fwrite(fdo, 1, fdoSize, star_fp);
                    fclose(star_fp);
                    printf("💾 Saved star Ada32 result\n");
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
                            printf("🎉🎉🎉 PERFECT MATCH WITH STAR ADA32! 🎉🎉🎉\n");
                        }
                        
                        free(golden_data);
                    }
                    fclose(golden_fp);
                }
            } else if (fdoSize > 0) {
                printf("Got %d bytes (not 356)\n", fdoSize);
            }
        }
    } else {
        printf("❌ AdaAssembleAtomStream failed\n");
    }
    
    free(input_text);
    FreeLibrary(ada32);
    
    printf("\n=== STAR ADA32 TEST SUMMARY ===\n");
    printf("Tested alternative Ada32.dll from star_us_50_32 program\n");
    
    return 0;
}