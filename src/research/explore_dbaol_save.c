/*
 * Explore Dbaol32.dll for save/write/insert functions
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

int main() {
    printf("=== Exploring Dbaol32.dll Save/Write Functions ===\n");
    
    HMODULE hDbaol = LoadLibrary("Dbaol32.dll");
    if (!hDbaol) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    printf("✅ Loaded Dbaol32.dll\n\n");
    
    // Test save/write related function names
    const char* save_functions[] = {
        // Basic save operations
        "DBSave",
        "DBSaveRecord", 
        "DBWriteRecord",
        "DBInsertRecord",
        "DBUpdateRecord",
        "DBStoreRecord",
        "DBCreateRecord",
        "DBAddRecord",
        "DBPutRecord",
        "DBSetRecord",
        
        // Export operations (what DbViewer uses)
        "DBExport",
        "DBExportRecord",
        "DBExportSingle",
        "DBExportToFile",
        "DBSaveToFile",
        "DBWriteToFile",
        
        // Encoding/formatting operations
        "DBFormatRecord",
        "DBEncodeRecord", 
        "DBPackRecord",
        "DBCompressRecord",
        "DBConvertRecord",
        "DBProcessRecord",
        "DBTransformRecord",
        
        // FDO specific
        "DBToFDO",
        "DBCreateFDO",
        "DBFormatFDO",
        "DBEncodeFDO",
        "DBConvertToFDO",
        
        // Raw to production conversion
        "DBRawToProd",
        "DBRawToFinal",
        "DBDebugToProd",
        "DBConvertFormat",
        "DBFinalizeRecord"
    };
    
    int num_functions = sizeof(save_functions) / sizeof(save_functions[0]);
    int found_count = 0;
    
    printf("Checking %d potential save/write functions:\n\n", num_functions);
    
    for (int i = 0; i < num_functions; i++) {
        void* func = GetProcAddress(hDbaol, save_functions[i]);
        if (func) {
            printf("✅ FOUND: %-20s at %p\n", save_functions[i], func);
            found_count++;
        } else {
            printf("❌        %-20s\n", save_functions[i]);
        }
    }
    
    printf("\nSummary: Found %d functions out of %d tested\n", found_count, num_functions);
    
    if (found_count == 0) {
        printf("\n🔍 No save functions found with obvious names.\n");
        printf("The save functionality might be:\n");
        printf("1. Using generic function names\n");
        printf("2. Embedded in DbViewer.exe itself\n"); 
        printf("3. Using the existing functions in a specific way\n");
    }
    
    FreeLibrary(hDbaol);
    return 0;
}