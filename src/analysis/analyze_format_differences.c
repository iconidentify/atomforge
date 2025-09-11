/*
 * Analyze the binary format differences between 413-byte and 356-byte formats
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int size, void* output, int* outSize);

void analyze_binary_structure(const char* name, const char* data, int size) {
    printf("\n=== %s (%d bytes) ===\n", name, size);
    
    // Header analysis
    printf("Header (first 32 bytes):\n");
    for (int i = 0; i < 32 && i < size; i++) {
        printf("%02x ", (unsigned char)data[i]);
        if ((i + 1) % 16 == 0) printf("\n");
    }
    if (size > 32) printf("...\n");
    else printf("\n");
    
    // Look for text content
    printf("Text content found:\n");
    int text_start = -1;
    for (int i = 0; i < size - 10; i++) {
        if (strncmp(&data[i], "Public Rooms", 12) == 0) {
            text_start = i;
            printf("  'Public Rooms...' at offset %d\n", i);
            break;
        }
    }
    
    // Look for other recognizable strings
    const char* search_strings[] = {
        "People Connection",
        "Welcome to",
        "Chat Area",
        "Location",
        NULL
    };
    
    for (int s = 0; search_strings[s]; s++) {
        for (int i = 0; i < size - strlen(search_strings[s]); i++) {
            if (strncmp(&data[i], search_strings[s], strlen(search_strings[s])) == 0) {
                printf("  '%s' at offset %d\n", search_strings[s], i);
                break;
            }
        }
    }
    
    // Structure analysis
    printf("Structure analysis:\n");
    printf("  Byte 0-1: %02x %02x", (unsigned char)data[0], (unsigned char)data[1]);
    if (data[0] == 0x40 && data[1] == 0x01) {
        printf(" (FDO format)\n");
    } else if (data[0] == 0x00 && data[1] == 0x01) {
        printf(" (Raw format)\n");
    } else {
        printf(" (Unknown format)\n");
    }
    
    if (size > 2) {
        printf("  Byte 2-3: %02x %02x\n", (unsigned char)data[2], (unsigned char)data[3]);
    }
    
    // Look for null padding or compression indicators
    int null_count = 0;
    int repeating_bytes = 0;
    for (int i = 0; i < size; i++) {
        if (data[i] == 0) null_count++;
    }
    
    printf("  Null bytes: %d (%.1f%%)\n", null_count, (float)null_count/size*100);
    
    // Tail analysis (last 16 bytes)
    printf("Tail (last 16 bytes):\n");
    int start = size > 16 ? size - 16 : 0;
    for (int i = start; i < size; i++) {
        printf("%02x ", (unsigned char)data[i]);
    }
    printf("\n");
}

void find_differences(const char* data1, int size1, const char* data2, int size2) {
    printf("\n=== Difference Analysis ===\n");
    printf("Size difference: %d bytes (%d - %d)\n", size1 - size2, size1, size2);
    
    // Find where they diverge
    int min_size = size1 < size2 ? size1 : size2;
    int first_diff = -1;
    int match_count = 0;
    
    for (int i = 0; i < min_size; i++) {
        if (data1[i] == data2[i]) {
            match_count++;
        } else if (first_diff == -1) {
            first_diff = i;
        }
    }
    
    printf("Matching bytes: %d/%d (%.1f%%)\n", match_count, min_size, (float)match_count/min_size*100);
    
    if (first_diff >= 0) {
        printf("First difference at offset %d:\n", first_diff);
        printf("  413-byte: %02x\n", (unsigned char)data1[first_diff]);
        printf("  356-byte: %02x\n", (unsigned char)data2[first_diff]);
        
        // Show context around first difference
        printf("Context (±8 bytes):\n");
        int start = first_diff > 8 ? first_diff - 8 : 0;
        int end = first_diff + 8 < min_size ? first_diff + 8 : min_size;
        
        printf("413-byte: ");
        for (int i = start; i < end; i++) {
            if (i == first_diff) printf("[%02x] ", (unsigned char)data1[i]);
            else printf("%02x ", (unsigned char)data1[i]);
        }
        printf("\n");
        
        printf("356-byte: ");
        for (int i = start; i < end; i++) {
            if (i == first_diff) printf("[%02x] ", (unsigned char)data2[i]);
            else printf("%02x ", (unsigned char)data2[i]);
        }
        printf("\n");
    }
    
    // Look for potential compression patterns
    if (size1 > size2) {
        printf("\nPotential compression analysis:\n");
        printf("Compression ratio: %.1f%% (%.1fx smaller)\n", 
               (float)(size1-size2)/size1*100, (float)size1/size2);
        
        // Check if it's just truncation
        int tail_matches = 0;
        for (int i = 0; i < size2 - 16; i++) {
            if (data1[i] == data2[i]) tail_matches++;
        }
        
        if (tail_matches > size2 * 0.9) {
            printf("Likely truncation - most content matches\n");
        } else {
            printf("Likely compression/encoding - content differs significantly\n");
        }
    }
}

int main() {
    printf("=== Binary Format Analysis: 413-byte vs 356-byte ===\n");
    
    // Generate fresh 413-byte data
    HMODULE ada32 = LoadLibraryA("Ada32.dll");
    if (!ada32) {
        printf("❌ Failed to load Ada32.dll\n");
        return 1;
    }
    
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(ada32, "AdaInitialize");
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(ada32, "AdaAssembleAtomStream");
    
    AdaInitialize();
    
    // Load input
    FILE* fp = fopen("clean_32-105.txt", "r");
    if (!fp) {
        printf("❌ Cannot open input file\n");
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
    
    // Generate 413-byte data
    char raw413[512] = {0};
    int raw413Size = 512;
    
    int result = AdaAssembleAtomStream(input_text, (int)input_size, raw413, &raw413Size);
    if (result != 0 || raw413Size != 413) {
        printf("❌ Failed to generate 413-byte data\n");
        free(input_text);
        FreeLibrary(ada32);
        return 1;
    }
    
    // Load 356-byte golden data
    FILE* golden_fp = fopen("golden_tests/32-105.str", "rb");
    if (!golden_fp) {
        printf("❌ Cannot open golden file\n");
        free(input_text);
        FreeLibrary(ada32);
        return 1;
    }
    
    fseek(golden_fp, 0, SEEK_END);
    int golden_size = ftell(golden_fp);
    fseek(golden_fp, 0, SEEK_SET);
    char* golden_data = malloc(golden_size);
    fread(golden_data, 1, golden_size, golden_fp);
    fclose(golden_fp);
    
    if (golden_size != 356) {
        printf("❌ Golden file is %d bytes, not 356\n", golden_size);
        free(input_text);
        free(golden_data);
        FreeLibrary(ada32);
        return 1;
    }
    
    printf("✅ Loaded 413-byte and 356-byte data for analysis\n");
    
    // Analyze both formats
    analyze_binary_structure("413-byte Raw Format", raw413, raw413Size);
    analyze_binary_structure("356-byte FDO Format", golden_data, golden_size);
    
    // Find differences
    find_differences(raw413, raw413Size, golden_data, golden_size);
    
    // Save analysis data
    FILE* raw_fp = fopen("test_output/format_analysis_413.dat", "wb");
    if (raw_fp) {
        fwrite(raw413, 1, raw413Size, raw_fp);
        fclose(raw_fp);
    }
    
    FILE* golden_copy_fp = fopen("test_output/format_analysis_356.dat", "wb");
    if (golden_copy_fp) {
        fwrite(golden_data, 1, golden_size, golden_copy_fp);
        fclose(golden_copy_fp);
    }
    
    printf("\n💾 Saved analysis data files\n");
    
    free(input_text);
    free(golden_data);
    FreeLibrary(ada32);
    
    printf("\n=== ANALYSIS SUMMARY ===\n");
    printf("Compared 413-byte raw output with 356-byte target\n");
    printf("This analysis helps identify the compression/encoding pattern\n");
    
    return 0;
}