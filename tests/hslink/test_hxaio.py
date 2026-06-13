import pytest
from hxaio import HSLinkFramer, HSLinkSession, crc16, crc24, crc32, ControlMapping, FileHeaderPacket, SequencePacket

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
        self.in_buffer.extend(data)

    def idle(self, timeout=0.01) -> bool:
        return True


@pytest.fixture
def mock_transport():
    return MockTransport()


def test_crc16():
    data = b'12345'
    expected_crc = 21612
    assert crc16(data) == expected_crc


def test_crc24():
    data = b'12345'
    expected_crc = 1674944
    assert crc24(data) == expected_crc


def test_crc32():
    data = b'12345'
    expected_crc = 3421846044
    assert crc32(data) == expected_crc


def test_control_mapping_pack_unpack():
    xon, xoff, dle, start, end = 0x11, 0x13, 0x1E, 0x02, 0x1B
    packed = ControlMapping.pack(xon, xoff, dle, start, end)
    unpacked = ControlMapping.unpack(packed)
    assert unpacked == (xon, xoff, dle, start, end)


def test_file_header_packet_pack_unpack():
    name = b'TESTFILE'
    size = 1024
    blocks = 1
    block_size = 1024
    time_dos = 0
    batch = 0
    packed = FileHeaderPacket.pack(name, size, blocks, block_size, time_dos, batch)
    unpacked = FileHeaderPacket.unpack(packed)
    assert unpacked['name'] == b'TESTFILE'
    assert unpacked['size'] == size
    assert unpacked['blocks'] == blocks
    assert unpacked['BlockSize'] == block_size
    assert unpacked['time'] == time_dos
    assert unpacked['batch'] == batch


def test_hslink_framer_send_packet(mock_transport):
    framer = HSLinkFramer(mock_transport)
    pkt_type = b'D'
    payload = b'Test Payload'
    framer.send_packet(pkt_type, payload)
    assert len(mock_transport.out_buffer) > 0


def test_hslink_framer_read_packets(mock_transport):
    framer = HSLinkFramer(mock_transport)
    framer.send_packet(b'D', b'Test Payload')
    packets = framer.read_packets()
    assert len(packets) == 1
    assert packets[0][0] == b'D'
    assert packets[0][1] == b'Test Payload'


def test_hslink_session_initialization(mock_transport):
    session = HSLinkSession(mock_transport)
    assert session.state == 'INIT'


def test_hslink_session_add_files(mock_transport):
    session = HSLinkSession(mock_transport)
    session.add_files(['file1.txt', 'file2.txt'])
    assert len(session.files_to_send) == 2
