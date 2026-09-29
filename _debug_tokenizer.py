import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tokenizers import Tokenizer
from tokenizers.models import BPE
from tokenizers.trainers import BpeTrainer
from tokenizers.pre_tokenizers import Whitespace
from tokenizers.processors import TemplateProcessing

tmp = Path(tempfile.mkdtemp())
tok = Tokenizer(BPE(unk_token="<unk>"))
tok.pre_tokenizer = Whitespace()
trainer = BpeTrainer(
    vocab_size=100,
    special_tokens=["<unk>", "<pad>", "<eos>", "<s>", "</s>"],
)
texts = [
    "<s>[INST] Hello [/INST] world</s>",
    "<s>[INST] How are you [/INST] fine</s>",
]
tok.train_from_iterator(texts, trainer)
tok.post_processor = TemplateProcessing(
    single="<s>:0 $A:0 </s>:0",
    pair=None,
    special_tokens=[("<s>", 0), ("</s>", 1)],
)

enc = tok.encode("<s>[INST] Hello [/INST] world</s>")
print("tokens:", enc.ids)
print("len:", len(enc.ids))
