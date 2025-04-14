import requests
import json
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('create_question.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def createQuestion(formatted_json):
    """
    Creates a question by first logging in and then calling the create question API.
    
    Args:
        formatted_json (dict): The formatted question JSON to be created
        
    Returns:
        dict: Response from the create question API
    """
    try:
        # Get environment variables
        login_url = os.getenv('LOGIN_API_URL')
        question_url = os.getenv('QUESTION_API_URL')
        email = os.getenv('API_EMAIL')
        password = os.getenv('API_PASSWORD')
        
        if not all([login_url, question_url, email, password]):
            raise Exception("Missing required environment variables")
        
        # Login API call
        login_headers = {
            'Content-Type': 'application/json',
            'Accept-Language': 'en',
            'Timezone': 'Asia/Kolkata'
        }
        login_data = {
            "email": email,
            "password": password
        }
        
        logger.info("Attempting to login...")
        login_response = requests.post(login_url, headers=login_headers, json=login_data)
        login_response.raise_for_status()
        login_data = login_response.json()
        logger.info("Successfully logged in")
        
        # Extract token from login response
        token = login_data.get('data', {}).get('token')
        if not token:
            raise Exception("No token received from login API")
        
        # Create Question API call
        question_headers = {
            'Accept-Language': 'hi',
            'Timezone': 'Asia/Kolkata',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        logger.info("Attempting to create question...")
        question_response = requests.post(question_url, headers=question_headers, json=formatted_json)
        question_response.raise_for_status()
        logger.info("Successfully created question")
        
        return question_response.json()
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Error in createQuestion: {e}")
        raise
