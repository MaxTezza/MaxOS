"""Multi-agent orchestration system with debate mechanism."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog

from max_os.agents.specialized import (
    BudgetAgent,
    CreativeAgent,
    PlanningAgent,
    ResearchAgent,
    TechnicalAgent,
)
from max_os.core.gemini_client import GeminiClient
from max_os.models.multi_agent import (
    AgentDebateResponse,
    AgentResult,
    ConsensusCheck,
    DebateLog,
    DebateResult,
    ManagerReview,
)


class MultiAgentOrchestrator:
    """Orchestrates multiple specialized agents working in parallel.

    Manager LLM synthesizes results and moderates debates.
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize multi-agent orchestrator.

        Args:
            config: Configuration dictionary with:
                - google_api_key: Google API key
                - max_debate_rounds: Maximum debate rounds (default: 3)
                - consensus_threshold: Consensus threshold (default: 0.8)
        """
        self.logger = structlog.get_logger("max_os.multi_agent")

        # Manager uses Pro for complex synthesis
        self.manager = GeminiClient(
            model="gemini-1.5-pro",
            api_key=config.get("google_api_key"),
            temperature=0.2,
            max_tokens=4096,
        )

        # Workers use Flash (cheaper, faster)
        self.worker_llm = GeminiClient(
            model="gemini-1.5-flash",
            api_key=config.get("google_api_key"),
            temperature=0.2,
            max_tokens=2048,
        )

        # Initialize specialized agents
        self.agents = self._initialize_agents()

        # Debate configuration
        self.max_debate_rounds = config.get("max_debate_rounds", 3)
        self.consensus_threshold = config.get("consensus_threshold", 0.8)

    def _initialize_agents(self) -> dict[str, Any]:
        """Create specialized agent instances.

        Returns:
            Dictionary of agent instances
        """
        # Creative uses Pro for better creative output
        creative_llm = GeminiClient(
            model="gemini-1.5-pro",
            api_key=(
                self.manager._model._client._api_key
                if hasattr(self.manager._model, "_client")
                else None
            ),
            temperature=0.8,
            max_tokens=2048,
        )

        return {
            "research": ResearchAgent(self.worker_llm),
            "creative": CreativeAgent(creative_llm),
            "technical": TechnicalAgent(self.worker_llm),
            "budget": BudgetAgent(self.worker_llm),
            "planning": PlanningAgent(self.worker_llm),
        }

    async def process_with_debate(
        self,
        user_query: str,
        context: dict[str, Any] | None = None,
        show_work: bool = True,
    ) -> DebateResult:
        """Main entry point for multi-agent processing.

        Args:
            user_query: The user's question/request
            context: Additional context (user history, preferences, etc)
            show_work: Whether to return full agent work logs

        Returns:
            DebateResult with final answer and optional work logs
        """
        context = context or {}

        self.logger.info("Starting multi-agent processing", query=user_query)

        # Step 1: Manager analyzes query and selects agents
        agent_selection = await self._select_agents(user_query, context)
        self.logger.info("Agents selected", agents=agent_selection)

        # Step 2: Spawn selected agents in parallel
        agent_results = await self._run_agents_parallel(agent_selection, user_query, context)
        self.logger.info("Agent processing complete", count=len(agent_results))

        # Step 3: Manager reviews all results
        review = await self._manager_review(user_query, agent_results)
        self.logger.info("Manager review complete", needs_debate=review.needs_debate)

        # Step 4: Run debate if contradictions detected
        if review.needs_debate:
            debate_result = await self._run_debate(user_query, agent_results, review.conflicts)
            final_answer = debate_result.consensus
            debate_log = debate_result
        else:
            final_answer = review.synthesis or "No consensus reached"
            debate_log = None

        # Step 5: Package results
        return DebateResult(
            final_answer=final_answer,
            agent_work_logs=agent_results if show_work else None,
            manager_review=review,
            debate_log=debate_log,
            agents_used=agent_selection,
            confidence=review.confidence,
        )

    async def _select_agents(self, query: str, context: dict[str, Any]) -> list[str]:
        """Manager decides which agents are needed.

        Args:
            query: User query
            context: Additional context

        Returns:
            List of selected agent names
        """
        prompt = f"""Query: {query}

