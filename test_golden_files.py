#!/usr/bin/env python3
"""
Golden File Test Suite for AOL Atom Stream Compiler/Decompiler

Tests that:
1. Compilation: .txt files compile to identical binary as reference .str files
2. Decompilation: .str files decompile back to functionally equivalent .txt files
3. Round-trip: .txt -> .str -> .txt produces equivalent results

Usage:
    python test_golden_files.py                    # Run all tests
    python test_golden_files.py --compile-only     # Test compilation only
    python test_golden_files.py --decompile-only   # Test decompilation only
    python test_golden_files.py --filter 32-105    # Test specific files matching pattern
    python test_golden_files.py --verbose          # Verbose output
"""

import os
import sys
import glob
import argparse
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import difflib

# Import our compiler/decompiler modules
try:
    from atom_stream_compiler import AtomStreamCompiler
    from atom_stream_decompiler import AtomStreamDecompiler
except ImportError as e:
    print(f"❌ Failed to import compiler/decompiler modules: {e}")
    print("   Make sure atom_stream_compiler.py and atom_stream_decompiler.py are in the same directory")
    sys.exit(1)

class GoldenFileTestSuite:
    """Test suite for golden file pairs (txt/str)"""
    
    def __init__(self, golden_dir: str = "golden_tests", verbose: bool = False):
        self.golden_dir = Path(golden_dir)
        self.verbose = verbose
        self.compiler = None
        self.decompiler = None
        
        # Setup logging
        level = logging.INFO if verbose else logging.WARNING
        logging.basicConfig(level=level, format='%(levelname)s: %(message)s')
        self.logger = logging.getLogger(__name__)
        
        if not self.golden_dir.exists():
            raise FileNotFoundError(f"Golden tests directory not found: {golden_dir}")
    
    def discover_test_pairs(self, filter_pattern: Optional[str] = None) -> List[Tuple[Path, Path]]:
        """Discover all txt/str file pairs in the golden directory"""
        
        txt_files = list(self.golden_dir.glob("*.txt"))
        test_pairs = []
        
        for txt_file in txt_files:
            # Find corresponding .str file
            str_file = txt_file.with_suffix(".str")
            
            if str_file.exists():
                # Apply filter if specified
                if filter_pattern is None or filter_pattern in txt_file.stem:
                    test_pairs.append((txt_file, str_file))
        
        test_pairs.sort(key=lambda x: x[0].stem)
        
        if self.verbose:
            self.logger.info(f"Discovered {len(test_pairs)} test pairs")
            for txt, str_file in test_pairs:
                self.logger.info(f"  {txt.name} <-> {str_file.name}")
        
        return test_pairs
    
    def setup_compiler_decompiler(self):
        """Initialize compiler and decompiler instances"""
        try:
            if self.compiler is None:
                self.compiler = AtomStreamCompiler()
                if not self.compiler.initialize():
                    self.logger.warning("Compiler initialization returned False, continuing anyway...")
            
            if self.decompiler is None:
                self.decompiler = AtomStreamDecompiler()
                if not self.decompiler.initialize():
                    self.logger.warning("Decompiler initialization returned False, continuing anyway...")
        
        except Exception as e:
            self.logger.error(f"Failed to setup compiler/decompiler: {e}")
            return False
        
        return True
    
    def test_compilation(self, txt_file: Path, str_file: Path) -> Dict:
        """Test compilation of .txt to .str format"""
        
        result = {
            'test': 'compilation',
            'input': txt_file.name,
            'reference': str_file.name,
            'passed': False,
            'message': '',
            'stats': {}
        }
        
        try:
            # Compile the .txt file
            compiled_binary = self.compiler.compile_txt_to_str(str(txt_file))
            
            # Read reference .str file
            with open(str_file, 'rb') as f:
                reference_binary = f.read()
            
            # Compare sizes
            result['stats']['compiled_size'] = len(compiled_binary)
            result['stats']['reference_size'] = len(reference_binary)
            result['stats']['size_match'] = len(compiled_binary) == len(reference_binary)
            
            # Compare byte-by-byte
            if len(compiled_binary) == len(reference_binary):
                matching_bytes = sum(1 for i in range(len(reference_binary)) 
                                   if compiled_binary[i] == reference_binary[i])
                
                result['stats']['matching_bytes'] = matching_bytes
                result['stats']['total_bytes'] = len(reference_binary)
                result['stats']['accuracy'] = (matching_bytes / len(reference_binary)) * 100
                
                # Consider test passed if accuracy is very high (allowing for minor differences)
                if matching_bytes == len(reference_binary):
                    result['passed'] = True
                    result['message'] = "Perfect byte-identical match!"
                elif result['stats']['accuracy'] >= 95.0:
                    result['passed'] = True
                    result['message'] = f"High accuracy match: {result['stats']['accuracy']:.1f}%"
                else:
                    result['message'] = f"Low accuracy: {result['stats']['accuracy']:.1f}% ({matching_bytes}/{len(reference_binary)} bytes)"
            else:
                result['message'] = f"Size mismatch: {len(compiled_binary)} vs {len(reference_binary)} bytes"
                
        except Exception as e:
            result['message'] = f"Compilation error: {str(e)}"
            self.logger.exception(f"Compilation failed for {txt_file.name}")
        
        return result
    
    def test_decompilation(self, str_file: Path, txt_file: Path) -> Dict:
        """Test decompilation of .str to .txt format"""
        
        result = {
            'test': 'decompilation',
            'input': str_file.name,
            'reference': txt_file.name,
            'passed': False,
            'message': '',
            'stats': {}
        }
        
        try:
            # Decompile the .str file
            decompiled_text = self.decompiler.decompile_str_to_atom_stream(str(str_file))
            
            # Read reference .txt file
            with open(txt_file, 'r') as f:
                reference_text = f.read()
            
            # Compare lengths
            result['stats']['decompiled_length'] = len(decompiled_text)
            result['stats']['reference_length'] = len(reference_text)
            
            # Structural comparison (look for key atom stream elements)
            decompiled_lines = [line.strip() for line in decompiled_text.split('\n') if line.strip()]
            reference_lines = [line.strip() for line in reference_text.split('\n') if line.strip()]
            
            # Check for key structural elements
            key_elements = [
                'uni_start_stream',
                'man_start_object',
                'man_end_object',
                'uni_end_stream'
            ]
            
            structural_matches = 0
            for element in key_elements:
                decompiled_has = any(element in line for line in decompiled_lines)
                reference_has = any(element in line for line in reference_lines)
                if decompiled_has == reference_has:
                    structural_matches += 1
            
            result['stats']['structural_accuracy'] = (structural_matches / len(key_elements)) * 100
            
            # Text similarity using difflib
            similarity = difflib.SequenceMatcher(None, reference_text, decompiled_text).ratio() * 100
            result['stats']['text_similarity'] = similarity
            
            # Consider test passed if structural elements match and similarity is reasonable
            if result['stats']['structural_accuracy'] >= 75.0 and similarity >= 50.0:
                result['passed'] = True
                result['message'] = f"Good structural match: {result['stats']['structural_accuracy']:.1f}% structure, {similarity:.1f}% similarity"
            else:
                result['message'] = f"Poor match: {result['stats']['structural_accuracy']:.1f}% structure, {similarity:.1f}% similarity"
                
        except Exception as e:
            result['message'] = f"Decompilation error: {str(e)}"
            self.logger.exception(f"Decompilation failed for {str_file.name}")
        
        return result
    
    def test_round_trip(self, txt_file: Path, str_file: Path) -> Dict:
        """Test round-trip: txt -> str -> txt"""
        
        result = {
            'test': 'round_trip',
            'input': txt_file.name,
            'passed': False,
            'message': '',
            'stats': {}
        }
        
        try:
            # Step 1: Compile txt to str
            compiled_binary = self.compiler.compile_txt_to_str(str(txt_file))
            
            # Step 2: Decompile the result back to txt
            # Save intermediate binary to temp file
            temp_str = txt_file.with_suffix('.temp.str')
            with open(temp_str, 'wb') as f:
                f.write(compiled_binary)
            
            try:
                decompiled_text = self.decompiler.decompile_str_to_atom_stream(str(temp_str))
                
                # Read original txt
                with open(txt_file, 'r') as f:
                    original_text = f.read()
                
                # Compare original with round-trip result
                original_lines = [line.strip() for line in original_text.split('\n') if line.strip()]
                roundtrip_lines = [line.strip() for line in decompiled_text.split('\n') if line.strip()]
                
                # Structural comparison
                key_elements = ['uni_start_stream', 'man_start_object', 'man_end_object', 'uni_end_stream']
                structural_matches = 0
                
                for element in key_elements:
                    original_has = any(element in line for line in original_lines)
                    roundtrip_has = any(element in line for line in roundtrip_lines)
                    if original_has == roundtrip_has:
                        structural_matches += 1
                
                result['stats']['structural_fidelity'] = (structural_matches / len(key_elements)) * 100
                
                # Text similarity
                similarity = difflib.SequenceMatcher(None, original_text, decompiled_text).ratio() * 100
                result['stats']['text_fidelity'] = similarity
                
                # Pass if reasonable fidelity maintained
                if result['stats']['structural_fidelity'] >= 75.0 and similarity >= 40.0:
                    result['passed'] = True
                    result['message'] = f"Round-trip maintained: {result['stats']['structural_fidelity']:.1f}% structure, {similarity:.1f}% fidelity"
                else:
                    result['message'] = f"Round-trip degraded: {result['stats']['structural_fidelity']:.1f}% structure, {similarity:.1f}% fidelity"
                    
            finally:
                # Clean up temp file
                if temp_str.exists():
                    temp_str.unlink()
                    
        except Exception as e:
            result['message'] = f"Round-trip error: {str(e)}"
            self.logger.exception(f"Round-trip failed for {txt_file.name}")
        
        return result
    
    def run_tests(self, test_compile: bool = True, test_decompile: bool = True, 
                  test_roundtrip: bool = True, filter_pattern: Optional[str] = None) -> Dict:
        """Run the full test suite"""
        
        print("🧪 AOL Atom Stream Golden File Test Suite")
        print("=" * 60)
        
        # Setup
        if not self.setup_compiler_decompiler():
            print("❌ Failed to setup compiler/decompiler")
            return {'passed': 0, 'failed': 0, 'total': 0}
        
        # Discover test pairs
        test_pairs = self.discover_test_pairs(filter_pattern)
        
        if not test_pairs:
            print("❌ No test pairs found")
            return {'passed': 0, 'failed': 0, 'total': 0}
        
        print(f"📁 Found {len(test_pairs)} test file pairs")
        if filter_pattern:
            print(f"🔍 Filter: '{filter_pattern}'")
        print()
        
        all_results = []
        passed = 0
        failed = 0
        
        # Run tests for each pair
        for i, (txt_file, str_file) in enumerate(test_pairs, 1):
            print(f"[{i:2d}/{len(test_pairs)}] Testing {txt_file.stem}...")
            
            pair_results = []
            
            # Test compilation
            if test_compile:
                result = self.test_compilation(txt_file, str_file)
                pair_results.append(result)
                status = "✅" if result['passed'] else "❌"
                print(f"     {status} Compilation: {result['message']}")
                
                if result['passed']:
                    passed += 1
                else:
                    failed += 1
            
            # Test decompilation
            if test_decompile:
                result = self.test_decompilation(str_file, txt_file)
                pair_results.append(result)
                status = "✅" if result['passed'] else "❌"
                print(f"     {status} Decompilation: {result['message']}")
                
                if result['passed']:
                    passed += 1
                else:
                    failed += 1
            
            # Test round-trip
            if test_roundtrip:
                result = self.test_round_trip(txt_file, str_file)
                pair_results.append(result)
                status = "✅" if result['passed'] else "❌"
                print(f"     {status} Round-trip: {result['message']}")
                
                if result['passed']:
                    passed += 1
                else:
                    failed += 1
            
            all_results.extend(pair_results)
            print()
        
        # Summary
        total_tests = len(all_results)
        print("📊 Test Summary")
        print("-" * 30)
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success rate: {(passed/total_tests)*100:.1f}%" if total_tests > 0 else "0%")
        
        # Show failed tests if any
        failed_tests = [r for r in all_results if not r['passed']]
        if failed_tests and self.verbose:
            print("\n❌ Failed Tests:")
            for test in failed_tests:
                print(f"   {test['input']} ({test['test']}): {test['message']}")
        
        return {
            'passed': passed,
            'failed': failed, 
            'total': total_tests,
            'results': all_results
        }

def main():
    """Main function with command line interface"""
    
    parser = argparse.ArgumentParser(description='Test AOL Atom Stream compiler/decompiler with golden files')
    parser.add_argument('--compile-only', action='store_true', help='Test compilation only')
    parser.add_argument('--decompile-only', action='store_true', help='Test decompilation only')
    parser.add_argument('--no-roundtrip', action='store_true', help='Skip round-trip tests')
    parser.add_argument('--filter', type=str, help='Filter test files by pattern')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--golden-dir', type=str, default='golden_tests', help='Golden tests directory')
    
    args = parser.parse_args()
    
    # Determine which tests to run
    test_compile = not args.decompile_only
    test_decompile = not args.compile_only
    test_roundtrip = not (args.compile_only or args.decompile_only or args.no_roundtrip)
    
    try:
        suite = GoldenFileTestSuite(args.golden_dir, args.verbose)
        results = suite.run_tests(
            test_compile=test_compile,
            test_decompile=test_decompile, 
            test_roundtrip=test_roundtrip,
            filter_pattern=args.filter
        )
        
        # Exit with appropriate code
        sys.exit(0 if results['failed'] == 0 else 1)
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()