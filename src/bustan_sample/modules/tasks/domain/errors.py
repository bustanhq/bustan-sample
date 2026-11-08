from uuid import UUID


class TaskError(Exception):
    """The base class of the errors of the tasks domain."""


class TaskNotFoundError(TaskError):
    """No task has the given id."""

    def __init__(self, task_id: UUID) -> None:
        super().__init__(f"no task with id {task_id}")
        self.task_id = task_id


class InvalidTaskError(TaskError):
    """A value does not obey a rule of the task entity."""
