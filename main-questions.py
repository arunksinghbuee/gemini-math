import requests
import logging
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_calls.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def call_process_pdf_api(attempt):
    """Call the process_pdf API with the given attempt number."""
    try:
        url = "http://localhost:8000/process_pdf"     
        
        # Form data
        files = {
            'pdf_file': ('ex-1.1.pdf', open('math/class-12/ncert/ch-1/ex-1.1.pdf', 'rb'), 'application/pdf')
        }
        
        data = {
            'prompt': """You are a mathematics teacher of class 12.
                    You need to solve questions provied in the exercise 1.1.

                    Title in en language must be exact same as question in PDF file.
                    Write solution for the each question considering level of class 12.
                    Write explanation of the solution.
                    Make sure that solution should not look like AI generated.
                    DifficultyLevelCode should EASY, MEDIUM, HARD. Provide best suggestion.
                    Generate and populate the best seoMetadata for respective example.
                    Add next line, double next line, paragraph etc whatever and wherever best applicable for the student in title, solution and explanation. Don't use markdown in title, solution and explanation.
                    title, solution, explanation, seoMetaData must be created for English (en) and Hindi (hi).
                    Please make sure that response must be in JSON format.
                    Do not provide 'Explanation of the Code and Choices' in the response.
                    Do not provide 'Important Considerations' in the response.
                    
                    Create response in the following json format.

Sample json response:
{
"title": {
"en": <question here> },
"hi": <respective hindi translation>,
"solution": {
"en": <solution here>,
"hi": <respective hindi translation>,
},
"explanation": {
"en": <explanation here>,
"hi": <respective hindi translation>,
},
"difficultyLevelCode": <difficulty level>,
"seoMetaData": {
"en": <best possible seo MetaData as per title, solution and explanation in en language>,
"hi": <best possible seo MetaData as per title, solution and explanation in hi language>,
},
"questionNo": Que <quesitonNo>
}""",
            'status': 'PUBLISHED',
            'gradeCode': 'GRADE_12',
            'subjectCode': 'MATH',
            'topicCode': 'REL_AND_FUNC',
            'postedByUserId': '67fabb8bf481c327cbb04d46',
            'board': 'CBSE',
            'source': 'NCERT Maths',
            'chapterNo': '1',
            'lastQuestionNumber': 16
        }
        
        logger.info(f"Attempt {attempt}: Calling process_pdf API")
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()
        
        logger.info(f"Attempt {attempt}: API call successful")
        return response.json()
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Attempt {attempt}: API request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Attempt {attempt}: Response status: {e.response.status_code}")
            logger.error(f"Attempt {attempt}: Response body: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Attempt {attempt}: Unexpected error: {e}")
        return None
    finally:
        # Close the file if it was opened
        if 'files' in locals():
            files['pdf_file'][1].close()

def main():
    """Main function to call the API 10 times."""
    logger.info("Starting API calls")
    
    for i in range(1, 50):
        logger.info(f"Starting attempt {i} of 50")
        result = call_process_pdf_api(i)    
        
        if result:
            logger.info(f"Attempt {i}: Successfully processed response")
        else:
            logger.error(f"Attempt {i}: Failed to process response")
        
        # if result contains "Example 26" or "Consider a function" then break the loop
        #if "Example 26" in result or "Consider a function" in result:
        #    logger.info(f"Breaking loop, reached to last question.")
        #    break

        # Add a small delay between calls to avoid overwhelming the server
        if i < 50:  # Don't wait after the last call
            logger.info(f"Waiting before next attempt...")
            time.sleep(10)  # 10 second delay between calls
    
    logger.info("Completed all API calls")

if __name__ == "__main__":
    main()
