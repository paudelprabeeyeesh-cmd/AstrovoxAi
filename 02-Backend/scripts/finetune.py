#!/usr/bin/env python3
"""
Weekly fine-tune script for AstrovoxAI.
Pulls high-rated interactions, formats as JSONL, validates, and triggers fine-tuning API.
"""
import sys
import os
import json
import argparse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db
from app.training_data_validator import validate_jsonl_format, generate_validation_report


def get_high_quality_interactions(min_rating=4, days=7, limit=5000):
    """Pull high-rated interactions from the last N days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
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


def trigger_fine_tune(
        file_path: str, model: str = "gpt-4o-mini", api_key: str | None = None
    ):
    """Trigger fine-tuning via provider API."""
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set. Skipping API call.")
        return None
    import urllib.request
    import urllib.error
    url = "https://api.openai.com/v1/files"
    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    with open(file_path, "rb") as f:
        file_data = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(file_path)}"\r\n'
        f"Content-Type: application/jsonl\r\n\r\n"
    ).encode("utf-8") + file_data + f"\r\n--{boundary}--\r\n".encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            print(f"Uploaded file ID: {result.get('id')}")
            return result
    except urllib.error.HTTPError as e:
        print(f"Upload failed: {e.code} {e.read().decode('utf-8')}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Fine-tune pipeline")
    parser.add_argument("--trigger-api", action="store_true", help="Trigger fine-tuning API call")
    parser.add_argument("--validate", action="store_true", help="Run validation and report errors")
    parser.add_argument("--dry-run", action="store_true", help="Export and validate without triggering API")
    parser.add_argument("--upload", action="store_true", help="Upload file to OpenAI fine-tuning endpoint")
    parser.add_argument("--model", default="gpt-4o-mini", help="Base model for fine-tuning")
    parser.add_argument("--limit", type=int, default=5000, help="Max interactions to export")
    parser.add_argument("--output", default=None, help="Output JSONL path")
    args = parser.parse_args()

    print("=== AstrovoxAI Fine-Tune Pipeline ===")

    interactions = get_high_quality_interactions(limit=args.limit)
    if not interactions:
        print("No high-quality interactions found for fine-tuning.")
        return

    print(f"Found {len(interactions)} high-quality interactions")

    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    output_path = args.output or f"/tmp/finetune_{date_str}.jsonl"
    export_jsonl(interactions, output_path)

    if args.validate:
        report = generate_validation_report(output_path)
        print("\nValidation report:")
        print(f"  Valid: {report['valid']}")
        print(f"  Record count: {report['record_count']}")
        if report["errors"]:
            print(f"  Errors ({len(report['errors'])}):")
            for e in report["errors"][:20]:
                print(f"    - {e}")
        else:
            print("  No errors found")
        if not report["valid"]:
            return
    else:
        count = validate_jsonl(output_path)
        print(f"\nValidated {count} entries")

    print("\nReady for fine-tuning:")
    print(f"  File: {output_path}")
    print(f"  Entries: {len(interactions)}")

    if args.dry_run:
        print("\nDry-run complete. Exiting without API calls.")
        return

    if args.upload:
        print("\nUploading file...")
        trigger_fine_tune(output_path, model=args.model)

    if args.trigger_api and not args.upload:
        print("\nTriggering fine-tuning API...")
        trigger_fine_tune(output_path, model=args.model)
    else:
        print("\nNext steps:")
        print(f"  1. Upload to provider: openai tools fine_tunes.prepare_data -f {output_path}")
        print(f"  2. Create fine-tune job: openai api fine_tunes.create -t {output_path} -m {args.model}")
        print(f"  3. Or use Together AI: together fine-tune --file {output_path} --model meta-llama/Llama-3.1-8B-Instruct")


if __name__ == "__main__":
    main()
