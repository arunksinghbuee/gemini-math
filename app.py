# Install necessary libraries:
# pip install fastapi uvicorn google-generativeai PyPDF2 python-multipart python-dotenv

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import google.generativeai as genai
import PyPDF2
import os
import json
from typing import Optional
from dotenv import load_dotenv

from formatQuestionJson import format_question_json

# Load environment variables
load_dotenv()

# Get API key from environment variable
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")

# Configure Gemini API
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

app = FastAPI()

def get_next_sequence_number(board, source, subjectCode, gradeCode, topicCode, chapterNo):
    """Get and increment sequence number by 10 from local file."""
    key = f"{board}_{source}_{subjectCode}_{gradeCode}_{topicCode}_{chapterNo}"
    filename = "sequence_numbers.json"
    
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                sequence_numbers = json.load(f)
        else:
            sequence_numbers = {key: 10}  # Initialize with 10 for new key
            with open(filename, 'w') as f:
                json.dump(sequence_numbers, f)
            return 10
        
        current_number = sequence_numbers.get(key, 10) + 10  # Default to 10 if key doesn't exist
        sequence_numbers[key] = current_number
        
        with open(filename, 'w') as f:
            json.dump(sequence_numbers, f)
            
        return current_number
    except Exception as e:
        print(f"Error managing sequence numbers: {e}")
        return 10  # Fallback to 10 if there's any error

def get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo):
    """Get and increment question number by 1 from local file."""
    key = f"{board}_{source}_{subjectCode}_{gradeCode}_{topicCode}_{chapterNo}_question"
    filename = "question_numbers.json"
    
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                question_numbers = json.load(f)
        else:
            question_numbers = {key: 1}  # Initialize with 1 for new key
            with open(filename, 'w') as f:
                json.dump(question_numbers, f)
            return 1
        
        current_number = question_numbers.get(key, 1) + 1  # Default to 1 if key doesn't exist
        question_numbers[key] = current_number
        
        with open(filename, 'w') as f:
            json.dump(question_numbers, f)
            
        return current_number
    except Exception as e:
        print(f"Error managing question numbers: {e}")
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
        return text
    except Exception as e:
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
    chapterNo: str = Form(...)
):
    """
    Processes a PDF file using Gemini 1.0 Pro based on the provided prompt.
    Required parameters:
    - status: Question status (e.g., PUBLISHED)
    - gradeCode: Grade code (e.g., GRADE_12)
    - subjectCode: Subject code (e.g., MATH)
    - topicCode: Topic code (e.g., REL_AND_FUNC)
    - postedByUserId: User ID who posted the question
    - board: Board name (e.g., CBSE)
    - source: Source of the question (e.g., NCERT Maths)
    - chapterNo: Chapter number
    """
    if not pdf_file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file format. Only PDF files are allowed.")

    try:
        # Save the uploaded PDF temporarily
        file_path = f"temp_{pdf_file.filename}"
        with open(file_path, "wb") as f:
            content = await pdf_file.read()
            f.write(content)

        pdf_text = extract_text_from_pdf(file_path)

        # Construct the final prompt for Gemini
        final_prompt = f"""Based on the content of the following PDF:\n\n{pdf_text}
                        Pick up examples from examples no {get_next_question_number(board, source, subjectCode, gradeCode, topicCode, chapterNo)}
                        \n\n{prompt}"""

        # Generate content using Gemini 1.0 Pro
        response = model.generate_content(final_prompt)
        response.resolve()  # Ensure the response is fully resolved

        # Clean up the temporary file
        os.remove(file_path)

        # Extract JSON from the response
        response_text = response.text
        if response_text.startswith("```json"):
            # Remove the markdown code block markers
            json_str = response_text.replace("```json", "").replace("```", "").strip()
            try:
                # Parse the JSON string
                json_data = json.loads(json_str)
                
                # Handle both single object and array cases
                if isinstance(json_data, dict):
                    # Single question
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
                    return formatted_json
                elif isinstance(json_data, list):
                    # Multiple questions
                    formatted_questions = []
                    for question in json_data:
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
                        formatted_questions.append(formatted_question)
                    return formatted_questions
                else:
                    raise HTTPException(status_code=500, detail="Invalid JSON structure")
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=500, detail=f"Error parsing JSON response: {e}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error processing questions: {e}")
        else:
            # If the response is not in JSON format, return it as is
            return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)