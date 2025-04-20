from models import DecisionInput, DecisionOutput, ReasoningStep, MovieRecommendation, PerceptionOutput, UserPreferences
from typing import Union, Dict, Any
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv
from memory import Memory

class DecisionMaker:
    def __init__(self):
        load_dotenv()
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('models/gemini-2.0-flash')  # Updated model name
        self.memory = Memory()
        
        self.system_prompt = """You are a movie recommendation AI. Analyze the user's request, preferences, and past interactions to suggest relevant movies.
IMPORTANT: Your response must be a SINGLE JSON object with NO code block formatting, NO markdown, and NO additional text.
The response must be a valid JSON object with exactly these fields:
{
    "confidence": float,  # between 0 and 1
    "reasoning": string,  # why these recommendations were chosen
    "recommendations": [
        {
            "title": string,
            "year": int,
            "genre": string,
            "rating": float,
            "why": string,
            "description": string
        }
    ]
}
Consider the user's past interactions and their ratings to improve recommendations.
Avoid recommending movies that were poorly rated in similar contexts.
DO NOT include any text before or after the JSON object. DO NOT use ```json or ``` markers."""

    def make_decision(self, input_data: Union[DecisionInput, PerceptionOutput]) -> DecisionOutput:
        try:
            print("\nAnalyzing your movie preferences...")
            
            # Handle both input types
            if isinstance(input_data, DecisionInput):
                perception_output = input_data.perception_output
                user_prefs = input_data.user_preferences
            else:  # PerceptionOutput
                perception_output = input_data
                # Create a fallback user preferences if not available
                user_prefs = UserPreferences(
                    name="Unknown",
                    location="Unknown",
                    favorite_genres=[],
                    favorite_movies=[],
                    preferred_languages=["English"],
                    mood=None
                )
            
            # Get relevant memories
            memory_output = self.memory.get_relevant_memories(perception_output.current_context)
            memory_context = ""
            if memory_output.relevant_memories:
                memory_context = "\nPast interactions:\n"
                for mem in memory_output.relevant_memories:
                    rating = f" (Rating: {mem.success_rating*5:.1f}/5)" if mem.success_rating is not None else ""
                    memory_context += f"Query: {mem.context}{rating}\n"
                    memory_context += f"Action: {mem.action_taken}\n\n"
            
            # Construct the prompt
            prompt = f"{self.system_prompt}\n\nUser preferences:\n"
            prompt += f"Name: {user_prefs.name}\n"
            prompt += f"Location: {user_prefs.location}\n"
            prompt += f"Genres: {', '.join(user_prefs.favorite_genres)}\n"
            prompt += f"Favorite movies: {', '.join(user_prefs.favorite_movies)}\n"
            prompt += f"Languages: {', '.join(user_prefs.preferred_languages)}\n"
            prompt += f"Mood: {user_prefs.mood or 'Unknown'}\n"
            prompt += memory_context
            prompt += f"\nUser request: {perception_output.current_context}\n"
            prompt += "\nRemember: Respond with ONLY the JSON object, no other text."
            
            print("\nSending request to Gemini API...")
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                print("\nReceived response from Gemini API")
                try:
                    # Clean the response text
                    response_text = response.text.strip()
                    
                    # Try to find a JSON object in the response
                    start = response_text.find('{')
                    end = response_text.rfind('}')
                    if start >= 0 and end > start:
                        response_text = response_text[start:end + 1]
                        
                        # Additional safety check: ensure we have valid JSON structure
                        if response_text.count('{') != response_text.count('}'):
                            print("\nInvalid JSON structure (unmatched braces)")
                            raise json.JSONDecodeError("Unmatched braces", response_text, 0)
                        
                        # Try to parse the JSON
                        result = json.loads(response_text)
                        
                        # Validate required fields
                        if not all(key in result for key in ["confidence", "reasoning", "recommendations"]):
                            print("\nMissing required fields in JSON response")
                            raise KeyError("Missing required fields")
                        
                        # Convert recommendations to proper format
                        recommendations = []
                        for rec in result["recommendations"]:
                            recommendations.append(MovieRecommendation(
                                title=rec["title"],
                                year=rec["year"],
                                genre=rec["genre"].split(", ") if isinstance(rec["genre"], str) else rec["genre"],
                                rating=rec["rating"],
                                description=rec["description"],
                                reason_recommended=rec["why"]
                            ))
                        
                        return DecisionOutput(
                            recommended_movies=recommendations,
                            confidence_score=float(result["confidence"]),
                            reasoning=str(result["reasoning"]),
                            reasoning_steps=[
                                ReasoningStep(
                                    step=1,
                                    action="Movie Analysis",
                                    reasoning=result["reasoning"]
                                )
                            ],
                            reasoning_type="recommendation",
                            fallback_used=False,
                            fallback_reason=None
                        )
                    else:
                        print("\nNo valid JSON object found in response")
                        raise json.JSONDecodeError("No JSON object found", response_text, 0)
                        
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"\nError parsing Gemini response: {e}")
                    print(f"Raw response: {response.text}")
                    print(f"Cleaned response text: {response_text}")
            
            # If we get here, either the response was empty or couldn't be parsed
            return self._get_fallback_recommendation(user_prefs)
            
        except Exception as e:
            print(f"\nError occurred: {str(e)}")
            return self._get_fallback_recommendation(user_prefs)

    def _get_fallback_recommendation(self, user_prefs: UserPreferences) -> DecisionOutput:
        print("\nUsing fallback recommendations")
        genres = user_prefs.favorite_genres
        print(f"Checking genres: {genres}")
        
        recommendations = []
        
        if any('comedy' in genre.lower() for genre in genres):
            print("Adding comedy recommendation")
            recommendations.append(MovieRecommendation(
                title="The Grand Budapest Hotel",
                year=2014,
                genre=["Comedy", "Drama"],
                rating=8.042,
                description="The Grand Budapest Hotel tells of a legendary concierge at a famous European hotel between the wars and his friendship with a young employee who becomes his trusted protégé. The story involves the theft and recovery of a priceless Renaissance painting, the battle for an enormous family fortune and the slow and then sudden upheavals that transformed Europe during the first half of the 20th century.",
                reason_recommended="A witty and charming comedy with stunning visuals and great performances"
            ))
        
        if any('action' in genre.lower() for genre in genres):
            print("Adding action recommendation")
            recommendations.append(MovieRecommendation(
                title="Mad Max: Fury Road",
                year=2015,
                genre=["Action", "Adventure"],
                rating=8.1,
                description="In a post-apocalyptic wasteland, a woman rebels against a tyrannical ruler in search for her homeland with the aid of a group of female prisoners, a psychotic worshiper, and a drifter named Max.",
                reason_recommended="High-octane action with stunning visuals and intense sequences"
            ))
            
        if any('drama' in genre.lower() for genre in genres):
            print("Adding drama recommendation")
            recommendations.append(MovieRecommendation(
                title="The Shawshank Redemption",
                year=1994,
                genre=["Drama"],
                rating=9.3,
                description="Two imprisoned men bond over a number of years, finding solace and eventual redemption through acts of common decency.",
                reason_recommended="A timeless classic that resonates with audiences of all preferences"
            ))
            
        if not recommendations:
            print("Adding default recommendation")
            recommendations.append(MovieRecommendation(
                title="Forrest Gump",
                year=1994,
                genre=["Drama", "Romance"],
                rating=8.8,
                description="The presidencies of Kennedy and Johnson, the Vietnam War, the Watergate scandal and other historical events unfold from the perspective of an Alabama man with an IQ of 75, whose only desire is to be reunited with his childhood sweetheart.",
                reason_recommended="A beloved classic that appeals to all audiences"
            ))
        
        return DecisionOutput(
            recommended_movies=recommendations,
            confidence_score=0.70,
            reasoning=f"Providing personalized recommendations based on your favorite genres: {', '.join(genres)}",
            reasoning_steps=[
                ReasoningStep(
                    step=1,
                    action="Fallback Recommendation",
                    reasoning="Using genre-based fallback recommendations due to processing error"
                )
            ],
            reasoning_type="fallback",
            fallback_used=True,
            fallback_reason="Error processing API response"
        ) 