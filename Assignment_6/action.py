from models import ActionInput, ActionOutput, MovieRecommendation
from typing import List, Dict, Optional
import requests
import os
from dotenv import load_dotenv

class MovieAPI:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('TMDB_API_KEY')
        self.base_url = "https://api.themoviedb.org/3"
        
    def search_movies(self, query: str) -> List[Dict]:
        endpoint = f"{self.base_url}/search/movie"
        params = {
            'api_key': self.api_key,
            'query': query,
            'language': 'en-US',
            'page': 1
        }
        response = requests.get(endpoint, params=params)
        return response.json().get('results', [])
    
    def get_movie_details(self, movie_id: int) -> Dict:
        endpoint = f"{self.base_url}/movie/{movie_id}"
        params = {
            'api_key': self.api_key,
            'language': 'en-US'
        }
        response = requests.get(endpoint, params=params)
        return response.json()
    
    def get_recommendations(self, movie_id: int) -> List[Dict]:
        endpoint = f"{self.base_url}/movie/{movie_id}/recommendations"
        params = {
            'api_key': self.api_key,
            'language': 'en-US',
            'page': 1
        }
        response = requests.get(endpoint, params=params)
        return response.json().get('results', [])

class Action:
    def __init__(self):
        self.movie_api = MovieAPI()
        self.available_actions = {
            "art_activity": self._provide_art_activities,
            "reading_suggestion": self._provide_reading_suggestions,
            "location_search": self._search_places,
            "recommendation": self._get_recommendations,
            "learning_resource": self._find_learning_resources
        }

    def execute(self, input_data: ActionInput) -> ActionOutput:
        try:
            # Get the recommended movies from the decision output
            recommended_movies = input_data.decision_output.recommended_movies
            
            # For each recommended movie, fetch additional details
            detailed_movies = []
            for movie in recommended_movies:
                # Search for the movie
                search_results = self.movie_api.search_movies(movie.title)
                
                if search_results:
                    # Get full details of the first matching movie
                    movie_id = search_results[0]['id']
                    details = self.movie_api.get_movie_details(movie_id)
                    
                    # Get similar movies
                    similar = self.movie_api.get_recommendations(movie_id)
                    
                    # Create a detailed movie recommendation
                    detailed_movie = MovieRecommendation(
                        title=details.get('title', movie.title),
                        year=int(details.get('release_date', '2000')[:4]),
                        genre=[genre['name'] for genre in details.get('genres', [])],
                        rating=float(details.get('vote_average', 0.0)),
                        description=details.get('overview', ''),
                        reason_recommended=movie.reason_recommended
                    )
                    detailed_movies.append(detailed_movie)
            
            # Generate next steps based on the movies
            next_steps = self._generate_next_steps(detailed_movies)
            
            return ActionOutput(
                movies_presented=detailed_movies,
                success_status=True,
                details=self._format_movie_details(detailed_movies),
                next_steps=next_steps
            )

        except Exception as e:
            return ActionOutput(
                movies_presented=[],
                success_status=False,
                details=f"Error fetching movie details: {str(e)}",
                next_steps=["Try a different movie", "Adjust your preferences", "Contact support if error persists"]
            )

    def _format_movie_details(self, movies: List[MovieRecommendation]) -> str:
        details = "Here are your movie recommendations:\n\n"
        for i, movie in enumerate(movies, 1):
            details += f"{i}. {movie.title} ({movie.year})\n"
            details += f"   Genre: {', '.join(movie.genre)}\n"
            details += f"   Rating: {movie.rating}/10\n"
            details += f"   Why: {movie.reason_recommended}\n"
            details += f"   Description: {movie.description}\n\n"
        return details

    def _generate_next_steps(self, movies: List[MovieRecommendation]) -> List[str]:
        base_steps = [
            "Rate these recommendations",
            "Save movies to watchlist",
            "Share recommendations with friends"
        ]
        
        movie_specific_steps = []
        for movie in movies:
            movie_specific_steps.extend([
                f"Watch trailer for {movie.title}",
                f"Find showtimes for {movie.title}",
                f"Read reviews for {movie.title}"
            ])
        
        return base_steps + movie_specific_steps[:5]  # Limit movie-specific steps to avoid too many

    def _parse_action_type(self, action: str) -> str:
        action_lower = action.lower()
        if any(word in action_lower for word in ["art", "draw", "paint", "gallery", "museum"]):
            return "art_activity"
        elif any(word in action_lower for word in ["read", "book", "novel", "story", "bestseller"]):
            return "reading_suggestion"
        elif any(word in action_lower for word in ["find", "search", "where", "location"]):
            return "location_search"
        elif any(word in action_lower for word in ["recommend", "suggest"]):
            return "recommendation"
        elif any(word in action_lower for word in ["learn", "study", "tutorial", "course"]):
            return "learning_resource"
        return "unknown"

    def _provide_art_activities(self, input_data: ActionInput) -> str:
        action = input_data.decision_output.recommended_action.lower()
        
        if "gallery" in action or "museum" in action:
            return """Here are some art gallery activities:
1. Take a guided tour to learn about current exhibitions
2. Sketch your favorite artworks in your notebook
3. Join an art appreciation workshop if available
4. Take photos of inspiring pieces (where allowed)
5. Check the gift shop for art books and prints"""
        
        elif "sketch" in action or "draw" in action:
            return """Getting started with sketching:
1. Choose your medium (pencil, charcoal, pen)
2. Find a comfortable workspace
3. Start with basic shapes and forms
4. Practice daily sketching exercises
5. Join online sketching communities"""
        
        return "Suggested art activities and resources provided"

    def _provide_reading_suggestions(self, input_data: ActionInput) -> str:
        action = input_data.decision_output.recommended_action.lower()
        
        if "bestseller" in action or "bookstore" in action:
            return """Bookstore exploration tips:
1. Check the bestsellers section
2. Browse staff recommendations
3. Look for local author selections
4. Check for book signing events
5. Ask staff for personalized recommendations"""
        
        elif "book club" in action:
            return """Getting started with book clubs:
1. Look for local book clubs at libraries
2. Join online reading communities
3. Start with current popular books
4. Prepare discussion points
5. Consider starting your own club"""
        
        return "Provided reading suggestions and resources"

    def _search_places(self, input_data: ActionInput) -> str:
        return f"Found several places matching {input_data.decision_output.recommended_action}"

    def _get_recommendations(self, input_data: ActionInput) -> str:
        return "Generated personalized recommendations based on preferences"

    def _find_learning_resources(self, input_data: ActionInput) -> str:
        return "Found relevant learning resources and tutorials" 