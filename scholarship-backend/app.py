from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from bson import ObjectId
from datetime import datetime
import os
from flask_cors import CORS
import gridfs
from werkzeug.utils import secure_filename
from documentVerifier import ScholarshipDocumentVerifier
import tempfile
import logging
from flask import send_file
import io

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

app.config["MONGO_URI"] = os.environ.get("MONGO_URI", "mongodb://localhost:27017/scholarship_db")
mongo = PyMongo(app)
scholarships = mongo.db.scholarships
applications = mongo.db.applications
fs = gridfs.GridFS(mongo.db)

verifier = ScholarshipDocumentVerifier()

SCHOLARSHIP_FIELDS = {
    "title": str,
    "provider": str,
    "amount": str,
    "deadline": str,
    "category": str,
    "description": str,
    "age_range": str,
    "income_range": str,
    "required_documents": list,
    "created_at": str
}

APPLICATION_FIELDS = {
    "scholarship_id": str,
    "user_id": str,
    "student_name": str,
    "student_email": str,
    "age": int,
    "gender": str,
    "dob": str,
    "father_name": str,
    "mother_name": str,
    "annual_income": float,
    "status": str,
    "submitted_at": str,
    "documents": list,
    "verification_result": dict,
    "remarks": list
}

@app.route("/api/scholarships", methods=["POST"])
def add_scholarship():
    try:
        data = request.get_json()
        logger.debug(f"Received scholarship data: {data}")
        
        required_fields = ["title", "provider", "amount", "deadline", "category", "description", "required_documents"]
        for field in required_fields:
            if field not in data or not data[field]:
                logger.error(f"Missing or empty required field: {field}")
                return jsonify({"error": f"Missing or empty required field: {field}"}), 400
        
        scholarship_data = {
            "title": data["title"],
            "provider": data["provider"],
            "amount": data["amount"],
            "deadline": data["deadline"],
            "category": data["category"],
            "description": data["description"],
            "age_range": data.get("age_range", ""),
            "income_range": data.get("income_range", ""),
            "required_documents": data["required_documents"],
            "created_at": datetime.utcnow().isoformat()
        }

        valid_categories = ['Undergraduate', 'Graduate', 'International', 'Merit-based', 'Need-based']
        if scholarship_data["category"] not in valid_categories:
            logger.error(f"Invalid category: {scholarship_data['category']}")
            return jsonify({"error": "Invalid category"}), 400
            
        try:
            datetime.fromisoformat(scholarship_data["deadline"].replace("Z", "+00:00"))
        except ValueError:
            logger.error(f"Invalid deadline format: {scholarship_data['deadline']}")
            return jsonify({"error": "Invalid deadline format. Use ISO format (YYYY-MM-DD)"}), 400

        logger.info("Inserting scholarship into MongoDB")
        result = scholarships.insert_one(scholarship_data)

        scholarship_data["id"] = str(result.inserted_id)
        logger.info(f"Scholarship inserted with ID: {scholarship_data['id']}")
        return jsonify(scholarship_data), 201
        
    except Exception as e:
        logger.exception(f"Error adding scholarship: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/scholarships", methods=["GET"])
def get_scholarships():
    try:
        logger.info("Fetching all scholarships")
        scholarship_list = []
        for scholarship in scholarships.find():
            scholarship["id"] = str(scholarship["_id"])
            del scholarship["_id"]
            scholarship_list.append(scholarship)
        
        logger.info(f"Retrieved {len(scholarship_list)} scholarships")
        return jsonify(scholarship_list), 200
        
    except Exception as e:
        logger.exception(f"Error fetching scholarships: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/scholarships/<id>", methods=["GET"])
def get_scholarship(id):
    try:
        logger.debug(f"Fetching scholarship with ID: {id}")
        if not ObjectId.is_valid(id):
            logger.error(f"Invalid scholarship ID: {id}")
            return jsonify({"error": "Invalid scholarship ID"}), 400
            
        scholarship = scholarships.find_one({"_id": ObjectId(id)})
        if not scholarship:
            logger.error(f"Scholarship not found: {id}")
            return jsonify({"error": "Scholarship not found"}), 404
            
        scholarship["id"] = str(scholarship["_id"])
        del scholarship["_id"]
        logger.info(f"Retrieved scholarship: {scholarship['id']}")
        return jsonify(scholarship), 200
        
    except Exception as e:
        logger.exception(f"Error fetching scholarship {id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/scholarships/<id>", methods=["PUT"])
