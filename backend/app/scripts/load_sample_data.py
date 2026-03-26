"""Script to load sample messages for testing."""
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.services.graph_service import GraphService


def load_sample_data():
    """Load and process sample messages."""
    sample_user_id = os.environ.get("SAMPLE_USER_ID")
    if not sample_user_id:
        print("Set SAMPLE_USER_ID to a users.id UUID (see User table).", file=sys.stderr)
        sys.exit(1)

    data_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data",
        "sample_messages.json",
    )

    with open(data_path, "r") as f:
        messages = json.load(f)

    print(f"Loaded {len(messages)} sample messages")
    print("\nProcessing messages...\n")

    results = []
    for i, msg_data in enumerate(messages, 1):
        print(f"Processing {i}/{len(messages)}: {msg_data['category']}")

        try:
            result = GraphService.process_message(
                user_id=sample_user_id,
                raw_message=msg_data["message"],
            )
            results.append(
                {
                    "index": i,
                    "category": msg_data["category"],
                    "thread_id": result["thread_id"],
                    "status": result["status"],
                }
            )
        except Exception as e:
            print(f"  Error: {e}")
            results.append(
                {
                    "index": i,
                    "category": msg_data["category"],
                    "status": "failed",
                    "error": str(e),
                }
            )

    print("\n" + "=" * 50)
    print("Summary:")
    print("=" * 50)

    success = sum(1 for r in results if r["status"] == "completed")
    failed = len(results) - success

    print(f"Total: {len(results)}")
    print(f"Success: {success}")
    print(f"Failed: {failed}")

    print("\nBy Category:")
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "success": 0}
        categories[cat]["total"] += 1
        if r["status"] == "completed":
            categories[cat]["success"] += 1

    for cat, stats in categories.items():
        print(f"  {cat}: {stats['success']}/{stats['total']}")

    return results


if __name__ == "__main__":
    load_sample_data()
