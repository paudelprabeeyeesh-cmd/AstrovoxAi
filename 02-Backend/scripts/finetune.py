#!/usr/bin/env python3
"""
Weekly fine-tune script for AstrovoxAI.
Pulls high-rated interactions, formats as JSONL, and uploads for fine-tuning.
"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db
from datetime import datetime, timedelta


def get_high_quality_interactions(min_rating=4, days=7, limit=5000):
    """Pull high-rated interactions from the last N days."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with get_db() as conn:
        rows = conn.execute("""
            SELECT prompt, response, model, metadata
            FROM interactions
            WHERE rating >= ? AND created_at >= ? AND correction IS NULL
            ORDER BY created_at DESC
            LIMIT ?
        """, (min_rating, cutoff, limit)).fetchall()
        return [dict(r) for r in rows]


def export_jsonl(interactions, output_path):
    """Export interactions to OpenAI fine-tune JSONL format."""
    with open(output_path, "w", encoding="utf-8") as f:
        for item in interactions:
            messages = [
                {"role": "user", "content": item["prompt"]},
                {"role": "assistant", "content": item["response"]}
            ]
            entry = {"messages": messages}
            if item.get("metadata"):
                entry["metadata"] = item["metadata"]
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"Exported {len(interactions)} interactions to {output_path}")


def validate_jsonl(path):
    """Validate that JSONL is well-formed."""
    count = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line.strip())
            assert "messages" in entry, "Missing 'messages' key"
            assert len(entry["messages"]) >= 2, "Need at least 2 messages"
            count += 1
    print(f"Validated {count} entries in {path}")
    return count


def main():
    print("=== AstrovoxAI Fine-Tune Pipeline ===")
    
    # 1. Pull high-quality interactions
    interactions = get_high_quality_interactions()
    if not interactions:
        print("No high-quality interactions found for fine-tuning.")
        return
    
    print(f"Found {len(interactions)} high-quality interactions")
    
    # 2. Export to JSONL
    date_str = datetime.utcnow().strftime("%Y%m%d")
    output_path = f"/tmp/finetune_{date_str}.jsonl"
    export_jsonl(interactions, output_path)
    
    # 3. Validate
    count = validate_jsonl(output_path)
    print(f"\nReady for fine-tuning:")
    print(f"  File: {output_path}")
    print(f"  Entries: {count}")
    print(f"\nNext steps:")
    print(f"  1. Upload to provider: openai tools fine_tunes.prepare_data -f {output_path}")
    print(f"  2. Create fine-tune job: openai api fine_tunes.create -t {output_path} -m gpt-4o-mini")
    print(f"  3. Or use Together AI: together fine-tune --file {output_path} --model meta-llama/Llama-3.1-8B-Instruct")


if __name__ == "__main__":
    main()