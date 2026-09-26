from typing import Optional, Dict, Any, List
import os
from pathlib import Path
from ASTROVOX_AI.ai_core.tokenization.custom_tokenizer import CustomTokenizer
from ASTROVOX_AI.ai_core.rag.incremental_indexing import IncrementalIndexer
from torch.utils.data import Dataset, DataLoader


class DataPipeline:
    def __init__(self, source_dir: str, tokenizer: Optional[CustomTokenizer] = None, batch_size: int = 32):
        self.source_dir = source_dir
        self.tokenizer = tokenizer or CustomTokenizer()
        self.batch_size = batch_size
        self.indexer = IncrementalIndexer()

    def load_raw(self, extensions: List[str] = None) -> List[Dict[str, str]]:
        extensions = extensions or ['.txt', '.md', '.json']
        documents = []
        source = Path(self.source_dir)
        for ext in extensions:
            for file_path in source.rglob(f'*{ext}'):
                try:
                    text = file_path.read_text(encoding='utf-8', errors='ignore')
                    documents.append({'id': str(file_path), 'text': text, 'metadata': {'source': str(file_path), 'ext': ext}})
                except Exception:
                    continue
        return documents

    def tokenize_batch(self, texts: List[str], max_length: int = 512) -> Dict[str, List]:
        input_ids = []
        attention_masks = []
        for text in texts:
            tokens = self.tokenizer.encode(text)[:max_length]
            padding = max_length - len(tokens)
            tokens = tokens + [0] * padding
            mask = [1] * len(tokens) + [0] * padding
            input_ids.append(tokens)
            attention_masks.append(mask[:max_length])
        return {'input_ids': input_ids, 'attention_mask': attention_masks}

    def create_dataloader(self, documents: List[Dict[str, str]], shuffle: bool = True) -> DataLoader:
        dataset = self._TextDataset(documents, self.tokenizer)
        return DataLoader(dataset, batch_size=self.batch_size, shuffle=shuffle, num_workers=4, pin_memory=True)

    class _TextDataset(Dataset):
        def __init__(self, documents: List[Dict[str, str]], tokenizer: CustomTokenizer, max_length: int = 512):
            self.documents = documents
            self.tokenizer = tokenizer
            self.max_length = max_length

        def __len__(self) -> int:
            return len(self.documents)

        def __getitem__(self, idx: int) -> Dict[str, List[int]]:
            text = self.documents[idx]['text']
            tokens = self.tokenizer.encode(text)[:self.max_length]
            tokens = tokens + [0] * (self.max_length - len(tokens))
            return {'input_ids': torch.tensor(tokens, dtype=torch.long)}
