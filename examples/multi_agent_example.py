"""
Example usage of the multi-agent orchestration system.

This demonstrates how to use the multi-agent system for complex decision-making
with debate mechanism and full transparency.
"""

import asyncio
import os

from max_os.core.multi_agent_orchestrator import MultiAgentOrchestrator


async def simple_usage_example():
    """Simple usage example."""
    print("=" * 80)
    print("Simple Usage Example")
    print("=" * 80)
    
    # Initialize orchestrator
    config = {
        "google_api_key": os.getenv("GOOGLE_API_KEY"),
        "max_debate_rounds": 3,
        "consensus_threshold": 0.8,
    }
    
    orchestrator = MultiAgentOrchestrator(config)
    
    # Process a query
    result = await orchestrator.process_with_debate(
        "Should I buy a house or keep renting in Seattle?"
    )
    
    print(f"\nFinal Answer:\n{result.final_answer}")
    print(f"\nConfidence: {result.confidence}")
    print(f"Agents Used: {', '.join(result.agents_used)}")


async def detailed_usage_example():
    """Detailed usage example with full work logs."""
    print("\n" + "=" * 80)
    print("Detailed Usage Example with Full Work Logs")
    print("=" * 80)
    
    # Initialize orchestrator
    config = {
        "google_api_key": os.getenv("GOOGLE_API_KEY"),
        "max_debate_rounds": 3,
        "consensus_threshold": 0.8,
    }
    
    orchestrator = MultiAgentOrchestrator(config)
    
    # Process a query with context
    result = await orchestrator.process_with_debate(
        user_query="Plan a week-long trip to Japan on $3000 budget",
        context={"preferences": "food and culture"},
        show_work=True,
    )
    
    print(f"\n{'='*80}")
    print("FINAL ANSWER")
    print(f"{'='*80}")
    print(result.final_answer)
    
    print(f"\n{'='*80}")
    print("AGENTS USED")
    print(f"{'='*80}")
    print(f"Agents: {', '.join(result.agents_used)}")
    print(f"Confidence: {result.confidence:.2f}")
    
    if result.agent_work_logs:
        print(f"\n{'='*80}")
        print("AGENT WORK LOGS")
        print(f"{'='*80}")
        for log in result.agent_work_logs:
            print(f"\n--- {log.agent_name.upper()} Agent ---")
            if log.success:
                print(f"Answer: {log.answer}")
                print(f"Confidence: {log.confidence:.2f}")
            else:
                print(f"Error: {log.error}")
    
    if result.debate_log:
        print(f"\n{'='*80}")
        print("DEBATE OCCURRED")
        print(f"{'='*80}")
        print(f"Rounds: {result.debate_log.rounds_needed}")
        print(f"Consensus Reached: {result.debate_log.consensus_reached}")
        print(f"Executive Decision: {result.debate_log.executive_decision}")
        
        for i, round_responses in enumerate(result.debate_log.rounds, 1):
            print(f"\n--- Round {i} ---")
            for response in round_responses:
                print(f"\n{response.agent_name}: {response.response[:200]}...")


async def decision_making_example():
    """Example of using multi-agent for complex decision making."""
    print("\n" + "=" * 80)
    print("Decision Making Example")
    print("=" * 80)
    
    # Initialize orchestrator
    config = {
        "google_api_key": os.getenv("GOOGLE_API_KEY"),
        "max_debate_rounds": 3,
        "consensus_threshold": 0.8,
    }
    
    orchestrator = MultiAgentOrchestrator(config)
    
    # Complex decision
    result = await orchestrator.process_with_debate(
        user_query="Should my startup build a mobile app or web app first?",
        context={
            "budget": 50000,
            "team_size": 3,
            "target_audience": "young professionals",
            "timeline": "6 months",
        },
        show_work=True,
    )
    
    print(f"\nFinal Recommendation:\n{result.final_answer}")
    print(f"\nConfidence: {result.confidence:.2f}")
    print(f"\nAgents Consulted: {', '.join(result.agents_used)}")
    
    if result.manager_review.conflicts:
        print(f"\nConflicts Identified:")
        for conflict in result.manager_review.conflicts:
            print(f"  - {conflict}")


async def main():
    """Run all examples."""
    # Check if API key is set
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY environment variable not set")
        print("Set it with: export GOOGLE_API_KEY='your-api-key'")
        return
    
    try:
        await simple_usage_example()
        await detailed_usage_example()
        await decision_making_example()
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
