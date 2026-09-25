#!/usr/bin/env python3
"""
Labeling pipeline for AstrovoxAI interactions.
Allows tagging interactions as good/bad/hallucination/needs-detail/incorrect.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db
import uuid


def get_unlabeled_interactions(limit=50):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT i.id, i.prompt, i.response, i.model, i.rating, i.created_at
            FROM interactions i
            LEFT JOIN interaction_labels l ON i.id = l.interaction_id
            WHERE l.id IS NULL
            ORDER BY i.created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def label_interaction(interaction_id: str, label: str, notes: str = None):
    label_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO interaction_labels (id, interaction_id, label, notes, labeled_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (label_id, interaction_id, label, notes, "cli", __import__('datetime').datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
    print(f"Labeled {interaction_id} as '{label}'")


def main():
    print("=== AstrovoxAI Labeling Pipeline ===")
    interactions = get_unlabeled_interactions()
    
    if not interactions:
        print("No unlabeled interactions found.")
        return
    
    print(f"Found {len(interactions)} unlabeled interactions.\n")
    
    for i, item in enumerate(interactions):
        print(f"[{i+1}/{len(interactions)}] ID: {item['id']}")
        print(f"  Prompt: {item['prompt'][:100]}...")
        print(f"  Response: {item['response'][:100]}...")
        print(f"  Model: {item['model']}, Rating: {item['rating']}")
        print()
        
        label = input("Label (good/bad/hallucination/needs-detail/incorrect/skip): ").strip().lower()
        if label == "skip":
            continue
        if label not in ["good", "bad", "hallucination", "needs-detail", "incorrect"]:
            print("Invalid label, skipping.")
            continue
        
        notes = input("Notes (optional): ").strip() or None
        label_interaction(item['id'], label, notes)
        print()
    
    print("Labeling complete.")


if __name__ == "__main__":
    main()