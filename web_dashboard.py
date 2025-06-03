from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from interview_bot import InterviewNotificationBot
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Initialize bot
bot = InterviewNotificationBot()

@app.route('/')
def dashboard():
    """Main dashboard page"""
    try:
        # Get all candidates data
        data = bot.sheets_handler.get_all_data()
        if data is not None:
            candidates = data.to_dict('records')
            
            # Calculate statistics
            total = len(candidates)
            scheduled = len([c for c in candidates if c.get('Status') == 'Scheduled'])
            cleared = len([c for c in candidates if c.get('Status') == 'Cleared'])
            rejected = len([c for c in candidates if c.get('Status') == 'Rejected'])
            
            stats = {
                'total': total,
                'scheduled': scheduled,
                'cleared': cleared,
                'rejected': rejected
            }
        else:
            candidates = []
            stats = {'total': 0, 'scheduled': 0, 'cleared': 0, 'rejected': 0}
        
        return render_template('dashboard.html', candidates=candidates, stats=stats)
    except Exception as e:
        flash(f'Error loading dashboard: {e}', 'error')
        return render_template('dashboard.html', candidates=[], stats={})

@app.route('/api/send-notifications', methods=['POST'])
def send_notifications():
    """API endpoint to trigger notifications"""
    try:
        bot.process_notifications()
        return jsonify({'success': True, 'message': 'Notifications processed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/test-message', methods=['POST'])
def test_message():
    """API endpoint to send test message"""
    try:
        phone = request.json.get('phone')
        if not phone:
            return jsonify({'success': False, 'message': 'Phone number required'})
        
        success, result = bot.whatsapp_sender.send_test_message(phone)
        return jsonify({'success': success, 'message': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Create templates directory and basic HTML template
templates_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Interview Bot Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .stats { display: flex; gap: 20px; margin-bottom: 30px; }
        .stat-card { background: #f0f0f0; padding: 20px; border-radius: 8px; text-align: center; }
        .candidates-table { width: 100%; border-collapse: collapse; }
        .candidates-table th, .candidates-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .candidates-table th { background-color: #f2f2f2; }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        .btn:hover { background: #0056b3; }
    </style>
</head>
<body>
    <h1>Interview Notification Bot Dashboard</h1>
    
    <div class="stats">
        <div class="stat-card">
            <h3>{{ stats.total }}</h3>
            <p>Total Candidates</p>
        </div>
        <div class="stat-card">
            <h3>{{ stats.scheduled }}</h3>
            <p>Scheduled</p>
        </div>
        <div class="stat-card">
            <h3>{{ stats.cleared }}</h3>
            <p>Cleared</p>
        </div>
        <div class="stat-card">
            <h3>{{ stats.rejected }}</h3>
            <p>Rejected</p>
        </div>
    </div>
    
    <button class="btn" onclick="sendNotifications()">Send Pending Notifications</button>
    
    <h2>Candidates</h2>
    <table class="candidates-table">
        <thead>
            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Phone</th>
                <th>Current Round</th>
                <th>Status</th>
                <th>Interview Date</th>
                <th>Notification Sent</th>
            </tr>
        </thead>
        <tbody>
            {% for candidate in candidates %}
            <tr>
                <td>{{ candidate.Candidate_ID }}</td>
                <td>{{ candidate.Name }}</td>
                <td>{{ candidate.Phone }}</td>
                <td>{{ candidate.Current_Round }}</td>
                <td>{{ candidate.Status }}</td>
                <td>{{ candidate.Interview_Date }}</td>
                <td>{{ candidate.Notification_Sent }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <script>
        function sendNotifications() {
            fetch('/api/send-notifications', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    if (data.success) location.reload();
                });
        }
    </script>
</body>
</html>
"""

# Create templates directory and save HTML
# Create templates directory and save HTML
import os
os.makedirs('templates', exist_ok=True)
with open('templates/dashboard.html', 'w', encoding='utf-8') as f:  # 👈 fixed
    f.write(templates_html)


if __name__ == '__main__':
    print("🌐 Starting web dashboard at http://localhost:5000")
    app.run(debug=True, port=5000)
