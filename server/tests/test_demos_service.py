import unittest
from datetime import datetime
from json import loads
from multiprocessing import Pool
import server.tests.utils as utils
import server.services.demos as demo_service
import server.services.users as user_service
import server.services.shipments as shipment_service
import server.services.distribution_centers as distribution_center_service
import server.services.retailers as retailer_service
from server.utils import async_helper
from server.exceptions import (UnprocessableEntityException,
                               ResourceDoesNotExistException)


def suite():
    test_suite = unittest.TestSuite()
    test_suite.addTest(CreateDemoTestCase('test_demo_create_success'))
    test_suite.addTest(RetrieveDemoTestCase('test_demo_retrieve_success'))
    test_suite.addTest(RetrieveDemoTestCase('test_demo_retrieve_invalid_input'))
    test_suite.addTest(RetrieveDemoTestCase('test_demo_retrieve_retailers_success'))
    test_suite.addTest(RetrieveDemoTestCase('test_admin_data_async_success'))
    test_suite.addTest(DeleteDemoTestCase('test_demo_delete_success'))
    test_suite.addTest(DeleteDemoTestCase('test_demo_delete_invalid_input'))
    return test_suite


###########################
#        Unit Tests       #
###########################

class CreateDemoTestCase(unittest.TestCase):
    """Tests for `services/demos.py - create_demo()`."""

    def test_demo_create_success(self):
        """With correct values, is a valid demo returned?"""

        # Create demo
        demo = demo_service.create_demo()

        # TODO: Update to use assertIsInstance(a,b)
        # Check all expected object values are present
        demo_json = loads(demo)
        self.assertTrue(demo_json.get('id'))
        self.assertTrue(demo_json.get('guid'))
        self.assertTrue(demo_json.get('createdAt'))
        self.assertTrue(demo_json.get('users'))

        # Check that the default supplychainmanager user was created
        created_user_json = demo_json.get('users')[0]
        self.assertTrue(created_user_json.get('id'))
        self.assertTrue(created_user_json.get('demoId'))
        self.assertTrue(created_user_json.get('username'))
        self.assertTrue(created_user_json.get('email'))
        self.assertTrue(created_user_json.get('roles'))

        # Check that the proper role was created
        scm_role_json = created_user_json.get('roles')[0]
        self.assertTrue(scm_role_json.get('id'))
        self.assertTrue(scm_role_json.get('name') == "supplychainmanager")
        self.assertTrue(scm_role_json.get('created'))
        self.assertTrue(scm_role_json.get('modified'))

        # Destroy demo
        demo_service.delete_demo_by_guid(demo_json.get('guid'))


