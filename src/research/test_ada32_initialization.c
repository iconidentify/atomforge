/*
 * Test Ada32.dll with proper initialization - discovered from star_us_50_32 comparison
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaTerminate_t)(void);
typedef int (__cdecl *AdaGetVersion_t)(void);
typedef const char* (__cdecl *AdaGetErrorText_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(const char* input, int inputSize, void* output, int* outputSize);

int main() {
    printf("=== Testing Ada32.dll with Proper Initialization ===\n");
    
    HMODULE hAda32 = LoadLibrary("Ada32.dll");
    if (!hAda32) {
        printf("❌ Failed to load Ada32.dll\n");
        return 1;
    }
    
    // Get initialization functions
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hAda32, "AdaInitialize");
    AdaTerminate_t AdaTerminate = (AdaTerminate_t)GetProcAddress(hAda32, "AdaTerminate");
    AdaGetVersion_t AdaGetVersion = (AdaGetVersion_t)GetProcAddress(hAda32, "AdaGetVersion");
    AdaGetErrorText_t AdaGetErrorText = (AdaGetErrorText_t)GetProcAddress(hAda32, "AdaGetErrorText");
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(hAda32, "AdaAssembleAtomStream");
    
    printf("Function availability:\n");
    printf("  AdaInitialize: %s\n", AdaInitialize ? "✅" : "❌");
    printf("  AdaTerminate: %s\n", AdaTerminate ? "✅" : "❌");
    printf("  AdaGetVersion: %s\n", AdaGetVersion ? "✅" : "❌");
    printf("  AdaGetErrorText: %s\n", AdaGetErrorText ? "✅" : "❌");
    printf("  AdaAssembleAtomStream: %s\n", AdaAssembleAtomStream ? "✅" : "❌");
    
    if (!AdaInitialize || !AdaAssembleAtomStream) {
        printf("❌ Essential functions not available\n");
        FreeLibrary(hAda32);
        return 1;
    }
    
    // Step 1: Initialize Ada32
    printf("\n=== Step 1: Initializing Ada32 ===\n");
    int init_result = AdaInitialize();
    printf("AdaInitialize() result: %d\n", init_result);
    
    if (init_result <= 0) {
        printf("❌ AdaInitialize failed\n");
        if (AdaGetErrorText) {
            const char* error = AdaGetErrorText();
            if (error) {
                printf("Error: %s\n", error);
            }
        }
        FreeLibrary(hAda32);
        return 1;
    }
    
    printf("✅ Ada32 initialized successfully\n");
    
    // Step 2: Get version info
    if (AdaGetVersion) {
        int version = AdaGetVersion();
        printf("Ada32 version: %d\n", version);
    }
    
    // Step 3: Test compilation with initialization
    printf("\n=== Step 2: Testing Compilation After Initialization ===\n");
    
    // Read our test file
    FILE* fp = fopen("clean_32-105.txt", "r");
    if (!fp) {
        printf("❌ Cannot open clean_32-105.txt\n");
        if (AdaTerminate) AdaTerminate();
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
    
    // Test compilation
    char output_buffer[2048];
    int output_size = sizeof(output_buffer);
    
    int compile_result = AdaAssembleAtomStream(input_text, (int)input_size, output_buffer, &output_size);
    printf("AdaAssembleAtomStream result: %d, size: %d\n", compile_result, output_size);
    
    if (AdaGetErrorText) {
        const char* error = AdaGetErrorText();
        if (error && strlen(error) > 0) {
            printf("Error text: '%s'\n", error);
        }
    }
    
    if (output_size > 0 && output_size < 2000) {
        printf("✅ Compilation successful: %d bytes\n", output_size);
        
        printf("Output header: ");
        for (int i = 0; i < 16 && i < output_size; i++) {
            printf("%02x ", (unsigned char)output_buffer[i]);
        }
        printf("\n");
        
        // Check the format
        if (output_size >= 2) {
            if ((unsigned char)output_buffer[0] == 0x00 && (unsigned char)output_buffer[1] == 0x01) {
                printf("📊 Raw format (00 01 header)\n");
                
                if (output_size == 413) {
                    printf("🎯 413-byte format (as expected)\n");
                } else {
                    printf("⚠️  Unexpected size: %d bytes\n", output_size);
                }
            } else if ((unsigned char)output_buffer[0] == 0x40 && (unsigned char)output_buffer[1] == 0x01) {
                printf("🎯 FDO format (40 01 header)!\n");
                
                if (output_size == 356) {
                    printf("🏆🏆🏆 PERFECT! 356-BYTE FDO FORMAT! 🏆🏆🏆\n");
                    printf("🎉 INITIALIZATION FIXED THE COMPRESSION! 🎉\n");
                } else {
                    printf("📊 FDO format but size: %d bytes\n", output_size);
                }
            } else {
                printf("❓ Unknown format: %02x %02x\n", 
                       (unsigned char)output_buffer[0], 
                       (unsigned char)output_buffer[1]);
            }
        }
        
        // Save the result
        FILE* output_fp = fopen("test_output/initialized_ada32_result.str", "wb");
        if (output_fp) {
            fwrite(output_buffer, 1, output_size, output_fp);
            fclose(output_fp);
            printf("💾 Saved result to initialized_ada32_result.str\n");
        }
        
        // Compare with golden file
        if (output_size == 356) {
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
                        if (output_buffer[i] == golden_data[i]) matches++;
                    }
                    
                    printf("\n📊 Golden file comparison:\n");
                    printf("Byte accuracy: %d/356 (%.1f%%)\n", matches, (float)matches/356*100);
                    
                    if (matches == 356) {
                        printf("🎉🎉🎉 PERFECT MATCH! COMPILER IS COMPLETE! 🎉🎉🎉\n");
                        printf("🏆 MISSION ACCOMPLISHED! 🏆\n");
                    } else if (matches > 300) {
                        printf("🎯 Very close! Only %d byte differences\n", 356 - matches);
                        
                        printf("First difference at byte: ");
                        for (int i = 0; i < 356; i++) {
                            if (output_buffer[i] != golden_data[i]) {
                                printf("%d (our: %02x, golden: %02x)\n", 
                                       i, (unsigned char)output_buffer[i], (unsigned char)golden_data[i]);
                                break;
                            }
                        }
                    }
                    
                    free(golden_data);
                }
                fclose(golden_fp);
            }
        }
    } else {
        printf("❌ Compilation failed or invalid size\n");
    }
    
    // Step 4: Test with different Ada32 functions
    printf("\n=== Step 3: Testing Other Ada32 Functions ===\n");
    
    void* AdaAssembleFragment = GetProcAddress(hAda32, "AdaAssembleFragment");
    void* AdaNormalizeAtomStream = GetProcAddress(hAda32, "AdaNormalizeAtomStream");
    
    if (AdaAssembleFragment) {
        printf("Testing AdaAssembleFragment...\n");
        
        int fragment_size = sizeof(output_buffer);
        int fragment_result = ((int (__cdecl *)(const char*, int, void*, int*))AdaAssembleFragment)(input_text, (int)input_size, output_buffer, &fragment_size);
        printf("AdaAssembleFragment: result=%d, size=%d\n", fragment_result, fragment_size);
        
        if (fragment_size > 0 && fragment_size < 2000) {
            if (fragment_size == 356) {
                printf("🏆 Fragment produced 356 bytes!\n");
                
                FILE* frag_fp = fopen("test_output/fragment_result.str", "wb");
                if (frag_fp) {
                    fwrite(output_buffer, 1, fragment_size, frag_fp);
                    fclose(frag_fp);
                    printf("💾 Saved fragment result\n");
                }
            }
        }
    }
    
    if (AdaNormalizeAtomStream) {
        printf("Testing AdaNormalizeAtomStream...\n");
        
        int normalize_size = sizeof(output_buffer);
        int normalize_result = ((int (__cdecl *)(const char*, int, void*, int*))AdaNormalizeAtomStream)(input_text, (int)input_size, output_buffer, &normalize_size);
        printf("AdaNormalizeAtomStream: result=%d, size=%d\n", normalize_result, normalize_size);
        
        if (normalize_size > 0 && normalize_size < 2000) {
            if (normalize_size == 356) {
                printf("🏆 Normalize produced 356 bytes!\n");
                
                FILE* norm_fp = fopen("test_output/normalize_result.str", "wb");
                if (norm_fp) {
                    fwrite(output_buffer, 1, normalize_size, norm_fp);
                    fclose(norm_fp);
                    printf("💾 Saved normalize result\n");
                }
            }
        }
    }
    
    // Cleanup
    printf("\n=== Cleanup ===\n");
    if (AdaTerminate) {
        int term_result = AdaTerminate();
        printf("AdaTerminate() result: %d\n", term_result);
    }
    
    free(input_text);
    FreeLibrary(hAda32);
    
    printf("\n=== SUMMARY ===\n");
    printf("Initialization discovery from star_us_50_32 comparison was the key!\n");
    printf("Always call AdaInitialize() before using other Ada32 functions.\n");
    
    return 0;
}