from flask import Blueprint, request, jsonify
from services.task_service import TaskService

task_bp = Blueprint('tasks', __name__)

@task_bp.route('/', methods=['GET'])
def list_tasks():
    user_id = request.args.get('user_id', 'local_user')
    show_done = request.args.get('show_done', 'false').lower() == 'true'
    tasks = TaskService.get_instance().list_tasks(user_id, show_done=show_done)
    return jsonify({"tasks": tasks})

@task_bp.route('/', methods=['POST'])
def add_task():
    data = request.get_json()
    user_id = data.get('user_id', 'local_user')
    title = data.get('title', '')
    deadline = data.get('deadline')
    
    if not title:
        return jsonify({"error": "Title is required"}), 400
    
    task = TaskService.get_instance().add_task(user_id, title, deadline)
    return jsonify({"task": task}), 201

@task_bp.route('/<int:task_id>/done', methods=['PUT'])
def mark_task_done(task_id):
    user_id = request.args.get('user_id', 'local_user')
    result = TaskService.get_instance().mark_done(user_id, task_id=task_id)
    if result:
        return jsonify({"task": result})
    return jsonify({"error": "Task not found"}), 404

@task_bp.route('/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    user_id = request.args.get('user_id', 'local_user')
    result = TaskService.get_instance().delete_task(user_id, task_id=task_id)
    if result:
        return jsonify({"task": result})
    return jsonify({"error": "Task not found"}), 404