def update_scholarship(id):
    try:
        logger.debug(f"Updating scholarship with ID: {id}")
        if not ObjectId.is_valid(id):
            logger.error(f"Invalid scholarship ID: {id}")
            return jsonify({"error": "Invalid scholarship ID"}), 400
            
        data = request.get_json()
        logger.debug(f"Received update data: {data}")
        
        required_fields = ["title", "provider", "amount", "deadline", "category", "description", "required_documents"]
        for field in required_fields:
            if field not in data or not data[field]:
                logger.error(f"Missing or empty required field: {field}")
                return jsonify({"error": f"Missing or empty required field: {field}"}), 400
        
        scholarship_data = {
            "title": data["title"],
            "provider": data["provider"],
            "amount": data["amount"],
            "deadline": data["deadline"],
            "category": data["category"],
            "description": data["description"],
            "age_range": data.get("age_range", ""),
            "income_range": data.get("income_range", ""),
            "required_documents": data["required_documents"],
            "created_at": data.get("created_at", datetime.utcnow().isoformat())
        }
        
        valid_categories = ['Undergraduate', 'Graduate', 'International', 'Merit-based', 'Need-based']
        if scholarship_data["category"] not in valid_categories:
            logger.error(f"Invalid category: {scholarship_data['category']}")
            return jsonify({"error": "Invalid category"}), 400
            
        try:
            datetime.fromisoformat(scholarship_data["deadline"].replace("Z", "+00:00"))
        except ValueError:
            logger.error(f"Invalid deadline format: {scholarship_data['deadline']}")
            return jsonify({"error": "Invalid deadline format. Use ISO format (YYYY-MM-DD)"}), 400
            
        logger.info(f"Updating scholarship {id} in MongoDB")
        result = scholarships.update_one(
            {"_id": ObjectId(id)},
            {"$set": scholarship_data}
        )
        
        if result.matched_count == 0:
            logger.error(f"Scholarship not found: {id}")
            return jsonify({"error": "Scholarship not found"}), 404
            
        scholarship_data["id"] = id
        logger.info(f"Scholarship updated: {id}")
        return jsonify(scholarship_data), 200
        
    except Exception as e:
        logger.exception(f"Error updating scholarship {id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/scholarships/<id>", methods=["DELETE"])
def delete_scholarship(id):
    try:
        logger.debug(f"Deleting scholarship with ID: {id}")
        if not ObjectId.is_valid(id):
            logger.error(f"Invalid scholarship ID: {id}")
            return jsonify({"error": "Invalid scholarship ID"}), 400
            
        logger.info(f"Deleting scholarship {id} from MongoDB")
        result = scholarships.delete_one({"_id": ObjectId(id)})
        
        if result.deleted_count == 0:
            logger.error(f"Scholarship not found: {id}")
            return jsonify({"error": "Scholarship not found"}), 404
            
        logger.info(f"Scholarship deleted: {id}")
        return jsonify({"message": "Scholarship deleted successfully"}), 200
        
    except Exception as e:
        logger.exception(f"Error deleting scholarship {id}: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/applications/<id>", methods=["PUT"])
def update_application_status(id):
    try:
        logger.debug(f"Updating application status for ID: {id}")
        if not ObjectId.is_valid(id):
            logger.error(f"Invalid application ID: {id}")
            return jsonify({"error": "Invalid application ID"}), 400

        data = request.get_json()
        logger.debug(f"Received update data: {data}")

        if "status" not in data or not data["status"]:
            logger.error("Missing or empty status field")
            return jsonify({"error": "Missing or empty status field"}), 400

        valid_statuses = ['pending', 'approved', 'rejected']
        if data["status"] not in valid_statuses:
            logger.error(f"Invalid status: {data['status']}")
            return jsonify({"error": f"Invalid status. Must be one of: {valid_statuses}"}), 400

        application = applications.find_one({"_id": ObjectId(id)})
        if not application:
            logger.error(f"Application not found: {id}")
            return jsonify({"error": "Application not found"}), 404

        logger.info(f"Updating application {id} status to {data['status']} in MongoDB")
        result = applications.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"status": data["status"]}}
        )

        if result.matched_count == 0:
            logger.error(f"Application not found during update: {id}")
            return jsonify({"error": "Application not found"}), 404
        
        updated_application = applications.find_one({"_id": ObjectId(id)})
        updated_application["id"] = str(updated_application["_id"])
        del updated_application["_id"]
        logger.info(f"Application status updated: {id}, new status: {data['status']}")
        return jsonify(updated_application), 200

    except Exception as e:
        logger.exception(f"Error updating application status {id}: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/applications/<id>", methods=["DELETE"])
