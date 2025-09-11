/*
 * Focus on the patterns that showed activity in the extensive probe
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);

int main() {
    printf("=== Testing Discovered Active Patterns ===\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    void* DBExtractRecord = GetProcAddress(hDll, "DBExtractRecord");
    void* DBUpdateRecord = GetProcAddress(hDll, "DBUpdateRecord");
    
    int dbHandle = DBOpen("golden_tests/main.IDX");
    printf("DBOpen result: %d\n", dbHandle);
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open database\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    // Focus on IDs that showed activity: 42, 61
    int active_ids[] = {42, 61};
    
    for (int i = 0; i < 2; i++) {
        int record_id = active_ids[i];
        printf("\n=== Testing Record ID %d (showed activity) ===\n", record_id);
        
        // Test the signature that showed buffer changes: (handle, buffer, bufferSize*, recordId)
        char buffer[1024];
        int buffer_size = sizeof(buffer);
        memset(buffer, 0xAA, sizeof(buffer)); // Different pattern this time
        
        printf("Before call: buffer[0]=0x%02x, size=%d\n", (unsigned char)buffer[0], buffer_size);
        
        int result = ((int (__stdcall *)(int, void*, int*, int))DBExtractRecord)(dbHandle, buffer, &buffer_size, record_id);
        
        printf("After call: result=%d, buffer[0]=0x%02x, size=%d\n", 
               result, (unsigned char)buffer[0], buffer_size);
        
        if (buffer[0] != (char)0xAA || buffer_size != sizeof(buffer)) {
            printf("✅ FUNCTION EXECUTED! Buffer or size changed\n");
            
            if (result > 0 && buffer_size > 0 && buffer_size < 1000) {
                printf("🎉 SUCCESS! Retrieved %d bytes\n", buffer_size);
                
                printf("Data: ");
                for (int j = 0; j < 32 && j < buffer_size; j++) {
                    printf("%02x ", (unsigned char)buffer[j]);
                }
                printf("\n");
                
                // Check for FDO format
                if (buffer_size >= 2 && (unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
                    printf("🎯 FDO FORMAT DETECTED!\n");
                    
                    if (buffer_size == 356) {
                        printf("🏆 PERFECT SIZE - THIS IS OUR TARGET!\n");
                        
                        // Save this successful read
                        char filename[256];
                        sprintf(filename, "test_output/successful_read_id_%d.str", record_id);
                        FILE* fp = fopen(filename, "wb");
                        if (fp) {
                            fwrite(buffer, 1, buffer_size, fp);
                            fclose(fp);
                            printf("💾 Saved to %s\n", filename);
                        }
                        
                        // NOW TEST UPDATE ON THIS WORKING ID!
                        printf("\n🔄 Testing UPDATE on working ID %d...\n", record_id);
                        
                        char test_data[] = "UPDATE_TEST_123";
                        int test_size = strlen(test_data);
                        
                        // Try the same parameter order that worked for reading
                        int update_result = ((int (__stdcall *)(int, void*, int, int))DBUpdateRecord)(dbHandle, test_data, test_size, record_id);
                        printf("Update result (same param order): %d\n", update_result);
                        
                        if (update_result > 0) {
                            printf("✅ UPDATE SUCCESS!\n");
                            
                            // Verify by reading back
                            memset(buffer, 0xBB, sizeof(buffer));
                            buffer_size = sizeof(buffer);
                            
                            int verify_result = ((int (__stdcall *)(int, void*, int*, int))DBExtractRecord)(dbHandle, buffer, &buffer_size, record_id);
                            
                            if (verify_result > 0 && buffer_size > 0) {
                                printf("🎉🎉🎉 ROUND-TRIP SUCCESS! 🎉🎉🎉\n");
                                printf("Updated size: %d bytes\n", buffer_size);
                                printf("Updated data: ");
                                for (int k = 0; k < buffer_size && k < 64; k++) {
                                    if (buffer[k] >= 32 && buffer[k] <= 126) {
                                        printf("%c", buffer[k]);
                                    } else {
                                        printf("[%02x]", (unsigned char)buffer[k]);
                                    }
                                }
                                printf("\n");
                                
                                printf("\n🏆 BREAKTHROUGH! FOUND WORKING READ/WRITE PATTERN! 🏆\n");
                                printf("Working signature: (handle, buffer, size*, recordId)\n");
                                printf("Working record ID: %d\n", record_id);
                                
                                break; // Success, no need to test more
                            }
                        } else {
                            // Try standard parameter order for update
                            int update_result2 = ((int (__stdcall *)(int, int, void*, int))DBUpdateRecord)(dbHandle, record_id, test_data, test_size);
                            printf("Update result (standard order): %d\n", update_result2);
                        }
                    }
                }
            } else {
                printf("Function executed but result/size indicate error\n");
            }
        } else {
            printf("No changes detected - function may not have executed properly\n");
        }
    }
    
    // Also test a few more IDs around the active ones
    printf("\n=== Testing IDs Around Active Ones ===\n");
    for (int id = 40; id <= 65; id++) {
        char small_buffer[512];
        int small_size = sizeof(small_buffer);
        memset(small_buffer, 0xDD, sizeof(small_buffer));
        
        int result = ((int (__stdcall *)(int, void*, int*, int))DBExtractRecord)(dbHandle, small_buffer, &small_size, id);
        
        if (small_buffer[0] != (char)0xDD || small_size != sizeof(small_buffer) || result != 0) {
            printf("ID %d: result=%d, size=%d, buffer[0]=0x%02x\n", 
                   id, result, small_size, (unsigned char)small_buffer[0]);
            
            if (result > 0 && small_size > 0 && small_size < 500) {
                printf("  ✅ Potential success!\n");
            }
        }
    }
    
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 0;
}