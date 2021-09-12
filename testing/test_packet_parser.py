import unittest
# https://stackoverflow.com/questions/42890302/relative-paths-for-modules-in-python
from context import packet_parser as pp
from struct import pack
from random import randint


class Test_header_funcs(unittest.TestCase):
    def test_parse_gossip_announce(self):
        # Note: We test for correct parsing, wo do not test whether the
        #       field values make sense.

        # correct packet
        test_packet = pack(pp.FORMAT_GOSSIP_ANNOUNCE+"H", 10, 500, 0, 0, 0, 0)
        self.assertEqual(pp.parse_gossip_announce(test_packet),
                         (0, 0, b'\x00\x00'),
                         "Gossip Announce parsed incorrectly")

        # correct packet: correct size, empty data
        test_packet = pack(pp.FORMAT_GOSSIP_ANNOUNCE, 8, 500, 0, 0, 0)
        self.assertEqual(pp.parse_gossip_announce(test_packet),
                         (0, 0, b''),
                         "Empty data was not parsed correctly")

        # wrong packet: empty buffer (b'')
        test_packet = b''
        self.assertEqual(pp.parse_gossip_announce(test_packet),
                         None, "Empty byte (b'') should return None")

        # wrong packet: correct size, packet too small
        test_packet = pack("!HHBB", 6, 500, 0, 0)
        self.assertEqual(pp.parse_gossip_announce(test_packet),
                         None, "Packet should throw error, too small to parse")

        # wrong packet: incorrect size
        test_packet = pack(pp.FORMAT_GOSSIP_ANNOUNCE+"H", 80, 500, 0, 0, 0, 0)
        self.assertEqual(pp.parse_gossip_announce(test_packet),
                         None, "Packet should have a wrong size")

    def test_parse_gossip_notify(self):
        # correct packet
        test_packet = pack(pp.FORMAT_GOSSIP_NOTIFY, 8, pp.GOSSIP_NOTIFY, 0, 1)
        self.assertEqual(pp.parse_gossip_notify(test_packet),
                         (1), "Packet should be correct and return datatype")

        # wrong type
        test_packet = pack(pp.FORMAT_GOSSIP_NOTIFY, 8, pp.GOSSIP_VALIDATION, 0,
                           1)
        self.assertEqual(pp.parse_gossip_notify(test_packet),
                         None, "wrong msg_type should return error")

        # empty buffer b''
        test_packet = b''
        self.assertEqual(pp.parse_gossip_notify(test_packet),
                         None, "Empty buffer should return None ()")

        # wrong size-field value
        test_packet = pack(pp.FORMAT_GOSSIP_NOTIFY, 60, pp.GOSSIP_NOTIFY, 0, 1)
        self.assertEqual(pp.parse_gossip_notify(test_packet),
                         None, "Wrong size value should return error")

        # too large packet, correct size-field
        test_packet = pack(pp.FORMAT_GOSSIP_NOTIFY+"HH", 12, pp.GOSSIP_NOTIFY,
                           0, 1, 0, 0)
        self.assertEqual(pp.parse_gossip_notify(test_packet),
                         None, "a too large packet should return as an error")

        # too small packet, correct size-field
        test_packet = pack("!HHH", 6, pp.GOSSIP_NOTIFY, 0)
        self.assertEqual(pp.parse_gossip_notify(test_packet),
                         None, "a too small packet should return as an error")

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
                         None, "missing data should throw error")

        # wrong packet: empty buffer (b'')
        test_packet = b''
        self.assertEqual(pp.parse_gossip_notification(test_packet),
                         None, "empty buffer b'' should throw error")

        # wrong packet: incorrect size
        test_packet = pack(pp.FORMAT_GOSSIP_NOTIFICATION+"H", 900,
                           pp.GOSSIP_NOTIFICATION, 12, 1, 0)
        self.assertEqual(pp.parse_gossip_notification(test_packet),
                         None, "wrong size should return error")

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
                           pp.GOSSIP_VALIDATION, 12, 3)
        self.assertEqual(pp.parse_gossip_validation(test_packet),
                         (12, True), "non-empty reserved field threw error")

        # wrong packet: too short
        test_packet = pack("!HHH", 6, pp.GOSSIP_VALIDATION, 12)
        self.assertEqual(pp.parse_gossip_validation(test_packet),
                         None, "too short packet threw no error")

        # wrong packet: too long
        test_packet = pack(pp.FORMAT_GOSSIP_VALIDATION+"H", 12,
                           pp.GOSSIP_VALIDATION, 1, 0, 0)
        self.assertEqual(pp.parse_gossip_validation(test_packet),
                         None, "too long packet threw no error")

        # wrong packet: incorrect msg_type
        test_packet = pack(pp.FORMAT_GOSSIP_VALIDATION, 8,
                           pp.GOSSIP_ANNOUNCE, 12, 1)
        self.assertEqual(pp.parse_gossip_validation(test_packet),
                         None, "incorrect msg_type threw no error")

        # wrong packet: incorrect size
        test_packet = pack(pp.FORMAT_GOSSIP_VALIDATION, 60,
                           pp.GOSSIP_VALIDATION, 12, 1)
        self.assertEqual(pp.parse_gossip_validation(test_packet),
                         None, "incorrect size-field value threw no error")

    def test_build_gossip_notification(self):
        test_packet = pp.build_gossip_notification(1, 1, b'')
        self.assertEqual(pp.parse_gossip_notification(test_packet),
                         (1, 1, b''))

    def test_get_type(self):
        # correct packet
        test_packet = pack(pp.FORMAT_GOSSIP_ANNOUNCE+"H", 10, 500, 0, 0, 0, 0)
        self.assertEqual(pp.get_header_type(test_packet),
                         500, "Message type should be 500 - Gossip Announce")

        # empty buffer b''
        test_packet = b''
        self.assertEqual(pp.get_header_type(test_packet),
                         -1, "empty buffer b'' should throw error")

