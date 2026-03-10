from flask import Blueprint, jsonify, request
from services.expense_service import ExpenseService

expense_bp = Blueprint('expenses', __name__)

@expense_bp.route('/balances', methods=['GET'])
def get_balances():
    """Get all account balances."""
    try:
        service = ExpenseService.get_instance()
        balances = service.get_balances("local_user")
        return jsonify({"accounts": balances})
    except Exception as e:
        print(f"[EXPENSE] Balances endpoint error: {e}")
        return jsonify({"error": str(e)}), 500

@expense_bp.route('/recent', methods=['GET'])
def get_recent():
    """Get recent transactions with optional filters."""
    try:
        days = request.args.get('days', 7, type=int)
        account = request.args.get('account', None)
        category = request.args.get('category', None)
        limit = request.args.get('limit', 50, type=int)
        service = ExpenseService.get_instance()
        txns = service.list_transactions("local_user", days=days, account_name=account, category=category, limit=limit)
        return jsonify({"transactions": txns, "days": days})
    except Exception as e:
        print(f"[EXPENSE] Recent endpoint error: {e}")
        return jsonify({"error": str(e)}), 500

@expense_bp.route('/summary', methods=['GET'])
def get_summary():
    """Get spending summary."""
    try:
        period = request.args.get('period', 'weekly')
        service = ExpenseService.get_instance()
        summary = service.get_summary("local_user", period=period)
        return jsonify(summary)
    except Exception as e:
        print(f"[EXPENSE] Summary endpoint error: {e}")
        return jsonify({"error": str(e)}), 500

@expense_bp.route('/debts', methods=['GET'])
def get_debts():
    """Get outstanding debts with optional person filter."""
    try:
        person = request.args.get('person', None)
        service = ExpenseService.get_instance()
        debts = service.list_debts("local_user")
        if person:
            debts = [d for d in debts if person.lower() in d["person"].lower()]
        return jsonify({"debts": debts})
    except Exception as e:
        print(f"[EXPENSE] Debts endpoint error: {e}")
        return jsonify({"error": str(e)}), 500

@expense_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all categories."""
    try:
        service = ExpenseService.get_instance()
        cats = service.get_categories("local_user")
        return jsonify({"categories": cats})
    except Exception as e:
        print(f"[EXPENSE] Categories endpoint error: {e}")
        return jsonify({"error": str(e)}), 500

@expense_bp.route('/search', methods=['GET'])
def search():
    """Global search across transactions and debts."""
    try:
        q = request.args.get('q', '')
        if not q:
            return jsonify({"transactions": [], "debts": []})
        service = ExpenseService.get_instance()
        results = service.global_search("local_user", q)
        return jsonify(results)
    except Exception as e:
        print(f"[EXPENSE] Search endpoint error: {e}")
        return jsonify({"error": str(e)}), 500
