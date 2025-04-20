from datetime import datetime
from typing import List, Dict
import json
import os
from models import MemoryItem, MemoryOutput

class Memory:
    def __init__(self, memory_file: str = "agent_memory.json"):
        self.memory_file = memory_file
        self.memories: List[MemoryItem] = []
        self._load_memories()

    def _load_memories(self):
        if os.path.exists(self.memory_file):
            with open(self.memory_file, 'r') as f:
                memory_data = json.load(f)
                self.memories = [MemoryItem(**item) for item in memory_data]

    def _save_memories(self):
        with open(self.memory_file, 'w') as f:
            json.dump([memory.dict() for memory in self.memories], f, indent=2)

    def add_memory(self, context: str, action_taken: str, success_rating: float = None):
        memory_item = MemoryItem(
            timestamp=datetime.now().isoformat(),
            context=context,
            action_taken=action_taken,
            success_rating=success_rating
        )
        self.memories.append(memory_item)
        self._save_memories()

    def get_relevant_memories(self, context: str, limit: int = 5) -> MemoryOutput:
        # Simple relevance scoring based on context similarity
        scored_memories = []
        for memory in self.memories:
            # Basic string matching (in a real system, use better similarity metrics)
            relevance = sum(word in memory.context.lower() 
                          for word in context.lower().split())
            scored_memories.append((memory, relevance))

        # Sort by relevance and get top memories
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        relevant_memories = [mem[0] for mem in scored_memories[:limit]]

        # Calculate pattern insights
        pattern_insights = self._analyze_patterns(relevant_memories)

        return MemoryOutput(
            relevant_memories=relevant_memories,
            pattern_insights=pattern_insights
        )

    def _analyze_patterns(self, memories: List[MemoryItem]) -> Dict[str, float]:
        # Simple pattern analysis (in a real system, use more sophisticated analysis)
        success_rate = 0.0
        if memories and any(m.success_rating is not None for m in memories):
            ratings = [m.success_rating for m in memories if m.success_rating is not None]
            success_rate = sum(ratings) / len(ratings) if ratings else 0.0

        return {
            "success_rate": success_rate,
            "action_consistency": 0.7,  # Placeholder for more complex analysis
            "context_similarity": 0.8   # Placeholder for more complex analysis
        } 