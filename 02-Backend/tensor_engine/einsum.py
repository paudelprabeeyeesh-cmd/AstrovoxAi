import numpy as np
from collections import defaultdict


class EinsumEquation:
    def __init__(self, equation):
        if "->" in equation:
            inputs_str, output_str = equation.split("->")
        else:
            inputs_str = equation
            output_str = ""

        input_strs = inputs_str.split(",")
        self.inputs = [s.strip() for s in input_strs]
        self.output = output_str.strip()
        self.ninputs = len(self.inputs)
        self.output_labels = list(self.output)

        # Map label to indices in each input
        self.label_to_inputs = defaultdict(list)
        for i, inp in enumerate(self.inputs):
            for j, label in enumerate(inp):
                self.label_to_inputs[label].append((i, j))

        # Contraction labels
        self.contract_labels = []
        for label, positions in self.label_to_inputs.items():
            if len(positions) > 1 and label not in self.output:
                self.contract_labels.append(label)

    def verify_shapes(self, shapes):
        if len(shapes) != self.ninputs:
            raise ValueError(
                f"Expected {self.ninputs} input arrays, got {len(shapes)}"
            )
        for i, (inp, shape) in enumerate(zip(self.inputs, shapes)):
            if len(inp) != len(shape):
                raise ValueError(
                    f"Input {i} has {len(shape)} dimensions but subscript has "
                    f"{len(inp)} labels"
                )
            for j, label in enumerate(inp):
                if label != " ":
                    for k, (other_i, other_j) in enumerate(self.label_to_inputs[label]):
                        if other_i != i:
                            if shapes[i][j] != shapes[other_i][other_j]:
                                raise ValueError(
                                    f"Dimension mismatch for label '{label}': "
                                    f"{shapes[i][j]} vs {shapes[other_i][other_j]}"
                                )

    def compute_output_shape(self, shapes):
        result_shape = []
        for label in self.output:
            for i, inp in enumerate(self.inputs):
                if label in inp:
                    j = inp.index(label)
                    result_shape.append(shapes[i][j])
                    break
        return tuple(result_shape)

    def contraction_axes(self, shape_i, shape_j):
        axes_i = []
        axes_j = []
        for label in self.contract_labels:
            if label in self.inputs[0] and label in self.inputs[1]:
                axes_i.append(self.inputs[0].index(label))
                axes_j.append(self.inputs[1].index(label))
        return axes_i, axes_j


def einsum(equation, *operands, optimize="greedy"):
    if not operands:
        raise ValueError("einsum requires at least one operand")

    eq = EinsumEquation(equation)
    shapes = [np.asarray(op).shape for op in operands]
    eq.verify_shapes(shapes)

    # Use numpy's einsum for computation; our parser identifies contraction dimensions
    result = np.einsum(equation, *operands, optimize=optimize)
    return result
