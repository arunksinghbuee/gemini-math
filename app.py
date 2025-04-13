# Install necessary libraries:
# pip install fastapi uvicorn google-generativeai PyPDF2 python-multipart python-dotenv

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import google.generativeai as genai
import PyPDF2
import os
from typing import Optional
from dotenv import load_dotenv

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
async def process_pdf(pdf_file: UploadFile = File(...), prompt: str = Form(...)):
    """
    Processes a PDF file using Gemini 1.0 Pro based on the provided prompt.
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
        final_prompt = f"Based on the content of the following PDF:\n\n{pdf_text}\n\n{prompt}"

        # Generate content using Gemini 1.0 Pro
        response = model.generate_content(final_prompt)
        response.resolve()  # Ensure the response is fully resolved

        # Clean up the temporary file
        os.remove(file_path)

        return JSONResponse(content={"response": response.text})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)