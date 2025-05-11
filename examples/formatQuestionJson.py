import json
from typing import Dict, Any, Optional

def format_question_json(
    input_data: Dict[str, Any],
    status: str = "DRAFT",
    gradeCode: str = "GRADE_12",
    subjectCode: str = "MATH",
    topicCode: str = "REL_AND_FUNC",
    postedByUserId: str = "67fabb8bf481c327cbb04d46",
    board: str = "CBSE",
    source: str = "NCERT Maths",
    chapterNo: str = "1",
    seqNumber: int = 10
) -> Dict[str, Any]:
    """
    Transform the input question JSON into the required format.
    
    Args:
        input_data: Input JSON data containing question information
        status: Status of the question (default: "PUBLISHED")
        gradeCode: Grade code (default: "GRADE_12")
        subjectCode: Subject code (default: "MATH")
        topicCode: Topic code (default: "REL_AND_FUNC")
        postedByUserId: User ID who posted the question (default: "67fabb8bf481c327cbb04d46")
        board: Board name (default: "CBSE")
        source: Source of the question (default: "NCERT Maths")
        chapterNo: Chapter number (default: "1")
        seqNumber: Sequence number (default: 10)
        
    Returns:
        Dict containing the formatted question data
    """
    # Handle SEO metadata in both formats
    seo_meta = input_data.get("seoMetaData", {})
    
    # Initialize SEO fields with empty values
    seo_metadata = {"en": "", "hi": ""}
    
    # Get title for SEO title
    seo_title = input_data.get("title", {"en": "", "hi": ""})
    
    # Create SEO description by combining solution and explanation
    solution = input_data.get("solution", {"en": "", "hi": ""})
    explanation = input_data.get("explanation", {"en": "", "hi": ""})
    
    seo_description = {
        "en": f"{solution.get('en', '')}\n\n{explanation.get('en', '')}",
        "hi": f"{solution.get('hi', '')}\n\n{explanation.get('hi', '')}"
    }
    
    # Handle SEO metadata
    if isinstance(seo_meta.get("en"), dict):
        seo_metadata = {
            "en": seo_meta.get("en", {}).get("keywords", ""),
            "hi": seo_meta.get("hi", {}).get("keywords", "")
        }
    else:
        seo_metadata = seo_meta
    
    # Create the formatted output
    formatted_data = {
        "title": input_data.get("title", {"en": "", "hi": ""}),
        "solution": input_data.get("solution", {"en": "", "hi": ""}),
        "explanation": input_data.get("explanation", {"en": "", "hi": ""}),
        "status": status,
        "gradeCode": gradeCode,
        "subjectCode": subjectCode,
        "topicCode": topicCode,
        "difficultyLevelCode": input_data.get("difficultyLevelCode", "EASY"),
        "postedByUserId": postedByUserId,
        "seoTitle": seo_title,
        "seoDescription": seo_description,
        "seoMetaData": seo_metadata,
        "questionNo": input_data.get("questionNo", ""),
        "board": board,
        "source": source,
        "chapterNo": chapterNo,
        "seqNumber": seqNumber
    }
    
    return formatted_data

def process_json_file(
    input_file: str,
    output_file: str,
    status: Optional[str] = None,
    gradeCode: Optional[str] = None,
    subjectCode: Optional[str] = None,
    topicCode: Optional[str] = None,
    postedByUserId: Optional[str] = None,
    board: Optional[str] = None,
    source: Optional[str] = None,
    chapterNo: Optional[str] = None,
    seqNumber: Optional[int] = None
) -> None:
    """
    Process a JSON file and save the formatted output.
    
    Args:
        input_file: Path to the input JSON file
        output_file: Path to save the output JSON file
        status: Status of the question
        gradeCode: Grade code
        subjectCode: Subject code
        topicCode: Topic code
        postedByUserId: User ID who posted the question
        board: Board name
        source: Source of the question
        chapterNo: Chapter number
        seqNumber: Sequence number
    """
    try:
        # Read input JSON file
        with open(input_file, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
        
        # Format the data with provided parameters
        formatted_data = format_question_json(
            input_data,
            status=status,
            gradeCode=gradeCode,
            subjectCode=subjectCode,
            topicCode=topicCode,
            postedByUserId=postedByUserId,
            board=board,
            source=source,
            chapterNo=chapterNo,
            seqNumber=seqNumber
        )
        
        # Write formatted data to output file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(formatted_data, f, ensure_ascii=False, indent=4)
            
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON file: {e}")
        raise
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        raise
    except Exception as e:
        print(f"Error processing JSON file: {e}")
        raise

if __name__ == "__main__":
    # Example usage
    input_file = "tmp.json"
    output_file = "working1.json"
    process_json_file(
        input_file,
        output_file,
        status="PUBLISHED",
        gradeCode="GRADE_12",
        subjectCode="MATH",
        topicCode="REL_AND_FUNC",
        postedByUserId="67fabb8bf481c327cbb04d46",
        board="CBSE",
        source="NCERT Maths",
        chapterNo="1",
        seqNumber=10
    )
