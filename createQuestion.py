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

def store_question_id(question_id):
    """Store the question ID in a text file."""
    try:
        with open('previousQuestionId.txt', 'w') as f:
            f.write(question_id)
        logger.info(f"Stored question ID: {question_id}")
    except Exception as e:
        logger.error(f"Error storing question ID: {e}")
        raise

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
        
        # Read previous question ID from file store_question_id
        previous_question_id = ""
        try:
            with open('previousQuestionId.txt', 'r') as f:
                previous_question_id = f.read().strip()
        except FileNotFoundError:
            logger.warning("No previous question ID found")

        # Create Question API call
        question_headers = {
            'Accept-Language': 'en',
            'Timezone': 'Asia/Kolkata',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        # Add previous question ID to the formatted JSON if it exists
        if previous_question_id:
            formatted_json['previousQuestionId'] = previous_question_id
        
        logger.info("Attempting to create question...")
        logger.info(f"Formatted JSON: {formatted_json}")
        question_response = requests.post(question_url, headers=question_headers, json=formatted_json)
        question_response.raise_for_status()
        response_data = question_response.json()
        logger.info("Successfully created question")
        
        # Store the question ID
        question_id = response_data.get('data', {}).get('id')
        if question_id:
            # Update next question id of the previous question
            update_next_question_id_of_previous_question(previous_question_id, question_id)
            store_question_id(question_id)

        else:
            logger.warning("No question ID found in response")
        
        return response_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Error in createQuestion: {e}")
        raise

def update_next_question_id_of_previous_question(previous_question_id, next_question_id):
    """Update the nextQuestionId of the previous question using PUT API."""
    try:
        if not previous_question_id or not next_question_id:
            logger.warning("Missing question IDs for update")
            return

        # Get environment variables
        question_url = os.getenv('QUESTION_API_URL')
        if not question_url:
            raise Exception("Missing QUESTION_API_URL environment variable")

        # Construct the update URL
        update_url = f"{question_url}/{previous_question_id}"
        
        # Get token from login
        login_url = os.getenv('LOGIN_API_URL')
        email = os.getenv('API_EMAIL')
        password = os.getenv('API_PASSWORD')
        
        if not all([login_url, email, password]):
            raise Exception("Missing required environment variables for login")
        
        # Login to get token
        login_headers = {
            'Content-Type': 'application/json',
            'Accept-Language': 'en',
            'Timezone': 'Asia/Kolkata'
        }
        login_data = {
            "email": email,
            "password": password
        }
        
        login_response = requests.post(login_url, headers=login_headers, json=login_data)
        login_response.raise_for_status()
        token = login_response.json().get('data', {}).get('token')
        
        if not token:
            raise Exception("No token received from login API")
        
        # Update headers
        update_headers = {
            'Accept-Language': 'en',
            'Timezone': 'Asia/Kolkata',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        # Update payload
        update_data = {
            "nextQuestionId": next_question_id
        }
        
        logger.info(f"Updating nextQuestionId for question {previous_question_id} to {next_question_id}")
        update_response = requests.put(update_url, headers=update_headers, json=update_data)
        update_response.raise_for_status()
        
        logger.info(f"Successfully updated nextQuestionId for question {previous_question_id}")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed while updating nextQuestionId: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Error updating nextQuestionId: {e}")
        raise
