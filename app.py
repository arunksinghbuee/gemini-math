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

def escape_latex_math(json_str: str) -> str:
    """Escape LaTeX-style math expressions in the JSON string."""
    # Replace \( and \) with \\\( and \\\)
    json_str = json_str.replace('\(', '\\\(').replace('\)', '\\\)')
    # Replace other LaTeX commands that might need escaping
    json_str = json_str.replace('\\{', '\\\\{').replace('\\}', '\\\\}')
    # Replace other common LaTeX expressions
    json_str = json_str.replace('\\in', '\\\\in')
    json_str = json_str.replace('\\neq', '\\\\neq')
    json_str = json_str.replace('\\not', '\\\\not')
    return json_str

def clean_json_string(json_str: str) -> str:
    """Clean and prepare JSON string for parsing."""
    import re
    
    # First, handle LaTeX expressions
    latex_patterns = [
        (r'\\in', '\\\\in'),
        (r'\\notin', '\\\\notin'),
        (r'\\ne', '\\\\ne'),
        (r'\\neq', '\\\\neq'),
        (r'\\not', '\\\\not'),
        (r'\\{', '\\\\{'),
        (r'\\}', '\\\\}'),
        (r'\(', '\\('),
        (r'\)', '\\)'),
        (r'\\*', '\\\\*'),  # Handle multiplication symbol
        (r'\\\\(', '\\\\('),  # Handle double escaped parentheses
        (r'\\\\)', '\\\\\)'),  # Handle double escaped parentheses
    ]
    
    for pattern, replacement in latex_patterns:
        json_str = json_str.replace(pattern, replacement)
    
    # Handle Unicode symbols
    unicode_symbols = {
        '∈': '\\in',
        '∉': '\\notin',
        '≠': '\\neq',
        '≤': '\\leq',
        '≥': '\\geq',
        '×': '\\times',
        '÷': '\\div',
        '±': '\\pm',
        '∞': '\\infty',
        '∑': '\\sum',
        '∏': '\\prod',
        '∫': '\\int',
        '√': '\\sqrt',
        '≈': '\\approx',
        '→': '\\rightarrow',
        '←': '\\leftarrow',
        '↔': '\\leftrightarrow',
        '∀': '\\forall',
        '∃': '\\exists',
        '∄': '\\nexists',
        '∅': '\\emptyset',
        '⊂': '\\subset',
        '⊃': '\\supset',
        '⊆': '\\subseteq',
        '⊇': '\\supseteq',
        '∪': '\\cup',
        '∩': '\\cap',
        '∖': '\\setminus',
        '∆': '\\Delta',
        '∇': '\\nabla',
        '∂': '\\partial',
        '∝': '\\propto',
        '∠': '\\angle',
        '⊥': '\\perp',
        '∥': '\\parallel',
        '∦': '\\nparallel',
        '∝': '\\propto',
        '∅': '\\emptyset',
        '∅': '\\varnothing',
    }
    
    # Find all text content between quotes
    text_pattern = r'"([^"]*)"'
    
    def clean_text_content(match):
        text = match.group(1)
        # Replace Unicode symbols with their LaTeX equivalents
        for symbol, latex in unicode_symbols.items():
            text = text.replace(symbol, latex)
        
        # Handle nested LaTeX expressions
        def replace_latex(m):
            expr = m.group(1)
            # Escape any special characters in the expression
            expr = expr.replace('\\', '\\\\')
            expr = expr.replace('{', '\\{').replace('}', '\\}')
            return f'\\\\({expr}\\\\)'
        
        # Handle inline math expressions
        text = re.sub(r'\\\((.*?)\\\)', replace_latex, text)
        
        # Escape any unescaped quotes within the text
        text = text.replace('"', '\\"')
        # Handle curly braces in text content
        text = text.replace('{', '\\{').replace('}', '\\}')
        # Handle other special characters
        text = text.replace('\\', '\\\\')
        return f'"{text}"'
    
    json_str = re.sub(text_pattern, clean_text_content, json_str)
    
    # Ensure proper JSON structure
    json_str = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
    
    # Remove any trailing commas before closing braces
    json_str = re.sub(r',\s*}', '}', json_str)
    
    return json_str

