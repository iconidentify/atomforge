/*
 * Test using Dbaol32.dll functions to compress 413-byte raw format to 356-byte FDO
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int size, void* output, int* outSize);

// Database function signatures
typedef int (__cdecl *DBUpdateRecord_t)(void* data, int size, int recordId);
typedef int (__cdecl *DBAddRecord_t)(void* data, int size);
typedef int (__cdecl *DBExtractRecord_t)(int recordId, void* output, int* outputSize);
typedef int (__cdecl *DBGetRecordSize_t)(int recordId);
typedef int (__cdecl *DBCompressRecord_t)(void* input, int size, void* output, int* outputSize);

int main() {
    printf("=== Testing Dbaol32 Compression of 413-byte Raw Data ===\n");
    
    // Load Ada32.dll for assembling
    HMODULE ada32 = LoadLibraryA("Ada32.dll");
    if (!ada32) {
        printf("❌ Failed to load Ada32.dll\n");
        return 1;
    }
    
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(ada32, "AdaInitialize");
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(ada32, "AdaAssembleAtomStream");
    
    // Load Dbaol32.dll for compression
    HMODULE dbaol32 = LoadLibraryA("Dbaol32.dll");
    if (!dbaol32) {
        printf("❌ Failed to load Dbaol32.dll\n");
        FreeLibrary(ada32);
        return 1;
    }
    
    DBUpdateRecord_t DBUpdateRecord = (DBUpdateRecord_t)GetProcAddress(dbaol32, "DBUpdateRecord");
    DBAddRecord_t DBAddRecord = (DBAddRecord_t)GetProcAddress(dbaol32, "DBAddRecord");
    DBExtractRecord_t DBExtractRecord = (DBExtractRecord_t)GetProcAddress(dbaol32, "DBExtractRecord");
    DBGetRecordSize_t DBGetRecordSize = (DBGetRecordSize_t)GetProcAddress(dbaol32, "DBGetRecordSize");
    DBCompressRecord_t DBCompressRecord = (DBCompressRecord_t)GetProcAddress(dbaol32, "DBCompressRecord");
    
    printf("Database function availability:\n");
    printf("  DBUpdateRecord: %s\n", DBUpdateRecord ? "✅" : "❌");
    printf("  DBAddRecord: %s\n", DBAddRecord ? "✅" : "❌");
    printf("  DBExtractRecord: %s\n", DBExtractRecord ? "✅" : "❌");
    printf("  DBGetRecordSize: %s\n", DBGetRecordSize ? "✅" : "❌");
    printf("  DBCompressRecord: %s\n", DBCompressRecord ? "✅" : "❌");
    
    // Initialize Ada32
    AdaInitialize();
    printf("\n✅ Ada32 initialized\n");
    
    // Load test input
    FILE* fp = fopen("clean_32-105.txt", "r");
    if (!fp) {
        printf("❌ Cannot open clean_32-105.txt\n");
        FreeLibrary(ada32);
        FreeLibrary(dbaol32);
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
    
    // Step 1: Generate 413-byte raw data with Ada32
    printf("\n=== Step 1: Generate 413-byte Raw Data ===\n");
    char raw[512] = {0};
    int rawSize = 512;
    
    int assemble_result = AdaAssembleAtomStream(input_text, (int)input_size, raw, &rawSize);
    printf("AdaAssembleAtomStream: result=%d, size=%d\n", assemble_result, rawSize);
    
    if (assemble_result != 0 || rawSize != 413) {
        printf("❌ Failed to generate 413-byte raw data\n");
        free(input_text);
        FreeLibrary(ada32);
        FreeLibrary(dbaol32);
        return 1;
    }
    
    printf("✅ Generated 413-byte raw data\n");
    
    // Step 2: Try database compression methods
    printf("\n=== Step 2: Testing Database Compression ===\n");
    
    // Method 1: Try DBCompressRecord if available
    if (DBCompressRecord) {
        printf("Testing DBCompressRecord...\n");
        char compressed[512] = {0};
        int compressedSize = 512;
        
        int compress_result = DBCompressRecord(raw, rawSize, compressed, &compressedSize);
        printf("DBCompressRecord: result=%d, size=%d\n", compress_result, compressedSize);
        
        if (compressedSize == 356) {
            printf("🏆🏆🏆 DBCompressRecord SUCCESS! Got 356 bytes! 🏆🏆🏆\n");
            
            // Check FDO format
            if (compressedSize >= 2 && (unsigned char)compressed[0] == 0x40 && (unsigned char)compressed[1] == 0x01) {
                printf("🎯 Perfect FDO format (40 01 header)!\n");
            }
            
            // Save result
            FILE* compress_fp = fopen("test_output/DBAOL_COMPRESS_SUCCESS.str", "wb");
            if (compress_fp) {
                fwrite(compressed, 1, compressedSize, compress_fp);
                fclose(compress_fp);
                printf("💾 Saved DBCompressRecord result\n");
            }
        } else if (compressedSize > 0) {
            printf("Got %d bytes (not 356)\n", compressedSize);
        }
    }
    
    // Method 2: Try round-trip through database
    if (DBAddRecord && DBExtractRecord) {
        printf("\nTesting round-trip through database...\n");
        
        // Add record
        int add_result = DBAddRecord(raw, rawSize);
        printf("DBAddRecord: result=%d\n", add_result);
        
        if (add_result >= 0) {
            // Extract record (might be compressed)
            char extracted[512] = {0};
            int extractedSize = 512;
            
            int extract_result = DBExtractRecord(add_result, extracted, &extractedSize);
            printf("DBExtractRecord: result=%d, size=%d\n", extract_result, extractedSize);
            
            if (extractedSize == 356) {
                printf("🏆🏆🏆 Database Round-trip SUCCESS! Got 356 bytes! 🏆🏆🏆\n");
                
                // Check FDO format
                if (extractedSize >= 2 && (unsigned char)extracted[0] == 0x40 && (unsigned char)extracted[1] == 0x01) {
                    printf("🎯 Perfect FDO format (40 01 header)!\n");
                }
                
                // Save result
                FILE* db_fp = fopen("test_output/DBAOL_ROUNDTRIP_SUCCESS.str", "wb");
                if (db_fp) {
                    fwrite(extracted, 1, extractedSize, db_fp);
                    fclose(db_fp);
                    printf("💾 Saved database round-trip result\n");
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
                            if (extracted[i] == golden_data[i]) matches++;
                        }
                        
                        printf("📊 Golden comparison: %d/356 (%.1f%%)\n", matches, (float)matches/356*100);
                        if (matches == 356) {
                            printf("🎉🎉🎉 PERFECT MATCH! DATABASE COMPRESSION IS THE SOLUTION! 🎉🎉🎉\n");
                        }
                        
                        free(golden_data);
                    }
                    fclose(golden_fp);
                }
            } else if (extractedSize > 0) {
                printf("Got %d bytes (not 356)\n", extractedSize);
            }
        }
    }
    
    // Method 3: Try different record IDs in case compression is index-dependent
    if (DBExtractRecord) {
        printf("\nTesting different record IDs for compression...\n");
        
        for (int recordId = 0; recordId < 10; recordId++) {
            char test_extract[512] = {0};
            int test_size = 512;
            
            int test_result = DBExtractRecord(recordId, test_extract, &test_size);
            if (test_result == 0 && test_size == 356) {
                printf("🏆 Record ID %d gives 356 bytes!\n", recordId);
                
                // Update this record with our data
                if (DBUpdateRecord) {
                    int update_result = DBUpdateRecord(raw, rawSize, recordId);
                    printf("DBUpdateRecord(%d): result=%d\n", recordId, update_result);
                    
                    if (update_result == 0) {
                        // Re-extract to see if it's compressed
                        memset(test_extract, 0, 512);
                        test_size = 512;
                        
                        int reextract_result = DBExtractRecord(recordId, test_extract, &test_size);
                        printf("Re-extract: result=%d, size=%d\n", reextract_result, test_size);
                        
                        if (test_size == 356) {
                            printf("🏆🏆🏆 Update/Extract SUCCESS! Got 356 bytes! 🏆🏆🏆\n");
                            
                            // Save result
                            char filename[256];
                            sprintf(filename, "test_output/DBAOL_UPDATE_%d_SUCCESS.str", recordId);
                            FILE* update_fp = fopen(filename, "wb");
                            if (update_fp) {
                                fwrite(test_extract, 1, test_size, update_fp);
                                fclose(update_fp);
                                printf("💾 Saved update/extract result\n");
                            }
                            
                            break; // Found working method
                        }
                    }
                }
            }
        }
    }
    
    free(input_text);
    FreeLibrary(ada32);
    FreeLibrary(dbaol32);
    
    printf("\n=== DBAOL32 COMPRESSION TEST SUMMARY ===\n");
    printf("Tested database functions for 413→356 byte compression\n");
    printf("If successful, this is the missing compression step!\n");
    
    return 0;
}