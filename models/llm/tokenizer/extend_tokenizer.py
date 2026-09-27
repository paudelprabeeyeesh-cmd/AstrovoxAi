import os

from tokenizers import Tokenizer

save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokenizer.json")
save_path = os.path.abspath(save_path)
tokenizer = Tokenizer.from_file(save_path)
current_vocab_size = tokenizer.get_vocab_size()
target_vocab_size = 32000

if current_vocab_size < target_vocab_size:
    extra_tokens = [f"<extra_{i}>" for i in range(target_vocab_size - current_vocab_size)]
    tokenizer.add_tokens(extra_tokens)
    tokenizer.save(save_path)
    print(f"Extended tokenizer from {current_vocab_size} to {tokenizer.get_vocab_size()} tokens")
else:
    print(f"Tokenizer already has {current_vocab_size} tokens")
