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

CLASS_NAME = "class 12"
CHAPTER_NUMBER = "1"
EXERCISE_NUMBER = "1.2"
EXERCISE_CODE = "EXERCISE-1-2"

STATUS = "PUBLISHED"
GRADE_CODE = "GRADE-12"
SUBJECT_CODE = "MATH"
TOPIC_CODE = "RELATIONS-AND-FUNCTIONS"
POSTED_BY_USER_ID = "6810b82fb49f7e3b1f0460ea"
BOARD = "CBSE"
SOURCE = "NCERT Maths"

def call_process_pdf_api(attempt):
    """Call the process_pdf API with the given attempt number."""
    try:
        url = "http://localhost:8000/process_pdf"     
        
        # Form data
        files = {
            'pdf_file': ('lemh101-ex-1.2.pdf', open('../book/ch-1/lemh101-ex-1.2.pdf', 'rb'), 'application/pdf')
        }
        
        data = {
            'prompt': f"""You are a professional mathematics teacher of {CLASS_NAME}.
                    You need to solve questions provied in the exercise {EXERCISE_NUMBER}.

                    Title in en language must be exact same as question in PDF file.
                    Write solution for the each question considering level of {CLASS_NAME}.
                    Write explanation of the solution.
                    Make sure that solution should not look like AI generated.
                    DifficultyLevelCode should EASY, MEDIUM, HARD. Provide best suggestion.
                    Must use latex in title, solution and explanation. Use LaTeX format Inline math expressions using $...$
                    Add next line, double next line, paragraph etc whatever and wherever best applicable for the student in title, solution and explanation. Don't use markup in title, solution and explanation.
                    title, solution, explanation must be created for English (en) language only.
                    englishTitle should be same as title.
                    Don't use latex in englishTitle and solutionWOLatex. englishTitle and solutionWOLatex should be in plain text.
                    Please make sure that response must be in XML format.
                    Do not provide 'Explanation of the Code and Choices' in the response.
                    Do not provide 'Important Considerations' in the response.
                    Provide only one question in the response.
                    Create response in the following XML format.

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
                    'status': STATUS,
                    'gradeCode': GRADE_CODE,
                    'subjectCode': SUBJECT_CODE,
                    'topicCode': TOPIC_CODE,
                    'postedByUserId': POSTED_BY_USER_ID,
                    'board': BOARD,
                    'source': SOURCE,
                    'chapterNo': CHAPTER_NUMBER,
                    'exerciseCode': EXERCISE_CODE
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
