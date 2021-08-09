import unittest
from context import Config


class Test_config(unittest.TestCase):
    def test_missing_degree(self):
        with self.assertRaises(KeyError) as cm:
            Config("./testing/configs/invalid/missing_degree.ini")
        # Test if an error message exists
        self.assertTrue(len(str(cm.exception)) > 0)

    def test_missing_p2p_address(self):
        with self.assertRaises(KeyError) as cm:
            Config("./testing/configs/invalid/missing_p2p_address.ini")
        # Test if an error message exists
        self.assertTrue(len(str(cm.exception)) > 0)

    def test_missing_api_address(self):
        with self.assertRaises(KeyError) as cm:
            Config("./testing/configs/invalid/missing_api_address.ini")
        # Test if an error message exists
        self.assertTrue(len(str(cm.exception)) > 0)

    def test_missing_max_connections(self):
        with self.assertRaises(KeyError) as cm:
            Config("./testing/configs/invalid/missing_max_connections.ini")
        # Test if an error message exists
        self.assertTrue(len(str(cm.exception)) > 0)

    def test_missing_min_connections(self):
        with self.assertRaises(KeyError) as cm:
            Config("./testing/configs/invalid/missing_min_connections.ini")
        # Test if an error message exists
        self.assertTrue(len(str(cm.exception)) > 0)

    def test_missing_bootstrapper(self):
        with self.assertRaises(KeyError) as cm:
            Config("./testing/configs/invalid/missing_bootstrapper.ini")
        # Test if an error message exists
        self.assertTrue(len(str(cm.exception)) > 0)

    def test_valid_no_except(self):
        # Tests if a valid config is not raising an exception
        try:
            Config("./testing/configs/valid/valid_config.ini")
        except Exception as e:
            self.fail("Config raised an Exception unexpectedly")


if __name__ == '__main__':
    unittest.main()
