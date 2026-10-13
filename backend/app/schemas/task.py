from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class TaskUserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str

    class Config:
        from_attributes = True


class TaskCommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class TaskCommentOut(BaseModel):
    id: int
    task_id: int
    user_id: Optional[int] = None
    author_name: str
    content: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    visibility: str = "WORKSPACE"  # WORKSPACE | PRIVATE
    priority: str = "MEDIUM"       # LOW | MEDIUM | HIGH | URGENT
    status: str = "TODO"           # TODO | IN_PROGRESS | WAITING | COMPLETED | CANCELLED
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None


class TaskCreate(TaskBase):
    project_id: Optional[int] = None
    assignee_ids: Optional[List[int]] = []
    assigned_to: Optional[str] = None  # Fallback/summary text


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    project_id: Optional[int] = None
    visibility: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    assignee_ids: Optional[List[int]] = None
    assigned_to: Optional[str] = None


class TaskOut(TaskBase):
    id: int
    project_id: Optional[int] = None
    project_title: Optional[str] = None
    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None
    assigned_to: Optional[str] = None
    assignees: List[TaskUserOut] = []
    comments_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskDetailOut(TaskOut):
    comments: List[TaskCommentOut] = []


class TaskStatsOut(BaseModel):
    total: int
    my_tasks: int
    assigned_to_me: int
    in_progress: int
    overdue: int
    completed: int