class RetrieveDemoTestCase(unittest.TestCase):
    """Tests for `services/demos.py - get_demo_by_guid(), get_demo_retailers()`.
       Tests for `web/utils.py - async_helper()`."""

    def setUp(self):
        # Create demo
        self.demo = demo_service.create_demo()
        demo_json = loads(self.demo)
        demo_guid = demo_json.get('guid')
        demo_user_id = demo_json.get('users')[0].get('id')

        # Log in user
        auth_data = user_service.login(demo_guid, demo_user_id)
        self.loopback_token = auth_data.get('loopback_token')

    def test_demo_retrieve_success(self):
        """With correct values, is a valid demo returned?"""

        # Retrieve demo
        retrieved_demo = demo_service.get_demo_by_guid(loads(self.demo).get('guid'))

        # TODO: Update to use assertIsInstance(a,b)
        # Check all expected object values are present
        created_demo_json = loads(self.demo)
        demo_json = loads(retrieved_demo)
        self.assertTrue(demo_json.get('id') == created_demo_json.get('id'))
        self.assertTrue(demo_json.get('guid') == created_demo_json.get('guid'))
        self.assertTrue(demo_json.get('name') == created_demo_json.get('name'))
        self.assertTrue(demo_json.get('createdAt') == created_demo_json.get('createdAt'))
        self.assertTrue(demo_json.get('users'))

        # Check that the users are valid
        for user_json in demo_json.get('users'):
            self.assertTrue(user_json.get('id'))
            self.assertTrue(user_json.get('demoId'))
            self.assertTrue(user_json.get('username'))
            self.assertTrue(user_json.get('email'))

            # Check that user roles are valid, if present
            if user_json.get('roles'):
                for role_json in user_json.get('roles'):
                    self.assertTrue(role_json.get('id'))
                    self.assertTrue(role_json.get('name'))
                    self.assertTrue(role_json.get('created'))
                    self.assertTrue(role_json.get('modified'))

    def test_demo_retrieve_invalid_input(self):
        """With invalid guid, is correct error thrown?"""
        self.assertRaises(ResourceDoesNotExistException,
                          demo_service.get_demo_by_guid,
                          'ABC123')

    def test_demo_retrieve_retailers_success(self):
        """With correct values, are valid demo retailers returned?"""

        # Retrieve demo retailers
        demo_guid = loads(self.demo).get('guid')
        retailers = demo_service.get_demo_retailers(demo_guid)
        retailers_json = loads(retailers)

        # TODO: Update to use assertIsInstance(a,b)
        # Check that the retailers are valid
        for retailer_json in retailers_json:
            self.assertTrue(retailer_json.get('id'))
            self.assertTrue(retailer_json.get('address'))

            address_json = retailer_json.get('address')
            self.assertTrue(address_json.get('city'))
            self.assertTrue(address_json.get('state'))
            self.assertTrue(address_json.get('country'))
            self.assertTrue(address_json.get('latitude'))
            self.assertTrue(address_json.get('longitude'))

    def test_admin_data_async_success(self):
        """With correct values, is valid data returned asynchronously?"""

        # Specify functions and their corresponding arguments to be called
        erp_calls = [(shipment_service.get_shipments, self.loopback_token),
                     (distribution_center_service.get_distribution_centers, self.loopback_token),
                     (retailer_service.get_retailers, self.loopback_token)]
        pool = Pool(processes=len(erp_calls))

        # Asynchronously make calls and then wait on all processes to finish
        results = pool.map(async_helper, erp_calls)
        pool.close()
        pool.join()

        # Check that the shipment is valid
        shipment = loads(results[0])[0]
        self.assertTrue(shipment.get('id'))
        self.assertTrue(shipment.get('status'))
        self.assertTrue(shipment.get('createdAt'))
        self.assertTrue(shipment.get('estimatedTimeOfArrival'))
        self.assertTrue(shipment.get('fromId'))
        self.assertTrue(shipment.get('toId'))
        if shipment.get('currentLocation'):
            self.assertTrue(shipment.get('currentLocation').get('city'))
            self.assertTrue(shipment.get('currentLocation').get('state'))
            self.assertTrue(shipment.get('currentLocation').get('country'))
            self.assertTrue(shipment.get('currentLocation').get('latitude'))
            self.assertTrue(shipment.get('currentLocation').get('longitude'))

        # Check that the retailer is valid
        retailer = loads(results[1])[0]
        self.assertTrue(retailer.get('id'))
        if retailer.get('address'):
            self.assertTrue(retailer.get('address').get('city'))
            self.assertTrue(retailer.get('address').get('state'))
            self.assertTrue(retailer.get('address').get('country'))
            self.assertTrue(retailer.get('address').get('latitude'))
            self.assertTrue(retailer.get('address').get('longitude'))

        # Check that the distribution center is valid
        distribution_center = loads(results[2])[0]
        self.assertTrue(distribution_center.get('id'))
        if distribution_center.get('address'):
            self.assertTrue(distribution_center.get('address').get('city'))
            self.assertTrue(distribution_center.get('address').get('state'))
            self.assertTrue(distribution_center.get('address').get('country'))
            self.assertTrue(distribution_center.get('address').get('latitude'))
            self.assertTrue(distribution_center.get('address').get('longitude'))

    def tearDown(self):
        demo_service.delete_demo_by_guid(loads(self.demo).get('guid'))


class DeleteDemoTestCase(unittest.TestCase):
    """Tests for `services/demos.py - delete_demo_by_guid()`."""

    def setUp(self):
        # Create demo
        self.demo = demo_service.create_demo()

    def test_demo_delete_success(self):
        """With correct values, is a valid demo deleted?"""

        self.assertTrue(demo_service.delete_demo_by_guid(loads(self.demo).get('guid')) is None)

    def test_demo_delete_invalid_input(self):
        """With invalid guid, is correct error thrown?"""

        # Attempt to delete demo with invalid guid
        self.assertRaises(ResourceDoesNotExistException,
                          demo_service.delete_demo_by_guid,
                          'ABC123')


if __name__ == '__main__':
    unittest.main()
