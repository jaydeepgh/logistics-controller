"""
Runs all integration tests by adding them to a test suite and then executes
the test suite
"""
import unittest
from os import environ as env

# Required tests
test_modules = [
    'server.tests.test_demos_service',
    'server.tests.test_distribution_centers_service',
    'server.tests.test_products_service',
    'server.tests.test_retailers_service',
    'server.tests.test_shipments_service',
    'server.tests.test_users_service'
    ]

suite = unittest.TestSuite()

for test in test_modules:
    try:
        # If the module defines a suite() function, call it to get the suite.
        mod = __import__(test, globals(), locals(), ['suite'])
        suite_func = getattr(mod, 'suite')
        suite.addTest(suite_func())
    except (ImportError, AttributeError):
        # else, just load all the test cases from the module.
        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(test))

unittest.TextTestRunner(failfast=True).run(suite)
