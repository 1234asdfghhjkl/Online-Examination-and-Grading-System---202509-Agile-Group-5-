# services/user_service.py
from io import BytesIO
from typing import List, Dict, Any
import openpyxl
import hashlib 
from firebase_admin import auth, firestore, exceptions

# Assuming firebase_db is set up and contains the db object
from core.firebase_db import db 

# Define the password hashing key once. 
# Temporary key for this implementation, should be secure/env variable in production.
HASH_KEY = b"your_secret_admin_import_key_123456" 


def parse_excel_data(file_content: bytes, user_type: str) -> List[Dict[str, Any]]:
    """
    Parses the byte content of an Excel file into a list of user dictionaries.
    """
    try:
        workbook = openpyxl.load_workbook(BytesIO(file_content))
        sheet = workbook.active
        
        # Get headers (first row)
        headers = [cell.value.lower().strip() for cell in sheet[1]]
        
        # Define required headers based on user type
        if user_type == 'lecturer':
            required_headers = ['lecturer_id', 'ic', 'name', 'email', 'faculty']
        elif user_type == 'student':
            required_headers = ['student_id', 'ic', 'name', 'email', 'major', 'year', 'semester']
        else:
            raise ValueError(f"Invalid user type: {user_type}")

        # Basic check for all required columns
        if not all(h in headers for h in required_headers):
            missing = [h for h in required_headers if h not in headers]
            raise ValueError(f"Missing required columns for {user_type}: {', '.join(missing)}")

        users = []
        for row_index in range(2, sheet.max_row + 1):
            user_data = {}
            row_is_empty = True
            
            for col_index, header in enumerate(headers):
                value = sheet.cell(row=row_index, column=col_index + 1).value
                if value is not None:
                    row_is_empty = False
                
                # Convert ID, IC, and email to string to handle Excel cell types
                if 'id' in header or header == 'email' or header == 'ic':
                    if value is not None:
                         user_data[header] = str(value).strip()
                    else:
                        user_data[header] = None
                # Convert year and semester to integers
                elif header in ['year', 'semester']:
                    if value is not None:
                        try:
                            user_data[header] = int(value)
                        except (ValueError, TypeError):
                            user_data[header] = None
                    else:
                        user_data[header] = None
                else:
                    user_data[header] = value
            
            if not row_is_empty:
                # Basic validation for required fields
                is_valid = True
                for h in required_headers:
                    if user_data.get(h) is None or str(user_data.get(h)).strip() == "":
                        is_valid = False
                        break
                
                if is_valid:
                    # Clean up user_data keys
                    final_user_data = {k: user_data.get(k) for k in required_headers}
                    users.append(final_user_data)

        if not users:
            raise ValueError("No valid user records found in the Excel file.")
            
        return users

    except Exception as e:
        raise Exception(f"Failed to process Excel file: {str(e)}")


def bulk_create_users(users: List[Dict[str, Any]], user_type: str) -> Dict[str, int]:
    """
    Creates user accounts in Firebase Auth and profile documents in Firestore.
    """
    
    auth_records = []
    firestore_batch = db.batch()
    
    stats = {"total": len(users), "created": 0, "updated": 0, "failed": 0, "errors": []}
    
    # 1. Prepare Firebase Auth records
    for user in users:
        email = user['email']
        
        # Determine UID and ID field based on user type
        if user_type == 'lecturer':
            user_id = str(user['lecturer_id'])
            id_field = 'lecturer_id'
        else: # student
            user_id = str(user['student_id'])
            id_field = 'student_id'
            
        # Use IC as the password
        ic_number = str(user['ic'])
        
        # Hash the IC number for Firebase Auth
        hashed_password = hashlib.sha256(HASH_KEY + ic_number.encode('utf-8')).digest()
        
        # Create the ImportUserRecord
        auth_records.append(
            auth.ImportUserRecord(
                uid=user_id, 
                email=email, 
                display_name=user['name'],
                password_hash=hashed_password, 
            )
        )
        
        # Prepare Firestore data
        profile_data = {
            'uid': user_id, 
            'email': email,
            'name': user['name'],
            'role': user_type,
            'ic': ic_number,  # Store IC in Firestore
            'created_at': firestore.SERVER_TIMESTAMP,
            id_field: user_id, 
        }
        
        if user_type == 'student':
            profile_data['major'] = user['major']
            profile_data['year'] = user.get('year')
            profile_data['semester'] = user.get('semester')
        elif user_type == 'lecturer':
            profile_data['faculty'] = user.get('faculty')
        
        # Add profile document to batch using user_id as the document ID
        user_doc_ref = db.collection('users').document(user_id)
        firestore_batch.set(user_doc_ref, profile_data, merge=True)
        
    # 2. Bulk import to Firebase Auth (skip if accounts already exist)
    try:
        hash_config = auth.UserImportHash.hmac_sha256(key=HASH_KEY)
        results = auth.import_users(auth_records, hash_alg=hash_config)

        # Process results
        for i, result in enumerate(results.errors):
            # Auth import errors are OK if account already exists
            if "already exists" in str(result.reason).lower():
                stats['updated'] += 1
            else:
                stats['failed'] += 1
                stats['errors'].append(f"Row {i+2} ({users[i]['email']}): {result.reason}")
        
        stats['created'] = len(users) - stats['failed'] - stats['updated']

    except exceptions.FirebaseError:
        # If auth import fails, still try to update Firestore
        stats['updated'] = len(users)
        
    # 3. Commit Firestore profile data (this will update existing documents)
    try:
        firestore_batch.commit()
    except exceptions.FirebaseError as e:
        stats['failed'] = len(users)
        stats['errors'].append(f"Critical Firestore Batch Write Error: {str(e)}")
        
    return stats