import numpy as np

from multimodal.multimodal_retrieval import (
    UnifiedEmbeddingSpace,
    CrossModalRetriever,
)


def _make_pixels(h=32, w=32):
    return np.random.randint(0, 255, size=(h, w, 3), dtype=np.uint8)


def _make_mfcc():
    return np.random.randn(13, 40).astype(np.float64)


def test_embed_text_shape():
    space = UnifiedEmbeddingSpace(embed_dim=256)
    emb = space.embed_text("hello world")
    assert emb.shape == (256,)


def test_embed_image_shape():
    space = UnifiedEmbeddingSpace(embed_dim=256)
    emb = space.embed_image(_make_pixels())
    assert emb.shape == (256,)


def test_embed_audio_shape():
    space = UnifiedEmbeddingSpace(embed_dim=256)
    emb = space.embed_audio(_make_mfcc())
    assert emb.shape == (256,)


def test_embed_video_shape():
    space = UnifiedEmbeddingSpace(embed_dim=256)
    emb = space.embed_video(np.random.randn(128).astype(np.float64))
    assert emb.shape == (256,)


def test_compute_similarity_range():
    space = UnifiedEmbeddingSpace(embed_dim=256)
    a = space.embed_text("cat")
    b = space.embed_text("cat")
    sim = space.compute_similarity(a, b)
    assert np.isfinite(sim)


def test_contrastive_loss_positive():
    space = UnifiedEmbeddingSpace(embed_dim=256)
    anchor = space.embed_text("cat")
    pos = space.embed_text("cat")
    negs = [space.embed_text("dog"), space.embed_text("bird")]
    loss = space.contrastive_loss(anchor, pos, negs)
    assert loss >= 0.0
    assert np.isfinite(loss)


def test_retriever_add_and_search():
    space = UnifiedEmbeddingSpace()
    retriever = CrossModalRetriever(space)
    pixels = _make_pixels()
    retriever.add_item("image", space.embed_image(pixels), {"label": "img1"})
    results = retriever.search(space.embed_text("image"), top_k=1)
    assert len(results) == 1
    assert results[0].modality == "image"


def test_retriever_build_index():
    space = UnifiedEmbeddingSpace()
    retriever = CrossModalRetriever(space)
    items = [
        ("text", "hello world", {"label": "t1"}),
        ("image", _make_pixels(), {"label": "i1"}),
    ]
    retriever.build_index(items)
    assert len(retriever.index) == 2


def test_retriever_modality_filter():
    space = UnifiedEmbeddingSpace()
    retriever = CrossModalRetriever(space)
    retriever.add_item("text", space.embed_text("hello"), {})
    retriever.add_item("image", space.embed_image(_make_pixels()), {})
    results = retriever.search(space.embed_text("hello"), top_k=5, modality_filter="text")
    assert all(r.modality == "text" for r in results)


def test_retrieve_text_to_image():
    space = UnifiedEmbeddingSpace()
    retriever = CrossModalRetriever(space)
    retriever.add_item("image", space.embed_image(_make_pixels()), {})
    results = retriever.retrieve_text_to_image("picture", top_k=1)
    assert len(results) == 1
    assert results[0].modality == "image"


def test_retrieve_image_to_text():
    space = UnifiedEmbeddingSpace()
    retriever = CrossModalRetriever(space)
    retriever.add_item("text", space.embed_text("description"), {})
    results = retriever.retrieve_image_to_text(_make_pixels(), top_k=1)
    assert len(results) == 1
    assert results[0].modality == "text"
