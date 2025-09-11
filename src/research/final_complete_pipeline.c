/*
 * Complete .txt to .str pipeline using both Ada32.dll and Dbaol32.dll
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

// Ada32.dll functions
typedef int (__cdecl *AdaAssembleAtomStream_t)(const char* input, int inputSize, void* output, int* outputSize);

// Dbaol32.dll functions
typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBCreate_t)(const char* filename);

// Different potential encoding functions
typedef int (__stdcall *DBUpdateRecord_t)(int handle, int recordId, void* data, int dataSize);
typedef int (__stdcall *DBExtractRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);
typedef int (__cdecl *DBUpdateRecord_cdecl_t)(int handle, int recordId, void* data, int dataSize);
typedef int (__cdecl *DBExtractRecord_cdecl_t)(int handle, int recordId, void* buffer, int* bufferSize);

int compile_txt_to_str(const char* input_file, const char* output_file) {
    printf("=== Complete .txt to .str Pipeline ===\n");
    
    // Step 1: Load Ada32.dll
    HMODULE hAda32 = LoadLibrary("Ada32.dll");
    if (!hAda32) {
        printf("❌ Failed to load Ada32.dll\n");
        return 0;
    }
    
    AdaAssembleAtomStream_t AdaAssembleAtomStream = 
        (AdaAssembleAtomStream_t)GetProcAddress(hAda32, "AdaAssembleAtomStream");
    
    if (!AdaAssembleAtomStream) {
        printf("❌ AdaAssembleAtomStream not found\n");
        FreeLibrary(hAda32);
        return 0;
    }
    
    // Step 2: Load Dbaol32.dll
    HMODULE hDbaol = LoadLibrary("Dbaol32.dll");
    if (!hDbaol) {
        printf("❌ Failed to load Dbaol32.dll\n");
        FreeLibrary(hAda32);
        return 0;
    }
    
    DBCreate_t DBCreate = (DBCreate_t)GetProcAddress(hDbaol, "DBCreate");
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDbaol, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDbaol, "DBClose");
    void* DBUpdateRecord = GetProcAddress(hDbaol, "DBUpdateRecord");
    void* DBExtractRecord = GetProcAddress(hDbaol, "DBExtractRecord");
    
    if (!DBCreate || !DBOpen || !DBUpdateRecord || !DBExtractRecord) {
        printf("❌ Database functions not found\n");
        FreeLibrary(hAda32);
        FreeLibrary(hDbaol);
        return 0;
    }
    
    printf("✅ Both DLLs loaded successfully\n");
    
    // Step 3: Read input text file
    FILE* fp = fopen(input_file, "r");
    if (!fp) {
        printf("❌ Cannot open input file: %s\n", input_file);
        FreeLibrary(hAda32);
        FreeLibrary(hDbaol);
        return 0;
    }
    
    fseek(fp, 0, SEEK_END);
    long input_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    
    char* input_text = malloc(input_size + 1);
    fread(input_text, 1, input_size, fp);
    input_text[input_size] = 0;
    fclose(fp);
    
    printf("📖 Loaded %ld bytes from %s\n", input_size, input_file);
    
    // Step 4: Compile with Ada32.dll
    char ada32_output[2048];
    int ada32_output_size = sizeof(ada32_output);
    
    printf("\n=== Step 1: Ada32 Compilation ===\n");
    int ada32_result = AdaAssembleAtomStream(input_text, (int)input_size, ada32_output, &ada32_output_size);
    printf("AdaAssembleAtomStream result: %d, size: %d\n", ada32_result, ada32_output_size);
    
    // Check output size instead of return code (Ada32 sometimes returns 0 but still works)
    if (ada32_output_size <= 0 || ada32_output_size > 2000) {
        printf("❌ Ada32 compilation failed - invalid output size\n");
        free(input_text);
        FreeLibrary(hAda32);
        FreeLibrary(hDbaol);
        return 0;
    }
    
    printf("✅ Ada32 compilation successful: %d bytes\n", ada32_output_size);
    printf("Ada32 header: ");
    for (int i = 0; i < 16 && i < ada32_output_size; i++) {
        printf("%02x ", (unsigned char)ada32_output[i]);
    }
    printf("\n");
    
    // Step 5: Create temporary database for encoding
    printf("\n=== Step 2: Database Encoding ===\n");
    const char* temp_db = "temp_encoding.idx";
    remove(temp_db);
    
    int create_result = DBCreate(temp_db);
    printf("DBCreate result: %d\n", create_result);
    
    if (create_result <= 0) {
        printf("❌ Failed to create database\n");
        free(input_text);
        FreeLibrary(hAda32);
        FreeLibrary(hDbaol);
        return 0;
    }
    
    int db_handle = DBOpen(temp_db);
    printf("DBOpen result: %d\n", db_handle);
    
    if (db_handle <= 0) {
        printf("❌ Failed to open database\n");
        free(input_text);
        FreeLibrary(hAda32);
        FreeLibrary(hDbaol);
        return 0;
    }
    
    // Step 6: Try to encode using database functions
    printf("Attempting database encoding...\n");
    
    int record_id = 1;
    int success = 0;
    
    // Try __stdcall first
    int update_stdcall = ((DBUpdateRecord_t)DBUpdateRecord)(db_handle, record_id, ada32_output, ada32_output_size);
    printf("DBUpdateRecord (__stdcall): %d\n", update_stdcall);
    
    if (update_stdcall > 0) {
        printf("✅ __stdcall update successful!\n");
        success = 1;
    } else {
        // Try __cdecl
        int update_cdecl = ((DBUpdateRecord_cdecl_t)DBUpdateRecord)(db_handle, record_id, ada32_output, ada32_output_size);
        printf("DBUpdateRecord (__cdecl): %d\n", update_cdecl);
        
        if (update_cdecl > 0) {
            printf("✅ __cdecl update successful!\n");
            success = 1;
        }
    }
    
    if (success) {
        // Try to extract the encoded result
        char encoded_output[1024];
        int encoded_size = sizeof(encoded_output);
        
        // Try __stdcall extract
        int extract_stdcall = ((DBExtractRecord_t)DBExtractRecord)(db_handle, record_id, encoded_output, &encoded_size);
        printf("DBExtractRecord (__stdcall): %d, size: %d\n", extract_stdcall, encoded_size);
        
        if (extract_stdcall <= 0) {
            // Try __cdecl extract
            encoded_size = sizeof(encoded_output);
            int extract_cdecl = ((DBExtractRecord_cdecl_t)DBExtractRecord)(db_handle, record_id, encoded_output, &encoded_size);
            printf("DBExtractRecord (__cdecl): %d, size: %d\n", extract_cdecl, encoded_size);
        }
        
        if (encoded_size > 0 && encoded_size < ada32_output_size) {
            printf("🎉 ENCODING SUCCESS!\n");
            printf("Raw Ada32: %d bytes → Encoded: %d bytes\n", ada32_output_size, encoded_size);
            printf("Compression: %.1f%%\n", (float)(ada32_output_size - encoded_size) / ada32_output_size * 100);
            
            printf("Encoded header: ");
            for (int i = 0; i < 16 && i < encoded_size; i++) {
                printf("%02x ", (unsigned char)encoded_output[i]);
            }
            printf("\n");
            
            // Check for FDO format
            if (encoded_size >= 2 && 
                (unsigned char)encoded_output[0] == 0x40 && 
                (unsigned char)encoded_output[1] == 0x01) {
                printf("🎯 FDO FORMAT CONFIRMED!\n");
                
                if (encoded_size == 356) {
                    printf("🏆 PERFECT SIZE! EXACT TARGET!\n");
                }
                
                // Save the final result
                FILE* output_fp = fopen(output_file, "wb");
                if (output_fp) {
                    fwrite(encoded_output, 1, encoded_size, output_fp);
                    fclose(output_fp);
                    printf("💾 Saved to %s\n", output_file);
                    
                    printf("\n🎉🎉🎉 COMPLETE PIPELINE SUCCESS! 🎉🎉🎉\n");
                    printf("✅ %s → %s (%d bytes)\n", input_file, output_file, encoded_size);
                    
                    // Clean up
                    DBClose(db_handle);
                    remove(temp_db);
                    free(input_text);
                    FreeLibrary(hAda32);
                    FreeLibrary(hDbaol);
                    return 1;
                }
            }
        }
    }
    
    printf("❌ Database encoding failed - using Ada32 output directly\n");
    printf("💡 This produces the 413-byte 'debug' format instead of 356-byte 'production' format\n");
    
    // Fallback: save Ada32 output directly
    FILE* output_fp = fopen(output_file, "wb");
    if (output_fp) {
        fwrite(ada32_output, 1, ada32_output_size, output_fp);
        fclose(output_fp);
        printf("💾 Saved Ada32 output to %s (%d bytes)\n", output_file, ada32_output_size);
    }
    
    // Clean up
    DBClose(db_handle);
    remove(temp_db);
    free(input_text);
    FreeLibrary(hAda32);
    FreeLibrary(hDbaol);
    return 0;
}

int main() {
    printf("=== AOL .txt to .str Compiler ===\n");
    
    // Test with our known working file
    const char* input_file = "clean_32-105.txt";
    const char* output_file = "test_output/FINAL_COMPILED_RESULT.str";
    
    int success = compile_txt_to_str(input_file, output_file);
    
    if (success) {
        printf("\n🏆 MISSION ACCOMPLISHED! 🏆\n");
        printf("Successfully compiled %s to %s\n", input_file, output_file);
        
        // Compare with golden file
        FILE* golden_fp = fopen("golden_tests/32-105.str", "rb");
        FILE* result_fp = fopen(output_file, "rb");
        
        if (golden_fp && result_fp) {
            fseek(golden_fp, 0, SEEK_END);
            fseek(result_fp, 0, SEEK_END);
            long golden_size = ftell(golden_fp);
            long result_size = ftell(result_fp);
            
            printf("\n📊 Final Comparison:\n");
            printf("Golden file: %ld bytes\n", golden_size);
            printf("Our result: %ld bytes\n", result_size);
            
            if (golden_size == result_size) {
                fseek(golden_fp, 0, SEEK_SET);
                fseek(result_fp, 0, SEEK_SET);
                
                char* golden_data = malloc(golden_size);
                char* result_data = malloc(result_size);
                fread(golden_data, 1, golden_size, golden_fp);
                fread(result_data, 1, result_size, result_fp);
                
                int matches = 0;
                for (long i = 0; i < golden_size; i++) {
                    if (golden_data[i] == result_data[i]) matches++;
                }
                
                printf("Accuracy: %d/%ld (%.1f%%)\n", matches, golden_size, (float)matches/golden_size*100);
                
                if (matches == golden_size) {
                    printf("🎉🎉🎉 PERFECT MATCH! COMPILER IS COMPLETE! 🎉🎉🎉\n");
                }
                
                free(golden_data);
                free(result_data);
            }
            
            fclose(golden_fp);
            fclose(result_fp);
        }
    } else {
        printf("\n⚠️ Partial success - database encoding needs more work\n");
        printf("Ada32 compilation works, but missing the final compression step\n");
    }
    
    return success;
}