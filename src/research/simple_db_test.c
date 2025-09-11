/*
 * Simple test of Dbaol32.dll extraction to understand compression
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *DBExtractRecord_t)(int recordId, void* output, int* outputSize);
typedef int (__cdecl *DBGetRecordSize_t)(int recordId);

int main() {
    printf("=== Simple Dbaol32 Extraction Test ===\n");
    
    HMODULE dbaol32 = LoadLibraryA("Dbaol32.dll");
    if (!dbaol32) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBExtractRecord_t DBExtractRecord = (DBExtractRecord_t)GetProcAddress(dbaol32, "DBExtractRecord");
    DBGetRecordSize_t DBGetRecordSize = (DBGetRecordSize_t)GetProcAddress(dbaol32, "DBGetRecordSize");
    
    printf("Function availability:\n");
    printf("  DBExtractRecord: %s\n", DBExtractRecord ? "✅" : "❌");
    printf("  DBGetRecordSize: %s\n", DBGetRecordSize ? "✅" : "❌");
    
    if (!DBExtractRecord) {
        printf("❌ Essential functions missing\n");
        FreeLibrary(dbaol32);
        return 1;
    }
    
    printf("\n=== Testing Record Extraction ===\n");
    
    // We know record 32 at position 23057 is our target 356-byte record
    // Let's try different approaches to extract it
    
    // Method 1: Direct extraction with record ID 32
    printf("Testing record ID 32 (known 356-byte record):\n");
    char record32[512] = {0};
    int record32Size = 512;
    
    int result32 = DBExtractRecord(32, record32, &record32Size);
    printf("DBExtractRecord(32): result=%d, size=%d\n", result32, record32Size);
    
    if (result32 == 0 && record32Size == 356) {
        printf("✅ Successfully extracted 356-byte record!\n");
        
        // Check format
        printf("Header: ");
        for (int i = 0; i < 16; i++) {
            printf("%02x ", (unsigned char)record32[i]);
        }
        printf("\n");
        
        if (record32Size >= 2 && (unsigned char)record32[0] == 0x40 && (unsigned char)record32[1] == 0x01) {
            printf("🎯 FDO format confirmed (40 01 header)!\n");
        }
        
        // Save extracted record
        FILE* extract_fp = fopen("test_output/db_extracted_record32.str", "wb");
        if (extract_fp) {
            fwrite(record32, 1, record32Size, extract_fp);
            fclose(extract_fp);
            printf("💾 Saved extracted record\n");
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
                    if (record32[i] == golden_data[i]) matches++;
                }
                
                printf("📊 Golden comparison: %d/356 (%.1f%%)\n", matches, (float)matches/356*100);
                if (matches == 356) {
                    printf("🎉 Perfect match with golden file!\n");
                } else {
                    printf("⚠️  Differences found - different compression?\n");
                }
                
                free(golden_data);
            }
            fclose(golden_fp);
        }
    } else if (result32 == 0) {
        printf("Got %d bytes (not 356)\n", record32Size);
    } else {
        printf("❌ Extraction failed with result %d\n", result32);
    }
    
    // Method 2: Test a range of record IDs to see what sizes we get
    printf("\n=== Testing Record ID Range ===\n");
    for (int id = 30; id <= 35; id++) {
        char test_record[512] = {0};
        int test_size = 512;
        
        int test_result = DBExtractRecord(id, test_record, &test_size);
        printf("Record %d: result=%d, size=%d", id, test_result, test_size);
        
        if (test_result == 0 && test_size > 0) {
            printf(" - header: %02x %02x", (unsigned char)test_record[0], (unsigned char)test_record[1]);
            if (test_size == 356) {
                printf(" ⭐ 356-byte target!");
            }
        }
        printf("\n");
    }
    
    FreeLibrary(dbaol32);
    
    printf("\n=== SIMPLE DB TEST SUMMARY ===\n");
    printf("Tested basic database record extraction\n");
    printf("This helps understand if DB functions access the compressed data\n");
    
    return 0;
}