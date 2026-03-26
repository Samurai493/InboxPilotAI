"""Benchmarking service for A/B testing specialist vs general routing."""
from typing import Dict, List, Any
from app.services.graph_service import GraphService
import json


class BenchmarkingService:
    """Service for running A/B tests and benchmarks."""
    
    @staticmethod
    def run_comparison(
        messages: List[Dict[str, str]],
        use_specialist: bool = True
    ) -> Dict[str, Any]:
        """
        Run comparison between specialist and general routing.
        
        Args:
            messages: List of message dictionaries with 'message' and 'category' keys
            use_specialist: Whether to use specialist routing
            
        Returns:
            Comparison results
        """
        results = []
        
        for msg_data in messages:
            try:
                # Process message
                result = GraphService.process_message(
                    user_id="benchmark-user",
                    raw_message=msg_data["message"],
                    use_specialist=use_specialist,
                )
                
                state = result.get("state", {})
                
                # Extract metrics
                metrics = {
                    "message_id": msg_data.get("id", "unknown"),
                    "category": msg_data.get("category", "unknown"),
                    "intent": state.get("intent"),
                    "confidence_score": state.get("confidence_score"),
                    "draft_reply": state.get("draft_reply"),
                    "extracted_tasks_count": len(state.get("extracted_tasks", [])),
                    "status": result.get("status"),
                    "use_specialist": use_specialist
                }
                
                results.append(metrics)
            except Exception as e:
                results.append({
                    "message_id": msg_data.get("id", "unknown"),
                    "category": msg_data.get("category", "unknown"),
                    "error": str(e),
                    "status": "failed",
                    "use_specialist": use_specialist
                })
        
        # Calculate aggregate metrics
        successful = [r for r in results if r.get("status") == "completed"]
        avg_confidence = sum(r.get("confidence_score", 0) for r in successful) / len(successful) if successful else 0
        avg_tasks = sum(r.get("extracted_tasks_count", 0) for r in successful) / len(successful) if successful else 0
        
        return {
            "total_messages": len(messages),
            "successful": len(successful),
            "failed": len(results) - len(successful),
            "average_confidence": avg_confidence,
            "average_tasks_extracted": avg_tasks,
            "use_specialist": use_specialist,
            "results": results
        }
    
    @staticmethod
    def compare_routing_strategies(
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Compare specialist vs general routing.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Comparison results
        """
        # Run with specialist routing
        specialist_results = BenchmarkingService.run_comparison(messages, use_specialist=True)
        
        general_results = BenchmarkingService.run_comparison(messages, use_specialist=False)
        
        return {
            "specialist_routing": specialist_results,
            "general_routing": general_results,
            "improvement": {
                "confidence_delta": specialist_results["average_confidence"] - general_results["average_confidence"],
                "tasks_delta": specialist_results["average_tasks_extracted"] - general_results["average_tasks_extracted"],
                "success_rate_delta": (specialist_results["successful"] / specialist_results["total_messages"]) - (general_results["successful"] / general_results["total_messages"])
            }
        }
