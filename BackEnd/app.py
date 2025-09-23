from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId, Binary
import os
from datetime import datetime
from dotenv import load_dotenv
import base64
from pdf_processor import PDFProcessor

# Load .env file BEFORE using os.getenv
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)

# More flexible CORS configuration
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    # Allow requests from Netlify, Cloudflare Pages, and localhost
    if origin and (
        origin.endswith('.netlify.app') or 
        origin.endswith('.pages.dev') or 
        origin == 'https://financepj.netlify.app' or
        origin == 'https://dev.finance-cpn.pages.dev' or
        origin.startswith('http://localhost')
    ):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "payslip_system")

if not MONGO_URI:
    raise ValueError("❌ Missing MONGO_URI in environment variables")

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")  # test connection
    print("✅ Connected to MongoDB successfully")
except Exception as e:
    print("❌ MongoDB connection failed:", str(e))
    raise e

db = client[DB_NAME]
payslips_collection = db["payslips"]

# Create indexes
payslips_collection.create_index([("accountNumber", 1)])
payslips_collection.create_index([("year", 1), ("month", 1)])
payslips_collection.create_index(
    [("accountNumber", 1), ("year", 1), ("month", 1)], unique=True
)

@app.route("/api/upload-slip", methods=["POST"])
def upload_slip():
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "ไม่พบไฟล์ที่อัปโหลด"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"success": False, "error": "ไม่ได้เลือกไฟล์"}), 400

        if not file.filename.lower().endswith(".pdf"):
            return jsonify({"success": False, "error": "กรุณาอัปโหลดไฟล์ PDF เท่านั้น"}), 400

        pdf_content = file.read()

        processor = PDFProcessor()
        extracted_slips = processor.process_pdf(pdf_content)

        inserted_count, updated_count = 0, 0

        for slip_data in extracted_slips:
            # Store PDF as Binary BSON type for MongoDB
            slip_data["pdfData"] = Binary(slip_data["pdfData"])
            slip_data["uploadedAt"] = datetime.utcnow()
            
            existing = payslips_collection.find_one({
                "accountNumber": slip_data["accountNumber"],
                "year": slip_data["year"],
                "month": slip_data["month"]
            })

            if existing:
                payslips_collection.update_one(
                    {"_id": existing["_id"]},
                    {"$set": slip_data}
                )
                updated_count += 1
            else:
                payslips_collection.insert_one(slip_data)
                inserted_count += 1

        return jsonify({
            "success": True,
            "message": f"อัปโหลดสำเร็จ: เพิ่มใหม่ {inserted_count} รายการ, อัปเดต {updated_count} รายการ",
            "inserted": inserted_count,
            "updated": updated_count,
            "total": len(extracted_slips)
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"เกิดข้อผิดพลาด: {str(e)}"}), 500


@app.route("/api/get-slip", methods=["POST"])
def get_slip():
    try:
        data = request.get_json(force=True)
        account = data.get("account")
        year = data.get("year")
        month = data.get("month")

        if not all([account, year, month]):
            return jsonify({"success": False, "error": "กรุณาระบุข้อมูลให้ครบถ้วน"}), 400

        slip = payslips_collection.find_one({
            "accountNumber": account,
            "year": str(year),
            "month": str(month).zfill(2)
        })

        if not slip:
            return jsonify({"success": False, "error": "ไม่พบสลิปเงินเดือน"}), 404

        if "pdfData" in slip:
            # Convert Binary/bytes to base64
            pdf_bytes = slip["pdfData"]
            if isinstance(pdf_bytes, Binary):
                pdf_bytes = bytes(pdf_bytes)
            
            pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
            
            return jsonify({
                "success": True,
                "pdfBase64": pdf_base64,
                "metadata": {
                    "name": slip.get("name", ""),
                    "rank": slip.get("rank", ""),
                    "accountNumber": slip.get("accountNumber", ""),
                    "year": slip.get("year", ""),
                    "month": slip.get("month", "")
                }
            })

        return jsonify({"success": False, "error": "ไม่พบข้อมูล PDF"}), 404

    except Exception as e:
        return jsonify({"success": False, "error": f"เกิดข้อผิดพลาด: {str(e)}"}), 500


