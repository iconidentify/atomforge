/*
 * Dbview Bridge - Interface to official AOL database functions
 * These are the functions used by the "Export Single Record" feature
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Dbaol32.dll function typedefs
typedef int (__cdecl *DBOpen_t)(const char* filename);
typedef int (__cdecl *DBClose_t)(int handle);
typedef int (__cdecl *DBExtractRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);
typedef int (__cdecl *DBCopyRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);
typedef int (__cdecl *DBGetInfo_t)(int handle, void* info);
typedef const char* (__cdecl *DBGetLastError_t)(void);

// Ada32.dll functions (we know these work)
typedef int (__cdecl *AdaInitialize_t)(void);

int main(int argc, char* argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: dbview_bridge.exe <command> [args...]\n");
        fprintf(stderr, "Commands:\n");
        fprintf(stderr, "  explore - Test available functions\n");
        fprintf(stderr, "  extract <dbfile> <recordid> - Extract record using official functions\n");
        return 1;
    }
    
    char* command = argv[1];
    
    // Load both DLLs
    HMODULE hDbaol = LoadLibrary("Dbaol32.dll");
    HMODULE hAda32 = LoadLibrary("Ada32.dll");
    
    if (!hDbaol) {
        fprintf(stderr, "ERROR: Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    if (!hAda32) {
        fprintf(stderr, "ERROR: Failed to load Ada32.dll\n");
        FreeLibrary(hDbaol);
        return 1;
    }
    
    // Get function pointers
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDbaol, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDbaol, "DBClose");
    DBExtractRecord_t DBExtractRecord = (DBExtractRecord_t)GetProcAddress(hDbaol, "DBExtractRecord");
    DBCopyRecord_t DBCopyRecord = (DBCopyRecord_t)GetProcAddress(hDbaol, "DBCopyRecord");
    DBGetLastError_t DBGetLastError = (DBGetLastError_t)GetProcAddress(hDbaol, "DBGetLastError");
    
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(hAda32, "AdaInitialize");
    
    if (strcmp(command, "explore") == 0) {
        printf("=== Dbview Bridge Function Explorer ===\n");
        
        printf("Dbaol32.dll functions:\n");
        printf("  DBOpen: %s\n", DBOpen ? "Found" : "NOT FOUND");
        printf("  DBClose: %s\n", DBClose ? "Found" : "NOT FOUND");
        printf("  DBExtractRecord: %s\n", DBExtractRecord ? "Found" : "NOT FOUND");
        printf("  DBCopyRecord: %s\n", DBCopyRecord ? "Found" : "NOT FOUND");
        printf("  DBGetLastError: %s\n", DBGetLastError ? "Found" : "NOT FOUND");
        
        printf("\nAda32.dll functions:\n");
        printf("  AdaInitialize: %s\n", AdaInitialize ? "Found" : "NOT FOUND");
        
        if (AdaInitialize) {
            int init_result = AdaInitialize();
            printf("  AdaInitialize result: %d\n", init_result);
        }
        
        FreeLibrary(hDbaol);
        FreeLibrary(hAda32);
        return 0;
    }
    
    if (strcmp(command, "extract") == 0) {
        if (argc < 4) {
            fprintf(stderr, "Usage: dbview_bridge.exe extract <dbfile> <recordid>\n");
            FreeLibrary(hDbaol);
            FreeLibrary(hAda32);
            return 1;
        }
        
        char* dbfile = argv[2];
        int recordId = atoi(argv[3]);
        
        printf("=== Official Database Record Extraction ===\n");
        printf("Database: %s\n", dbfile);
        printf("Record ID: %d\n", recordId);
        
        if (!DBOpen || !DBExtractRecord || !DBClose) {
            fprintf(stderr, "ERROR: Required database functions not found\n");
            FreeLibrary(hDbaol);
            FreeLibrary(hAda32);
            return 1;
        }
        
        // Try to open database
        int dbHandle = DBOpen(dbfile);
        printf("DBOpen result: %d\n", dbHandle);
        
        if (dbHandle <= 0) {
            if (DBGetLastError) {
                printf("Database error: %s\n", DBGetLastError());
            }
            fprintf(stderr, "ERROR: Failed to open database\n");
            FreeLibrary(hDbaol);
            FreeLibrary(hAda32);
            return 1;
        }
        
        // Try to extract record
        char buffer[65536];  // Large buffer for record data
        int bufferSize = sizeof(buffer);
        
        int result = DBExtractRecord(dbHandle, recordId, buffer, &bufferSize);
        printf("DBExtractRecord result: %d\n", result);
        printf("Buffer size: %d\n", bufferSize);
        
        if (result > 0 && bufferSize > 0) {
            // Write the extracted record to stdout as binary
            fwrite(buffer, 1, bufferSize, stdout);
            fflush(stdout);
            
            fprintf(stderr, "SUCCESS: Extracted %d bytes for record %d\n", bufferSize, recordId);
        } else {
            if (DBGetLastError) {
                fprintf(stderr, "Database error: %s\n", DBGetLastError());
            }
            fprintf(stderr, "ERROR: Failed to extract record\n");
        }
        
        DBClose(dbHandle);
        FreeLibrary(hDbaol);
        FreeLibrary(hAda32);
        return result > 0 ? 0 : 1;
    }
    
    fprintf(stderr, "ERROR: Unknown command: %s\n", command);
    FreeLibrary(hDbaol);
    FreeLibrary(hAda32);
    return 1;
}