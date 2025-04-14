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
Generate and populate the best SeoTitle, seoDescription and seoMetadata for respective example.
Add next line, double next line, paragraph etc whatever and wherever best applicable for the student in title, solution and explanation. Don't use markdown in title, solution and explanation.

Response must be json only.

title, solution, explanation, seoTitle, SeoDescription and seoMetaData must be created for following languages.

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
"status": "PUBLISHED",
"gradeCode": "GRADE_12",
"subjectCode": "MATH",
"topicCode": "REL_AND_FUNC",
"difficultyLevelCode": <difficulty level>,
"postedByUserId": "67fabb8bf481c327cbb04d46",
"seoTitle": {
"en": <same as title in en language>
"hi": <same as title hi en language>,
},
"seoDescription": {
"en": <same as solution + explanation in en language>
"hi": <same as solution + explanation in hi language>,
},
"seoMetaData": {
"en": <best possible seo MetaData as per seoTitle and seoDescription in en language>,
"hi": <best possible seo MetaData as per seoTitle and seoDescription in hi language>,
},
"questionNo": <quesitonNo>,
"board": "CBSE",
"source": "NCERT Maths",
"chapterNo": "1",
"seqNumber": <incremental in a gap of 10, starting from 10>
}