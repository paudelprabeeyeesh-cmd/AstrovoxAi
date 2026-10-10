package ir

// Value represents an SSA value.
type Value struct {
	ID    int
	Name  string
	Type  string
	Block int
}

// Block represents a basic block in SSA form.
type Block struct {
	ID   int
	Name string
	Ops  []*Value
	Phi  []*PhiNode
}

// PhiNode represents a PHI node for merging values from different blocks.
type PhiNode struct {
	ID    int
	Value *Value
	Pairs []PhiPair
}

// PhiPair represents a value + predecessor pair for a PHI node.
type PhiPair struct {
	Value       *Value
	Predecessor int
}

// Function represents an SSA function.
type Function struct {
	Name   string
	Blocks map[int]*Block
	Values map[int]*Value
	Order  []int
}

// NewFunction creates a new SSA function.
func NewFunction(name string) *Function {
	return &Function{
		Name:   name,
		Blocks: make(map[int]*Block),
		Values: make(map[int]*Value),
	}
}

// AddBlock adds a basic block.
func (f *Function) AddBlock(b *Block) {
	f.Blocks[b.ID] = b
	f.Order = append(f.Order, b.ID)
}

// AddValue adds an SSA value.
func (f *Function) AddValue(v *Value) {
	f.Values[v.ID] = v
}

// Builder provides a fluent API for constructing SSA functions.
type Builder struct {
	fn      *Function
	counter int
}

// NewBuilder creates a new SSA builder.
func NewBuilder(name string) *Builder {
	return &Builder{fn: NewFunction(name)}
}

// Build returns the constructed function.
func (b *Builder) Build() *Function {
	return b.fn
}

// CreateValue creates a new SSA value.
func (b *Builder) CreateValue(name, typ string, block int) *Value {
	b.counter++
	v := &Value{ID: b.counter, Name: name, Type: typ, Block: block}
	b.fn.AddValue(v)
	return v
}

// CreateBlock creates a new basic block.
func (b *Builder) CreateBlock(name string) *Block {
	b.counter++
	blk := &Block{ID: b.counter, Name: name}
	b.fn.AddBlock(blk)
	return blk
}
