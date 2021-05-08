import unittest
# https://stackoverflow.com/questions/42890302/relative-paths-for-modules-in-python
from context import packet_parser as pp
from struct import pack


class Test_header_funcs(unittest.TestCase):
    def test_get_size(self):
        test_packet1 = pack(pp.FORMAT_GOSSIP_ANNOUNCE+"H", 10, 500, 0, 0, 0, 0)
        self.assertEqual(pp.get_header_size(test_packet1),
                         10, "Size should be 10")

    def test_get_type(self):
        test_packet1 = pack(pp.FORMAT_GOSSIP_ANNOUNCE+"H", 10, 500, 0, 0, 0, 0)
        self.assertEqual(pp.get_header_type(test_packet1),
                         500, "Message type should be 500 - Gossip Announce")


if __name__ == '__main__':
    unittest.main()
