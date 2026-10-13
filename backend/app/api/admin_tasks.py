from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, or_, and_

try:
    from app.database.session import get_db
    from app.models.task import Task, TaskAssignment, TaskComment
    from app.models.project import Project
    from app.models.user import User, UserRole
    from app.schemas.task import (
        TaskCreate,
        TaskUpdate,
        TaskOut,
        TaskDetailOut,
        TaskStatsOut,
        TaskUserOut,
        TaskCommentCreate,
        TaskCommentOut,
    )
    from app.core.dependencies import get_current_user, require_roles, log_activity
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.task import Task, TaskAssignment, TaskComment
    from backend.app.models.project import Project
    from backend.app.models.user import User, UserRole
    from backend.app.schemas.task import (
        TaskCreate,
        TaskUpdate,
        TaskOut,
        TaskDetailOut,
        TaskStatsOut,
        TaskUserOut,
        TaskCommentCreate,
        TaskCommentOut,
    )
    from backend.app.core.dependencies import get_current_user, require_roles, log_activity

router = APIRouter(prefix="/admin/tasks", tags=["Admin Tasks"])


def is_executive_user(user: User) -> bool:
    """Check if the user has executive / administrative clearance."""
    role = (user.role or "").upper()
    return role in (UserRole.MASTER.value, UserRole.OWNER.value, UserRole.ADMIN.value)


def apply_task_visibility_filter(query, current_user: User, db: Session):
    """
    Enforces task visibility strictly at the database query level:
    - Executive administrators can see all tasks (WORKSPACE and PRIVATE).
    - Other active studio members can see:
        1. WORKSPACE tasks.
        2. PRIVATE tasks they created.
        3. PRIVATE tasks they are assigned to.
    """
    if is_executive_user(current_user):
        return query

    # Subquery for tasks assigned to current user
    assigned_task_ids = db.query(TaskAssignment.task_id).filter(TaskAssignment.user_id == current_user.id).subquery()

    return query.filter(
        or_(
            Task.visibility == "WORKSPACE",
            Task.created_by_id == current_user.id,
            Task.id.in_(assigned_task_ids.select()),
            # Fallback legacy username matching
            func.lower(Task.assigned_to) == current_user.username.lower()
        )
    )


def check_task_access(task: Task, current_user: User, db: Session) -> bool:
    """Check if current user is authorized to view a specific task."""
    if is_executive_user(current_user):
        return True
    if task.visibility == "WORKSPACE":
        return True
    if task.created_by_id == current_user.id:
        return True
    
    # Check if user is in assignments
    for a in task.assignments:
        if a.user_id == current_user.id:
            return True
            
    if task.assigned_to and task.assigned_to.strip().lower() == current_user.username.lower():
        return True

    return False


def build_task_out(task: Task) -> TaskOut:
    """Helper to convert Task model to TaskOut schema with assignees and project title."""
    project_title = task.project.title if task.project else "Studio Task"
    created_by_name = task.created_by.username if task.created_by else None

    assignees_out: List[TaskUserOut] = []
    for assign in task.assignments:
        if assign.user:
            assignees_out.append(
                TaskUserOut(
                    id=assign.user.id,
                    username=assign.user.username,
                    email=assign.user.email,
                    role=assign.user.role
                )
            )

    return TaskOut(
        id=task.id,
        project_id=task.project_id,
        project_title=project_title,
        created_by_id=task.created_by_id,
        created_by_name=created_by_name,
        title=task.title,
        description=task.description,
        assigned_to=task.assigned_to,
        visibility=task.visibility or "WORKSPACE",
        priority=task.priority or "MEDIUM",
        status=task.status or "TODO",
        start_date=task.start_date,
        due_date=task.due_date,
        assignees=assignees_out,
        comments_count=len(task.comments) if task.comments else 0,
        created_at=task.created_at,
        updated_at=task.updated_at
    )


# ============================================================================
# 1. ASSIGNEES / REGISTERED TEAM MEMBERS LIST
# ============================================================================

