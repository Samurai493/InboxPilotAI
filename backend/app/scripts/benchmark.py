"""Script to run benchmarking comparisons."""
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.services.benchmarking import BenchmarkingService


def run_benchmark():
    """Run benchmarking comparison."""
    # Load sample messages
    data_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data",
        "sample_messages.json"
    )
    
    with open(data_path, "r") as f:
        messages = json.load(f)
    
    # Convert to benchmark format
    benchmark_messages = [
        {"id": str(i), "message": msg["message"], "category": msg["category"]}
        for i, msg in enumerate(messages[:20])  # Use first 20 for quick benchmark
    ]
    
    print("Running benchmark comparison...")
    print(f"Processing {len(benchmark_messages)} messages\n")
    
    # Run comparison
    results = BenchmarkingService.compare_routing_strategies(benchmark_messages)
    
    print("="*60)
    print("BENCHMARK RESULTS")
    print("="*60)
    print(f"\nSpecialist Routing:")
    print(f"  Success Rate: {results['specialist_routing']['successful']}/{results['specialist_routing']['total_messages']}")
    print(f"  Avg Confidence: {results['specialist_routing']['average_confidence']:.2f}")
    print(f"  Avg Tasks: {results['specialist_routing']['average_tasks_extracted']:.2f}")
    
    print(f"\nGeneral Routing:")
    print(f"  Success Rate: {results['general_routing']['successful']}/{results['general_routing']['total_messages']}")
    print(f"  Avg Confidence: {results['general_routing']['average_confidence']:.2f}")
    print(f"  Avg Tasks: {results['general_routing']['average_tasks_extracted']:.2f}")
    
    print(f"\nImprovement:")
    print(f"  Confidence Delta: {results['improvement']['confidence_delta']:+.2f}")
    print(f"  Tasks Delta: {results['improvement']['tasks_delta']:+.2f}")
    print(f"  Success Rate Delta: {results['improvement']['success_rate_delta']:+.2%}")
    
    # Save results
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data",
        "benchmark_results.json"
    )
    
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    run_benchmark()
