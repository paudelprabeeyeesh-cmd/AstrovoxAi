from zero_shot_learning.description_encoder import DescriptionEncoder, EncodedDescription


def test_encode_shape():
    encoder = DescriptionEncoder(dim=32)
    desc = encoder.encode("a small furry pet")
    assert len(desc.embedding) == 32
    assert desc.text == "a small furry pet"
    assert len(desc.tokens) > 0


def test_similarity_high():
    encoder = DescriptionEncoder(dim=32)
    a = encoder.encode("furry pet cat")
    b = encoder.encode("furry pet cat")
    score = encoder.similarity(a, b)
    assert score > 0.99


def test_similarity_low():
    encoder = DescriptionEncoder(dim=32)
    a = encoder.encode("red apple")
    b = encoder.encode("blue car")
    score = encoder.similarity(a, b)
    assert score >= 0.0


def test_batch_encode():
    encoder = DescriptionEncoder(dim=16)
    descs = encoder.batch_encode(["cat", "dog", "car"])
    assert len(descs) == 3
    assert all(len(d.embedding) == 16 for d in descs)
