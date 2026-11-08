import unittest
from agent.evidence import syntax_result, policy_check, patch_text, evidence_passport


class EvidenceTests(unittest.TestCase):
    def test_syntax(self):
        self.assertTrue(syntax_result('x = 1\n')['passed'])
        self.assertFalse(syntax_result('def f(:\n')['passed'])

    def test_policy_imports(self):
        result = policy_check('x = 1\n', 'import requests\nx = 1\n', False, True)
        self.assertFalse(result[0]['passed'])

    def test_patch_path(self):
        with self.assertRaises(ValueError):
            patch_text('x\n', 'y\n', '../outside.py')

    def test_passport_honest(self):
        result = evidence_passport('x=1\n', 'x=2\n', [], {'status':'DEMO'}, [], {'id':'SEC-001'})
        self.assertFalse(result['opengrep_rescan']['executed'])
        self.assertEqual(result['mode'], 'SIMULATED')

    def test_invalid_syntax_cannot_pass_import_policy(self):
        self.assertFalse(policy_check('x = 1\n', 'def x(:\n', False, True)[0]['passed'])

    def test_demo_cannot_claim_live_mode(self):
        with self.assertRaises(ValueError):
            evidence_passport('x=1\n', 'x=2\n', [], {}, [], {}, mode='LIVE')

if __name__ == '__main__':
    unittest.main()
