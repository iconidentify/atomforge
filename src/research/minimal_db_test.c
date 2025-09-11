/*
 * Minimal test focusing on the exact database that Dbviewer uses successfully
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);

int main() {
    printf("=== Minimal Database Test - Focus on What Works ===\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    void* DBExtractRecord = GetProcAddress(hDll, "DBExtractRecord");
    
    printf("✅ Basic functions loaded\n");
    
    // Test the exact database file that Dbviewer uses
    printf("\n=== Testing main.IDX (Dbviewer's database) ===\n");
    
    int dbHandle = DBOpen("golden_tests/main.IDX");
    printf("DBOpen(main.IDX): %d\n", dbHandle);
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open main.IDX\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    // We know from manual extraction that there's data at position 23057
    // If records are indexed sequentially, that might be record: 23057 / 356 = 64.7
    // So maybe record IDs around 64, 65 exist
    
    printf("\n=== Testing Calculated Record IDs ===\n");
    
    // Calculate potential record IDs based on file positions
    long file_position = 23057;
    int record_size = 356;
    int calculated_id = file_position / record_size;
    
    printf("Calculated record ID from position %ld: %d\n", file_position, calculated_id);
    
    // Test a range around this calculated ID
    for (int offset = -10; offset <= 10; offset++) {
        int test_id = calculated_id + offset;
        if (test_id < 0) continue;
        
        char buffer[512];
        int buffer_size = sizeof(buffer);
        
        // Try the most standard signature
        int result = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(dbHandle, test_id, buffer, &buffer_size);
        
        if (result != 0 || buffer_size != sizeof(buffer)) {
            printf("ID %d: result=%d, size=%d\n", test_id, result, buffer_size);
            
            if (result > 0 && buffer_size > 0 && buffer_size < 500) {
                printf("  ✅ POTENTIAL SUCCESS!\n");
                printf("  First 16 bytes: ");
                for (int i = 0; i < 16 && i < buffer_size; i++) {
                    printf("%02x ", (unsigned char)buffer[i]);
                }
                printf("\n");
                
                if (buffer_size >= 2 && (unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
                    printf("  🎯 FDO FORMAT!\n");
                    if (buffer_size == 356) {
                        printf("  🏆 PERFECT SIZE!\n");
                        
                        // Save this success
                        char filename[256];
                        sprintf(filename, "test_output/found_record_id_%d.str", test_id);
                        FILE* fp = fopen(filename, "wb");
                        if (fp) {
                            fwrite(buffer, 1, buffer_size, fp);
                            fclose(fp);
                            printf("  💾 Saved successful extraction\n");
                        }
                        
                        printf("\n🎉 FOUND WORKING RECORD ID: %d 🎉\n", test_id);
                        break;
                    }
                }
            }
        }
    }
    
    printf("\n=== Testing Very Simple Record IDs ===\n");
    
    // Maybe records are just numbered 1, 2, 3, etc.
    for (int simple_id = 1; simple_id <= 20; simple_id++) {
        char simple_buffer[512];
        int simple_size = sizeof(simple_buffer);
        
        int simple_result = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(dbHandle, simple_id, simple_buffer, &simple_size);
        
        if (simple_result > 0 && simple_size > 0 && simple_size < 500) {
            printf("Simple ID %d: SUCCESS! %d bytes\n", simple_id, simple_size);
            
            if (simple_size == 356) {
                printf("  🏆 PERFECT SIZE!\n");
                
                printf("  Data: ");
                for (int i = 0; i < 16; i++) {
                    printf("%02x ", (unsigned char)simple_buffer[i]);
                }
                printf("\n");
            }
        }
    }
    
    printf("\n=== Testing Alternative Approaches ===\n");
    
    // Maybe the function signature is completely different
    // Let's try some radical alternatives
    
    // Alternative 1: Maybe it's a direct file read operation disguised as DBExtractRecord
    char alt_buffer[512];
    int alt_size = 356; // Exact size we want
    
    // Try: (handle, file_position, buffer, size)
    int alt_result1 = ((int (__stdcall *)(int, int, void*, int))DBExtractRecord)(dbHandle, 23057, alt_buffer, alt_size);
    if (alt_result1 != 0) {
        printf("Alternative 1 (position-based): result=%d\n", alt_result1);
        
        if (alt_result1 > 0) {
            printf("  Data: ");
            for (int i = 0; i < 16; i++) {
                printf("%02x ", (unsigned char)alt_buffer[i]);
            }
            printf("\n");
        }
    }
    
    // Alternative 2: Maybe buffer size needs to be pre-set to expected size
    alt_size = 356;
    int alt_result2 = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(dbHandle, 1, alt_buffer, &alt_size);
    if (alt_result2 != 0 || alt_size != 356) {
        printf("Alternative 2 (pre-sized): result=%d, size=%d\n", alt_result2, alt_size);
    }
    
    printf("\n=== Summary ===\n");
    printf("We know the database contains valid data (manual extraction works)\n");
    printf("Dbviewer successfully uses these same DLL functions\n");
    printf("Our challenge: Find the exact calling pattern Dbviewer uses\n");
    
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 0;
}