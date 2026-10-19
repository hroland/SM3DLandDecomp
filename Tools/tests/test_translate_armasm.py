import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from translate_armasm import translate


class AssemblyTranslationTest(unittest.TestCase):
    def test_embedded_function_keeps_instructions_and_symbol_extent(self):
        source = '''AREA ||.arm_vfe_header||, DATA, READONLY, NOALLOC
DCD 0
AREA ||i.test||, CODE, READONLY
ARM
EXPORT |test|
|test| PROC
 push {r0, r4}
 svc 0x1
 pop {r0, r4}
 bx lr
ENDP
ASSERT {ENDIAN} = "little"
END
'''
        result = translate(source)
        self.assertIn('.section "i.test","ax",%progbits', result)
        self.assertIn("test:\npush {r0, r4}\nsvc 0x1\npop {r0, r4}\nbx lr\n.size test, .-test", result)
        self.assertNotIn(".word 0", result)

    def test_unknown_assertion_and_macro_fail(self):
        for source in ('ASSERT {ENDIAN} = "big"', 'AREA code, CODE\nMACRO test'):
            with self.assertRaises(ValueError):
                translate(source)

    def test_truncated_function_fails(self):
        with self.assertRaises(ValueError):
            translate('AREA code, CODE\n|test| PROC\nbx lr')
