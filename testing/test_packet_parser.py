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
                         (0, 0, 0, b'\x00\x00'),
                         "Gossip Announce parsed incorrectly")

        # correct packet: correct size, empty data
        test_packet = pack(pp.FORMAT_GOSSIP_ANNOUNCE, 8, 500, 0, 0, 0)
        self.assertEqual(pp.parse_gossip_announce(test_packet),
                         (0, 0, 0, b''),
                         "Empty data was not parsed correctly")

        # wrong packet: empty buffer (b'')
        test_packet = b''
        self.assertEqual(pp.parse_gossip_announce(test_packet),
                         (), "Empty byte (b'') should return empty tuple")

        # wrong packet: incorrect message type
        test_packet = pack(pp.FORMAT_GOSSIP_ANNOUNCE, 8, 600, 0, 0, 0)
        self.assertEqual(pp.parse_gossip_announce(test_packet),
                         (), "Wrong message type should return empty tuple")

        # wrong packet: correct size, packet too small
        test_packet = pack("!HHBB", 6, 500, 0, 0)
        self.assertEqual(pp.parse_gossip_announce(test_packet),
                         (), "Packet should throw error, too small to parse")

        # wrong packet: incorrect size
        test_packet = pack(pp.FORMAT_GOSSIP_ANNOUNCE+"H", 80, 500, 0, 0, 0, 0)
        self.assertEqual(pp.parse_gossip_announce(test_packet),
                         (), "Packet should have a wrong size")

    def test_parse_gossip_notify(self):
        # correct packet
        test_packet = pack(pp.FORMAT_GOSSIP_NOTIFY, 8, pp.GOSSIP_NOTIFY, 0, 1)
        self.assertEqual(pp.parse_gossip_notify(test_packet),
                         (1), "Packet should be correct and return datatype")

        # wrong type
        test_packet = pack(pp.FORMAT_GOSSIP_NOTIFY, 8, pp.GOSSIP_VALIDATION, 0,
                           1)
        self.assertEqual(pp.parse_gossip_notify(test_packet),
                         (), "wrong msg_type should return error")

        # empty buffer b''
        test_packet = b''
        self.assertEqual(pp.parse_gossip_notify(test_packet),
                         (), "Empty buffer should return empty tuple ()")

        # wrong size-field value
        test_packet = pack(pp.FORMAT_GOSSIP_NOTIFY, 60, pp.GOSSIP_NOTIFY, 0, 1)
        self.assertEqual(pp.parse_gossip_notify(test_packet),
                         (), "Wrong size value should return error")

        # too large packet, correct size-field
        test_packet = pack(pp.FORMAT_GOSSIP_NOTIFY+"HH", 12, pp.GOSSIP_NOTIFY,
                           0, 1, 0, 0)
        self.assertEqual(pp.parse_gossip_notify(test_packet),
                         (), "a too large packet should return as an error")

        # too small packet, correct size-field
        test_packet = pack("!HHH", 6, pp.GOSSIP_NOTIFY, 0)
        self.assertEqual(pp.parse_gossip_notify(test_packet),
                         (), "a too small packet should return as an error")

    def test_parse_gossip_notification(self):
        # correct packet
        test_packet = pack(pp.FORMAT_GOSSIP_NOTIFICATION+"H", 10,
                           pp.GOSSIP_NOTIFICATION, 10, 1, 0)
        self.assertEqual(pp.parse_gossip_notification(test_packet),
                         (10, 1, b'\x00\x00'), "correct packet threw error")

        # wrong packet: packet too short, no data
        test_packet = pack(pp.FORMAT_GOSSIP_NOTIFICATION, 8,
                           pp.GOSSIP_NOTIFICATION, 12, 1)
        self.assertEqual(pp.parse_gossip_announce(test_packet),
                         (), "missing data should throw error")

        # wrong packet: empty buffer (b'')
        test_packet = b''
        self.assertEqual(pp.parse_gossip_notification(test_packet),
                         (), "empty buffer b'' should throw error")

        # wrong packet: incorrect message type
        test_packet = pack(pp.FORMAT_GOSSIP_NOTIFICATION+"H", 10,
                           pp.GOSSIP_ANNOUNCE, 12, 1, 0)
        self.assertEqual(pp.parse_gossip_notification(test_packet),
                         (), "wrong msg_type should return error")

        # wrong packet: incorrect size
        test_packet = pack(pp.FORMAT_GOSSIP_NOTIFICATION+"H", 900,
                           pp.GOSSIP_NOTIFICATION, 12, 1, 0)
        self.assertEqual(pp.parse_gossip_notification(test_packet),
                         (), "wrong size should return error")

    def test_parse_gossip_validation(self):
        # correct packet: bit set
        test_packet = pack(pp.FORMAT_GOSSIP_VALIDATION, 8,
                           pp.GOSSIP_VALIDATION, 12, 1)
        self.assertEqual(pp.parse_gossip_validation(test_packet),
                         (12, True), "correct packet was parsed incorrectly")

        # correct packet: bit not set
        test_packet = pack(pp.FORMAT_GOSSIP_VALIDATION, 8,
                           pp.GOSSIP_VALIDATION, 12, 0)
        self.assertEqual(pp.parse_gossip_validation(test_packet),
                         (12, False), "correct packet was parsed incorrectly")

        # wrong packet: reserved field is not empty
        test_packet = pack(pp.FORMAT_GOSSIP_VALIDATION, 8,
                           pp.GOSSIP_VALIDATION, 12, 2)
        self.assertEqual(pp.parse_gossip_validation(test_packet),
                         (), "non-empty reserved field was not caught")

        # wrong packet: too short
        test_packet = pack("!HHH", 6, pp.GOSSIP_VALIDATION, 12)
        self.assertEqual(pp.parse_gossip_validation(test_packet),
                         (), "too short packet threw no error")

        # wrong packet: too long
        test_packet = pack(pp.FORMAT_GOSSIP_VALIDATION+"H", 12,
                           pp.GOSSIP_VALIDATION, 1, 0, 0)
        self.assertEqual(pp.parse_gossip_validation(test_packet),
                         (), "too long packet threw no error")

        # wrong packet: incorrect msg_type
        test_packet = pack(pp.FORMAT_GOSSIP_VALIDATION, 8,
                           pp.GOSSIP_ANNOUNCE, 12, 1)
        self.assertEqual(pp.parse_gossip_validation(test_packet),
                         (), "incorrect msg_type threw no error")

        # wrong packet: incorrect size
        test_packet = pack(pp.FORMAT_GOSSIP_VALIDATION, 60,
                           pp.GOSSIP_VALIDATION, 12, 1)
        self.assertEqual(pp.parse_gossip_validation(test_packet),
                         (), "incorrect size-field value threw no error")

    def test_get_type(self):
        # correct packet
        test_packet = pack(pp.FORMAT_GOSSIP_ANNOUNCE+"H", 10, 500, 0, 0, 0, 0)
        self.assertEqual(pp.get_header_type(test_packet),
                         500, "Message type should be 500 - Gossip Announce")

        # empty buffer b''
        test_packet = b''
        self.assertEqual(pp.get_header_type(test_packet),
                         -1, "empty buffer b'' should throw error")


if __name__ == '__main__':
    unittest.main()
