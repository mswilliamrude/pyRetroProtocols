import pytest
from hsaio import HSLinkFramer, HSLinkSession, ControlMapping, FileHeaderPacket, SequencePacket, crc16, crc24, crc32

class MockTransport:
    def __init__(self):
        self.in_buffer = bytearray()
        self.out_buffer = bytearray()

    def read(self, max_bytes=4096) -> bytes:
        data = bytes(self.in_buffer)
        self.in_buffer.clear()
        return data

    def write(self, data: bytes):
        self.out_buffer.extend(data)

    def idle(self, timeout=0.01) -> bool:
        return True

@pytest.fixture
def mock_transport():
    return MockTransport()

@pytest.fixture
def framer(mock_transport):
    return HSLinkFramer(mock_transport)

@pytest.fixture
def session(mock_transport):
    return HSLinkSession(mock_transport)

def test_framer_initialization(mock_transport):
    framer = HSLinkFramer(mock_transport)
    assert framer.transport == mock_transport
    assert framer.crc_size == 3
    assert framer._buffer == bytearray()
    assert framer._in_packet is False


def test_send_packet(framer):
    pkt_type = b'D'
    payload = b'Test payload'
    framer.send_packet(pkt_type, payload)
    assert len(framer.transport.out_buffer) > 0


def test_read_packets(framer):
    # Simulate sending a packet
    framer.send_packet(b'D', b'Test payload')
    framer.transport.in_buffer.extend(framer.transport.out_buffer)
    framer.transport.out_buffer.clear()

    packets = framer.read_packets()
    assert len(packets) == 1
    assert packets[0][0] == b'D'
    assert packets[0][1] == b'Test payload'


def test_control_mapping_pack_unpack():
    packed = ControlMapping.pack(0x11, 0x13, 0x1E, 0x02, 0x1B)
    unpacked = ControlMapping.unpack(packed)
    assert unpacked == (0x11, 0x13, 0x1E, 0x02, 0x1B)


def test_file_header_packet_pack_unpack():
    packed = FileHeaderPacket.pack(b'example.txt', 1234, 1, 4096, 0, 0)
    unpacked = FileHeaderPacket.unpack(packed)
    assert unpacked['name'] == b'example.txt'
    assert unpacked['size'] == 1234
    assert unpacked['blocks'] == 1
    assert unpacked['BlockSize'] == 4096


def test_sequence_packet_pack_unpack():
    packed = SequencePacket.pack(1, 2)
    unpacked = SequencePacket.unpack(packed)
    assert unpacked['batch'] == 1
    assert unpacked['block'] == 2


def test_crc_functions():
    data = b'Test data'
    assert crc16(data) == 50630
    assert crc24(data) == 10037075
    assert crc32(data) == 1375284241


def test_session_initialization(mock_transport):
    session = HSLinkSession(mock_transport)
    assert session.transport == mock_transport
    assert session.state == 'INIT'
    assert session.files_to_send == []
