/*
 * Examine what AdaNormalizeAtomStream actually produces
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaNormalizeAtomStream_t)(const char* input, int inputSize, void* output, int* outputSize);

int main() {
    printf("=== Examining Normalized Output ===\n");
    
    HMODULE hAda32 = LoadLibrary("Ada32.dll");
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hAda32, "AdaInitialize");
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
    
    printf("Original input (%ld bytes):\n", size);
    printf("'%.200s...'\n\n", input);
    
    // Normalize
    char* normalized = malloc(8192);
    int norm_size = 8192;
    AdaNormalizeAtomStream(input, (int)size, normalized, &norm_size);
    
    printf("Normalized output (%d bytes):\n", norm_size);
    
    if (norm_size > 0) {
        // Show as text
        printf("As text (first 500 chars):\n'");
        for (int i = 0; i < 500 && i < norm_size; i++) {
            if (normalized[i] >= 32 && normalized[i] <= 126) {
                printf("%c", normalized[i]);
            } else if (normalized[i] == '\n') {
                printf("\\n");
            } else if (normalized[i] == '\r') {
                printf("\\r");
            } else if (normalized[i] == '\t') {
                printf("\\t");
            } else {
                printf("[%02x]", (unsigned char)normalized[i]);
            }
        }
        printf("'\n\n");
        
        // Show as hex
        printf("As hex (first 200 bytes):\n");
        for (int i = 0; i < 200 && i < norm_size; i++) {
            printf("%02x ", (unsigned char)normalized[i]);
            if ((i + 1) % 16 == 0) printf("\n");
        }
        printf("\n\n");
        
        // Look for patterns
        printf("Analysis:\n");
        
        // Count printable chars
        int printable = 0, binary = 0;
        for (int i = 0; i < norm_size; i++) {
            if (normalized[i] >= 32 && normalized[i] <= 126) {
                printable++;
            } else {
                binary++;
            }
        }
        printf("Printable chars: %d (%.1f%%)\n", printable, (float)printable/norm_size*100);
        printf("Binary chars: %d (%.1f%%)\n", binary, (float)binary/norm_size*100);
        
        // Check if it looks like expanded atom format
        if (normalized[0] == 'u' && normalized[1] == 'n' && normalized[2] == 'i') {
            printf("✅ Starts with 'uni' - looks like expanded atom format\n");
        } else {
            printf("❓ Doesn't start with 'uni' - unexpected format\n");
        }
        
        // Save for analysis
        FILE* save_fp = fopen("test_output/normalized_analysis.txt", "wb");
        if (save_fp) {
            fwrite(normalized, 1, norm_size, save_fp);
            fclose(save_fp);
            printf("💾 Saved normalized output for analysis\n");
        }
        
        // Check if it's just expanded version of original
        printf("\nSize comparison:\n");
        printf("Original: %ld bytes\n", size);
        printf("Normalized: %d bytes\n", norm_size);
        printf("Expansion ratio: %.1fx\n", (float)norm_size/size);
        
    } else {
        printf("❌ No normalized output\n");
    }
    
    free(input);
    free(normalized);
    FreeLibrary(hAda32);
    return 0;
}