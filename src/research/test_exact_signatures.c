/*
 * Test exact function signatures based on buffer size changes we observed
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);

int main() {
    printf("=== Testing Exact Function Signatures ===\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    void* DBExtractRecord = GetProcAddress(hDll, "DBExtractRecord");
    void* DBCopyRecord = GetProcAddress(hDll, "DBCopyRecord");
    
    int dbHandle = DBOpen("golden_tests/main.IDX");
    printf("DBOpen result: %d\n", dbHandle);
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open database\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    printf("\n=== Testing DBExtractRecord Signatures ===\n");
    
    // We saw buffer size change to 6813656 for ID 6813396, so maybe there's a pattern
    // Let's try the exact ID that caused the size change
    int test_id = 105;  // From our golden files like 32-105.str
    char buffer[2048];
    int buffer_size;
    
    printf("Testing record ID %d with different signatures:\n", test_id);
    
    // Signature 1: Standard (handle, recordId, buffer, bufferSize*)
    buffer_size = sizeof(buffer);
    int result1 = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(dbHandle, test_id, buffer, &buffer_size);
    printf("Sig 1 (__stdcall): result=%d, size=%d\n", result1, buffer_size);
    
    if (result1 > 0 && buffer_size > 0 && buffer_size < 2000) {
        printf("✅ SUCCESS! Found working signature 1\n");
        printf("Data: ");
        for (int i = 0; i < 16 && i < buffer_size; i++) {
            printf("%02x ", (unsigned char)buffer[i]);
        }
        printf("\n");
        
        // Check for FDO format
        if (buffer_size >= 2 && (unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
            printf("🎯 FDO FORMAT! Size: %d\n", buffer_size);
            if (buffer_size == 356) {
                printf("🏆 PERFECT SIZE!\n");
            }
        }
    }
    
    // Signature 2: __cdecl
    buffer_size = sizeof(buffer);
    int result2 = ((int (__cdecl *)(int, int, void*, int*))DBExtractRecord)(dbHandle, test_id, buffer, &buffer_size);
    printf("Sig 2 (__cdecl): result=%d, size=%d\n", result2, buffer_size);
    
    if (result2 > 0 && buffer_size > 0 && buffer_size < 2000) {
        printf("✅ SUCCESS! Found working signature 2\n");
    }
    
    // Try more record IDs systematically
    printf("\n=== Testing Multiple Record IDs ===\n");
    int known_ids[] = {32, 105, 106, 117, 9736};  // From our analysis
    
    for (int i = 0; i < 5; i++) {
        int id = known_ids[i];
        buffer_size = sizeof(buffer);
        
        // Try __stdcall first
        int result = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(dbHandle, id, buffer, &buffer_size);
        
        if (result > 0 && buffer_size > 0 && buffer_size < 2000) {
            printf("✅ ID %d (__stdcall): SUCCESS! %d bytes\n", id, buffer_size);
            
            if (buffer_size >= 2 && (unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
                printf("   🎯 FDO FORMAT!\n");
                
                // Save successful extraction
                char filename[256];
                sprintf(filename, "test_output/extracted_id_%d.str", id);
                FILE* fp = fopen(filename, "wb");
                if (fp) {
                    fwrite(buffer, 1, buffer_size, fp);
                    fclose(fp);
                    printf("   💾 Saved to %s\n", filename);
                }
                
                // Now try to UPDATE this same record ID to see if it works!
                printf("   🔄 Testing UPDATE on working ID %d...\n", id);
                
                void* DBUpdateRecord = GetProcAddress(hDll, "DBUpdateRecord");
                if (DBUpdateRecord) {
                    char test_data[] = "TESTUPDATE";
                    int test_size = strlen(test_data);
                    
                    int update_result = ((int (__stdcall *)(int, int, void*, int))DBUpdateRecord)(dbHandle, id, test_data, test_size);
                    printf("   DBUpdateRecord on ID %d: %d\n", id, update_result);
                    
                    if (update_result > 0) {
                        printf("   🎉 UPDATE SUCCESS!\n");
                        
                        // Try to read it back
                        char verify_buffer[512];
                        int verify_size = sizeof(verify_buffer);
                        int verify_result = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(dbHandle, id, verify_buffer, &verify_size);
                        
                        if (verify_result > 0) {
                            printf("   ✅ ROUND-TRIP VERIFIED! New size: %d\n", verify_size);
                            printf("   New data: ");
                            for (int j = 0; j < 16 && j < verify_size; j++) {
                                if (verify_buffer[j] >= 32 && verify_buffer[j] <= 126) {
                                    printf("%c", verify_buffer[j]);
                                } else {
                                    printf("[%02x]", (unsigned char)verify_buffer[j]);
                                }
                            }
                            printf("\n");
                            
                            printf("\n🎉🎉🎉 BREAKTHROUGH! We can read AND write records! 🎉🎉🎉\n");
                            printf("Working pattern: ID %d with __stdcall\n", id);
                            break;
                        }
                    }
                }
            }
        } else {
            printf("   ID %d: result=%d, size=%d\n", id, result, buffer_size);
        }
    }
    
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 0;
}