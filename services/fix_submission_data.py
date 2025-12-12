"""
Data Repair Script
Fixes corrupted MCQ score data in submissions
Run this once to repair existing data

Usage:
    python fix_submission_data.py
"""

from core.firebase_db import db


def fix_all_submissions():
    """
    Fix MCQ score data for all submissions where mcq_score might be wrong
    """
    print("🔧 Starting submission data repair...")
    
    # Get all submissions
    submissions_ref = db.collection("submissions").stream()
    
    fixed_count = 0
    checked_count = 0
    
    for doc in submissions_ref:
        checked_count += 1
        submission_id = doc.id
        data = doc.to_dict()
        
        # Get the grading result which has the correct data
        grading_result = data.get("grading_result", {})
        
        if not grading_result:
            print(f"⚠️  Submission {submission_id}: No grading result found, skipping")
            continue
        
        # Get correct values from grading_result
        correct_obtained = grading_result.get("obtained_marks", 0)
        correct_total = grading_result.get("total_marks", 0)
        correct_percentage = grading_result.get("percentage", 0)
        
        # Get current values
        current_score = data.get("mcq_score", 0)
        current_total = data.get("mcq_total", 0)
        
        # Check if data is corrupted (mcq_score equals mcq_total but percentage is 0)
        is_corrupted = (
            current_score == current_total and 
            current_score > 0 and 
            data.get("overall_percentage", 100) == 0
        )
        
        # Or check if mcq_score doesn't match obtained_marks from grading_result
        is_mismatched = current_score != correct_obtained
        
        if is_corrupted or is_mismatched:
            print(f"\n🔍 Found issue in submission {submission_id}:")
            print(f"   Student: {data.get('student_id')}")
            print(f"   Current mcq_score: {current_score} (WRONG)")
            print(f"   Should be: {correct_obtained} (from grading_result)")
            
            # Calculate correct overall scores
            sa_obtained = data.get("sa_obtained_marks", 0)
            sa_total = data.get("sa_total_marks", 0)
            
            overall_total = correct_total + sa_total
            overall_obtained = correct_obtained + sa_obtained
            overall_percentage = (
                (overall_obtained / overall_total * 100) if overall_total > 0 else 0
            )
            
            # Fix the data
            update_data = {
                "mcq_score": correct_obtained,
                "mcq_total": correct_total,
                "mcq_percentage": correct_percentage,
                "overall_obtained_marks": overall_obtained,
                "overall_total_marks": overall_total,
                "overall_percentage": round(overall_percentage, 2),
            }
            
            doc.reference.update(update_data)
            fixed_count += 1
            
            print("   ✅ FIXED!")
            print(f"   New mcq_score: {correct_obtained}")
            print(f"   New overall_percentage: {round(overall_percentage, 2)}%")
        else:
            print(f"✓ Submission {submission_id}: OK")
    
    print(f"\n{'='*60}")
    print("📊 Summary:")
    print(f"   Total submissions checked: {checked_count}")
    print(f"   Submissions fixed: {fixed_count}")
    print(f"   Submissions OK: {checked_count - fixed_count}")
    print(f"{'='*60}")


def fix_specific_submission(submission_id: str):
    """
    Fix a specific submission by ID
    
    Args:
        submission_id: The submission document ID
    """
    print(f"🔧 Fixing submission: {submission_id}")
    
    doc_ref = db.collection("submissions").document(submission_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        print(f"❌ Submission {submission_id} not found!")
        return
    
    data = doc.to_dict()
    grading_result = data.get("grading_result", {})
    
    if not grading_result:
        print("❌ No grading result found for this submission!")
        return
    
    # Get correct values
    correct_obtained = grading_result.get("obtained_marks", 0)
    correct_total = grading_result.get("total_marks", 0)
    correct_percentage = grading_result.get("percentage", 0)
    
    # Calculate correct overall scores
    sa_obtained = data.get("sa_obtained_marks", 0)
    sa_total = data.get("sa_total_marks", 0)
    
    overall_total = correct_total + sa_total
    overall_obtained = correct_obtained + sa_obtained
    overall_percentage = (
        (overall_obtained / overall_total * 100) if overall_total > 0 else 0
    )
    
    print("\n📋 Current values:")
    print(f"   mcq_score: {data.get('mcq_score')}")
    print(f"   mcq_total: {data.get('mcq_total')}")
    print(f"   overall_percentage: {data.get('overall_percentage')}%")
    
    print("\n✅ Correct values (from grading_result):")
    print(f"   mcq_score: {correct_obtained}")
    print(f"   mcq_total: {correct_total}")
    print(f"   overall_percentage: {round(overall_percentage, 2)}%")
    
    # Fix the data
    update_data = {
        "mcq_score": correct_obtained,
        "mcq_total": correct_total,
        "mcq_percentage": correct_percentage,
        "overall_obtained_marks": overall_obtained,
        "overall_total_marks": overall_total,
        "overall_percentage": round(overall_percentage, 2),
    }
    
    doc_ref.update(update_data)
    print(f"\n✅ Submission {submission_id} has been fixed!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Fix specific submission
        submission_id = sys.argv[1]
        fix_specific_submission(submission_id)
    else:
        # Fix all submissions
        fix_all_submissions()