Available specialized agents:
- research: Find factual information, data, and sources
- creative: Generate ideas, creative solutions, brainstorming
- technical: Analyze technical feasibility and implementation
- budget: Calculate costs, financial analysis
- planning: Create plans, schedules, and roadmaps

Context: {context}

Which agents should work on this query? Select 2-4 agents that would be most helpful.
Return ONLY a JSON array with no additional text: ["agent1", "agent2", ...]
"""

        try:
            response = await self.manager.process(prompt)
            # Extract JSON from response
            response = response.strip()
            # Try to find JSON array in response
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                response = response[start:end]
            agents = json.loads(response)

            # Validate agent names
            valid_agents = [a for a in agents if a in self.agents]

            return valid_agents or ["research"]  # Fallback

        except Exception as e:
            self.logger.warning("Agent selection failed, using fallback", error=str(e))
            # Fallback: use research agent
            return ["research"]

    async def _run_agents_parallel(
        self, agent_names: list[str], query: str, context: dict[str, Any]
    ) -> list[AgentResult]:
        """Execute multiple agents in parallel.

        Args:
            agent_names: List of agent names to run
            query: User query
            context: Additional context

        Returns:
            List of agent results
        """
        tasks = [self.agents[name].process(query, context) for name in agent_names]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any agent failures gracefully
        agent_results = []
        for name, result in zip(agent_names, results, strict=False):
            if isinstance(result, Exception):
                agent_results.append(
                    AgentResult(
                        agent_name=name,
                        success=False,
                        error=str(result),
                        answer=None,
                        confidence=0.0,
                    )
                )
            else:
                agent_results.append(result)

        return agent_results

    async def _manager_review(self, query: str, agent_results: list[AgentResult]) -> ManagerReview:
        """Manager analyzes all agent results.

        Args:
            query: User query
            agent_results: Results from all agents

        Returns:
            ManagerReview with synthesis and debate decision
        """
        results_summary = "\n\n".join(
            [
                f"**{r.agent_name}:**\n{r.answer}\nConfidence: {r.confidence}"
                for r in agent_results
                if r.success
            ]
        )

        prompt = f"""Original Query: {query}

Agent Results:
{results_summary}

Analyze these results:
1. Are there contradictions or conflicts between agents?
2. Which answers are most reliable?
3. Can you synthesize a coherent final answer?

Return ONLY valid JSON with no additional text:
{{
  "needs_debate": true or false,
  "conflicts": ["description of conflict 1", ...],
  "synthesis": "synthesized answer if no debate needed, or null",
  "confidence": 0.0-1.0
}}
"""

        try:
            response = await self.manager.process(prompt)
            # Extract JSON from response
            response = response.strip()
            # Try to find JSON object in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                response = response[start:end]
            review_data = json.loads(response)

            return ManagerReview(
                needs_debate=review_data.get("needs_debate", False),
                conflicts=review_data.get("conflicts", []),
                synthesis=review_data.get("synthesis"),
                confidence=review_data.get("confidence", 0.5),
            )

        except Exception as e:
            self.logger.warning("Manager review failed, using fallback", error=str(e))
            # Fallback: no debate, use first successful agent
            first_success = next((r for r in agent_results if r.success), None)
            return ManagerReview(
                needs_debate=False,
                conflicts=[],
                synthesis=first_success.answer if first_success else "Unable to process query",
                confidence=first_success.confidence if first_success else 0.0,
            )

    async def _run_debate(
        self, query: str, agent_results: list[AgentResult], conflicts: list[str]
    ) -> DebateLog:
        """Agents debate their different conclusions.

        Args:
            query: User query
            agent_results: Results from all agents
            conflicts: List of identified conflicts

        Returns:
            DebateLog with debate transcript and consensus
        """
        debate_rounds = []

        for round_num in range(self.max_debate_rounds):
            self.logger.info("Starting debate round", round=round_num + 1)

            # Each agent defends their position
            round_responses = []

            for result in agent_results:
                if not result.success:
                    continue

                agent = self.agents[result.agent_name]

                defense_prompt = f"""Query: {query}

Your original answer: {result.answer}

Other agents said:
{self._format_other_answers(agent_results, result.agent_name)}

Conflicts identified:
{conflicts}