def delete_application(id):
    try:
        logger.debug(f"Deleting application with ID: {id}")
        if not ObjectId.is_valid(id):
            logger.error(f"Invalid application ID: {id}")
            return jsonify({"error": "Invalid application ID"}), 400
            
        application = applications.find_one({"_id": ObjectId(id)})
        if not application:
            logger.error(f"Application not found: {id}")
            return jsonify({"error": "Application not found"}), 404
            
        for doc in application.get("documents", []):
            file_id = doc.get("file_id")
            if file_id and ObjectId.is_valid(file_id):
                logger.debug(f"Deleting document with file_id: {file_id}")
                fs.delete(ObjectId(file_id))
                
        logger.info(f"Deleting application {id} from MongoDB")
        result = applications.delete_one({"_id": ObjectId(id)})
        
        if result.deleted_count == 0:
            logger.error(f"Application not found during deletion: {id}")
            return jsonify({"error": "Application not found"}), 404
            
        logger.info(f"Application deleted: {id}")
        return jsonify({"message": "Application deleted successfully"}), 200
        
    except Exception as e:
        logger.exception(f"Error deleting application {id}: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/documents/<file_id>", methods=["GET"])
def get_document(file_id):
    try:
        logger.debug(f"Fetching document with file_id: {file_id}")
        if not ObjectId.is_valid(file_id):
            logger.error(f"Invalid file ID: {file_id}")
            return jsonify({"error": "Invalid file ID"}), 400
            
        file = fs.get(ObjectId(file_id))
        if not file:
            logger.error(f"File not found: {file_id}")
            return jsonify({"error": "File not found"}), 404
            
        filename = file.filename or "document.pdf"
        logger.info(f"Serving file: {filename} with file_id: {file_id}")
        return send_file(
            io.BytesIO(file.read()),
            download_name=filename,
            as_attachment=True,
            mimetype="application/pdf"
        )
        
    except Exception as e:
        logger.exception(f"Error fetching document {file_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/applications", methods=["GET"])
def get_applications():
    try:
        logger.info("Fetching all applications")
        application_list = []
        for application in applications.find():
            application["id"] = str(application["_id"])
            del application["_id"]
            application_list.append(application)
        
        logger.info(f"Retrieved {len(application_list)} applications")
        return jsonify(application_list), 200
        
    except Exception as e:
        logger.exception(f"Error fetching applications: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/applications", methods=["POST"])
