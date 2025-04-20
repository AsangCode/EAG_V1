import os
from dotenv import load_dotenv
from models import (
    UserPreferences, 
    PerceptionInput,
    DecisionInput,
    ActionInput
)
from perception import Perception
from decision import DecisionMaker
from action import Action
from memory import Memory

def get_user_preferences() -> UserPreferences:
    """Collect user preferences through interactive prompts."""
    print("\n=== Welcome to Your Movie Recommendation System! ===")
    print("Please share some information to help me recommend movies you'll love.\n")

    name = input("What's your name? ")
    location = input("Where are you located? (city, country) ")
    
    print("\nWhat are your favorite movie genres? (comma-separated)")
    print("Examples: Action, Drama, Comedy, Sci-Fi, Horror, Romance, etc.")
    favorite_genres = [i.strip() for i in input("> ").split(",")]

    print("\nWhat are some of your favorite movies? (comma-separated)")
    favorite_movies = [t.strip() for t in input("> ").split(",")]

    print("\nWhat languages do you prefer watching movies in? (comma-separated)")
    print("Examples: English, Hindi, Korean, Spanish, etc.")
    preferred_languages = [a.strip() for a in input("> ").split(",")]

    print("\nHow would you describe your current mood? (optional)")
    print("Examples: happy, excited, relaxed, thoughtful, etc.")
    mood = input("> ").strip() or None

    return UserPreferences(
        name=name,
        location=location,
        favorite_genres=favorite_genres,
        favorite_movies=favorite_movies,
        preferred_languages=preferred_languages,
        mood=mood
    )

def main():
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Please set GEMINI_API_KEY in your .env file")

    # Initialize components
    perception = Perception(api_key)
    decision = DecisionMaker()
    action = Action()
    memory = Memory()  # Initialize memory system

    # Get user preferences
    user_prefs = get_user_preferences()
    print("\nThank you! I'll use this information to provide personalized movie recommendations.")

    while True:
        # Get current context
        print("\nWhat kind of movie would you like to watch? (or type 'quit' to exit)")
        print("Examples:")
        print("- Suggest some action movies")
        print("- I want to watch something funny")
        print("- Find movies similar to The Matrix")
        print("- What's a good movie for date night?")
        current_context = input("> ")
        
        if current_context.lower() == 'quit':
            break

        # Execute recommendation flow
        try:
            # Get relevant memories
            memory_output = memory.get_relevant_memories(current_context)
            if memory_output.relevant_memories:
                print("\nConsidering your previous interactions...")
                for mem in memory_output.relevant_memories[:2]:  # Show top 2 relevant memories
                    print(f"- Previously recommended when you asked: {mem.context}")

            # Perception
            perception_input = PerceptionInput(
                user_preferences=user_prefs,
                current_context=current_context
            )
            perception_output = perception.analyze(perception_input)
            print("\nAnalyzing your movie preferences...")

            # Decision
            decision_output = decision.make_decision(perception_output)
            print(f"\nConfidence in recommendations: {decision_output.confidence_score:.2f}")
            print(f"Reasoning: {decision_output.reasoning}")

            # Action
            action_input = ActionInput(
                decision_output=decision_output,
                user_preferences=user_prefs
            )
            action_output = action.execute(action_input)

            # Store interaction in memory
            success_rating = None
            if action_output.success_status:
                print("\nHow would you rate these recommendations? (1-5, or press Enter to skip)")
                rating_input = input("> ").strip()
                if rating_input and rating_input.isdigit():
                    success_rating = float(rating_input) / 5.0  # Convert to 0-1 scale

            memory.add_memory(
                context=current_context,
                action_taken=action_output.details,
                success_rating=success_rating
            )

            # Display results
            print("\nMovie Recommendations:")
            print(action_output.details)
            
            if action_output.next_steps:
                print("\nWhat would you like to do next?")
                for step in action_output.next_steps:
                    print(f"- {step}")

        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            # Still store failed interactions in memory
            memory.add_memory(
                context=current_context,
                action_taken="Error occurred: " + str(e),
                success_rating=0.0
            )

if __name__ == "__main__":
    main() 