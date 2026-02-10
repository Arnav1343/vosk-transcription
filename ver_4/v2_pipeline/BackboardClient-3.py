"""BackboardClient.py v1.0.0 - Backboard.io API Wrapper
Thin wrapper for Backboard SDK to handle assistant creation, threads, and messaging."""

import json
import sys
import asyncio
from typing import Dict, Optional, List

try:
    from backboard import BackboardClient as BB
except ImportError:
    print("[ERROR] backboard-sdk not installed. Run: pip install backboard-sdk", file=sys.stderr)
    BB = None

from config import BACKBOARD_API_KEY, DEFAULT_MODEL, ASSISTANT_NAME, ASSISTANT_INSTRUCTIONS

VERSION = "1.0.0"


class BackboardWrapper:
    """Wrapper for Backboard.io API interactions with sync interface."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize Backboard client.
        
        Args:
            api_key: Backboard API key (defaults to config value)
            model: LLM model to use (defaults to config value)
        """
        if BB is None:
            raise ImportError("backboard-sdk not installed. Run: pip install backboard-sdk")
        
        self.api_key = api_key or BACKBOARD_API_KEY
        self.model = model or DEFAULT_MODEL
        self.client = BB(api_key=self.api_key)
        self.assistant_id: Optional[str] = None
        self.thread_id: Optional[str] = None
    
    def _run_async(self, coro):
        """Run an async coroutine synchronously."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, coro)
                    return future.result()
            return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)
    
    def create_assistant(self, name: Optional[str] = None, system_prompt: Optional[str] = None) -> str:
        """Create or get an assistant for call analysis.
        
        Args:
            name: Assistant name (defaults to config value)
            system_prompt: System instructions (defaults to config value)
            
        Returns:
            Assistant ID
        """
        try:
            assistant = self._run_async(
                self.client.create_assistant(
                    name=name or ASSISTANT_NAME,
                    system_prompt=system_prompt or ASSISTANT_INSTRUCTIONS
                )
            )
            self.assistant_id = str(assistant.assistant_id)
            print(f"[INFO] Created assistant: {self.assistant_id}", file=sys.stderr)
            return self.assistant_id
        except Exception as e:
            print(f"[ERROR] Failed to create assistant: {e}", file=sys.stderr)
            raise
    
    def create_thread(self, assistant_id: Optional[str] = None) -> str:
        """Create a new conversation thread.
        
        Args:
            assistant_id: Assistant to create thread for (uses current if not specified)
        
        Returns:
            Thread ID
        """
        aid = assistant_id or self.assistant_id
        if not aid:
            aid = self.create_assistant()
        
        try:
            thread = self._run_async(self.client.create_thread(assistant_id=aid))
            self.thread_id = str(thread.thread_id)
            print(f"[INFO] Created thread: {self.thread_id}", file=sys.stderr)
            return self.thread_id
        except Exception as e:
            print(f"[ERROR] Failed to create thread: {e}", file=sys.stderr)
            raise
    
    def send_message(self, content: str, thread_id: Optional[str] = None) -> Dict:
        """Send a message to the assistant and get a response.
        
        Args:
            content: Message content to send
            thread_id: Thread ID (uses current thread if not specified)
            
        Returns:
            Assistant's response as a dictionary
        """
        tid = thread_id or self.thread_id
        if not tid:
            tid = self.create_thread()
        
        try:
            # Add message and get response
            kwargs = {"thread_id": tid, "content": content}
            if self.model:
                kwargs["model_name"] = self.model
            response = self._run_async(
                self.client.add_message(**kwargs)
            )
            
            # Extract response text
            if hasattr(response, 'content') and response.content:
                response_text = response.content
            elif hasattr(response, 'text'):
                response_text = response.text
            elif isinstance(response, dict):
                response_text = response.get('content', response.get('text', str(response)))
            else:
                response_text = str(response)
            
            return {"success": True, "response": response_text}
            
        except Exception as e:
            print(f"[ERROR] Message failed: {e}", file=sys.stderr)
            return {"success": False, "error": str(e)}
    
    def analyze_event(self, event: Dict, transcript_context: str = "") -> Dict:
        """Analyze a single event and return LLM interpretation.
        
        Args:
            event: Event dictionary from EventGen.py
            transcript_context: Relevant transcript text for context
            
        Returns:
            LLM analysis as a dictionary
        """
        prompt = self._build_analysis_prompt(event, transcript_context)
        response = self.send_message(prompt)
        
        if response.get("success"):
            return self._parse_analysis_response(response["response"])
        else:
            return {
                "summary": "Analysis unavailable",
                "risk_level": "unknown",
                "recommended_action": "Manual review required",
                "confidence": 0.0,
                "error": response.get("error")
            }
    
    def _build_analysis_prompt(self, event: Dict, context: str) -> str:
        """Build the analysis prompt for an event."""
        return f"""Analyze this detected event from a customer service call:

EVENT TYPE: {event.get('event_type', 'unknown')}
TIMESTAMP: {event.get('timestamp', {})}
EVIDENCE: {json.dumps(event.get('evidence', []), indent=2)}
EXPLANATION: {event.get('explanation', 'No explanation provided')}
FINANCIAL CONTEXT: {json.dumps(event.get('financial_context', {}), indent=2)}

TRANSCRIPT CONTEXT:
{context if context else 'Not provided'}

Please provide your analysis in this exact JSON format:
{{
    "summary": "One sentence human-readable explanation of what happened",
    "risk_level": "low|medium|high",
    "recommended_action": "Specific action for the compliance/customer service team",
    "confidence": 0.0-1.0
}}

Respond ONLY with the JSON, no additional text."""

    def _parse_analysis_response(self, response: str) -> Dict:
        """Parse the LLM response into a structured analysis."""
        try:
            # Handle if response is not a string
            if not isinstance(response, str):
                response = str(response)
            
            # Try to extract JSON from response
            response = response.strip()
            if response.startswith("```"):
                # Remove markdown code blocks
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])
            
            analysis = json.loads(response)
            
            # Validate required fields
            return {
                "summary": analysis.get("summary", "Analysis provided"),
                "risk_level": analysis.get("risk_level", "medium"),
                "recommended_action": analysis.get("recommended_action", "Review recommended"),
                "confidence": float(analysis.get("confidence", 0.7))
            }
        except (json.JSONDecodeError, ValueError) as e:
            # Fall back to using raw response
            return {
                "summary": response[:200] if response else "Analysis unavailable",
                "risk_level": "medium",
                "recommended_action": "Review recommended",
                "confidence": 0.5
            }


# Alias for backwards compatibility
BackboardClient = BackboardWrapper


def main():
    """Test the Backboard client."""
    print("[INFO] Testing BackboardClient...", file=sys.stderr)
    
    try:
        client = BackboardWrapper()
        print("[INFO] Creating assistant...", file=sys.stderr)
        client.create_assistant()
        print("[INFO] Creating thread...", file=sys.stderr)
        client.create_thread()
        
        # Test message
        print("[INFO] Sending test message...", file=sys.stderr)
        response = client.send_message("Hello! Reply with: Connection successful.")
        print(json.dumps(response, indent=2))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
