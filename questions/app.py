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
import xml.etree.ElementTree as ET

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
            # read example-numbers.txt file. It contains all example numbers in new line. Get next example number after question_numbers.get(key, 1)
            current_number = question_numbers.get(key, 1)
            
            try:
                with open("example-numbers.txt", "r") as f:
                    example_numbers = [line.strip() for line in f if line.strip()]
                
                if current_number == 0:
                    return example_numbers[0]
                
                # Find the next number after current_number
                i=0
                for num in example_numbers:
                    if num == str(current_number):
                        return example_numbers[i+1]
                    i+=1                    
                return str(current_number + 1)
            except Exception as e:
                logger.error(f"Error reading example numbers: {e}")
                return str(current_number + 1)
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
        url = "http://3.109.211.113:5000/read-pdf"
        
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

def extract_fields_from_xml(xml_text):
    """Extract fields from XML response and return a dictionary."""
    try:
        # Remove markdown code block markers if present
        if xml_text.startswith("```xml"):
            xml_text = xml_text.replace("```xml", "").replace("```", "").strip()
        
        logger.info(f"Processing XML text: {xml_text[:200]}...")  # Log first 200 chars
        
        # Parse XML string
        root = ET.fromstring(xml_text)
        
        # If root is the question element, use it directly
        question = root if root.tag == 'question' else root.find('question')
        if question is None:
            logger.error(f"XML structure: {ET.tostring(root, encoding='unicode')[:200]}...")  # Log XML structure
            raise ValueError("No question element found in XML")
        
        # Extract fields with more detailed error handling
        try:
            title_en = question.findtext('.//title/en', '').strip()
            english_title_en = question.findtext('.//englishTitle', '').strip()
            solution_en = question.findtext('.//solution/en', '').strip()
            explanation_en = question.findtext('.//explanation/en', '').strip()
            solution_wo_latex_en = question.findtext('.//solutionWOLatex/en', '').strip()
            difficulty_level = question.findtext('.//difficultyLevelCode', '').strip()
            question_no = question.findtext('.//questionNo', '').strip()
            
            result = {
                "title": {"en": title_en},
                "englishTitle": english_title_en,
                "solution": {"en": solution_en},
                "explanation": {"en": explanation_en},
                "solutionWOLatex": {"en": solution_wo_latex_en},
                "difficultyLevelCode": difficulty_level,
                "questionNo": question_no
            }
            
            # Log the extracted fields (first 100 chars of each)
            logger.info("Extracted fields:")
            for key, value in result.items():
                if isinstance(value, dict):
                    logger.info(f"{key}: {str(value)[:100]}...")
                else:
                    logger.info(f"{key}: {str(value)[:100]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting specific fields: {e}")
            raise ValueError(f"Error extracting fields from XML: {e}")
            
    except ET.ParseError as e:
        logger.error(f"XML parsing error: {e}")
        raise ValueError(f"Invalid XML format: {e}")
    except Exception as e:
        logger.error(f"Error extracting fields from XML: {e}")
        raise

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
    exerciseNo: str = Form(...),
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
        final_prompt = f"""{prompt}\n\n
                        Based on the content of the following PDF:\n\n{pdf_text}
                         Pick up question number {next_question_number}
                        """
        #if lastQuestionNumber < next_question_number:
        #    raise HTTPException(status_code=500, detail="No new questions found")

        logger.info("Generated final prompt for Gemini")

        # Generate content using Gemini 1.0 Pro
        response = model.generate_content(final_prompt)
        response.resolve()  # Ensure the response is fully resolved
        # response object should be printed as string in following logger
        logger.info(f"Received response from Gemini: {response}")

        # Clean up the temporary file
        os.remove(file_path)
        logger.info(f"Removed temporary file: {file_path}")

        # Extract fields from XML response
        response_text = response.text
        logger.info(f"Received response from Gemini: {response_text}")
        
        try:
            json_data = extract_fields_from_xml(response_text)
            logger.info("Successfully parsed XML response")
            
            # Format the question JSON
            next_sequence_number = get_next_sequence_number(board, source, subjectCode, gradeCode, topicCode, chapterNo)
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
                seqNumber=next_sequence_number,
                exerciseNo=exerciseNo
            )
            
            # Create question using API
            try:
                api_response = create_question_api(formatted_json)
                update_sequence_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, next_sequence_number)
                logger.info(f"Question created successfully: {api_response}")
                update_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo, next_question_number)
                return formatted_json
            except Exception as e:
                logger.error(f"Error creating question via API: {e}")
                raise HTTPException(status_code=500, detail=f"Error creating question: {e}")
        except ValueError as e:
            logger.error(f"Error processing XML response: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing request: {e}")
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {e}")

def format_question_json(json_data, status, gradeCode, subjectCode, topicCode, postedByUserId, board, source, chapterNo, seqNumber, exerciseNo):
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
            "exerciseNo": exerciseNo
        })
        
        return json_data
    except Exception as e:
        logger.error(f"Error formatting question JSON: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)