def validate_and_clean_json(json_str: str) -> str:
    """Validate and clean the JSON string before parsing."""
    import re
    
    # Remove any duplicate keys in the same object
    pattern = r'"([^"]+)":\s*([^,}\n]+)'
    matches = re.finditer(pattern, json_str)
    seen_keys = set()
    cleaned_str = json_str
    
    for match in matches:
        key = match.group(1)
        if key in seen_keys:
            # Remove the duplicate key-value pair
            start = match.start()
            end = match.end()
            # Find the next comma or closing brace
            next_comma = cleaned_str.find(',', end)
            next_brace = cleaned_str.find('}', end)
            if next_comma != -1 and (next_brace == -1 or next_comma < next_brace):
                end = next_comma + 1
            else:
                end = next_brace + 1
            cleaned_str = cleaned_str[:start] + cleaned_str[end:]
        else:
            seen_keys.add(key)
    
    # Ensure all property names are properly quoted
    cleaned_str = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', cleaned_str)
    
    # Remove any trailing commas before closing braces
    cleaned_str = re.sub(r',\s*}', '}', cleaned_str)
    
    return cleaned_str

def extract_json_fields(response_text: str) -> dict:
    """Extract required fields from the JSON response using string operations."""
    try:
        # Find the JSON content between ```json and ```
        start_marker = "```json"
        end_marker = "```"
        start_idx = response_text.find(start_marker)
        if start_idx == -1:
            return None
        
        start_idx += len(start_marker)
        end_idx = response_text.find(end_marker, start_idx)
        if end_idx == -1:
            return None
        
        json_str = response_text[start_idx:end_idx].strip()
        
        # Extract required fields using string operations
        fields = {}
        
        def extract_nested_field(field_name: str) -> dict:
            start = json_str.find(f'"{field_name}":')
            if start == -1:
                return None
            
            # Find the opening brace
            start = json_str.find('{', start)
            if start == -1:
                return None
            
            # Count braces to find the matching closing brace
            brace_count = 1
            end = start + 1
            while brace_count > 0 and end < len(json_str):
                if json_str[end] == '{':
                    brace_count += 1
                elif json_str[end] == '}':
                    brace_count -= 1
                end += 1
            
            if brace_count == 0:
                return json_str[start:end]
            return None
        
        def extract_simple_field(field_name: str) -> str:
            start = json_str.find(f'"{field_name}":')
            if start == -1:
                return None
            
            # Find the value after the colon
            start = json_str.find(':', start) + 1
            while start < len(json_str) and json_str[start].isspace():
                start += 1
            
            # Find the end of the value
            end = start
            if json_str[start] == '"':
                # Handle string values
                end = json_str.find('"', start + 1)
                while end != -1 and json_str[end-1] == '\\':
                    end = json_str.find('"', end + 1)
                if end != -1:
                    end += 1
            else:
                # Handle non-string values
                while end < len(json_str) and json_str[end] not in ',}':
                    end += 1
            
            return json_str[start:end]
        
        # Extract nested fields
        title = extract_nested_field('title')
        if title:
            fields['title'] = title
        
        solution = extract_nested_field('solution')
        if solution:
            fields['solution'] = solution
        
        explanation = extract_nested_field('explanation')
        if explanation:
            fields['explanation'] = explanation
        
        # Extract simple fields
        difficulty = extract_simple_field('difficultyLevelCode')
        if difficulty:
            fields['difficultyLevelCode'] = difficulty
        
        question_no = extract_simple_field('questionNo')
        if question_no:
            fields['questionNo'] = question_no
        
        # Construct the final JSON string
        if not fields:
            return None
            
        final_json = "{\n"
        for key, value in fields.items():
            final_json += f'  "{key}": {value},\n'
        final_json = final_json.rstrip(',\n') + "\n}"
        
        return json.loads(final_json)
    except Exception as e:
        logger.error(f"Error extracting JSON fields: {e}")
        return None

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
        
        # Try to extract fields using string operations
        json_data = extract_json_fields(response_text)
        if json_data:
            logger.info("Successfully extracted JSON fields")
            try:
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
                        except Exception as e:
                            logger.error(f"Error creating question via API: {e}")
                            raise HTTPException(status_code=500, detail=f"Error creating question: {e}")
                    except Exception as e:
                        logger.error(f"Error formatting question: {e}")
                        raise
                else:
                    logger.error("Invalid JSON structure received")
                    raise HTTPException(status_code=500, detail="Invalid JSON structure")
            except Exception as e:
                logger.error(f"Error processing questions: {e}")
                raise HTTPException(status_code=500, detail=f"Error processing questions: {e}")
        else:
            logger.warning("Failed to extract JSON fields")
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
            #"seoMetaData": {
            #    "en": json_data.get("seoMetaData", {}).get("en", ""),
            #    "hi": json_data.get("seoMetaData", {}).get("hi", "")
            #}
        })
        
        return json_data
    except Exception as e:
        logger.error(f"Error formatting question JSON: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)