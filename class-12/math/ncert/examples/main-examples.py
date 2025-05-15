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
            'pdf_file': ('ncert-math-ch-1.pdf', open('../math/class-12/ncert/ch-1/ncert-math-ch-1-relations-functions.pdf', 'rb'), 'application/pdf')
        }
        
        data = {
            'prompt': """You are a professional mathematics teacher of class 12.
                    Read example and its solution from attached PDF file.
                    Title and solution in en language must be exacted same as in PDF file.
                    Example has its solution just after the example. Use that solution rather than creating your own solution.
                    Write explanation of the solution.
                    Make sure that solution should not look like AI generated.
                    DifficultyLevelCode should EASY, MEDIUM, HARD. Provide best suggestion.                    
                    Don't use latex in englishTitle and solutionWOLatex. englishTitle and solutionWOLatex should be in plain text.
                    englishTitle should be picked from title.
                    Must use latex in title, solution and explanation. Use LaTeX format Inline math expressions using $...$
                    Do not provide 'Explanation of the Code and Choices' in the response.
                    Do not provide 'Important Considerations' in the response.
                    Don't use markup symbols in title, solution and explanation.
                    Add next line, double next line, paragraph etc whatever and wherever best applicable for the student in title, solution and explanation.
                    title, solution, explanation must be created for English (en) language only.
                    Read and respond only one example at a time.
                    Only examples should be read and responded. For example, Example 1, Example 2, Example 3, etc.
                    Response must be XML only. Create response in the following format.

Sample xml response:
    <question>
        <title> <en><![CDATA[question here]]></en> </title>
        <englishTitle><![CDATA[question here]]></englishTitle>
        <solution> <en><![CDATA[solution here]]></en> </solution>
        <solutionWOLatex> <en><![CDATA[solution here]]></en> </solutionWOLatex>
        <explanation> <en><![CDATA[explanation here]]></en> </explanation>
        <difficultyLevelCode><difficulty level></difficultyLevelCode>
        <questionNo>Example <exampleNo></questionNo>
    </question>
""",
            'status': 'PUBLISHED',
            'gradeCode': 'GRADE_12',
            'subjectCode': 'MATH',
            'topicCode': 'REL_AND_FUNC',
            'postedByUserId': '6810b82fb49f7e3b1f0460ea',
            'board': 'CBSE',
            'source': 'NCERT Maths',
            'chapterNo': '1',
            'lastQuestionNumber': 26
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
        
        if i < 50:  # Don't wait after the last call
            logger.info(f"Waiting before next attempt...")
            time.sleep(10)  # 10 second delay between calls
    
    logger.info("Completed all API calls")

if __name__ == "__main__":
    main()
