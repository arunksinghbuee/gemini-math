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

import createQuestion
from formatQuestionJson import format_question_json

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

def get_next_sequence_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, should_rollback=False):
    """Get and increment sequence number by 10 from local file."""
    key = f"{board}_{source}_{subjectCode}_{gradeCode}_{topicCode}_{chapterNo}"
    filename = "sequence_numbers.json"
    
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                sequence_numbers = json.load(f)
            logger.info(f"Loaded sequence numbers from {filename}")
        else:
            sequence_numbers = {key: 10}  # Initialize with 10 for new key
            with open(filename, 'w') as f:
                json.dump(sequence_numbers, f)
            logger.info(f"Created new sequence numbers file with initial value 10 for key {key}")
            return 10
        
        if should_rollback:
            current_number = sequence_numbers.get(key, 10) - 10  # Rollback by 10
            logger.info(f"Rolling back sequence number for key {key} to {current_number}")
        else:
            current_number = sequence_numbers.get(key, 10) + 10  # Increment by 10
        
        sequence_numbers[key] = current_number
        
        with open(filename, 'w') as f:
            json.dump(sequence_numbers, f)
        logger.info(f"Updated sequence number for key {key} to {current_number}")
            
        return current_number
    except Exception as e:
        logger.error(f"Error managing sequence numbers: {e}")
        return 10  # Fallback to 10 if there's any error

def get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, should_rollback=False):
    """Get and increment question number by 1 from local file."""
    key = f"{board}_{source}_{subjectCode}_{gradeCode}_{topicCode}_{chapterNo}_question"
    filename = "question_numbers.json"
    
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                question_numbers = json.load(f)
            logger.info(f"Loaded question numbers from {filename}")
        else:
            question_numbers = {key: 1}  # Initialize with 1 for new key
            with open(filename, 'w') as f:
                json.dump(question_numbers, f)
            logger.info(f"Created new question numbers file with initial value 1 for key {key}")
            return 1
        
        if should_rollback:
            current_number = question_numbers.get(key, 1) - 1  # Rollback by 1
            logger.info(f"Rolling back question number for key {key} to {current_number}")
        else:
            current_number = question_numbers.get(key, 1) + 1  # Increment by 1
        
        question_numbers[key] = current_number
        
        with open(filename, 'w') as f:
            json.dump(question_numbers, f)
        logger.info(f"Updated question number for key {key} to {current_number}")
            
        return current_number
    except Exception as e:
        logger.error(f"Error managing question numbers: {e}")
        return 1  # Fallback to 1 if there's any error

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts text content from a PDF file."""
    text = ""
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
        logger.info(f"Successfully extracted text from PDF: {pdf_path}")
        return text
    except Exception as e:
        logger.error(f"Error reading PDF {pdf_path}: {e}")
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

        pdf_text = extract_text_from_pdf(file_path)

        next_question_number = get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo)
        # Construct the final prompt for Gemini
        final_prompt = f"""Based on the content of the following PDF:\n\n{pdf_text}
                         Pick up examples from examples no {next_question_number}
                         \n\n{prompt}"""
        if lastQuestionNumber < next_question_number:
            raise HTTPException(status_code=500, detail="No new questions found")

        logger.info("Generated final prompt for Gemini")
        get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, should_rollback=True)

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
                            seqNumber=get_next_sequence_number(board, source, subjectCode, gradeCode, topicCode, chapterNo)                            
                        )
                        # Create question using API
                        try:
                            api_response = create_question_api(formatted_json)
                            logger.info(f"Question created successfully: {api_response}")
                            next_question_number = get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo)                            
                            # if api_response contains "Example 26" or "Consider a function" then throw an error                           
                        except Exception as e:
                            logger.error(f"Error creating question via API: {e}")
                            # Rollback sequence number
                            get_next_sequence_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, should_rollback=True)
                            get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, should_rollback=True)
                            raise HTTPException(status_code=500, detail=f"Error creating question: {e}")
                    except Exception as e:
                        logger.error(f"Error formatting question: {e}")
                        # Rollback sequence number
                        get_next_sequence_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, should_rollback=True)
                        get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, should_rollback=True)
                        raise
                elif isinstance(json_data, list):
                    logger.info(f"Processing {len(json_data)} questions")
                    formatted_questions = []
                    for question in json_data:
                        try:
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
                                seqNumber=get_next_sequence_number(board, source, subjectCode, gradeCode, topicCode, chapterNo)
                            )
                            # Create question using API
                            try:
                                api_response = create_question_api(formatted_question)
                                logger.info(f"Question created successfully: {api_response}")
                                next_question_number = get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo)                                
                                formatted_questions.append(formatted_question)
                                if lastQuestionNumber < next_question_number:
                                    break
                            except Exception as e:
                                logger.error(f"Error creating question via API: {e}")
                                # Rollback sequence number
                                get_next_sequence_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, should_rollback=True)
                                get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, should_rollback=True)
                                raise HTTPException(status_code=500, detail=f"Error creating question: {e}")
                        except Exception as e:
                            logger.error(f"Error formatting question: {e}")
                            # Rollback sequence number
                            get_next_sequence_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, should_rollback=True)
                            get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, should_rollback=True)
                            raise
                    return formatted_questions
                else:
                    logger.error("Invalid JSON structure received")
                    get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, should_rollback=True)
                    raise HTTPException(status_code=500, detail="Invalid JSON structure")
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, should_rollback=True)
                raise HTTPException(status_code=500, detail=f"Error parsing JSON response: {e}")
            except Exception as e:
                logger.error(f"Error processing questions: {e}")
                get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, should_rollback=True)
                raise HTTPException(status_code=500, detail=f"Error processing questions: {e}")
        else:
            logger.warning("Received non-JSON response from Gemini")
            get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, should_rollback=True)
            return {"response": response_text}
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, should_rollback=True)
        raise HTTPException(status_code=500, detail=f"Error processing request: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)