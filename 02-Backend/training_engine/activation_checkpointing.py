import numpy as np


def checkpoint_forward(func, inputs, *args, **kwargs):
    return func(inputs, *args, **kwargs)


def checkpoint_backward(func, inputs, *args, **kwargs):
    saved = [np.copy(np.asarray(i)) for i in inputs]
    return func(saved, *args, **kwargs)


class ActivationCheckpoint:
    def __init__(self, func):
        self.func = func

    def forward(self, x, *args, **kwargs):
        self._saved_input = np.copy(np.asarray(x))
        return self.func(x, *args, **kwargs)

    def backward(self, grad_output, *args, **kwargs):
        x = self._saved_input
        return self.func(x, *args, **kwargs) * grad_output
