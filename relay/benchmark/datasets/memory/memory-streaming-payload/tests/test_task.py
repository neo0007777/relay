def test_streaming_chunk_size():
    from src.memory.stream import JSONStreamer
    assert JSONStreamer().stream_chunks() == 64 # KB chunks
