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

## Prompt
You are a mathematics teacher of class 12.
Read all the examples and its solutions from attached PDF file and create response in the following format.
Write explanation of the solution. Make sure that solution should not look like AI generated.
DifficultyLevelCode should EASY, MEDIUM, HARD. Provide best suggestion.
Generate and populate the best seoMetadata for respective example.
Add next line, double next line, paragraph etc whatever and wherever best applicable for the student in title, solution and explanation. Don't use markdown in title, solution and explanation.

Response must be json only.

title, solution, explanation, seoMetaData must be created for following languages.

English (en)
Hindi (hi)

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
"questionNo": Example <quesitonNo>
}