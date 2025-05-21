import os
import json
import re
from typing import Dict, List
from PIL import Image
import pdf2image
import tempfile
import google.generativeai as genai
from fuzzywuzzy import fuzz
import base64
from datetime import datetime
import logging
import time

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ScholarshipDocumentVerifier:
    def __init__(self):
        genai.configure(api_key="AIzaSyDpifhK-BN9ddPd5kRCv9SLH9IfF3-xiBg")
        #self.model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.max_retries = 3
        self.retry_delay = 2
        self.name_match_threshold = 80  

    def parse_age_range(self, age_range: str) -> tuple:
        """Parse age range string (e.g., '13-18') to tuple (min, max)."""
        try:
            min_age, max_age = map(int, age_range.split("-"))
            return min_age, max_age
        except ValueError:
            raise ValueError(f"Invalid age_range format: {age_range}")

    def parse_income_range(self, income_range: str) -> tuple:
        """Parse income range string (e.g., 'INR 0 - 350000') to tuple (min, max)."""
        try:
            parts = income_range.replace("INR", "").strip().split("-")
            min_income = int(parts[0].strip())
            max_income = int(parts[1].strip())
            return min_income, max_income
        except ValueError:
            raise ValueError(f"Invalid income_range format: {income_range}")

    def calculate_age(self, dob: str) -> int:
        """Calculate age from DOB string (e.g., '2000-05-15')."""
        try:
            dob_date = datetime.strptime(dob, "%Y-%m-%d")
            today = datetime.now()
            age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
            return age
        except ValueError:
            return -1  

    def file_to_base64(self, file_path: str) -> str:
        """Convert file (PDF) to base64 string."""
        try:
            with open(file_path, "rb") as file:
                return base64.b64encode(file.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to convert file to base64: {file_path}, error: {str(e)}")
            raise ValueError(f"Failed to process file: {str(e)}")

    def clean_response_text(self, text: str) -> str:
        """Clean Gemini API response by removing markdown fences and extraneous whitespace."""
        text = re.sub(r'^```json\s*\n|\n```$', '', text, flags=re.MULTILINE)
        text = text.strip()
        return text

    def generate_name_combinations(self, name: str) -> List[str]:
        """Generate possible name combinations for fuzzy matching."""
        parts = name.strip().split()
        if not parts:
            return [name]
        combinations = []
        combinations.append(name)
       
        if len(parts) > 1:
            combinations.append(" ".join(parts[::-1]))
       
        for i in range(len(parts)):
            initial = parts[i][0]
            other_parts = parts[:i] + parts[i+1:]
            combinations.append(f"{initial} {' '.join(other_parts)}")
            combinations.append(f"{' '.join(other_parts)} {initial}")

        combinations.extend(parts)
        return list(set(combinations))

    def fuzzy_match_names(self, extracted: str, provided: str) -> bool:
        """Compare two names using fuzzy matching with combinations."""
        if not extracted or not provided:
            return True 
        extracted_combinations = self.generate_name_combinations(extracted)
        provided_combinations = self.generate_name_combinations(provided)
        for e in extracted_combinations:
            for p in provided_combinations:
                score = fuzz.token_sort_ratio(e.lower(), p.lower())
                if score >= self.name_match_threshold:
                    return True
        return False

    def verify_scholarship_documents(self, scholarship: Dict, document_paths: List[str], user_data: Dict) -> Dict:
        """
        Verify scholarship documents using Gemini API by comparing with user-provided data.
        Args:
            scholarship: Dictionary with scholarship details (title, age_range, income_range, required_documents, etc.)
            document_paths: List of file paths to documents (PDFs expected)
            user_data: Dictionary with user-provided data (student_name, dob, father_name, mother_name, annual_income, age)
        Returns:
            Dictionary: {"documentValid": bool, "reasonForRejection": list}
        """
        try:
           
            if "required_documents" not in scholarship or not scholarship["required_documents"]:
                return {
                    "documentValid": False,
                    "reasonForRejection": ["Scholarship JSON missing required_documents"]
                }
            required_docs = scholarship["required_documents"]

            if len(document_paths) != len(required_docs):
                return {
                    "documentValid": False,
                    "reasonForRejection": [f"Expected {len(required_docs)} documents ({', '.join(required_docs)}), received {len(document_paths)}"]
                }

      
            eligibility = []
            age_eligible = True
            income_eligible = True
            if "age_range" in scholarship and scholarship["age_range"]:
                min_age, max_age = self.parse_age_range(scholarship["age_range"])
                eligibility.append(f"Age: {min_age}-{max_age} years")
                user_age = user_data.get("age", -1)
                if user_age < min_age or user_age > max_age:
                    age_eligible = False
            if "income_range" in scholarship and scholarship["income_range"]:
                min_income, max_income = self.parse_income_range(scholarship["income_range"])
                eligibility.append(f"Annual Family Income: INR {min_income}-{max_income}")
                user_income = user_data.get("annual_income", -1)
                if user_income < min_income or user_income > max_income:
                    income_eligible = False
            if "eligibility_criteria" in scholarship and scholarship["eligibility_criteria"]:
                eligibility.append(scholarship["eligibility_criteria"])
            if scholarship.get("category") == "Need-based":
                eligibility.append("Nationality: Indian")
            if scholarship.get("category") == "Merit-based":
                eligibility.append("Minimum academic performance: As specified in scholarship description")

          
            documents = []
            for file_path, expected_doc in zip(document_paths, required_docs):
                if not file_path.lower().endswith(".pdf"):
                    return {
                        "documentValid": False,
                        "reasonForRejection": [f"Document for {expected_doc} must be a PDF"]
                    }
                base64_data = self.file_to_base64(file_path)
                documents.append({
                    "type": expected_doc,
                    "base64_data": base64_data,
                    "mime_type": "application/pdf"
                })

            prompt = (
                f"You are an Indian scholarship provider verifying documents submitted for the scholarship '{scholarship.get('title', 'Unknown')}'. "
                f"Your task is to extract information from the provided PDF documents and compare it with user-provided data. "
                f"Perform these checks:\n"
                f"1. **Document Type and Completeness**: Confirm each document matches its expected type and contains required fields:\n"
                f"   - Aadhar Card: Name, DOB, Address (ignore Aadhar number).\n"
                f"   - Academic Transcript: Name, Class/Grade, Marks/Grades, Institution Name.\n"
                f"   - Income Certificate: Name, Annual Income.\n"
                f"   - Other Government IDs: Name, DOB (ignore ID number).\n"
                f"   - Report missing fields (e.g., 'Missing DOB in Aadhar Card').\n"
                f"2. **Field Extraction and Comparison**: Extract the following fields from each document (if present) and compare with user-provided data:\n"
                f"   - Name: Match with '{user_data.get('student_name', '')}'.\n"
                f"   - Father's Name: Match with '{user_data.get('father_name', '')}'.\n"
                f"   - Mother's Name: Match with '{user_data.get('mother_name', '')}'.\n"
                f"   - DOB: Match with '{user_data.get('dob', '')}' (format: DD-MM-YYYY).\n"
                f"   - Annual Income: Match with {user_data.get('annual_income', 0)} (from Income Certificate).\n"
                f"   - Skip fields not present in a document (e.g., if Father's Name is missing, do not compare).\n"
                f"   - Do NOT compare fields across documents; only compare with user-provided data.\n"
                f"   - Do NOT compare unique identifiers (e.g., Aadhar number, PAN number, roll number).\n"
                f"3. **Name Matching**: Handle name variations:\n"
                f"   - Names can be in different formats (e.g., 'Anil Kumar' vs. 'K Anil', 'Anil K', 'Kumar Anil', 'A Kumar').\n"
                f"   - Generate combinations of name parts (full name, reversed, initials with parts, single parts).\n"
                f"   - Use fuzzy matching with at least 80% similarity (ignore case, minor spelling errors like 'Kummar' vs. 'Kumar').\n"
                f"   - Apply the same logic to Father's Name and Mother's Name, matching only with their respective user-provided fields.\n"
                f"   - Example: For user-provided 'Anil Kumar', accept 'K Anil', 'Anil K', 'Kumar Anil', 'A Kumar' if similarity ≥ 80%.\n"
                f"4. **Language Translation**: If a document is in a non-English language (e.g., Hindi, Tamil), translate to English before extraction. Note translation issues.\n"
                f"5. **Eligibility**: Verify the applicant meets: {', '.join(eligibility) if eligibility else 'None specified'}.\n"
                f"   - Calculate age from user-provided DOB (today: {datetime.now().strftime('%Y-%m-%d')}).\n"
                f"   - Check income from user-provided annual_income against scholarship income_range.\n"
                f"   - Assume Indian nationality for Need-based scholarships unless specified.\n"
                f"6. **Output**: For each document, list extracted fields and comparison results. Report mismatches as reasons.\n"
                f"Return a JSON response in this exact format: {{'is_valid': bool, 'reasons': []}}. "
                f"Set 'is_valid': true only if all documents match user-provided data and meet eligibility. "
                f"List specific reasons in 'reasons' for any mismatches or missing fields (e.g., 'Name mismatch in Aadhar Card: Anil Kumar vs. Anil Sharma'). "
                f"Do not include markdown code fences or text outside the JSON object.\n"
                f"Documents:\n{json.dumps(documents, indent=2)}\n"
                f"Required documents: {json.dumps(required_docs, indent=2)}\n"
                f"User-provided data:\n{json.dumps(user_data, indent=2)}"
            )

            content = [prompt]
            for doc in documents:
                content.append({
                    "inline_data": {
                        "mime_type": doc["mime_type"],
                        "data": doc["base64_data"]
                    }
                })

            for attempt in range(self.max_retries):
                try:
                    response = self.model.generate_content(content)
                    logger.debug(f"Gemini API raw response: {repr(response.text)}")
                    cleaned_response = self.clean_response_text(response.text)
                    logger.debug(f"Cleaned response: {repr(cleaned_response)}")
                    try:
                        result = json.loads(cleaned_response)
                        if not isinstance(result, dict) or "is_valid" not in result or "reasons" not in result:
                            logger.error(f"Invalid Gemini response format: {cleaned_response}")
                            return {
                                "documentValid": False,
                                "reasonForRejection": ["Invalid response format from Gemini API"]
                            }
                        reasons = result["reasons"]
                        if not age_eligible:
                            reasons.append(f"User age {user_data.get('age', -1)} does not meet scholarship age range {scholarship.get('age_range', '')}")
                        if not income_eligible:
                            reasons.append(f"User annual income {user_data.get('annual_income', -1)} does not meet scholarship income range {scholarship.get('income_range', '')}")
                        is_valid = result["is_valid"] and age_eligible and income_eligible
                        return {
                            "documentValid": is_valid,
                            "reasonForRejection": reasons
                        }
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse cleaned Gemini response: {cleaned_response}, error: {str(e)}")
                        if attempt == self.max_retries - 1:
                            return {
                                "documentValid": False,
                                "reasonForRejection": ["Failed to parse Gemini API response"]
                            }
                        logger.info(f"Retrying API call ({attempt + 1}/{self.max_retries})")
                        time.sleep(self.retry_delay)
                except Exception as e:
                    logger.error(f"Gemini API call failed: {str(e)}")
                    if attempt == self.max_retries - 1:
                        return {
                            "documentValid": False,
                            "reasonForRejection": [f"Gemini API call failed: {str(e)}"]
                        }
                    logger.info(f"Retrying API call ({attempt + 1}/{self.max_retries})")
                    time.sleep(self.retry_delay)

            return {
                "documentValid": False,
                "reasonForRejection": ["Failed to verify documents after multiple attempts"]
            }

        except Exception as e:
            logger.exception(f"Verification failed: {str(e)}")
            return {
                "documentValid": False,
                "reasonForRejection": [f"Verification failed: {str(e)}"]
            }