def add_application():
    temp_paths = []
    try:
        logger.debug(f"Received application request: {request.form.to_dict()}, files: {[f.filename for f in request.files.values()]}")
        if not request.form or not request.files:
            logger.error("Missing form data or files")
            return jsonify({"error": "Missing form data or files"}), 400

        required_fields = ["scholarship_id", "user_id", "student_name", "student_email", "age", "gender", "dob", "father_name", "mother_name", "annual_income", "status", "submitted_at"]
        application_data = {}
        for field in required_fields:
            if field not in request.form or not request.form[field]:
                logger.error(f"Missing or empty required field: {field}")
                return jsonify({"error": f"Missing or empty required field: {field}"}), 400
            application_data[field] = request.form[field]

        try:
            application_data["age"] = int(application_data["age"])
            application_data["annual_income"] = float(application_data["annual_income"])
        except ValueError as e:
            logger.error(f"Invalid numeric field format: {str(e)}")
            return jsonify({"error": "Age and annual income must be numeric"}), 400

        valid_statuses = ['pending', 'approved', 'rejected']
        if application_data["status"] not in valid_statuses:
            logger.error(f"Invalid status: {application_data['status']}")
            return jsonify({"error": f"Invalid status. Must be one of: {valid_statuses}"}), 400

        try:
            datetime.fromisoformat(application_data["dob"].replace("Z", "+00:00"))
        except ValueError:
            logger.error(f"Invalid DOB format: {application_data['dob']}")
            return jsonify({"error": "Invalid DOB format. Use ISO format (YYYY-MM-DD)"}), 400

        if not ObjectId.is_valid(application_data["scholarship_id"]):
            logger.error(f"Invalid scholarship ID: {application_data['scholarship_id']}")
            return jsonify({"error": "Invalid scholarship ID"}), 400
        scholarship = scholarships.find_one({"_id": ObjectId(application_data["scholarship_id"])})
        if not scholarship:
            logger.error(f"Scholarship not found: {application_data['scholarship_id']}")
            return jsonify({"error": "Scholarship not found"}), 404

        existing_application = applications.find_one({
            "user_id": application_data["user_id"],
            "scholarship_id": application_data["scholarship_id"]
        })
        if existing_application:
            logger.error(f"Duplicate application for user {application_data['user_id']} and scholarship {application_data['scholarship_id']}")
            return jsonify({"error": "User has already applied for this scholarship"}), 409

        documents = []
        for doc_name in scholarship["required_documents"]:
            if doc_name not in request.files:
                logger.error(f"Missing file for document: {doc_name}")
                return jsonify({"error": f"Missing file for document: {doc_name}"}), 400
            file = request.files[doc_name]
            if not file or file.filename == '':
                logger.error(f"Empty file for document: {doc_name}")
                return jsonify({"error": f"Empty file for document: {doc_name}"}), 400
            if not file.filename.lower().endswith('.pdf'):
                logger.error(f"Invalid file type for {doc_name}: {file.filename}")
                return jsonify({"error": f"File for {doc_name} must be a PDF"}), 400

            logger.debug(f"Saving temporary file for {doc_name}: {file.filename}")
            temp_path = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False).name
            file.seek(0)
            file.save(temp_path)
            temp_paths.append(temp_path)

            filename = secure_filename(file.filename)
            file.seek(0)
            logger.debug(f"Storing {filename} in GridFS")
            file_id = fs.put(file, filename=filename, metadata={"document_name": doc_name})
            documents.append({"name": doc_name, "file_id": str(file_id)})
            logger.info(f"Stored {doc_name} in GridFS with file_id: {file_id}")

        application_data["documents"] = documents
        application_data["status"] = "pending"
        application_data["verification_result"] = {}
        application_data["remarks"] = []

        logger.info("Inserting application with status 'pending' into MongoDB")
        result = applications.insert_one(application_data.copy())
        application_id = str(result.inserted_id)
        application_data["id"] = application_id
        logger.info(f"Application inserted with ID: {application_id}")

        user_data = {
            "student_name": application_data["student_name"],
            "dob": application_data["dob"],
            "father_name": application_data["father_name"],
            "mother_name": application_data["mother_name"],
            "annual_income": application_data["annual_income"],
            "age": application_data["age"]
        }

        try:
            logger.info("Preparing scholarship JSON for Gemini verification")
            scholarship_json = scholarship.copy()
            scholarship_json["id"] = str(scholarship["_id"])
            del scholarship_json["_id"]
            logger.debug(f"Scholarship JSON: {scholarship_json}")

            logger.info(f"Calling Gemini API for document verification with {len(temp_paths)} documents")
            verification_result = verifier.verify_scholarship_documents(scholarship_json, temp_paths, user_data)
            logger.info(f"Gemini verification result: {verification_result}")

            final_status = "approved" if verification_result["documentValid"] else "rejected"
            application_data["verification_result"] = verification_result
            application_data["remarks"] = verification_result["reasonForRejection"]
            application_data["status"] = final_status

            logger.info(f"Updating application {application_id} with verification result and status '{final_status}'")
            applications.update_one(
                {"_id": ObjectId(application_id)},
                {
                    "$set": {
                        "verification_result": verification_result,
                        "remarks": verification_result["reasonForRejection"],
                        "status": final_status
                    }
                }
            )

        except Exception as e:
            logger.exception(f"Document verification failed for application {application_id}: {str(e)}")
            verification_result = {
                "documentValid": False,
                "reasonForRejection": ["Document verification failed due to server error"]
            }
            application_data["verification_result"] = verification_result
            application_data["status"] = "pending"  # Keep pending for manual review
            application_data["remarks"] = []

            logger.info(f"Updating application {application_id} with verification failure and status 'pending'")
            applications.update_one(
                {"_id": ObjectId(application_id)},
                {
                    "$set": {
                        "verification_result": verification_result,
                        "remarks": [],
                        "status": "pending"
                    }
                }
            )
            return jsonify({"error": "Document verification failed due to server error. Application saved for manual review."}), 500

        return jsonify(application_data), 201

    except Exception as e:
        logger.exception(f"Error processing application: {str(e)}")
        return jsonify({"error": str(e)}), 500

    finally:
        for temp_path in temp_paths:
            if os.path.exists(temp_path):
                logger.debug(f"Cleaning up temporary file: {temp_path}")
                os.unlink(temp_path)