@router.get("/assignees", response_model=List[TaskUserOut], summary="List active registered studio users for task assignment")
def list_task_assignees(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns all active registered users so any authorized studio member can assign tasks to teammates.
    """
    users = db.query(User).filter(User.is_active == True).order_by(User.username.asc()).all()
    return [
        TaskUserOut(
            id=u.id,
            username=u.username,
            email=u.email,
            role=u.role
        )
        for u in users
    ]


# ============================================================================
# 2. TASK OVERVIEW STATISTICS
# ============================================================================

@router.get("/stats", response_model=TaskStatsOut, summary="Get studio task statistics based on user visibility")
def get_task_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns real computed task statistics matching the current user's visibility permissions.
    """
    base_query = db.query(Task)
    visible_query = apply_task_visibility_filter(base_query, current_user, db)

    now = datetime.utcnow()

    # Subquery for tasks assigned to current user
    assigned_task_ids = db.query(TaskAssignment.task_id).filter(TaskAssignment.user_id == current_user.id).subquery()

    total = visible_query.count()

    my_tasks = visible_query.filter(
        or_(
            Task.created_by_id == current_user.id,
            Task.id.in_(assigned_task_ids.select()),
            func.lower(Task.assigned_to) == current_user.username.lower()
        )
    ).count()

    assigned_to_me = visible_query.filter(
        or_(
            Task.id.in_(assigned_task_ids.select()),
            func.lower(Task.assigned_to) == current_user.username.lower()
        )
    ).count()

    in_progress = visible_query.filter(Task.status.in_(["IN_PROGRESS", "TODO"])).count()

    completed = visible_query.filter(Task.status == "COMPLETED").count()

    overdue = visible_query.filter(
        Task.status.notin_(["COMPLETED", "CANCELLED"]),
        Task.due_date.isnot(None),
        Task.due_date < now
    ).count()

    return TaskStatsOut(
        total=total,
        my_tasks=my_tasks,
        assigned_to_me=assigned_to_me,
        in_progress=in_progress,
        overdue=overdue,
        completed=completed
    )


# ============================================================================
# 3. LIST & SEARCH TASKS
# ============================================================================

@router.get("", response_model=List[TaskOut], summary="List and filter tasks")
def list_tasks(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    visibility: Optional[str] = None,
    assigned_to: Optional[str] = None,
    assignee_id: Optional[int] = None,
    created_by_id: Optional[int] = None,
    search: Optional[str] = None,
    view: Optional[str] = Query(None, description="View filter: all, my_tasks, assigned_to_me, workspace, private, overdue, completed"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Task).outerjoin(Project, Task.project_id == Project.id)
    query = apply_task_visibility_filter(query, current_user, db)

    # Apply View presets
    now = datetime.utcnow()
    assigned_sub = db.query(TaskAssignment.task_id).filter(TaskAssignment.user_id == current_user.id).subquery()

    if view == "my_tasks":
        query = query.filter(
            or_(
                Task.created_by_id == current_user.id,
                Task.id.in_(assigned_sub),
                func.lower(Task.assigned_to) == current_user.username.lower()
            )
        )
    elif view == "assigned_to_me":
        query = query.filter(
            or_(
                Task.id.in_(assigned_sub),
                func.lower(Task.assigned_to) == current_user.username.lower()
            )
        )
    elif view == "workspace":
        query = query.filter(Task.visibility == "WORKSPACE")
    elif view == "private":
        query = query.filter(Task.visibility == "PRIVATE")
    elif view == "overdue":
        query = query.filter(
            Task.status.notin_(["COMPLETED", "CANCELLED"]),
            Task.due_date.isnot(None),
            Task.due_date < now
        )
    elif view == "completed":
        query = query.filter(Task.status == "COMPLETED")

    # Filters
    if project_id is not None:
        if project_id == 0:
            query = query.filter(Task.project_id.is_(None))
        else:
            query = query.filter(Task.project_id == project_id)
            
    if status and status.upper() != "ALL":
        query = query.filter(Task.status == status.upper())
        
    if priority and priority.upper() != "ALL":
        query = query.filter(Task.priority == priority.upper())
        
    if visibility and visibility.upper() != "ALL":
        query = query.filter(Task.visibility == visibility.upper())

    if created_by_id is not None:
        query = query.filter(Task.created_by_id == created_by_id)

    if assignee_id is not None:
        sub = db.query(TaskAssignment.task_id).filter(TaskAssignment.user_id == assignee_id).subquery()
        query = query.filter(Task.id.in_(sub))

    if assigned_to and assigned_to.strip():
        clean_assigned = assigned_to.strip().lower()
        matched_user = db.query(User).filter(func.lower(User.username) == clean_assigned).first()
        if matched_user:
            sub = db.query(TaskAssignment.task_id).filter(TaskAssignment.user_id == matched_user.id).subquery()
            query = query.filter(or_(Task.id.in_(sub), func.lower(Task.assigned_to) == clean_assigned))
        else:
            query = query.filter(func.lower(Task.assigned_to) == clean_assigned)

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(Task.title).like(term),
                func.lower(Task.description).like(term)
            )
        )

    tasks = query.order_by(
        case(
            (Task.status == "TODO", 1),
            (Task.status == "IN_PROGRESS", 2),
            (Task.status == "WAITING", 3),
            (Task.status == "COMPLETED", 4),
            (Task.status == "CANCELLED", 5),
            else_=6
        ),
        Task.due_date.asc().nullslast(),
        Task.id.desc()
    ).all()

    return [build_task_out(t) for t in tasks]


