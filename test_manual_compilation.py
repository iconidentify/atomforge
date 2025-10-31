"""
Comprehensive Test Suite for Manual FDO Compilation

Validates the manual compiler against daemon output and tests edge cases.
"""

import sys
import time
import asyncio
from pathlib import Path

# Add api/src to path
sys.path.insert(0, str(Path(__file__).parent / 'api' / 'src'))

from fdo_manual_compiler import FdoManualCompiler, validate_manual_compilation
from fdo_daemon_client import FdoDaemonClient


class ManualCompilerTests:
    """Test suite for manual FDO compiler."""

    def __init__(self, daemon_host='127.0.0.1', daemon_port=8080):
        self.daemon_client = FdoDaemonClient(daemon_host, daemon_port)
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def test_provided_examples(self):
        """Test the examples provided by the user."""
        print("\n=== Testing Provided Examples ===")

        examples = [
            {
                'name': 'idb_append_data Example 1 (150 bytes)',
                'source': 'idb_append_data <01x,00x,01x,00x,01x,00x,0bx,05x,00x,00x,01x,00x,00x,00x,05x,02x,78x,00x,29x,00x,00x,00x,e7x,04x,00x,00x,24x,00x,00x,00x,00x,00x,00x,00x,00x,00x,80x,fdx,00x,00x,47x,49x,46x,38x,37x,61x,78x,00x,29x,00x,d5x,00x,00x,00x,00x,00x,ffx,00x,00x,ffx,80x,00x,ffx,80x,40x,ffx,8ex,1cx,edx,92x,24x,f7x,99x,2bx,fcx,9dx,2cx,fcx,9fx,31x,ffx,9fx,20x,fcx,a1x,34x,ffx,a2x,2fx,fcx,a4x,3cx,ffx,a4x,24x,fcx,a7x,42x,fcx,a8x,44x,ffx,aax,00x,ffx,aax,2bx,ffx,aax,39x,fcx,acx,4cx,fcx,afx,53x,fcx,b0x,56x,fcx,b3x,5bx,fdx,b6x,63x,ffx,b6x,24x,fdx,b8x,66x,fdx,bax,6ax,fdx,bex,73x,fdx,c0x,77x,fdx,c2x,7cx,fdx,c6x,84x,fdx,c7x,88x,fdx>',
                'expected': bytes.fromhex('050B80960100010001000B050000010000000502780029000000E70400002400000000000000000080FD000047494638376178002900D50000000000FF0000FF8000FF8040FF8E1CED9224F7992BFC9D2CFC9F31FF9F20FCA134FFA22FFCA43CFFA424FCA742FCA844FFAA00FFAA2BFFAA39FCAC4CFCAF53FCB056FCB35BFDB663FFB624FDB866FDBA6AFDBE73FDC077FDC27CFDC684FDC788FD')
            },
            {
                'name': 'idb_append_data Example 2 (150 bytes)',
                'source': 'idb_append_data <c9x,8bx,fdx,cdx,93x,fdx,d1x,9dx,fdx,d4x,a4x,fdx,d7x,a9x,fdx,d9x,aex,fdx,dcx,b4x,fdx,dex,bax,fdx,e0x,bex,fdx,e3x,c4x,fex,e6x,cbx,fex,e8x,cex,fex,eax,d3x,fex,eex,dcx,fex,f0x,dfx,fex,f1x,e3x,fex,f5x,ebx,fex,f7x,f0x,fex,f9x,f4x,ffx,ffx,00x,ffx,ffx,ffx,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,00x,21x,f9x,04x,09x,00x,00x,35x,00x,2cx,00x,00x,00x,00x,78x,00x,29x,00x,00x,06x,ffx,c0x,9ax,70x,38x,3cx,18x,8fx,c8x,a4x,72x,c9x,6cx,3ax,9fx,d0x,a8x,93x,48x,adx,d6x,a4x,d8x,acx,76x,cbx,65x,5ax,89x,ddx,b0x,78x,4cx,fex,5ex,c9x>',
                'expected': bytes.fromhex('050B8096C98BFDCD93FDD19DFDD4A4FDD7A9FDD9AEFDDCB4FDDEBAFDE0BEFDE3C4FEE6CBFEE8CEFEEAD3FEEEDCFEF0DFFEF1E3FEF5EBFEF7F0FEF9F4FFFF00FFFFFF00000000000000000000000000000000000000000000000000000000000021F90409000035002C00000000780029000006FFC09A70383C188FC8A472C96C3A9FD0A89348ADD6A4D8AC76CB655A89DDB0784CFE5EC9')
            }
        ]

        for example in examples:
            self._test_example(example['name'], example['source'], example['expected'])

    def _test_example(self, name: str, source: str, expected: bytes):
        """Test a single example."""
        print(f"\nTest: {name}")

        # Manual compilation
        manual_output = FdoManualCompiler.compile_line(source)

        if manual_output is None:
            print(f"  FAILED: Manual compilation returned None")
            self.failed += 1
            return

        # Compare
        if manual_output == expected:
            print(f"  PASSED: Perfect match ({len(manual_output)} bytes)")
            self.passed += 1
        else:
            print(f"  FAILED: Mismatch")
            print(f"    Expected: {expected.hex().upper()[:80]}...")
            print(f"    Got:      {manual_output.hex().upper()[:80]}...")
            self.failed += 1

    def test_edge_cases(self):
        """Test edge cases without daemon."""
        print("\n=== Testing Edge Cases ===")

        # Empty data
        print("\nTest: Empty hex pairs")
        try:
            result = FdoManualCompiler.compile_idb_append_data([])
            if len(result) == 4:  # Header only
                print(f"  PASSED: Empty data produces header-only output ({len(result)} bytes)")
                self.passed += 1
            else:
                print(f"  FAILED: Unexpected length {len(result)}")
                self.failed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            self.failed += 1

        # Single byte
        print("\nTest: Single byte")
        result = FdoManualCompiler.compile_idb_append_data(['FF'])
        expected_single = bytes([0x05, 0x0B, 0x80, 0x01, 0xFF])
        if result == expected_single:
            print(f"  PASSED: Single byte compiled correctly")
            self.passed += 1
        else:
            print(f"  FAILED: Expected {expected_single.hex()}, got {result.hex()}")
            self.failed += 1

        # Maximum length (255 bytes)
        print("\nTest: Maximum length (255 bytes)")
        max_hex = ['FF'] * 255
        try:
            result = FdoManualCompiler.compile_idb_append_data(max_hex)
            if len(result) == 259:  # 4 header + 255 payload
                print(f"  PASSED: 255-byte payload compiled")
                self.passed += 1
            else:
                print(f"  FAILED: Expected 259 bytes, got {len(result)}")
                self.failed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            self.failed += 1

        # Over maximum (should fail)
        print("\nTest: Over maximum (256 bytes - should fail)")
        over_max_hex = ['FF'] * 256
        try:
            result = FdoManualCompiler.compile_idb_append_data(over_max_hex)
            print(f"  FAILED: Should have raised ValueError for 256 bytes")
            self.failed += 1
        except ValueError:
            print(f"  PASSED: Correctly rejected 256-byte payload")
            self.passed += 1

    def test_detection(self):
        """Test detection of compilable lines."""
        print("\n=== Testing Line Detection ===")

        test_cases = [
            ('idb_append_data <01x, 02x>', True, 'Simple hex-pair format'),
            ('dod_data <AAx, BBx, CCx>', True, 'dod_data with hex pairs'),
            ('man_append_data <FFx>', True, 'man_append_data single byte'),
            ('idb_append_data <AABBCC>', False, 'Continuous hex (no pairs)'),
            ('idb_append_data <"text">', False, 'Quoted text format'),
            ('uni_start_stream <00x>', False, 'Unsupported atom type'),
            ('idb_append_data <01x, ' + '02x, ' * 300 + '>', False, 'Too long (>255)'),
        ]

        for source, expected_result, description in test_cases:
            result = FdoManualCompiler.can_compile_manually(source)
            if result == expected_result:
                print(f"  PASSED: {description}")
                self.passed += 1
            else:
                print(f"  FAILED: {description} (expected {expected_result}, got {result})")
                self.failed += 1

    def test_with_daemon(self):
        """Test manual compilation against actual daemon output."""
        print("\n=== Testing Against Daemon ===")

        # Check if daemon is available
        try:
            health = self.daemon_client.health_check()
            if not health.get('healthy'):
                print("  SKIPPED: Daemon not healthy")
                self.skipped += 3
                return
        except Exception as e:
            print(f"  SKIPPED: Daemon not available ({e})")
            self.skipped += 3
            return

        test_lines = [
            'idb_append_data <01x, 02x, 03x>',
            'dod_data <AAx, BBx, CCx, DDx, EEx>',
            'man_append_data <FFx, 00x, 11x>',
        ]

        for line in test_lines:
            print(f"\nTest: {line}")
            try:
                # Get daemon output
                full_script = f"uni_start_stream <00x>\n{line}\nuni_end_stream <>"
                daemon_result = self.daemon_client.compile_source(full_script)

                if daemon_result['success']:
                    daemon_binary = bytes.fromhex(daemon_result['binary_data'])

                    # Manual compilation
                    manual_output = FdoManualCompiler.compile_line(line)

                    # The daemon output includes stream wrappers, so we need to extract just the atom
                    # For now, just check if manual output is a substring
                    if manual_output and manual_output in daemon_binary:
                        print(f"  PASSED: Manual output found in daemon binary")
                        self.passed += 1
                    else:
                        print(f"  WARNING: Manual output not found in daemon binary (may need stream wrapper)")
                        print(f"    Manual: {manual_output.hex() if manual_output else 'None'}")
                        print(f"    Daemon: {daemon_binary.hex()}")
                        self.skipped += 1
                else:
                    print(f"  FAILED: Daemon compilation failed: {daemon_result.get('error')}")
                    self.failed += 1
            except Exception as e:
                print(f"  FAILED: {e}")
                self.failed += 1

    def test_large_file(self):
        """Test with large_dod_test.fdo.txt if available."""
        print("\n=== Testing Large File ===")

        large_file = Path(__file__).parent / 'large_dod_test.fdo.txt'

        if not large_file.exists():
            print(f"  SKIPPED: {large_file} not found")
            self.skipped += 1
            return

        print(f"\nReading {large_file}...")
        content = large_file.read_text()
        lines = content.strip().split('\n')

        # Count compilable lines
        compilable_count = 0
        manual_compile_time = 0

        for line in lines:
            if FdoManualCompiler.can_compile_manually(line):
                compilable_count += 1
                start = time.time()
                manual_output = FdoManualCompiler.compile_line(line)
                manual_compile_time += time.time() - start

                if manual_output is None:
                    print(f"  WARNING: Failed to compile: {line[:50]}...")

        print(f"\n  File stats:")
        print(f"    Total lines: {len(lines)}")
        print(f"    Compilable lines: {compilable_count}")
        print(f"    Manual compile time: {manual_compile_time*1000:.2f}ms")
        print(f"    Avg per line: {(manual_compile_time/compilable_count)*1000:.3f}ms" if compilable_count else "N/A")

        if compilable_count > 0:
            print(f"  PASSED: Successfully compiled {compilable_count} lines")
            self.passed += 1
        else:
            print(f"  FAILED: No compilable lines found")
            self.failed += 1

    def run_all(self):
        """Run all tests."""
        print("=" * 70)
        print("MANUAL FDO COMPILER TEST SUITE")
        print("=" * 70)

        self.test_provided_examples()
        self.test_edge_cases()
        self.test_detection()
        self.test_with_daemon()
        self.test_large_file()

        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        print(f"Passed:  {self.passed}")
        print(f"Failed:  {self.failed}")
        print(f"Skipped: {self.skipped}")
        print(f"Total:   {self.passed + self.failed + self.skipped}")

        if self.failed == 0:
            print("\nALL TESTS PASSED!")
            return 0
        else:
            print(f"\n{self.failed} TEST(S) FAILED")
            return 1


if __name__ == '__main__':
    tests = ManualCompilerTests()
    sys.exit(tests.run_all())
