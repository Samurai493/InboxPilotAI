"""Evaluation script using LangSmith."""
import json
import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from langsmith import Client, aevaluate
from app.services.graph_service import GraphService


async def evaluate_with_langsmith():
    """Run evaluation using LangSmith."""
    # Load evaluation dataset
    data_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data",
        "evaluation_dataset.json"
    )
    
    with open(data_path, "r") as f:
        dataset = json.load(f)
    
    # Create LangSmith client
    client = Client()
    
    # Create dataset in LangSmith
    dataset_name = "inboxpilot-evaluation"
    
    try:
        # Check if dataset exists
        existing = client.read_dataset(dataset_name=dataset_name)
        print(f"Using existing dataset: {dataset_name}")
    except:
        # Create new dataset
        print(f"Creating new dataset: {dataset_name}")
        inputs = [item["input"] for item in dataset]
        outputs = [item["expected"] for item in dataset]
        
        client.create_dataset(
            dataset_name=dataset_name,
            inputs=inputs,
            outputs=outputs
        )
    
    # Define target function
    async def target(inputs: dict) -> dict:
        """Target function for evaluation."""
        message = inputs["message"]
        result = GraphService.process_message(
            user_id="evaluation-user",
            raw_message=message
        )
        
        state = result.get("state", {})
        
        return {
            "intent": state.get("intent"),
            "tasks": state.get("extracted_tasks", []),
            "draft_reply": state.get("draft_reply", "")
        }
    
    # Define evaluators
    async def check_intent(outputs: dict, reference_outputs: dict) -> dict:
        """Check if intent classification is correct."""
        predicted = outputs.get("intent", "")
        expected = reference_outputs.get("intent", "")
        
        return {
            "score": 1.0 if predicted == expected else 0.0,
            "correct": predicted == expected
        }
    
    async def check_tasks(outputs: dict, reference_outputs: dict) -> dict:
        """Check if tasks were extracted."""
        predicted_tasks = outputs.get("tasks", [])
        expected_tasks = reference_outputs.get("tasks", [])
        
        if len(expected_tasks) == 0:
            return {"score": 1.0 if len(predicted_tasks) == 0 else 0.5}
        
        # Simple check: at least one task extracted
        score = min(1.0, len(predicted_tasks) / len(expected_tasks))
        
        return {
            "score": score,
            "predicted_count": len(predicted_tasks),
            "expected_count": len(expected_tasks)
        }
    
    # Run evaluation
    print("Running evaluation...")
    results = await aevaluate(
        target,
        data=dataset_name,
        evaluators=[check_intent, check_tasks],
        max_concurrency=2
    )
    
    print("\n" + "="*60)
    print("EVALUATION RESULTS")
    print("="*60)
    
    # Print summary
    intent_scores = [r.get("check_intent", {}).get("score", 0) for r in results]
    task_scores = [r.get("check_tasks", {}).get("score", 0) for r in results]
    
    print(f"\nIntent Classification:")
    print(f"  Accuracy: {sum(intent_scores) / len(intent_scores):.2%}")
    print(f"  Correct: {sum(intent_scores)}/{len(intent_scores)}")
    
    print(f"\nTask Extraction:")
    print(f"  Average Score: {sum(task_scores) / len(task_scores):.2f}")
    
    # Save results
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data",
        "evaluation_results.json"
    )
    
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {output_path}")
    print(f"\nView results in LangSmith: https://smith.langchain.com")


if __name__ == "__main__":
    asyncio.run(evaluate_with_langsmith())
