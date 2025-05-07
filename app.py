# Install necessary libraries:
# pip install fastapi uvicorn google-generativeai PyPDF2 python-multipart python-dotenv

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import google.generativeai as genai
import PyPDF2
import os
import json
import logging
from typing import Optional
from dotenv import load_dotenv
from createQuestion import createQuestion as create_question_api
import requests
from formatQuestionJson import format_question_json
import pytesseract
from pdf2image import convert_from_path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get API key from environment variable
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")

# Configure Gemini API
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

app = FastAPI()

def get_next_sequence_number(board, source, subjectCode, gradeCode, topicCode, chapterNo):
    """Get current sequence number from local file."""
    key = f"{board}_{source}_{subjectCode}_{gradeCode}_{topicCode}_{chapterNo}"
    filename = "sequence_numbers.json"
    
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                sequence_numbers = json.load(f)
            logger.info(f"Loaded sequence numbers from {filename}")
            return sequence_numbers.get(key, 10) + 10
        else:
            logger.info(f"Sequence numbers file not found, returning default value 10")
            return 10
    except Exception as e:
        logger.error(f"Error reading sequence numbers: {e}")
        return 10  # Fallback to 10 if there's any error

def update_sequence_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, sequence_number):
    """Update sequence number in local file."""
    key = f"{board}_{source}_{subjectCode}_{gradeCode}_{topicCode}_{chapterNo}"
    filename = "sequence_numbers.json"
    
    try:
        # Get current sequence numbers
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                sequence_numbers = json.load(f)
        else:
            sequence_numbers = {}

        # Update the dictionary
        sequence_numbers[key] = sequence_number
        
        # Save back to file
        with open(filename, 'w') as f:
            json.dump(sequence_numbers, f)
        logger.info(f"Updated sequence number for key {key} to {sequence_number}")
    except Exception as e:
        logger.error(f"Error updating sequence numbers: {e}")

def get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo):
    """Get next question number from local file."""
    key = f"{board}_{source}_{subjectCode}_{gradeCode}_{topicCode}_{chapterNo}_question"
    filename = "question_numbers.json"
    
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                question_numbers = json.load(f)
            logger.info(f"Loaded question numbers from {filename}")
            return question_numbers.get(key, 1) + 1
        else:
            logger.info(f"Question numbers file not found, returning default value 1")
            return 1
    except Exception as e:
        logger.error(f"Error reading question numbers: {e}")
        return 1  # Fallback to 1 if there's any error

