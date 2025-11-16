"""Prompt optimization filter that adapts responses to user personality."""
from __future__ import annotations

import re
from typing import Any, Dict

from max_os.agents.base import AgentResponse
from max_os.learning.personality import UserPersonalityModel


class PromptOptimizationFilter:
    """Tailors all agent communication to user's learned personality."""

    def __init__(self, personality_model: UserPersonalityModel):
        self.upm = personality_model

    def optimize_response(self, response: AgentResponse, context: Dict[str, Any]) -> AgentResponse:
        """Transform agent response to match user preferences."""

        # Get user's communication preferences
        params = self.upm.get_communication_params()

        # Optimize message text
        optimized_message = self._optimize_message(response.message, params, context)

        # Filter payload based on verbosity
        optimized_payload = self._filter_payload(response.payload, params)

        # Create optimized response
        optimized = AgentResponse(
            agent=response.agent,
            status=response.status,
            message=optimized_message,
            payload=optimized_payload
        )

        return optimized

    def _optimize_message(self, message: str, params: Dict[str, float], context: Dict[str, Any]) -> str:
        """Rewrite message to match user's communication style."""

        # Apply verbosity adjustment
        if params['verbosity'] < 0.3:
            # User prefers terse - extract key facts only
            message = self._make_terse(message)
        elif params['verbosity'] > 0.7:
            # User prefers verbose - add context
            message = self._add_context(message, context)

        # Apply technical level adjustment
        if params['technical_level'] > 0.8:
            # User is expert - add technical details
            message = self._add_technical_details(message, context)
        elif params['technical_level'] < 0.3:
            # User is beginner - simplify
            message = self._simplify_language(message)

        # Apply formality adjustment
        if params['formality'] < 0.3:
            # User prefers casual
            message = self._make_casual(message)
        elif params['formality'] > 0.7:
            # User prefers formal
            message = self._make_formal(message)

        # Remove emojis if user doesn't like them
        if params['emoji_tolerance'] < 0.1:
            message = self._strip_emojis(message)

        return message

    def _make_terse(self, message: str) -> str:
        """Compress message to essentials."""
        # Remove filler words
        fillers = [
            'successfully', 'currently', 'basically', 'actually',
            'I have', 'I\'ve', 'has been', 'have been'
        ]
        for filler in fillers:
            message = message.replace(filler, '')

        # Simplify common phrases
        replacements = {
            'Retrieved information for': 'Info:',
            'Found a total of': 'Found',
            'Successfully completed': 'Done:',
            'Failed to': 'Error:',
            'The following': '',
        }
        for old, new in replacements.items():
            message = message.replace(old, new)

        # Clean up extra spaces
        message = re.sub(r'\s+', ' ', message).strip()

        return message

    def _add_context(self, message: str, context: Dict[str, Any]) -> str:
        """Add contextual information for verbose users."""
        # Add relevant context based on domain
        domain = context.get('domain')

        additions = []
        if domain == 'filesystem' and 'search_path' in context:
            additions.append(f"(searched in {context['search_path']})")
        elif domain == 'git' and 'repo_path' in context:
            additions.append(f"(repo: {context.get('repo_path', '')})")

        if additions:
            message = f"{message} {' '.join(additions)}"

        return message

    def _add_technical_details(self, message: str, context: Dict[str, Any]) -> str:
        """Add technical details for expert users."""
        # Add implementation hints or technical context
        domain = context.get('domain')

        if domain == 'system':
            # Add command hints
            if 'using psutil' not in message.lower():
                message += " [via psutil]"
        elif domain == 'network':
            # Add protocol info
            if 'ping' in message.lower():
                message += " [ICMP echo request]"

        return message

    def _simplify_language(self, message: str) -> str:
        """Simplify technical language for beginners."""
        # Replace technical terms with simpler ones
        replacements = {
            'repository': 'project folder',
            'uncommitted': 'unsaved',
            'partition': 'disk',
            'interface': 'connection',
            'daemon': 'background service',
        }

        for technical, simple in replacements.items():
            message = re.sub(rf'\b{technical}\b', simple, message, flags=re.IGNORECASE)

        return message

    def _make_casual(self, message: str) -> str:
        """Make message more casual."""
        # Add casual contractions
        replacements = {
            'cannot': "can't",
            'is not': "isn't",
            'are not': "aren't",
            'does not': "doesn't",
            'do not': "don't",
            'will not': "won't",
            'have not': "haven't",
        }

        for formal, casual in replacements.items():
            message = message.replace(formal, casual)

        return message

    def _make_formal(self, message: str) -> str:
        """Make message more formal."""
        # Expand contractions
        replacements = {
            "can't": 'cannot',
            "isn't": 'is not',
            "aren't": 'are not',
            "doesn't": 'does not',
            "don't": 'do not',
            "won't": 'will not',
            "haven't": 'have not',
        }

        for casual, formal in replacements.items():
            message = message.replace(casual, formal)

        return message

    def _strip_emojis(self, message: str) -> str:
        """Remove all emojis from message."""
        # Remove emoji characters
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        return emoji_pattern.sub('', message)

    def _filter_payload(self, payload: Dict[str, Any] | None, params: Dict[str, float]) -> Dict[str, Any] | None:
        """Filter payload based on verbosity preferences."""
        if not payload:
            return payload

        # Make a copy to avoid mutating original
        filtered = dict(payload)

        # If user prefers terse output, remove verbose fields
        if params['verbosity'] < 0.3:
            # Remove descriptive fields, keep only essential data
            verbose_keys = ['summary', 'next_steps', 'reason', 'description']
            for key in verbose_keys:
                filtered.pop(key, None)

        # If user prefers verbose, keep everything
        # (default behavior, no filtering needed)

        return filtered

    def add_predictive_suggestions(
        self,
        response: AgentResponse,
        predictions: list[Dict[str, Any]]
    ) -> AgentResponse:
        """Add predictive suggestions to response."""
        if not predictions:
            return response

        # Get user's verbosity preference
        params = self.upm.get_communication_params()

        # Format suggestions based on verbosity
        if params['verbosity'] < 0.3:
            # Terse: just list actions
            suggestions = [p['task'] for p in predictions[:3]]
            suggestion_text = f"Next: {', '.join(suggestions)}"
        else:
            # Verbose: include reasons
            suggestions = []
            for p in predictions[:3]:
                suggestions.append(f"{p['task']} ({p['reason']})")
            suggestion_text = "You might want to: " + "; ".join(suggestions)

        # Add to message
        enhanced_message = f"{response.message}\n\n{suggestion_text}"

        return AgentResponse(
            agent=response.agent,
            status=response.status,
            message=enhanced_message,
            payload=response.payload
        )

    def estimate_technical_complexity(self, text: str, domain: str) -> float:
        """Estimate technical complexity of a response (0.0 - 1.0)."""
        complexity = 0.5  # baseline

        # Technical keywords increase complexity
        technical_keywords = [
            'algorithm', 'protocol', 'daemon', 'kernel', 'mutex',
            'async', 'thread', 'process', 'socket', 'buffer',
            'hash', 'encryption', 'compilation', 'parsing'
        ]

        keyword_count = sum(1 for kw in technical_keywords if kw in text.lower())
        complexity += min(0.3, keyword_count * 0.05)

        # Domain-specific terms
        if domain == 'programming':
            code_indicators = ['def ', 'class ', 'import ', 'function', 'variable']
            if any(ind in text for ind in code_indicators):
                complexity += 0.1

        # Command-line syntax
        if re.search(r'`[^`]+`', text) or re.search(r'\$\s+\w+', text):
            complexity += 0.1

        return min(1.0, complexity)
