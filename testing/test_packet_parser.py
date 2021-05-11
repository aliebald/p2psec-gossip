import unittest
# https://stackoverflow.com/questions/42890302/relative-paths-for-modules-in-python
from context import packet_parser as pp
from struct import pack


class Test_header_funcs(unittest.TestCase):
    def test_parse_gossip_announce(self):
        # Note: We test for correct parsing, wo do not test whether the
        #       field values make sense.

        # correct packet
        test_packet = pack(pp.FORMAT_GOSSIP_ANNOUNCE+"H", 10, 500, 0, 0, 0, 0)
        self.assertEqual(pp.parse_gossip_announce(test_packet),
                         (10, 500, 0, 0, 0, b'\x00\x00'),
                         "Gossip Announce parsed incorrectly")

        # correct packet: correct size, empty data
        test_packet = pack(pp.FORMAT_GOSSIP_ANNOUNCE, 8, 500, 0, 0, 0)
        self.assertEqual(pp.parse_gossip_announce(test_packet),
                         (8, 500, 0, 0, 0, b''),
                         "Empty data was not parsed correctly")

        # wrong packet: empty buffer (b'')
        test_packet = b''
        self.assertEqual(pp.parse_gossip_announce(test_packet),
                         (), "Empty byte (b'') should return empty tuple")

        # wrong packet: correct size, packet too small
        test_packet = pack("!HHBB", 6, 500, 0, 0)
        self.assertEqual(pp.parse_gossip_announce(test_packet),
                         (), "Packet should throw error, too small to parse")

        # wrong packet: incorrect size
        test_packet = pack(pp.FORMAT_GOSSIP_ANNOUNCE+"H", 80, 500, 0, 0, 0, 0)
        self.assertEqual(pp.parse_gossip_announce(test_packet),
                         (), "Packet should have a wrong size")

    def test_get_type(self):
        test_packet = pack(pp.FORMAT_GOSSIP_ANNOUNCE+"H", 10, 500, 0, 0, 0, 0)
        self.assertEqual(pp.get_header_type(test_packet),
                         500, "Message type should be 500 - Gossip Announce")


if __name__ == '__main__':
    unittest.main()
