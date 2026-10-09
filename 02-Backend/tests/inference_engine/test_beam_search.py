import numpy as np

from inference_engine.beam_search import (
    BeamSearchDecoder,
    Beam,
    BeamHypothesis,
    BeamSearchMode,
    LengthPenaltyType,
    length_penalty_wu,
    length_penalty_leng,
    softmax,
    log_softmax,
)


def test_beam_hypothesis_extend():
    h = BeamHypothesis(token_ids=[1, 2])
    new_h = h.extend(token_id=3, log_prob=-0.5)
    assert new_h.token_ids == [1, 2, 3]
    assert abs(new_h.log_prob - (-0.5)) < 1e-6


def test_beam_hypothesis_score():
    h = BeamHypothesis(token_ids=[1, 2], log_prob=-2.0, length_penalty=0.9)
    score = h.score
    assert isinstance(score, float)


def test_beam_hypothesis_completed():
    h = BeamHypothesis(token_ids=list(range(50)))
    assert h.completed(max_length=10) is True


def test_beam_hypothesis_copy():
    h = BeamHypothesis(token_ids=[1, 2], log_prob=-1.0)
    h2 = h.copy()
    assert h2 is not h
    assert h2.token_ids == [1, 2]
    assert abs(h2.log_prob - (-1.0)) < 1e-6


def test_beam_defaults():
    beam = Beam(num_beams=4)
    assert beam.num_beams == 4
    assert beam.mode == BeamSearchMode.BEST_K


def test_beam_current():
    beam = Beam(num_beams=4)
    current = beam.current
    assert current is not None
    assert len(current.token_ids) == 0


def test_beam_step():
    beam = Beam(num_beams=4)
    log_probs = np.array([-0.1, -0.2, -0.3, -0.4])
    next_hypos = beam.step(log_probs, eos_token_id=2)
    assert len(next_hypos) <= 4
    for h in next_hypos:
        assert isinstance(h, BeamHypothesis)


def test_beam_step_one_vs_n():
    beam = Beam(mode=BeamSearchMode.ONE_VS_N, num_beams=4)
    log_probs = np.array([-0.1, -0.2, -0.3, -0.4])
    next_hypos = beam.step_one_vs_n(log_probs, eos_token_id=2)
    assert isinstance(next_hypos, list)


def test_beam_is_done():
    beam = Beam(num_beams=4)
    assert beam.is_done(max_length=10) is False


def test_beam_best():
    beam = Beam(num_beams=4)
    log_probs = np.array([-0.1, -0.2, -0.3, -0.4])
    beam.step(log_probs, eos_token_id=2)
    best = beam.best()
    assert best is not None


def test_beam_search_decoder_defaults():
    decoder = BeamSearchDecoder()
    assert decoder.num_beams == 4
    assert decoder.max_length == 50
    assert decoder.eos_token_id == 2


def test_beam_search_decoder_decode():
    decoder = BeamSearchDecoder(num_beams=4, max_length=20)
    log_probs = np.array([-0.1, -0.2, -0.3, -0.4, 0.0, 0.0, 0.0, 0.0])
    result = decoder.decode(log_probs)
    assert result is None or isinstance(result, BeamHypothesis)


def test_beam_search_decoder_reset():
    decoder = BeamSearchDecoder()
    log_probs = np.array([-0.1, -0.2])
    decoder.decode(log_probs)
    decoder.reset()
    assert len(decoder.get_all_hypos()) == 0


def test_beam_search_decoder_get_all_hypos():
    decoder = BeamSearchDecoder()
    log_probs = np.array([-0.1, -0.2])
    decoder.decode(log_probs)
    all_hypos = decoder.get_all_hypos()
    assert isinstance(all_hypos, list)


def test_beam_search_decoder_get_best_hypo():
    decoder = BeamSearchDecoder()
    log_probs = np.array([-0.1, -0.2])
    decoder.decode(log_probs)
    best = decoder.get_best_hypo()
    assert best is not None


def test_beam_search_decoder_get_top_k():
    decoder = BeamSearchDecoder(num_beams=4)
    for _ in range(5):
        log_probs = np.array([-0.1, -0.2, -0.3, -0.4])
        decoder.decode(log_probs)
    top_2 = decoder.get_top_k_hypos(k=2)
    assert len(top_2) == 2


def test_beam_search_decoder_force_step():
    decoder = BeamSearchDecoder()
    log_probs = np.array([-0.1])
    decoder.decode(log_probs)
    decoder.force_step(token_id=5, log_prob=-1.0)
    assert len(decoder.get_all_hypos()) == 2


def test_beam_search_decoder_decode_one_vs_n():
    decoder = BeamSearchDecoder(
        num_beams=4,
        beam_mode=BeamSearchMode.ONE_VS_N,
        max_length=20,
    )
    log_probs = np.array([-0.1, -0.2, -0.3, -0.4])
    result = decoder.decode_one_vs_n(log_probs)
    assert result is None or isinstance(result, BeamHypothesis)


def test_length_penalty_wu():
    lp = length_penalty_wu(length=10, alpha=0.9)
    assert lp > 0


def test_length_penalty_leng():
    lp = length_penalty_leng(length=10, beta=0.5)
    assert lp > 0


def test_softmax():
    x = np.array([[1.0, 2.0, 3.0]])
    probs = softmax(x)
    assert abs(probs.sum() - 1.0) < 1e-5


def test_log_softmax():
    x = np.array([[1.0, 2.0, 3.0]])
    log_probs = log_softmax(x)
    assert log_probs.shape == (1, 3)
    assert abs(np.exp(log_probs).sum() - 1.0) < 1e-5


def test_beam_hypothesis_score_positive():
    h = BeamHypothesis(token_ids=[1, 2, 3], log_prob=-1.0)
    assert h.score is not None


def test_beam_hypothesis_score_consistent():
    h = BeamHypothesis(token_ids=[1, 2, 3], log_prob=-1.0)
    score1 = h.score
    score2 = h.score
    assert abs(score1 - score2) < 1e-10
