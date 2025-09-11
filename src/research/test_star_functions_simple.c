/*
 * Simple test of star Ada32 functions to avoid crashes
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(const char* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaNormalizeAtomStream_t)(const char* input, int inputSize, void* output, int* outputSize);

int main() {
    printf("=== Simple Star Ada32 Function Test ===\n");
    
    HMODULE hStarAda32 = LoadLibrary("star_us_50_32/ADA32.DLL");
    if (!hStarAda32) {
        printf("❌ Failed to load star Ada32\n");
        return 1;
    }
    
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hStarAda32, "AdaInitialize");
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(hStarAda32, "AdaAssembleAtomStream");
    AdaNormalizeAtomStream_t AdaNormalizeAtomStream = (AdaNormalizeAtomStream_t)GetProcAddress(hStarAda32, "AdaNormalizeAtomStream");
    
    if (!AdaInitialize || !AdaAssembleAtomStream) {
        printf("❌ Essential functions missing\n");
        FreeLibrary(hStarAda32);
        return 1;
    }
    
    // Initialize
    AdaInitialize();
    printf("✅ Star Ada32 initialized\n");
    
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
    
    // Test AdaAssembleAtomStream
    char output1[2048];
    int size1 = sizeof(output1);
    int result1 = AdaAssembleAtomStream(input_text, (int)input_size, output1, &size1);
    printf("AdaAssembleAtomStream: result=%d, size=%d\n", result1, size1);
    
    if (size1 > 0) {
        FILE* fp1 = fopen("test_output/star_simple_stream.str", "wb");
        if (fp1) {
            fwrite(output1, 1, size1, fp1);
            fclose(fp1);
            printf("💾 Saved stream result (%d bytes)\n", size1);
        }
    }
    
    // Test AdaNormalizeAtomStream
    char output2[2048];
    int size2 = 0;
    if (AdaNormalizeAtomStream) {
        size2 = sizeof(output2);
        int result2 = AdaNormalizeAtomStream(input_text, (int)input_size, output2, &size2);
        printf("AdaNormalizeAtomStream: result=%d, size=%d\n", result2, size2);
        
        if (size2 > 0) {
            FILE* fp2 = fopen("test_output/star_simple_normalize.str", "wb");
            if (fp2) {
                fwrite(output2, 1, size2, fp2);
                fclose(fp2);
                printf("💾 Saved normalize result (%d bytes)\n", size2);
            }
            
            if (size2 == 356) {
                printf("🏆 NORMALIZE PRODUCES 356 BYTES!\n");
            }
        }
    }
    
    printf("\n=== Star Ada32 Results ===\n");
    printf("Stream size: %d bytes\n", size1);
    if (AdaNormalizeAtomStream) {
        printf("Normalize size: %d bytes\n", size2);
    }
    
    free(input_text);
    FreeLibrary(hStarAda32);
    return 0;
}