@app.route("/api/applications/user/<user_id>", methods=["GET"])
def get_applications_by_user(user_id):
    try:
        logger.debug(f"Fetching applications for user: {user_id}")
        if not isinstance(user_id, str) or not user_id.strip():
            logger.error(f"Invalid user ID: {user_id}")
            return jsonify({"error": "Invalid user ID"}), 400
            
        application_list = []
        for application in applications.find({"user_id": user_id}):
            application["id"] = str(application["_id"])
            del application["_id"]
            application_list.append(application)
        
        logger.info(f"Retrieved {len(application_list)} applications for user {user_id}")
        return jsonify(application_list), 200
        
    except Exception as e:
        logger.exception(f"Error fetching applications for user {user_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/applications/<id>", methods=["GET"])
def get_application(id):
    try:
        logger.debug(f"Fetching application with ID: {id}")
        if not ObjectId.is_valid(id):
            logger.error(f"Invalid application ID: {id}")
            return jsonify({"error": "Invalid application ID"}), 400
            
        application = applications.find_one({"_id": ObjectId(id)})
        if not application:
            logger.error(f"Application not found: {id}")
            return jsonify({"error": "Application not found"}), 404
            
        application["id"] = str(application["_id"])
        del application["_id"]
        logger.info(f"Retrieved application: {id}")
        return jsonify(application), 200
        
    except Exception as e:
        logger.exception(f"Error fetching application {id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/applications/scholarship/<scholarship_id>", methods=["GET"])
def get_applications_by_scholarship(scholarship_id):
    try:
        logger.debug(f"Fetching applications for scholarship: {scholarship_id}")
        if not ObjectId.is_valid(scholarship_id):
            logger.error(f"Invalid scholarship ID: {scholarship_id}")
            return jsonify({"error": "Invalid scholarship ID"}), 400
            
        if not scholarships.find_one({"_id": ObjectId(scholarship_id)}):
            logger.error(f"Scholarship not found: {scholarship_id}")
            return jsonify({"error": "Scholarship not found"}), 404
            
        application_list = []
        for application in applications.find({"scholarship_id": scholarship_id}):
            application["id"] = str(application["_id"])
            del application["_id"]
            application_list.append(application)
        
        logger.info(f"Retrieved {len(application_list)} applications for scholarship {scholarship_id}")
        return jsonify(application_list), 200
        
    except Exception as e:
        logger.exception(f"Error fetching applications for scholarship {scholarship_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/applications/user/<user_id>/scholarship/<scholarship_id>", methods=["GET"])
def check_user_application(user_id, scholarship_id):
    try:
        logger.debug(f"Checking application for user {user_id} and scholarship {scholarship_id}")
        if not isinstance(user_id, str) or not user_id.strip():
            logger.error(f"Invalid user ID: {user_id}")
            return jsonify({"error": "Invalid user ID"}), 400
        if not ObjectId.is_valid(scholarship_id):
            logger.error(f"Invalid scholarship ID: {scholarship_id}")
            return jsonify({"error": "Invalid scholarship ID"}), 400
            
        application = applications.find_one({
            "user_id": user_id,
            "scholarship_id": scholarship_id
        })
        
        if not application:
            logger.info(f"No application found for user {user_id} and scholarship {scholarship_id}")
            return jsonify({"hasApplied": False}), 200
            
        application["id"] = str(application["_id"])
        del application["_id"]
        logger.info(f"Found application for user {user_id} and scholarship {scholarship_id}")
        return jsonify({"hasApplied": True, "application": application}), 200
        
    except Exception as e:
        logger.exception(f"Error checking application for user {user_id} and scholarship {scholarship_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    logger.info("Starting Flask application")
    app.run(debug=True, host="0.0.0.0", port=5001)