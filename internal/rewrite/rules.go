package rewrite

import "github.com/astrovox/astrovox/internal/ir"

// Built-in rewrite rules.
var (
	RuleMatMulBias = &RewriteRule{
		Name:     "MatMulBiasToLinear",
		Pattern:  &Pattern{Name: "matmul_bias", Nodes: []*ir.Node{{Op: "matmul"}, {Op: "add"}}},
		Priority: 10,
		Replace: func(g *ir.Graph, m MatchResult) []*ir.Node {
			return []*ir.Node{{Op: "linear", Inputs: []int64{m.Root}}}
		},
	}
	RuleConvBN = &RewriteRule{
		Name:     "ConvBNToFusedConv",
		Pattern:  &Pattern{Name: "conv_bn", Nodes: []*ir.Node{{Op: "conv"}, {Op: "batch_norm"}}},
		Priority: 10,
		Replace: func(g *ir.Graph, m MatchResult) []*ir.Node {
			return []*ir.Node{{Op: "fused_conv_bn", Inputs: []int64{m.Root}}}
		},
	}
	RuleAddRelu = &RewriteRule{
		Name:     "AddReluToFusedAddRelu",
		Pattern:  &Pattern{Name: "add_relu", Nodes: []*ir.Node{{Op: "add"}, {Op: "relu"}}},
		Priority: 5,
		Replace: func(g *ir.Graph, m MatchResult) []*ir.Node {
			return []*ir.Node{{Op: "fused_add_relu", Inputs: []int64{m.Root}}}
		},
	}
)

// RegisterDefaults registers built-in rules.
func RegisterDefaults(e *RuleEngine) {
	e.AddRule(RuleMatMulBias)
	e.AddRule(RuleConvBN)
	e.AddRule(RuleAddRelu)
}