# ============================================================================
# 4. GET SINGLE TASK DETAIL
# ============================================================================

@router.get("/{task_id}", response_model=TaskDetailOut, summary="Get detailed task with comments")
def get_task_detail(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not check_task_access(task, current_user, db):
        raise HTTPException(status_code=403, detail="Access denied: You do not have permission to view this private task.")

    base_out = build_task_out(task)

    comments_out: List[TaskCommentOut] = []
    for c in task.comments:
        comments_out.append(
            TaskCommentOut(
                id=c.id,
                task_id=c.task_id,
                user_id=c.user_id,
                author_name=c.author_name,
                content=c.content,
                created_at=c.created_at
            )
        )

    return TaskDetailOut(
        **base_out.dict(),
        comments=comments_out
    )


# ============================================================================
# 5. CREATE TASK
# ============================================================================

@router.post("", response_model=TaskOut, summary="Create a new task")
def create_task(
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify project if provided
    project_title = "Studio Task"
    if payload.project_id:
        project = db.query(Project).filter(Project.id == payload.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail=f"Project ID {payload.project_id} not found")
        project_title = project.title

    visibility = (payload.visibility or "WORKSPACE").upper()
    if visibility not in ("WORKSPACE", "PRIVATE"):
        visibility = "WORKSPACE"

    priority = (payload.priority or "MEDIUM").upper()
    status_val = (payload.status or "TODO").upper()

    task = Task(
        project_id=payload.project_id if payload.project_id else None,
        created_by_id=current_user.id,
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
        visibility=visibility,
        priority=priority,
        status=status_val,
        start_date=payload.start_date,
        due_date=payload.due_date,
        assigned_to=payload.assigned_to.strip() if payload.assigned_to else None
    )
    db.add(task)
    db.flush()

    # Assign users
    assignee_names: List[str] = []
    if payload.assignee_ids:
        # Validate users
        valid_users = db.query(User).filter(
            User.id.in_(payload.assignee_ids),
            User.is_active == True
        ).all()

        for u in valid_users:
            assignment = TaskAssignment(task_id=task.id, user_id=u.id)
            db.add(assignment)
            assignee_names.append(u.username)

    if assignee_names:
        task.assigned_to = ", ".join(assignee_names)
    elif not task.assigned_to:
        task.assigned_to = current_user.username

    db.commit()
    db.refresh(task)

    log_activity(
        db,
        current_user,
        action="Created Task",
        entity_type="task",
        entity_id=str(task.id),
        details=f"Task '{task.title}' [{task.visibility}] for '{project_title}'"
    )

    return build_task_out(task)


# ============================================================================
# 6. UPDATE TASK
# ============================================================================

@router.put("/{task_id}", response_model=TaskOut, summary="Update task details and assignments")
def update_task(
    task_id: int,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not check_task_access(task, current_user, db):
        raise HTTPException(status_code=403, detail="Access denied: You do not have permission to modify this private task.")

    if payload.title is not None:
        clean_title = payload.title.strip()
        if clean_title:
            task.title = clean_title

    if payload.description is not None:
        task.description = payload.description.strip() if payload.description else None

    if payload.project_id is not None:
        if payload.project_id == 0:
            task.project_id = None
        else:
            proj = db.query(Project).filter(Project.id == payload.project_id).first()
            if not proj:
                raise HTTPException(status_code=404, detail="Target project not found")
            task.project_id = payload.project_id

    if payload.visibility is not None:
        vis = payload.visibility.upper()
        if vis in ("WORKSPACE", "PRIVATE"):
            task.visibility = vis

    if payload.priority is not None:
        task.priority = payload.priority.upper()

    if payload.status is not None:
        task.status = payload.status.upper()

    if payload.start_date is not None:
        task.start_date = payload.start_date

    if payload.due_date is not None:
        task.due_date = payload.due_date

    # Sync Assignees
    if payload.assignee_ids is not None:
        # Remove existing assignments
        db.query(TaskAssignment).filter(TaskAssignment.task_id == task.id).delete()
        
        valid_users = db.query(User).filter(
            User.id.in_(payload.assignee_ids),
            User.is_active == True
        ).all()

        assignee_names = []
        for u in valid_users:
            assignment = TaskAssignment(task_id=task.id, user_id=u.id)
            db.add(assignment)
            assignee_names.append(u.username)

        task.assigned_to = ", ".join(assignee_names) if assignee_names else None
    elif payload.assigned_to is not None:
        task.assigned_to = payload.assigned_to.strip() if payload.assigned_to else None

    db.commit()
    db.refresh(task)

    log_activity(
        db,
        current_user,
        action="Updated Task",
        entity_type="task",
        entity_id=str(task.id),
        details=f"Task '{task.title}' updated (Status: {task.status}, Priority: {task.priority})"
    )

    return build_task_out(task)


# ============================================================================
# 7. STATUS TOGGLE
# ============================================================================

@router.patch("/{task_id}/status", summary="Update task status")
def toggle_task_status(
    task_id: int,
    status: str = Query(..., description="Target status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not check_task_access(task, current_user, db):
        raise HTTPException(status_code=403, detail="Access denied.")

    new_status = status.upper()
    valid_statuses = ["TODO", "IN_PROGRESS", "WAITING", "COMPLETED", "CANCELLED"]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    task.status = new_status
    db.commit()

    log_activity(
        db,
        current_user,
        action=f"Task marked as {new_status}",
        entity_type="task",
        entity_id=str(task.id),
        details=f"'{task.title}' -> {new_status}"
    )

    return {"success": True, "id": task.id, "status": task.status}


# ============================================================================
# 8. DELETE TASK
# ============================================================================

@router.delete("/{task_id}", summary="Delete task")
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    is_exec = is_executive_user(current_user)
    is_creator = task.created_by_id == current_user.id

    if not (is_exec or is_creator):
        raise HTTPException(status_code=403, detail="Access denied: Only administrators or the task creator can delete this task.")

    title = task.title
    db.delete(task)
    db.commit()

    log_activity(
        db,
        current_user,
        action="Deleted Task",
        entity_type="task",
        entity_id=str(task_id),
        details=f"Deleted task '{title}'"
    )

    return {"success": True, "message": f"Task '{title}' deleted."}


# ============================================================================
# 9. TASK COMMENTS
# ============================================================================

@router.get("/{task_id}/comments", response_model=List[TaskCommentOut], summary="Get task discussion comments")
def get_task_comments(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not check_task_access(task, current_user, db):
        raise HTTPException(status_code=403, detail="Access denied.")

    comments = db.query(TaskComment).filter(TaskComment.task_id == task_id).order_by(TaskComment.created_at.asc()).all()
    return [
        TaskCommentOut(
            id=c.id,
            task_id=c.task_id,
            user_id=c.user_id,
            author_name=c.author_name,
            content=c.content,
            created_at=c.created_at
        )
        for c in comments
    ]


@router.post("/{task_id}/comments", response_model=TaskCommentOut, summary="Add a comment or discussion to a task")
def add_task_comment(
    task_id: int,
    payload: TaskCommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not check_task_access(task, current_user, db):
        raise HTTPException(status_code=403, detail="Access denied.")

    clean_content = payload.content.strip()
    if not clean_content:
        raise HTTPException(status_code=400, detail="Comment cannot be empty.")

    comment = TaskComment(
        task_id=task.id,
        user_id=current_user.id,
        author_name=current_user.username,
        content=clean_content
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    log_activity(
        db,
        current_user,
        action="Task Comment Added",
        entity_type="task",
        entity_id=str(task.id),
        details=f"Comment on '{task.title}' by {current_user.username}"
    )

    return TaskCommentOut(
        id=comment.id,
        task_id=comment.task_id,
        user_id=comment.user_id,
        author_name=comment.author_name,
        content=comment.content,
        created_at=comment.created_at
    )