@app.route("/api/available-months", methods=["GET"])
def get_available_months():
    try:
        pipeline = [
            {"$group": {"_id": {"year": "$year", "month": "$month"}}},
            {"$group": {"_id": "$_id.year", "months": {"$push": "$_id.month"}}},
            {"$sort": {"_id": -1}}
        ]

        results = list(payslips_collection.aggregate(pipeline))

        data = {}
        for item in results:
            year = item["_id"]
            months = sorted(item["months"])
            data[year] = months

        return jsonify({"success": True, "data": data})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/files/list", methods=["GET"])
def list_files():
    try:
        query = {}
        year = request.args.get("year")
        month = request.args.get("month")
        account = request.args.get("account")
        limit = int(request.args.get("limit", 100))

        if year:
            query["year"] = year
        if month:
            query["month"] = month
        if account:
            query["accountNumber"] = account

        files = list(payslips_collection.find(
            query,
            {"pdfData": 0}
        ).sort("uploadedAt", -1).limit(limit))

        for file in files:
            file["_id"] = str(file["_id"])
            if "uploadedAt" in file:
                file["uploadedAt"] = file["uploadedAt"].isoformat()

        return jsonify({"success": True, "files": files})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/files/delete", methods=["DELETE"])
def delete_file():
    try:
        file_id = request.args.get("file_id")
        account = request.args.get("account")
        year = request.args.get("year")
        month = request.args.get("month")

        if file_id:
            result = payslips_collection.delete_one({"_id": ObjectId(file_id)})
        elif all([account, year, month]):
            result = payslips_collection.delete_one({
                "accountNumber": account,
                "year": year,
                "month": month
            })
        else:
            return jsonify({"success": False, "error": "ต้องระบุ file_id หรือ account/year/month"}), 400

        if result.deleted_count > 0:
            return jsonify({"success": True, "message": "ลบไฟล์สำเร็จ"})
        else:
            return jsonify({"success": False, "error": "ไม่พบไฟล์"}), 404

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/search", methods=["POST"])
def search_slips():
    try:
        data = request.get_json(force=True)
        search_term = data.get("search", "")

        if not search_term:
            return jsonify({"success": False, "error": "กรุณาระบุคำค้นหา"}), 400

        query = {
            "$or": [
                {"name": {"$regex": search_term, "$options": "i"}},
                {"accountNumber": {"$regex": search_term, "$options": "i"}}
            ]
        }

        results = list(payslips_collection.find(
            query,
            {"pdfData": 0}
        ).sort("year", -1).limit(50))

        for result in results:
            result["_id"] = str(result["_id"])
            if "uploadedAt" in result:
                result["uploadedAt"] = result["uploadedAt"].isoformat()

        return jsonify({"success": True, "results": results})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def get_statistics():
    try:
        total_slips = payslips_collection.count_documents({})
        unique_accounts = len(payslips_collection.distinct("accountNumber"))

        stats = {
            "totalSlips": total_slips,
            "uniqueAccounts": unique_accounts
        }

        return jsonify({"success": True, "stats": stats})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    try:
        client.admin.command("ping")
        return jsonify({"status": "healthy", "message": "API and database are running"})
    except Exception:
        return jsonify({"status": "unhealthy", "message": "Database connection failed"}), 500
    

@app.route("/api/get-download-url", methods=["POST"])
def get_download_url():
    """Generate a download URL for the PDF"""
    try:
        data = request.get_json(force=True)
        account = data.get("account")
        year = data.get("year")
        month = data.get("month")

        if not all([account, year, month]):
            return jsonify({"success": False, "error": "กรุณาระบุข้อมูลให้ครบถ้วน"}), 400

        # Build the download URL
        download_url = f"{request.host_url}api/download-pdf?account={account}&year={year}&month={month}"

        return jsonify({
            "success": True,
            "downloadUrl": download_url
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/download-pdf", methods=["GET"])
def download_pdf():
    """Serve the PDF file for download"""
    try:
        account = request.args.get("account")
        year = request.args.get("year")
        month = request.args.get("month")

        if not all([account, year, month]):
            return jsonify({"success": False, "error": "กรุณาระบุข้อมูลให้ครบถ้วน"}), 400

        slip = payslips_collection.find_one({
            "accountNumber": account,
            "year": str(year),
            "month": str(month).zfill(2)
        })

        if not slip or "pdfData" not in slip:
            return jsonify({"success": False, "error": "ไม่พบสลิปเงินเดือน"}), 404

        # Create a file-like object from the PDF data
        pdf_io = io.BytesIO(slip["pdfData"])
        
        # Generate filename
        filename = f"slip_{account}_{month}_{year}.pdf"

        return send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
