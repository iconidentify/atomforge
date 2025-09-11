/*
 * Dbaol Bridge - Interface to official AOL database functions
 * This uses the same functions as Dbview.exe "Export Single Record"
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Dbaol32.dll function typedefs (using __stdcall based on typical Windows DLL conventions)
typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBExtractRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);
typedef int (__stdcall *DBGetInfo_t)(int handle, void* info);
typedef const char* (__stdcall *DBGetLastError_t)(void);

int main(int argc, char* argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: dbaol_bridge.exe <command> [args...]\n");
        fprintf(stderr, "Commands:\n");
        fprintf(stderr, "  test - Test Dbaol32.dll loading\n");
        fprintf(stderr, "  open <dbfile> - Open database and show info\n");
        fprintf(stderr, "  extract <dbfile> <recordid> - Extract record using official functions\n");
        return 1;
    }
    
    char* command = argv[1];
    
    // Load Dbaol32.dll
    HMODULE hDbaol = LoadLibrary("Dbaol32.dll");
    if (!hDbaol) {
        fprintf(stderr, "ERROR: Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    printf("✅ Loaded Dbaol32.dll successfully\n");
    
    // Get function pointers - try both calling conventions
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDbaol, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDbaol, "DBClose");
    DBExtractRecord_t DBExtractRecord = (DBExtractRecord_t)GetProcAddress(hDbaol, "DBExtractRecord");
    DBGetInfo_t DBGetInfo = (DBGetInfo_t)GetProcAddress(hDbaol, "DBGetInfo");
    DBGetLastError_t DBGetLastError = (DBGetLastError_t)GetProcAddress(hDbaol, "DBGetLastError");
    
    if (strcmp(command, "test") == 0) {
        printf("=== Dbaol32.dll Function Test ===\n");
        printf("DBOpen: %s\n", DBOpen ? "✅ Found" : "❌ NOT FOUND");
        printf("DBClose: %s\n", DBClose ? "✅ Found" : "❌ NOT FOUND");
        printf("DBExtractRecord: %s\n", DBExtractRecord ? "✅ Found" : "❌ NOT FOUND");
        printf("DBGetInfo: %s\n", DBGetInfo ? "✅ Found" : "❌ NOT FOUND");
        printf("DBGetLastError: %s\n", DBGetLastError ? "✅ Found" : "❌ NOT FOUND");
        
        FreeLibrary(hDbaol);
        return 0;
    }
    
    if (strcmp(command, "open") == 0) {
        if (argc < 3) {
            fprintf(stderr, "Usage: dbaol_bridge.exe open <dbfile>\n");
            FreeLibrary(hDbaol);
            return 1;
        }
        
        char* dbfile = argv[2];
        printf("=== Database Open Test ===\n");
        printf("Database file: %s\n", dbfile);
        
        if (!DBOpen) {
            fprintf(stderr, "ERROR: DBOpen function not found\n");
            FreeLibrary(hDbaol);
            return 1;
        }
        
        int dbHandle = DBOpen(dbfile);
        printf("DBOpen result: %d\n", dbHandle);
        
        if (dbHandle > 0) {
            printf("✅ Database opened successfully!\n");
            
            if (DBGetInfo) {
                char info[1024];
                int result = DBGetInfo(dbHandle, info);
                printf("DBGetInfo result: %d\n", result);
                if (result > 0) {
                    printf("Database info: %s\n", info);
                }
            }
            
            if (DBClose) {
                DBClose(dbHandle);
                printf("Database closed\n");
            }
        } else {
            printf("❌ Failed to open database\n");
            if (DBGetLastError) {
                const char* error = DBGetLastError();
                if (error) {
                    printf("Error: %s\n", error);
                }
            }
        }
        
        FreeLibrary(hDbaol);
        return dbHandle > 0 ? 0 : 1;
    }
    
    if (strcmp(command, "extract") == 0) {
        if (argc < 4) {
            fprintf(stderr, "Usage: dbaol_bridge.exe extract <dbfile> <recordid>\n");
            FreeLibrary(hDbaol);
            return 1;
        }
        
        char* dbfile = argv[2];
        int recordId = atoi(argv[3]);
        
        printf("=== Official Record Extraction ===\n");
        printf("Database: %s\n", dbfile);
        printf("Record ID: %d\n", recordId);
        
        if (!DBOpen || !DBExtractRecord) {
            fprintf(stderr, "ERROR: Required functions not found\n");
            FreeLibrary(hDbaol);
            return 1;
        }
        
        int dbHandle = DBOpen(dbfile);
        printf("DBOpen result: %d\n", dbHandle);
        
        if (dbHandle <= 0) {
            printf("❌ Failed to open database\n");
            if (DBGetLastError) {
                const char* error = DBGetLastError();
                if (error) {
                    printf("Error: %s\n", error);
                }
            }
            FreeLibrary(hDbaol);
            return 1;
        }
        
        // Extract record using official function
        char buffer[65536];  // Large buffer
        int bufferSize = sizeof(buffer);
        
        int result = DBExtractRecord(dbHandle, recordId, buffer, &bufferSize);
        printf("DBExtractRecord result: %d\n", result);
        printf("Buffer size: %d\n", bufferSize);
        
        if (result > 0 && bufferSize > 0) {
            // Write the extracted .str data to stdout
            fwrite(buffer, 1, bufferSize, stdout);
            fflush(stdout);
            
            fprintf(stderr, "✅ SUCCESS: Extracted %d bytes for record %d\n", bufferSize, recordId);
        } else {
            fprintf(stderr, "❌ Extraction failed\n");
            if (DBGetLastError) {
                const char* error = DBGetLastError();
                if (error) {
                    fprintf(stderr, "Error: %s\n", error);
                }
            }
        }
        
        if (DBClose) {
            DBClose(dbHandle);
        }
        
        FreeLibrary(hDbaol);
        return result > 0 ? 0 : 1;
    }
    
    fprintf(stderr, "ERROR: Unknown command: %s\n", command);
    FreeLibrary(hDbaol);
    return 1;
}