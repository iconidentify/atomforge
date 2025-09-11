/*
 * Test if database uses cursor/iterator pattern
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);

// Functions that might work with cursor pattern
typedef int (__stdcall *DBCopyThisRecord_t)(int handle, void* buffer, int* bufferSize);
typedef int (__stdcall *DBDeleteThisRecord_t)(int handle);
typedef const char* (__stdcall *DBGetLastError_t)(void);

// Maybe there are navigation functions I missed
typedef int (__stdcall *DBFirst_t)(int handle);
typedef int (__stdcall *DBNext_t)(int handle);
typedef int (__stdcall *DBSeek_t)(int handle, int position);

int main() {
    printf("=== Testing Database Cursor Pattern ===\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    DBCopyThisRecord_t DBCopyThisRecord = (DBCopyThisRecord_t)GetProcAddress(hDll, "DBCopyThisRecord");
    DBDeleteThisRecord_t DBDeleteThisRecord = (DBDeleteThisRecord_t)GetProcAddress(hDll, "DBDeleteThisRecord");
    DBGetLastError_t DBGetLastError = (DBGetLastError_t)GetProcAddress(hDll, "DBGetLastError");
    
    // Try to find navigation functions
    DBFirst_t DBFirst = (DBFirst_t)GetProcAddress(hDll, "DBFirst");
    DBNext_t DBNext = (DBNext_t)GetProcAddress(hDll, "DBNext");
    DBSeek_t DBSeek = (DBSeek_t)GetProcAddress(hDll, "DBSeek");
    
    printf("Cursor-style functions:\n");
    printf("  DBCopyThisRecord: %s\n", DBCopyThisRecord ? "✅" : "❌");
    printf("  DBDeleteThisRecord: %s\n", DBDeleteThisRecord ? "✅" : "❌");
    printf("  DBFirst: %s\n", DBFirst ? "✅" : "❌");
    printf("  DBNext: %s\n", DBNext ? "✅" : "❌");
    printf("  DBSeek: %s\n", DBSeek ? "✅" : "❌");
    
    int dbHandle = DBOpen("working_copy.IDX");
    printf("\\nDBOpen result: %d\n", dbHandle);
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open database\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    printf("✅ Database opened\n");
    
    // Test 1: Try DBCopyThisRecord without positioning - maybe it copies current record
    if (DBCopyThisRecord) {
        printf("\\n=== Testing DBCopyThisRecord (no positioning) ===\n");
        
        char buffer[1024];
        int buffer_size = sizeof(buffer);
        
        int result = DBCopyThisRecord(dbHandle, buffer, &buffer_size);
        printf("DBCopyThisRecord result: %d, size: %d\n", result, buffer_size);
        
        if (result > 0 && buffer_size > 0 && buffer_size < 1024) {
            printf("✅ SUCCESS! Got %d bytes from current position\n", buffer_size);
            printf("First 16 bytes: ");
            for (int i = 0; i < 16 && i < buffer_size; i++) {
                printf("%02x ", (unsigned char)buffer[i]);
            }
            printf("\n");
            
            // Check for FDO format
            if (buffer_size >= 2 && (unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
                printf("🎯 FDO FORMAT!\n");
                if (buffer_size == 356) {
                    printf("🎉 PERFECT SIZE! This might be our record!\n");
                }
                
                FILE* fp = fopen("test_output/copy_this_record.str", "wb");
                if (fp) {
                    fwrite(buffer, 1, buffer_size, fp);
                    fclose(fp);
                    printf("💾 Saved copied record\n");
                }
            }
        } else {
            printf("❌ Failed or no data\n");
        }
    }
    
    // Test 2: Try navigation functions if they exist
    if (DBFirst) {
        printf("\\n=== Testing Database Navigation ===\n");
        
        int first_result = DBFirst(dbHandle);
        printf("DBFirst result: %d\n", first_result);
        
        if (first_result > 0) {
            printf("✅ Positioned to first record!\n");
            
            // Now try DBCopyThisRecord
            if (DBCopyThisRecord) {
                char buffer[1024];
                int buffer_size = sizeof(buffer);
                
                int copy_result = DBCopyThisRecord(dbHandle, buffer, &buffer_size);
                printf("DBCopyThisRecord after DBFirst: result=%d, size=%d\n", copy_result, buffer_size);
                
                if (copy_result > 0 && buffer_size > 0) {
                    printf("🎯 SUCCESS! Got first record: %d bytes\n", buffer_size);
                    
                    if (buffer_size >= 2 && (unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
                        printf("✅ FDO format confirmed!\n");
                        
                        FILE* fp = fopen("test_output/first_record.str", "wb");
                        if (fp) {
                            fwrite(buffer, 1, buffer_size, fp);
                            fclose(fp);
                            printf("💾 Saved first record\n");
                        }
                    }
                    
                    // Try to navigate to next records
                    if (DBNext) {
                        printf("\\nNavigating through records...\n");
                        
                        for (int i = 1; i <= 10; i++) {  // Try first 10 records
                            int next_result = DBNext(dbHandle);
                            if (next_result > 0) {
                                buffer_size = sizeof(buffer);
                                int next_copy = DBCopyThisRecord(dbHandle, buffer, &buffer_size);
                                
                                if (next_copy > 0 && buffer_size > 0) {
                                    printf("Record %d: %d bytes", i+1, buffer_size);
                                    
                                    if (buffer_size == 356) {
                                        printf(" 🎯 TARGET SIZE!");
                                        
                                        char filename[256];
                                        sprintf(filename, "test_output/record_%d.str", i+1);
                                        FILE* fp = fopen(filename, "wb");
                                        if (fp) {
                                            fwrite(buffer, 1, buffer_size, fp);
                                            fclose(fp);
                                            printf(" (saved)");
                                        }
                                    }
                                    printf("\n");
                                } else {
                                    printf("Record %d: failed to copy\n", i+1);
                                }
                            } else {
                                printf("No more records after record %d\n", i);
                                break;
                            }
                        }
                        
                        printf("\\n🎉 NAVIGATION WORKS! We can iterate through records!\n");
                    }
                }
            }
        }
    }
    
    // Test 3: Try seeking to specific positions
    if (DBSeek) {
        printf("\\n=== Testing Database Seeking ===\n");
        
        // We know from manual analysis that record at position 23057 is our target
        int seek_result = DBSeek(dbHandle, 23057);
        printf("DBSeek(23057) result: %d\n", seek_result);
        
        if (seek_result > 0 && DBCopyThisRecord) {
            char buffer[1024];
            int buffer_size = sizeof(buffer);
            
            int copy_result = DBCopyThisRecord(dbHandle, buffer, &buffer_size);
            printf("Copy after seek: result=%d, size=%d\n", copy_result, buffer_size);
            
            if (copy_result > 0 && buffer_size == 356) {
                printf("🎉 PERFECT! Found our 356-byte record by seeking!\n");
                
                FILE* fp = fopen("test_output/seeked_record.str", "wb");
                if (fp) {
                    fwrite(buffer, 1, buffer_size, fp);
                    fclose(fp);
                    printf("💾 Saved seeked record\n");
                }
            }
        }
    }
    
    // Show any errors
    if (DBGetLastError) {
        const char* error = DBGetLastError();
        if (error && strlen(error) > 0) {
            printf("\\nLast error: %s\n", error);
        }
    }
    
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 0;
}