# ============================================================================
# PEER MESSAGES

    def test_parse_peer_announce(self):
        test_packet = pack(pp.FORMAT_PEER_ANNOUNCE+"H", 18,
                           pp.PEER_ANNOUNCE, 1, 1, 0, 1, 0)
        self.assertEqual(pp.parse_peer_announce(test_packet),
                         (1, 1, 1, b'\x00\x00'))

    def test_check_peer_discovery(self):
        test_packet = pack(pp.FORMAT_PEER_DISCOVERY, 4,
                           pp.PEER_DISCOVERY)
        self.assertEqual(pp.check_peer_discovery(test_packet),
                         True)

    def test_parse_peer_offer(self):
        test_packet = pack(pp.FORMAT_PEER_OFFER+"H", 6,
                           pp.PEER_OFFER, 0)
        self.assertEqual(pp.parse_peer_offer(test_packet),
                         ['\x00\x00'])

    def test_parse_peer_info(self):
        test_packet = pack(pp.FORMAT_PEER_INFO, 8, pp.PEER_INFO, 0, 1)
        self.assertEqual(pp.parse_peer_info(test_packet),
                         1)

    def test_parse_peer_challenge(self):
        # correct packet
        num = randint(0, (2**64)-1)
        test_packet = pack(pp.FORMAT_PEER_CHALLENGE, 12, pp.PEER_CHALLENGE,
                           num)
        self.assertEqual(pp.parse_peer_challenge(test_packet), num)

    def test_parse_peer_verification(self):
        # correct packet
        num = randint(0, (2**64)-1)
        test_packet = pack(pp.FORMAT_PEER_VERIFICATION, 12,
                           pp.PEER_VERIFICATION, num)
        self.assertEqual(pp.parse_peer_verification(test_packet), num)

    def test_parse_peer_validation(self):
        # correct packet
        test_packet = pack(pp.FORMAT_PEER_VALIDATION, 8,
                           pp.PEER_VALIDATION, 0, True)
        self.assertEqual(pp.parse_peer_validation(test_packet), True)

    def test_pack_peer_announce(self):
        test_packet = pp.pack_peer_announce(1, 1, 1, b'')
        self.assertEqual(pp.parse_peer_announce(test_packet),
                         (1, 1, 1, b''))

    def test_pack_peer_discovery(self):
        test_packet = pp.pack_peer_discovery()
        self.assertEqual(pp.check_peer_discovery(test_packet),
                         True)

    def test_pack_peer_offer(self):
        test_packet = pp.pack_peer_offer(b'')
        self.assertEqual(pp.parse_peer_offer(test_packet),
                         [''])

    def test_pack_peer_info(self):
        test_packet = pp.pack_peer_info(1)
        self.assertEqual(pp.parse_peer_info(test_packet),
                         (1))

    def test_pack_peer_challenge(self):
        test_packet = pp.pack_peer_challenge(1)
        self.assertEqual(pp.parse_peer_challenge(test_packet),
                         (1))

    def test_pack_peer_verification(self):
        test_packet = pp.pack_peer_verification(1)
        self.assertEqual(pp.parse_peer_verification(test_packet),
                         (1))

    def test_pack_peer_validation(self):
        test_packet = pp.pack_peer_validation(True)
        self.assertEqual(pp.parse_peer_validation(test_packet),
                         (True))

# ============================================================================


if __name__ == '__main__':
    unittest.main()
