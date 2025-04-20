from typing import Dict, List
import google.generativeai as genai
from models import PerceptionInput, PerceptionOutput, ReasoningStep
import json

class Perception:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('models/gemini-2.0-flash')
        self.system_prompt = """You are an AI perception system that analyzes movie preferences and queries.
        Follow these steps carefully for each analysis:

        1. QUERY ANALYSIS:
           - Identify the type of movie request (genre-based, mood-based, similar to another movie, etc.)
           - Extract key preferences and constraints
           - Consider temporal context (new releases, classics, etc.)
           - Note any specific requirements (language, rating, etc.)

        2. PREFERENCE MATCHING:
           - Compare query against user's favorite genres
           - Consider alignment with favorite movies
           - Check language preferences
           - Factor in current mood
           - Score relevance of each factor

        3. CONTEXT UNDERSTANDING:
           - Determine if request is for immediate watching
           - Consider social context (alone, date, family, etc.)
           - Assess if specific recommendations or general exploration
           - Evaluate mood influence on selection

        4. OUTPUT FORMAT:
        You must respond in the following JSON format:
        {
            "analyzed_context": {
                "genre_relevance": float,
                "mood_alignment": float,
                "language_match": float,
                "temporal_relevance": float
            },
            "relevant_preferences": ["pref1", "pref2", ...],
            "reasoning_steps": [
                {"step": integer, "action": "string", "reasoning": "string"}
            ],
            "confidence_level": "HIGH|MEDIUM|LOW",
            "reasoning_type": "genre_based|mood_based|similar_movies|hybrid",
            "fallback_used": boolean,
            "fallback_reason": string (optional),
            "current_context": string
        }"""
    
    def analyze(self, input_data: PerceptionInput) -> PerceptionOutput:
        # Construct the prompt using user preferences
        prompt = f"""
        User Profile:
        - Name: {input_data.user_preferences.name}
        - Location: {input_data.user_preferences.location}
        - Favorite Genres: {', '.join(input_data.user_preferences.favorite_genres)}
        - Favorite Movies: {', '.join(input_data.user_preferences.favorite_movies)}
        - Preferred Languages: {', '.join(input_data.user_preferences.preferred_languages)}
        - Current Mood: {input_data.user_preferences.mood}

        Current Request: {input_data.current_context}

        Analyze the user's movie preferences and request to provide relevant insights.
        Remember to follow the steps outlined and provide output in the specified JSON format.
        """

        try:
            # Get Gemini response
            response = self.model.generate_content([
                self.system_prompt,
                prompt
            ])
            
            # Parse the JSON response
            result = json.loads(response.text)
            
            # Convert reasoning steps to proper format
            reasoning_steps = [
                ReasoningStep(
                    step=step["step"],
                    action=step["action"],
                    reasoning=step["reasoning"]
                )
                for step in result["reasoning_steps"]
            ]
            
            return PerceptionOutput(
                analyzed_context=result["analyzed_context"],
                relevant_preferences=result["relevant_preferences"],
                reasoning_steps=reasoning_steps,
                confidence_level=result["confidence_level"],
                reasoning_type=result["reasoning_type"],
                fallback_used=result["fallback_used"],
                fallback_reason=result.get("fallback_reason"),
                current_context=input_data.current_context
            )
        except (json.JSONDecodeError, KeyError, Exception) as e:
            # Fallback if response parsing fails
            return PerceptionOutput(
                analyzed_context={
                    "genre_relevance": 0.8,
                    "mood_alignment": 0.7,
                    "language_match": 0.9,
                    "temporal_relevance": 0.6
                },
                relevant_preferences=[
                    genre for genre in input_data.user_preferences.favorite_genres[:2]
                ],
                reasoning_steps=[
                    ReasoningStep(
                        step=1,
                        action="Fallback Analysis",
                        reasoning="Using basic preference matching due to processing error"
                    )
                ],
                confidence_level="LOW",
                reasoning_type="fallback_analysis",
                fallback_used=True,
                fallback_reason=f"Error processing response: {str(e)}",
                current_context=input_data.current_context
            ) 