Round {round_num + 1} of debate:
- Defend your position with evidence
- Or acknowledge if another agent has better reasoning
- Focus on resolving: {conflicts[0] if conflicts else 'disagreements'}
"""

                try:
                    defense = await agent.llm.process(defense_prompt)
                    round_responses.append(
                        AgentDebateResponse(
                            agent_name=result.agent_name, round=round_num + 1, response=defense
                        )
                    )
                except Exception as e:
                    self.logger.warning(
                        "Agent debate response failed", agent=result.agent_name, error=str(e)
                    )

            debate_rounds.append(round_responses)

            # Manager checks for consensus after each round
            consensus_check = await self._check_consensus(query, debate_rounds)

            if consensus_check.reached:
                return DebateLog(
                    rounds=debate_rounds,
                    consensus_reached=True,
                    consensus=consensus_check.final_answer or "Consensus reached",
                    rounds_needed=round_num + 1,
                )

        # Max rounds reached - manager makes executive decision
        executive_decision = await self._manager_executive_decision(query, debate_rounds)

        return DebateLog(
            rounds=debate_rounds,
            consensus_reached=False,
            consensus=executive_decision,
            rounds_needed=self.max_debate_rounds,
            executive_decision=True,
        )

    def _format_other_answers(self, agent_results: list[AgentResult], exclude_agent: str) -> str:
        """Format other agents' answers for debate.

        Args:
            agent_results: All agent results
            exclude_agent: Agent to exclude

        Returns:
            Formatted string of other answers
        """
        other_answers = [
            f"- {r.agent_name}: {r.answer}"
            for r in agent_results
            if r.success and r.agent_name != exclude_agent
        ]
        return "\n".join(other_answers)

    async def _check_consensus(
        self, query: str, debate_rounds: list[list[AgentDebateResponse]]
    ) -> ConsensusCheck:
        """Manager checks if agents have reached consensus.

        Args:
            query: User query
            debate_rounds: All debate rounds so far

        Returns:
            ConsensusCheck with decision
        """
        latest_round = debate_rounds[-1]

        prompt = f"""Query: {query}

Latest debate round:
{self._format_debate_round(latest_round)}

Has consensus been reached?
- Are agents now agreeing on a solution?
- Is there a clear best answer?

Return ONLY valid JSON with no additional text:
{{
  "reached": true or false,
  "final_answer": "answer if consensus reached, otherwise null",
  "reasoning": "why consensus was or wasn't reached"
}}
"""

        try:
            response = await self.manager.process(prompt)
            # Extract JSON from response
            response = response.strip()
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                response = response[start:end]
            data = json.loads(response)

            return ConsensusCheck(
                reached=data.get("reached", False),
                final_answer=data.get("final_answer"),
                reasoning=data.get("reasoning", "No reasoning provided"),
            )

        except Exception as e:
            self.logger.warning("Consensus check failed", error=str(e))
            return ConsensusCheck(reached=False, final_answer=None, reasoning="Check failed")

    def _format_debate_round(self, round_responses: list[AgentDebateResponse]) -> str:
        """Format debate round for display.

        Args:
            round_responses: Responses in this round

        Returns:
            Formatted string
        """
        return "\n\n".join([f"**{r.agent_name}:** {r.response}" for r in round_responses])

    def _format_all_debate_rounds(self, debate_rounds: list[list[AgentDebateResponse]]) -> str:
        """Format all debate rounds.

        Args:
            debate_rounds: All debate rounds

        Returns:
            Formatted string
        """
        formatted = []
        for i, round_responses in enumerate(debate_rounds, 1):
            formatted.append(f"=== Round {i} ===")
            formatted.append(self._format_debate_round(round_responses))
        return "\n\n".join(formatted)

    async def _manager_executive_decision(
        self, query: str, debate_rounds: list[list[AgentDebateResponse]]
    ) -> str:
        """Manager makes final call when debate doesn't reach consensus.

        Args:
            query: User query
            debate_rounds: All debate rounds

        Returns:
            Final executive decision
        """
        prompt = f"""Query: {query}

Debate transcript (all rounds):
{self._format_all_debate_rounds(debate_rounds)}

The debate did not reach consensus after {len(debate_rounds)} rounds.
As the manager, make the final executive decision:
- Weigh all arguments
- Choose the most reliable answer
- Explain your reasoning

Return the final answer with your reasoning.
"""

        try:
            return await self.manager.process(prompt)
        except Exception as e:
            self.logger.error("Executive decision failed", error=str(e))
            return "Unable to reach a decision due to technical issues."
