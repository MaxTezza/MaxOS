#!/usr/bin/env python3
"""
Demo script showing LLM-powered intent classification in action.

This script demonstrates how MaxOS uses LLM to classify user intents
and extract entities from natural language commands.
"""

import asyncio
from max_os.core.intent_classifier import IntentClassifier
from max_os.utils.config import load_settings


async def demo():
    """Run demo of intent classification."""
    print("=" * 70)
    print("MaxOS LLM-Powered Intent Classification Demo")
    print("=" * 70)
    print()
    
    settings = load_settings()
    classifier = IntentClassifier(settings=settings)
    
    # Determine if LLM is enabled
    if classifier.use_llm:
        print("✅ LLM Classification: ENABLED")
        print(f"   Provider: {settings.orchestrator.get('provider')}")
        print(f"   Model: {settings.orchestrator.get('model')}")
    else:
        print("⚠️  LLM Classification: DISABLED (using rule-based fallback)")
        print("   Set GOOGLE_API_KEY to enable LLM classification")
    print()
    
    # Test cases
    test_cases = [
        ("copy Documents/report.pdf to Backup folder", {}),
        ("search Downloads for .psd files larger than 200MB", {}),
        ("show system health", {}),
        ("check docker service status", {}),
        ("ping google.com", {}),
        ("show git status", {}),
        ("commit my changes", {"git_status": "modified"}),
        ("what is kubernetes", {}),
    ]
    
    print("Testing intent classification:")
    print("-" * 70)
    
    for user_input, context in test_cases:
        intent = await classifier.classify(user_input, context)
        
        print(f"\n📝 Input: '{user_input}'")
        if context:
            print(f"   Context: {context}")
        print(f"   Intent: {intent.name} (confidence: {intent.confidence:.2f})")
        
        if intent.slots:
            print(f"   Entities:")
            for slot in intent.slots:
                # Show only the first 60 chars of value
                value = slot.value[:60] + "..." if len(slot.value) > 60 else slot.value
                print(f"     - {slot.name}: {value}")
    
    print()
    print("=" * 70)
    print("Demo complete!")
    print()


if __name__ == "__main__":
    asyncio.run(demo())
