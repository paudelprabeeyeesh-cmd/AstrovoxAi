import os
from tokenizers import Tokenizer
from tokenizers.models import BPE
from tokenizers.trainers import BpeTrainer
from tokenizers.pre_tokenizers import ByteLevel
from tokenizers.decoders import ByteLevel as ByteLevelDecoder

dummy_text = (
    "Hello world! This is a test sentence for the dummy tokenizer. "
    "The quick brown fox jumps over the lazy dog. "
    "Artificial intelligence is transforming the world. "
    "Machine learning models require data to train. "
    "Natural language processing enables computers to understand text. "
    "Deep learning uses neural networks with many layers. "
    "Transformers have revolutionized sequence modeling. "
    "Attention mechanisms help models focus on relevant parts. "
    "Tokenization splits text into smaller units called tokens. "
    "Byte Pair Encoding is a popular tokenization algorithm. "
) * 2000

save_path = os.path.join(os.path.dirname(__file__), "tokenizer.json")
os.makedirs(os.path.dirname(save_path), exist_ok=True)

with open(save_path + ".train.txt", "w", encoding="utf-8") as f:
    f.write(dummy_text)

tokenizer = Tokenizer(BPE(unk_token="<unk>"))
tokenizer.pre_tokenizer = ByteLevel()
tokenizer.decoder = ByteLevelDecoder()
trainer = BpeTrainer(
    vocab_size=32000,
    special_tokens=["<unk>", "<pad>", "<bos>", "<eos>"],
    min_frequency=2,
)
tokenizer.train([save_path + ".train.txt"], trainer)
tokenizer.save(save_path)
print(f"Dummy tokenizer saved to {save_path}")
os.remove(save_path + ".train.txt")
