from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
import os
from datetime import datetime
from dotenv import load_dotenv
import base64
from pdf_processor import PDFProcessor

app = Flask(__name__)
CORS(app)
load_dotenv()

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('DB_NAME', 'payslip_system')

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
payslips_collection = db['payslips']

# Create indexes for better query performance
payslips_collection.create_index([("accountNumber", 1)])
payslips_collection.create_index([("year", 1), ("month", 1)])
payslips_collection.create_index([("accountNumber", 1), ("year", 1), ("month", 1)], unique=True)

@app.route('/api/upload-slip', methods=['POST'])
def upload_slip():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'ไม่พบไฟล์ที่อัปโหลด'}), 400

        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'ไม่ได้เลือกไฟล์'}), 400

        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'กรุณาอัปโหลดไฟล์ PDF เท่านั้น'}), 400

        # Read PDF content
        pdf_content = file.read()
        
        # Process PDF to extract information and split pages
        processor = PDFProcessor()
        extracted_slips = processor.process_pdf(pdf_content)
        
        inserted_count = 0
        updated_count = 0
        
        for slip_data in extracted_slips:
            # Check if slip already exists
            existing = payslips_collection.find_one({
                'accountNumber': slip_data['accountNumber'],
                'year': slip_data['year'],
                'month': slip_data['month']
            })
            
            if existing:
                # Update existing document
                payslips_collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': slip_data}
                )
                updated_count += 1
            else:
                # Insert new document
                payslips_collection.insert_one(slip_data)
                inserted_count += 1
        
        return jsonify({
            'success': True,
            'message': f'อัปโหลดสำเร็จ: เพิ่มใหม่ {inserted_count} รายการ, อัปเดต {updated_count} รายการ',
            'inserted': inserted_count,
            'updated': updated_count,
            'total': len(extracted_slips)
        })
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

@app.route('/api/get-slip', methods=['POST'])
def get_slip():
    try:
        data = request.get_json()
        account = data.get('account')
        year = data.get('year')
        month = data.get('month')
        
        if not all([account, year, month]):
            return jsonify({'success': False, 'error': 'กรุณาระบุข้อมูลให้ครบถ้วน'}), 400
        
        # Find the slip in MongoDB
        slip = payslips_collection.find_one({
            'accountNumber': account,
            'year': str(year),
            'month': str(month).zfill(2)  # Ensure month is 2 digits
        })
        
        if not slip:
            return jsonify({'success': False, 'error': 'ไม่พบสลิปเงินเดือน'}), 404
        
        # Convert PDF binary to base64 for frontend display
        if 'pdfData' in slip:
            pdf_base64 = base64.b64encode(slip['pdfData']).decode('utf-8')
            pdf_data_url = f"data:application/pdf;base64,{pdf_base64}"
            
            return jsonify({
                'success': True,
                'pdfData': pdf_data_url,
                'metadata': {
                    'name': slip.get('name', ''),
                    'rank': slip.get('rank', '')
                }
            })
        
        return jsonify({'success': False, 'error': 'ไม่พบข้อมูล PDF'}), 404
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

@app.route('/api/available-months', methods=['GET'])
def get_available_months():
    try:
        # Get distinct year-month combinations
        pipeline = [
            {
                '$group': {
                    '_id': {
                        'year': '$year',
                        'month': '$month'
                    }
                }
            },
            {
                '$group': {
                    '_id': '$_id.year',
                    'months': {'$push': '$_id.month'}
                }
            },
            {
                '$sort': {'_id': -1}  # Sort years descending
            }
        ]
        
        results = list(payslips_collection.aggregate(pipeline))
        
        # Format the data
        data = {}
        for item in results:
            year = item['_id']
            months = sorted(item['months'])
            data[year] = months
        
        return jsonify({'success': True, 'data': data})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/list', methods=['GET'])
def list_files():
    try:
        # Get query parameters for filtering
        year = request.args.get('year')
        month = request.args.get('month')
        account = request.args.get('account')
        
        # Build query
        query = {}
        if year:
            query['year'] = year
        if month:
            query['month'] = month
        if account:
            query['accountNumber'] = account
        
        # Find documents (exclude PDF data for listing)
        files = list(payslips_collection.find(
            query,
            {'pdfData': 0}  # Exclude PDF binary data from results
        ).sort('uploadedAt', -1).limit(100))
        
        # Convert ObjectId to string for JSON serialization
        for file in files:
            file['_id'] = str(file['_id'])
        
        return jsonify({'success': True, 'files': files})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/delete', methods=['DELETE'])
def delete_file():
    try:
        file_id = request.args.get('file_id')
        account = request.args.get('account')
        year = request.args.get('year')
        month = request.args.get('month')
        
        if file_id:
            # Delete by ObjectId
            result = payslips_collection.delete_one({'_id': ObjectId(file_id)})
        elif all([account, year, month]):
            # Delete by account, year, month
            result = payslips_collection.delete_one({
                'accountNumber': account,
                'year': year,
                'month': month
            })
        else:
            return jsonify({'success': False, 'error': 'ต้องระบุ file_id หรือ account/year/month'}), 400
        
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'ลบไฟล์สำเร็จ'})
        else:
            return jsonify({'success': False, 'error': 'ไม่พบไฟล์'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/search', methods=['POST'])
def search_slips():
    """Search for slips by name or account number"""
    try:
        data = request.get_json()
        search_term = data.get('search', '')
        
        if not search_term:
            return jsonify({'success': False, 'error': 'กรุณาระบุคำค้นหา'}), 400
        
        # Search in name and account number fields
        query = {
            '$or': [
                {'name': {'$regex': search_term, '$options': 'i'}},
                {'accountNumber': {'$regex': search_term, '$options': 'i'}}
            ]
        }
        
        results = list(payslips_collection.find(
            query,
            {'pdfData': 0}  # Exclude PDF data
        ).sort('year', -1).limit(50))
        
        # Convert ObjectId to string
        for result in results:
            result['_id'] = str(result['_id'])
        
        return jsonify({'success': True, 'results': results})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """Get system statistics"""
    try:
        total_slips = payslips_collection.count_documents({})
        
        # Get unique accounts
        unique_accounts = len(payslips_collection.distinct('accountNumber'))
        
        stats = {
            'totalSlips': total_slips,
            'uniqueAccounts': unique_accounts
        }
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        # Check MongoDB connection
        client.admin.command('ping')
        return jsonify({'status': 'healthy', 'message': 'API and database are running'})
    except:
        return jsonify({'status': 'unhealthy', 'message': 'Database connection failed'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)