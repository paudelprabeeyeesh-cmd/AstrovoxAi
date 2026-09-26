from ASTROVOX_AI.ai_core.rag.hybrid_rag import HybridRAG
from ASTROVOX_AI.ai_core.memory.cross_session_memory import CrossSessionMemory
from ASTROVOX_AI.ai_core.agent_communication_protocol import AgentCommunicationProtocol


class RetrievalAugmentedAgent:
    def __init__(self, model: nn.Module, tokenizer, memory: CrossSessionMemory, rag: HybridRAG):
        self.model = model
        self.tokenizer = tokenizer
        self.memory = memory
        self.rag = rag
        self.comm = AgentCommunicationProtocol('rag_agent')

    def query(self, user_query: str, top_k: int = 5, use_memory: bool = True, use_rag: bool = True) -> str:
        context_parts = []
        if use_memory:
            query_embedding = torch.randn(768)
            memory_context = self.memory.get_cross_session_context(query_embedding, top_k=3)
            if memory_context:
                context_parts.append('Memory Context:\n' + '\n'.join([m.get('text', '') for m in memory_context]))
        if use_rag:
            rag_results = self.rag.retrieve(user_query, top_k=top_k)
            if rag_results:
                context_parts.append('Retrieved Context:\n' + '\n'.join([r.get('text', '') for r in rag_results]))
        prompt = user_query
        if context_parts:
            prompt = '\n\n'.join(context_parts) + '\n\nQuery: ' + user_query
        inputs = torch.tensor(self.tokenizer.encode(prompt)).unsqueeze(0)
        with torch.no_grad():
            output = self.model(inputs)
        response = self.tokenizer.decode(output[0].tolist())
        self.memory.store_memory('default', {'text': response, 'embedding': torch.randn(768), 'importance': 0.8})
        return response
