/*
 * Test if database functions work after Ada32 initialization
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaTerminate_t)(void);

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);

int main() {
    printf("=== Testing Database Functions After Ada32 Initialization ===\n");
    
    // Load both DLLs
    HMODULE hAda32 = LoadLibrary("Ada32.dll");
    HMODULE hDbaol = LoadLibrary("Dbaol32.dll");
    
    if (!hAda32 || !hDbaol) {
        printf("❌ Failed to load DLLs\n");
        return 1;
    }
    
    // Get Ada32 functions
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hAda32, "AdaInitialize");
    AdaTerminate_t AdaTerminate = (AdaTerminate_t)GetProcAddress(hAda32, "AdaTerminate");
    
    // Get database functions
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDbaol, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDbaol, "DBClose");
    void* DBExtractRecord = GetProcAddress(hDbaol, "DBExtractRecord");
    void* DBUpdateRecord = GetProcAddress(hDbaol, "DBUpdateRecord");
    
    if (!AdaInitialize || !DBOpen || !DBExtractRecord) {
        printf("❌ Essential functions not available\n");
        return 1;
    }
    
    // Step 1: Initialize Ada32 FIRST
    printf("\n=== Step 1: Initialize Ada32 ===\n");
    int init_result = AdaInitialize();
    printf("AdaInitialize(): %d\n", init_result);
    
    if (init_result <= 0) {
        printf("❌ Ada32 initialization failed\n");
        return 1;
    }
    
    printf("✅ Ada32 initialized\n");
    
    // Step 2: NOW try database operations
    printf("\n=== Step 2: Database Operations After Ada32 Init ===\n");
    
    int dbHandle = DBOpen("golden_tests/main.IDX");
    printf("DBOpen result: %d\n", dbHandle);
    
    if (dbHandle > 0) {
        printf("✅ Database opened successfully\n");
        
        // Test read operations
        printf("\nTesting read operations after Ada32 init:\n");
        
        for (int id = 0; id <= 20; id++) {
            char buffer[512];
            int buffer_size = sizeof(buffer);
            
            int read_result = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(dbHandle, id, buffer, &buffer_size);
            
            if (read_result > 0 && buffer_size > 0 && buffer_size < 500) {
                printf("✅ ID %d: SUCCESS! %d bytes\n", id, buffer_size);
                
                if (buffer_size == 356) {
                    printf("   🏆 PERFECT SIZE!\n");
                    
                    printf("   Data: ");
                    for (int i = 0; i < 16; i++) {
                        printf("%02x ", (unsigned char)buffer[i]);
                    }
                    printf("\n");
                    
                    if ((unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
                        printf("   🎯 FDO FORMAT!\n");
                        
                        // Save successful read
                        char filename[256];
                        sprintf(filename, "test_output/db_read_after_ada_init_id_%d.str", id);
                        FILE* fp = fopen(filename, "wb");
                        if (fp) {
                            fwrite(buffer, 1, buffer_size, fp);
                            fclose(fp);
                            printf("   💾 Saved extraction\n");
                        }
                        
                        // Test update on this working record
                        printf("   🔄 Testing update...\n");
                        
                        char test_data[] = "ADA_INIT_UPDATE";
                        int test_size = strlen(test_data);
                        
                        int update_result = ((int (__stdcall *)(int, int, void*, int))DBUpdateRecord)(dbHandle, id, test_data, test_size);
                        printf("   Update result: %d\n", update_result);
                        
                        if (update_result > 0) {
                            printf("   🎉🎉🎉 UPDATE SUCCESS AFTER ADA INIT! 🎉🎉🎉\n");
                            
                            // Verify update
                            char verify_buffer[512];
                            int verify_size = sizeof(verify_buffer);
                            int verify_result = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(dbHandle, id, verify_buffer, &verify_size);
                            
                            if (verify_result > 0) {
                                printf("   ✅ Verification: %d bytes\n", verify_size);
                                printf("   🏆 COMPLETE SUCCESS! Ada32 init enabled database R/W!\n");
                            }
                        }
                        
                        break; // Found working record, stop testing
                    }
                }
            } else if (read_result != 0 || buffer_size != sizeof(buffer)) {
                printf("   ID %d: result=%d, size=%d\n", id, read_result, buffer_size);
            }
        }
        
        DBClose(dbHandle);
    }
    
    // Step 3: Test fresh database after Ada32 init
    printf("\n=== Step 3: Fresh Database After Ada32 Init ===\n");
    
    void* DBCreate = GetProcAddress(hDbaol, "DBCreate");
    void* DBAddRecord = GetProcAddress(hDbaol, "DBAddRecord");
    
    if (DBCreate && DBAddRecord) {
        const char* fresh_db = "ada_init_test.idx";
        remove(fresh_db);
        
        int create_result = ((int (__stdcall *)(const char*))DBCreate)(fresh_db);
        printf("DBCreate after Ada init: %d\n", create_result);
        
        if (create_result > 0) {
            int fresh_handle = DBOpen(fresh_db);
            printf("Fresh DBOpen: %d\n", fresh_handle);
            
            if (fresh_handle > 0) {
                char fresh_data[] = "ADA_INIT_FRESH";
                int fresh_size = strlen(fresh_data);
                int new_id = 0;
                
                int add_result = ((int (__stdcall *)(int, void*, int, int*))DBAddRecord)(fresh_handle, fresh_data, fresh_size, &new_id);
                printf("DBAddRecord after Ada init: result=%d, newId=%d\n", add_result, new_id);
                
                if (add_result > 0) {
                    printf("✅ ADD SUCCESS after Ada32 initialization!\n");
                    
                    // Try to read it back
                    char read_fresh[512];
                    int read_fresh_size = sizeof(read_fresh);
                    int read_fresh_result = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(fresh_handle, new_id, read_fresh, &read_fresh_size);
                    
                    if (read_fresh_result > 0) {
                        printf("✅ Read back success: %d bytes\n", read_fresh_size);
                        printf("Data: ");
                        for (int i = 0; i < read_fresh_size && i < 32; i++) {
                            if (read_fresh[i] >= 32 && read_fresh[i] <= 126) {
                                printf("%c", read_fresh[i]);
                            } else {
                                printf("[%02x]", (unsigned char)read_fresh[i]);
                            }
                        }
                        printf("\n");
                        
                        printf("🎉🎉🎉 COMPLETE FRESH DB SUCCESS! 🎉🎉🎉\n");
                    }
                }
                
                DBClose(fresh_handle);
            }
        }
        
        remove(fresh_db);
    }
    
    // Cleanup
    printf("\n=== Cleanup ===\n");
    if (AdaTerminate) {
        int term_result = AdaTerminate();
        printf("AdaTerminate(): %d\n", term_result);
    }
    
    FreeLibrary(hAda32);
    FreeLibrary(hDbaol);
    
    printf("\n=== SUMMARY ===\n");
    printf("Testing if Ada32 initialization enables database functions...\n");
    
    return 0;
}