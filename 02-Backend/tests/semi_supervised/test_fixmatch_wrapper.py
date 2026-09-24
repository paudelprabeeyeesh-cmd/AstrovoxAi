import math

from semi_supervised.fixmatch_wrapper import FixMatchWrapper


def _model(x: list[list[float]]) -> list[list[float]]:
    return [[math.cos(sum(sample) + i) for i in range(3)] for sample in x]


def _cross_entropy_loss(logits: list[list[float]], labels: list[int]) -> float:
    loss = 0.0
    for logit, label in zip(logits, labels):
        max_logit = max(logit)
        exps = [math.exp(l - max_logit) for l in logit]
        sum_exps = sum(exps)
        probs = [e / sum_exps for e in exps]
        loss += -math.log(probs[label] + 1e-12)
    return loss / len(logits)


def test_fixmatch_keys():
    wrapper = FixMatchWrapper(threshold=0.9, lambda_u=1.0)
    labeled_x = [[1.0, 2.0], [3.0, 4.0]]
    labeled_y = [0, 1]
    unlabeled_x_weak = [[5.0, 6.0], [7.0, 8.0]]
    unlabeled_x_strong = [[5.1, 6.1], [7.1, 8.1]]
    result = wrapper(labeled_x, labeled_y, unlabeled_x_weak, unlabeled_x_strong, _model, _cross_entropy_loss)
    assert "loss" in result
    assert "labeled_loss" in result
    assert "unlabeled_loss" in result
    assert "mask" in result
    assert "pseudo_labels" in result


def test_fixmatch_loss_positive():
    wrapper = FixMatchWrapper(threshold=0.9, lambda_u=1.0)
    labeled_x = [[1.0, 2.0]]
    labeled_y = [0]
    unlabeled_x_weak = [[5.0, 6.0]]
    unlabeled_x_strong = [[5.1, 6.1]]
    result = wrapper(labeled_x, labeled_y, unlabeled_x_weak, unlabeled_x_strong, _model, _cross_entropy_loss)
    assert result["loss"] > 0.0
    assert result["labeled_loss"] > 0.0


def test_fixmatch_mask():
    wrapper = FixMatchWrapper(threshold=0.9, lambda_u=1.0)
    labeled_x = [[1.0, 2.0]]
    labeled_y = [0]
    unlabeled_x_weak = [[5.0, 6.0]]
    unlabeled_x_strong = [[5.1, 6.1]]
    result = wrapper(labeled_x, labeled_y, unlabeled_x_weak, unlabeled_x_strong, _model, _cross_entropy_loss)
    assert all(m in (0.0, 1.0) for m in result["mask"])
