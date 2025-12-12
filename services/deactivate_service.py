

def deactivate_lecturer_by_id(lecturer_id, db_client):
    if not lecturer_id:
        return {"success": False, "message": "No ID provided"}

    users_ref = db_client.collection("users")
    docs = list(users_ref.where("lecturer_id", "==", lecturer_id).limit(1).get())
    if not docs:
        return {"success": False, "message": "User not found"}

    docs[0].reference.update({"is_active": False, "status": "inactive"})
    return {"success": True, "message": "User deactivated"}


def reactivate_lecturer_by_id(lecturer_id, db_client):
    if not lecturer_id:
        return {"success": False, "message": "No ID provided"}

    users_ref = db_client.collection("users")
    docs = list(users_ref.where("lecturer_id", "==", lecturer_id).limit(1).get())
    if not docs:
        return {"success": False, "message": "User not found"}

    docs[0].reference.update({"is_active": True, "status": "active"})
    return {"success": True, "message": "User reactivated"}


def deactivate_student_by_id(student_id, db_client):
    if not student_id:
        return {"success": False, "message": "No ID provided"}

    users_ref = db_client.collection("users")
    docs = list(users_ref.where("student_id", "==", student_id).limit(1).get())
    if not docs:
        return {"success": False, "message": "User not found"}

    docs[0].reference.update({"is_active": False, "status": "inactive"})
    return {"success": True, "message": "User deactivated"}


def reactivate_student_by_id(student_id, db_client):
    if not student_id:
        return {"success": False, "message": "No ID provided"}

    users_ref = db_client.collection("users")
    docs = list(users_ref.where("student_id", "==", student_id).limit(1).get())
    if not docs:
        return {"success": False, "message": "User not found"}

    docs[0].reference.update({"is_active": True, "status": "active"})
    return {"success": True, "message": "User reactivated"}
