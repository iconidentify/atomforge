/*
 * Find the correct record ID for the 32-105 record
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBExtractRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);
typedef int (__stdcall *DBGetFirstRecord_t)(int handle, int* recordId);
typedef int (__stdcall *DBGetNextRecord_t)(int handle, int* recordId);
typedef int (__stdcall *DBGetRecordCount_t)(int handle);
typedef const char* (__stdcall *DBGetLastError_t)(void);

int main() {
    printf("=== Finding Correct Record ID ===\n");
    
    HMODULE hDbaol = LoadLibrary("Dbaol32.dll");
    if (!hDbaol) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDbaol, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDbaol, "DBClose");
    DBExtractRecord_t DBExtractRecord = (DBExtractRecord_t)GetProcAddress(hDbaol, "DBExtractRecord");
    DBGetFirstRecord_t DBGetFirstRecord = (DBGetFirstRecord_t)GetProcAddress(hDbaol, "DBGetFirstRecord");
    DBGetNextRecord_t DBGetNextRecord = (DBGetNextRecord_t)GetProcAddress(hDbaol, "DBGetNextRecord");
    DBGetRecordCount_t DBGetRecordCount = (DBGetRecordCount_t)GetProcAddress(hDbaol, "DBGetRecordCount");
    DBGetLastError_t DBGetLastError = (DBGetLastError_t)GetProcAddress(hDbaol, "DBGetLastError");
    
    printf("Available functions:\n");
    printf("DBOpen: %s\n", DBOpen ? "✅" : "❌");
    printf("DBExtractRecord: %s\n", DBExtractRecord ? "✅" : "❌");
    printf("DBGetFirstRecord: %s\n", DBGetFirstRecord ? "✅" : "❌");
    printf("DBGetNextRecord: %s\n", DBGetNextRecord ? "✅" : "❌");
    printf("DBGetRecordCount: %s\n", DBGetRecordCount ? "✅" : "❌");
    
    int dbHandle = DBOpen("golden_tests/main.IDX");
    if (dbHandle <= 0) {
        printf("❌ Failed to open database\n");
        FreeLibrary(hDbaol);
        return 1;
    }
    
    printf("✅ Database opened: handle %d\n", dbHandle);
    
    // Try to get record count
    if (DBGetRecordCount) {
        int count = DBGetRecordCount(dbHandle);
        printf("Record count: %d\n", count);
    }
    
    // Try different record IDs around our known values
    int test_ids[] = {
        1, 2, 3, 4, 5,           // Simple sequential IDs
        32105, 32106, 32117,     // Based on file names
        335544363,               // Our calculated ID
        0x14000000 + 105,        // Alternative calculation
        0x20000000 + 105,        // Another alternative
        105, 106, 117            // Simple numbers
    };
    
    int num_tests = sizeof(test_ids) / sizeof(test_ids[0]);
    
    printf("\nTesting different record IDs:\n");
    
    for (int i = 0; i < num_tests; i++) {
        int record_id = test_ids[i];
        char buffer[1024];
        int buffer_size = sizeof(buffer);
        
        int result = DBExtractRecord(dbHandle, record_id, buffer, &buffer_size);
        
        if (result > 0 && buffer_size > 0) {
            printf("✅ ID %d: SUCCESS! Size: %d bytes", record_id, buffer_size);
            
            // Check if it's FDO format
            if (buffer_size >= 2 && (unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
                printf(" (FDO format)");
                
                if (buffer_size == 356) {
                    printf(" 🎯 PERFECT SIZE!");
                    
                    // Check if this contains our expected text
                    if (strstr(buffer, "Public Rooms in People Connection")) {
                        printf(" 🎉 FOUND 32-105 RECORD!");
                        
                        // Save this record
                        FILE* fp = fopen("test_output/found_32-105_record.str", "wb");
                        if (fp) {
                            fwrite(buffer, 1, buffer_size, fp);
                            fclose(fp);
                            printf("\n💾 Saved found record");
                        }
                    }
                }
            }
            printf("\n");
        } else {
            printf("❌ ID %d: Failed (result=%d, size=%d)\n", record_id, result, buffer_size);
        }
    }
    
    // If we have enumeration functions, try those
    if (DBGetFirstRecord && DBGetNextRecord) {
        printf("\n🔍 Enumerating records...\n");
        int current_id = 0;
        int enum_result = DBGetFirstRecord(dbHandle, &current_id);
        int count = 0;
        
        while (enum_result > 0 && count < 10) {  // Limit to first 10 records
            printf("Found record ID: %d\n", current_id);
            
            // Try to extract this record
            char buffer[1024];
            int buffer_size = sizeof(buffer);
            int extract_result = DBExtractRecord(dbHandle, current_id, buffer, &buffer_size);
            
            if (extract_result > 0) {
                printf("  Size: %d bytes", buffer_size);
                if (buffer_size == 356) {
                    printf(" 🎯 TARGET SIZE!");
                }
                if (buffer_size >= 2 && (unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
                    printf(" (FDO)");
                }
                printf("\n");
            }
            
            enum_result = DBGetNextRecord(dbHandle, &current_id);
            count++;
        }
    }
    
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDbaol);
    return 0;
}