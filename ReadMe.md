## .env file:
GOOGLE_API_KEY=<google-api-key>

## Install dependencies
pip install -r requirements.txt

## To create venv
python -m venv .venv
./venv/Scripts/activate

## API Call
curl --location 'http://localhost:8000/process_pdf' \
--header 'Content-Type: multipart/form-data' \
--form 'pdf_file=@"/C:/Users/615180708/Downloads/ncert-math-ch-1.pdf"' \
--form 'prompt="\"You are a Class 12 mathematics teacher. Your task is to analyze examples and their solutions from the provided PDF document and present them in a structured JSON format.