def update_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, question_number):
    """Update question number in local file."""
    key = f"{board}_{source}_{subjectCode}_{gradeCode}_{topicCode}_{chapterNo}_question"
    filename = "question_numbers.json"
    
    try:
        # Get current question numbers
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                question_numbers = json.load(f)
        else:
            question_numbers = {}
        
        # Update the dictionary
        question_numbers[key] = question_number
        
        # Save back to file
        with open(filename, 'w') as f:
            json.dump(question_numbers, f)
        logger.info(f"Updated question number for key {key} to {question_number}")
    except Exception as e:
        logger.error(f"Error updating question numbers: {e}")

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts text content from a PDF file using external API."""
    try:
        # API endpoint
        url = "http://localhost:5000/read-pdf"
        
        # Headers
        headers = {
            'x-api-key': os.getenv('PDF_API_KEY', '')  # Get API key from environment variable
        }
        
        # Prepare the file
        with open(pdf_path, 'rb') as pdf_file:
            files = {
                'file': (os.path.basename(pdf_path), pdf_file, 'application/pdf')
            }
            
            # Make the API call
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()  # Raise exception for bad status codes
            
            # Parse the response
            result = response.json()
            if result.get('success'):
                text = result.get('text', '')
                logger.info(f"Successfully extracted text from PDF: {pdf_path}")
                return text
            else:
                raise Exception("PDF text extraction failed")
                
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error calling PDF extraction API: {e}")
    except Exception as e:
        logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
        raise HTTPException(status_code=400, detail=f"Error reading PDF: {e}")

@app.post("/process_pdf")
async def process_pdf(
    pdf_file: UploadFile = File(...),
    prompt: str = Form(...),
    status: str = Form(...),
    gradeCode: str = Form(...),
    subjectCode: str = Form(...),
    topicCode: str = Form(...),
    postedByUserId: str = Form(...),
    board: str = Form(...),
    source: str = Form(...),
    chapterNo: str = Form(...),
    lastQuestionNumber: int = Form(...)
):
    logger.info(f"Received PDF processing request for file: {pdf_file.filename}")
    logger.info(f"Parameters - Board: {board}, Source: {source}, Subject: {subjectCode}, Grade: {gradeCode}, Topic: {topicCode}, Chapter: {chapterNo}")

    if not pdf_file.filename.endswith(".pdf"):
        logger.error(f"Invalid file format received: {pdf_file.filename}")
        raise HTTPException(status_code=400, detail="Invalid file format. Only PDF files are allowed.")

    try:
        # Save the uploaded PDF temporarily
        file_path = f"temp_{pdf_file.filename}"
        with open(file_path, "wb") as f:
            content = await pdf_file.read()
            f.write(content)
        logger.info(f"Temporarily saved PDF to {file_path}")

        try:
            pdf_text = extract_text_from_pdf(file_path)
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise HTTPException(status_code=500, detail=f"Error extracting text from PDF: {e}")

        next_question_number = get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo)
        # Construct the final prompt for Gemini
        final_prompt = f"""Based on the content of the following PDF:\n\n{pdf_text}
                         Pick up questions from question no {next_question_number}
                         \n\n{prompt}
                        """
        if lastQuestionNumber < next_question_number:
            raise HTTPException(status_code=500, detail="No new questions found")

        logger.info("Generated final prompt for Gemini")

        # Generate content using Gemini 1.0 Pro
        response = model.generate_content(final_prompt)
        response.resolve()  # Ensure the response is fully resolved
        # response object should be printed as string in following logger
        logger.info(f"Received response from Gemini: {response}")

        # Clean up the temporary file
        os.remove(file_path)
        logger.info(f"Removed temporary file: {file_path}")

        # Extract JSON from the response
        response_text = response.text
        logger.info(f"Received response from Gemini: {response_text}")
        if response_text.startswith("```json"):
            # Remove the markdown code block markers
            json_str = response_text.replace("```json", "").replace("```", "").strip()
            
            # Clean the JSON string
            # Remove control characters except newlines and tabs
            json_str = ''.join(char for char in json_str if ord(char) >= 32 or char in '\n\r\t')
            
            # Fix any malformed JSON by replacing problematic characters
            json_str = json_str.replace('\\n', '\\\\n')  # Escape newlines
            json_str = json_str.replace('\\"', '"')      # Fix escaped quotes
            json_str = json_str.replace('\\t', '\\\\t')  # Escape tabs
            
            # Remove any extra whitespace between words
            json_str = ' '.join(json_str.split())
            
            try:
                # Parse the JSON string
                json_data = json.loads(json_str)
                logger.info("Successfully parsed JSON response")
                
                # Handle both single object and array cases
                if isinstance(json_data, dict):
                    logger.info("Processing single question")
                    next_sequence_number = get_next_sequence_number(board, source, subjectCode, gradeCode, topicCode, chapterNo)
                    try:
                        formatted_json = format_question_json(
                            json_data,
                            status=status,
                            gradeCode=gradeCode,
                            subjectCode=subjectCode,
                            topicCode=topicCode,
                            postedByUserId=postedByUserId,
                            board=board,
                            source=source,
                            chapterNo=chapterNo,
                            seqNumber=next_sequence_number                            
                        )
                        # Create question using API
                        try:
                            api_response = create_question_api(formatted_json)
                            update_sequence_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, next_sequence_number)
                            logger.info(f"Question created successfully: {api_response}")
                            update_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, next_question_number)                        
                            # if api_response contains "Example 26" or "Consider a function" then throw an error                           
                        except Exception as e:
                            logger.error(f"Error creating question via API: {e}")
                            raise HTTPException(status_code=500, detail=f"Error creating question: {e}")
                    except Exception as e:
                        logger.error(f"Error formatting question: {e}")
                        raise
                elif isinstance(json_data, list):
                    logger.info(f"Processing {len(json_data)} questions")
                    formatted_questions = []
                    for question in json_data:
                        try:
                            next_sequence_number = get_next_sequence_number(board, source, subjectCode, gradeCode, topicCode, chapterNo)
                            formatted_question = format_question_json(
                                question,
                                status=status,
                                gradeCode=gradeCode,
                                subjectCode=subjectCode,
                                topicCode=topicCode,
                                postedByUserId=postedByUserId,
                                board=board,
                                source=source,
                                chapterNo=chapterNo,
                                seqNumber=next_sequence_number
                            )
                            # Create question using API
                            try:
                                api_response = create_question_api(formatted_question)
                                update_sequence_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, next_sequence_number)
                                update_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, next_question_number)
                                next_question_number = get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo)
                                logger.info(f"Question created successfully: {api_response}")
                                formatted_questions.append(formatted_question)
                                if lastQuestionNumber < next_question_number:
                                    break
                            except Exception as e:
                                logger.error(f"Error creating question via API: {e}")
                                raise HTTPException(status_code=500, detail=f"Error creating question: {e}")
                        except Exception as e:
                            logger.error(f"Error formatting question: {e}")
                            raise
                    return formatted_questions
                else:
                    logger.error("Invalid JSON structure received")
                    raise HTTPException(status_code=500, detail="Invalid JSON structure")
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                raise HTTPException(status_code=500, detail=f"Error parsing JSON response: {e}")
            except Exception as e:
                logger.error(f"Error processing questions: {e}")
                raise HTTPException(status_code=500, detail=f"Error processing questions: {e}")
        else:
            logger.warning("Received non-JSON response from Gemini")
            return {"response": response_text}
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {e}")

def format_question_json(json_data, status, gradeCode, subjectCode, topicCode, postedByUserId, board, source, chapterNo, seqNumber):
    """Format the question JSON with additional metadata."""
    try:
        # Ensure json_data is a dictionary
        if not isinstance(json_data, dict):
            raise ValueError("Input must be a dictionary")

        # Add metadata fields
        json_data.update({
            "status": status,
            "gradeCode": gradeCode,
            "subjectCode": subjectCode,
            "topicCode": topicCode,
            "postedByUserId": postedByUserId,
            "board": board,
            "source": source,
            "chapterNo": chapterNo,
            "seqNumber": seqNumber,
            "seoMetaData": {
                "en": json_data.get("seoMetaData", {}).get("en", ""),
                "hi": json_data.get("seoMetaData", {}).get("hi", "")
            }
        })
        
        return json_data
    except Exception as e:
        logger.error(f"Error formatting question JSON: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)