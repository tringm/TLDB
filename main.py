import argparse
import unittest
import importlib

from config import root_path
from test.tests import get_suites, TestResultCompareFileMeld

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TLDB')
    suites = get_suites()
    parser.add_argument('--test',
                        help=f"Test all or a specific suite among: {'|'.join(list(suites.keys()) + ['all'])} "
                        f"or a specific test cases",
                        type=str,
                        required=False)
    parser.add_argument('--meld',
                        help='Use meld to compare out and exp file',
                        type=bool,
                        default=False,
                        required=False)

    try:
        args = parser.parse_args()
    except:
        parser.print_help()
        exit()

    if args.meld:
        result_class = TestResultCompareFileMeld
    else:
        result_class = unittest.TextTestResult

    runner = unittest.TextTestRunner(verbosity=2, resultclass=result_class)

    if args.test:
        if args.test == 'all':
            for s in suites:
                runner.run(suites[s])
        else:
            if args.test in list(suites.keys()):
                runner = unittest.TextTestRunner(verbosity=2, resultclass=result_class).run(suites[args.test])
            else:
                try:
                    test_path = args.test.split('.')
                    module = importlib.import_module('.'.join(test_path[:-1]))
                    test_case_class = getattr(module, test_path[-1])
                    suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_case_class)
                    runner.run(suite)
                except ValueError:
                    print("Suite or test case not found")

