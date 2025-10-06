# app/websockets/__init__.py
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request
import logging
from app.monitoring import AdvancedLogger
from app.tasks import celery
from app.models import db, Keyword, SearchResult
import json
from datetime import datetime

logger = AdvancedLogger('websockets')
socketio = SocketIO(cors_allowed_origins="*")


class RealTimeDashboard:
    def __init__(self):
        self.active_connections = {}
        self.room_subscriptions = {}

    def init_app(self, app):
        """Initialize WebSocket with Flask app"""
        socketio.init_app(app)
        self.setup_handlers()

    def setup_handlers(self):
        """Setup WebSocket event handlers"""

        @socketio.on('connect')
        def handle_connect():
            """Handle new client connection"""
            client_id = request.sid
            self.active_connections[client_id] = {
                'connected_at': datetime.utcnow(),
                'rooms': set(),
                'user_agent': request.headers.get('User-Agent', 'Unknown')
            }

            logger.logger.info(f"Client connected: {client_id}")
            emit('connection_established', {
                'message': 'Connected to real-time dashboard',
                'client_id': client_id,
                'timestamp': datetime.utcnow().isoformat()
            })

        @socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            client_id = request.sid
            if client_id in self.active_connections:
                # Leave all rooms
                for room in self.active_connections[client_id]['rooms']:
                    self.leave_room(client_id, room)

                del self.active_connections[client_id]

            logger.logger.info(f"Client disconnected: {client_id}")

        @socketio.on('join_room')
        def handle_join_room(data):
            """Handle client joining a room"""
            room = data.get('room')
            client_id = request.sid

            if room:
                self.join_room(client_id, room)
                emit('room_joined', {
                    'room': room,
                    'message': f'Joined room: {room}',
                    'timestamp': datetime.utcnow().isoformat()
                })

        @socketio.on('leave_room')
        def handle_leave_room(data):
            """Handle client leaving a room"""
            room = data.get('room')
            client_id = request.sid

            if room:
                self.leave_room(client_id, room)
                emit('room_left', {
                    'room': room,
                    'message': f'Left room: {room}',
                    'timestamp': datetime.utcnow().isoformat()
                })

        @socketio.on('subscribe_scraping_updates')
        def handle_scraping_subscription(data):
            """Subscribe to scraping progress updates"""
            keyword_id = data.get('keyword_id')
            client_id = request.sid

            if keyword_id:
                room = f'scraping_{keyword_id}'
                self.join_room(client_id, room)

                # Send current status if available
                keyword = Keyword.query.get(keyword_id)
                if keyword:
                    emit('scraping_status', {
                        'keyword_id': keyword_id,
                        'status': keyword.status,
                        'progress': self.get_scraping_progress(keyword_id),
                        'timestamp': datetime.utcnow().isoformat()
                    })

        @socketio.on('request_system_stats')
        def handle_system_stats_request():
            """Handle system stats request"""
            client_id = request.sid
            self.send_system_stats(client_id)

    def join_room(self, client_id, room):
        """Join a client to a room"""
        join_room(room)

        if client_id in self.active_connections:
            self.active_connections[client_id]['rooms'].add(room)

        # Initialize room subscriptions
        if room not in self.room_subscriptions:
            self.room_subscriptions[room] = set()
        self.room_subscriptions[room].add(client_id)

        logger.logger.info(f"Client {client_id} joined room: {room}")

    def leave_room(self, client_id, room):
        """Remove a client from a room"""
        leave_room(room)

        if client_id in self.active_connections:
            self.active_connections[client_id]['rooms'].discard(room)

        if room in self.room_subscriptions:
            self.room_subscriptions[room].discard(client_id)
            if not self.room_subscriptions[room]:
                del self.room_subscriptions[room]

        logger.logger.info(f"Client {client_id} left room: {room}")

    def broadcast_to_room(self, room, event, data):
        """Broadcast data to all clients in a room"""
        socketio.emit(event, data, room=room, namespace='/')

    def send_system_stats(self, client_id=None):
        """Send system statistics to client(s)"""
        stats = self.get_system_statistics()

        if client_id:
            emit('system_stats', stats, room=client_id)
        else:
            self.broadcast_to_room('system_monitoring', 'system_stats', stats)

    def get_system_statistics(self):
        """Get current system statistics"""
        from app.monitoring import PerformanceMonitor

        monitor = PerformanceMonitor()
        performance_data = monitor.get_performance_report()

        # Get task queue status
        inspector = celery.control.inspect()
        active_tasks = inspector.active() or {}

        stats = {
            'timestamp': datetime.utcnow().isoformat(),
            'system': {
                'cpu_usage': performance_data.get('system', {}).get('cpu_percent', 0),
                'memory_usage': performance_data.get('system', {}).get('memory_percent', 0),
                'active_connections': len(self.active_connections),
                'active_rooms': len(self.room_subscriptions)
            },
            'application': {
                'total_keywords': Keyword.query.count(),
                'total_results': SearchResult.query.count(),
                'pending_scrapes': Keyword.query.filter_by(status='pending').count(),
                'active_scrapes': Keyword.query.filter_by(status='in_progress').count()
            },
            'tasks': {
                'active_tasks': sum(len(tasks) for tasks in active_tasks.values()),
                'queues': {
                    'scraping': len(active_tasks.get('scraping', [])),
                    'analysis': len(active_tasks.get('analysis', [])),
                    'reporting': len(active_tasks.get('reporting', [])),
                    'maintenance': len(active_tasks.get('maintenance', []))
                }
            }
        }

        return stats

    def get_scraping_progress(self, keyword_id):
        """Get scraping progress for a keyword"""
        keyword = Keyword.query.get(keyword_id)
        if not keyword:
            return {'progress': 0, 'status': 'unknown'}

        # This would be more sophisticated in a real implementation
        # For now, return basic progress based on status
        progress_map = {
            'pending': 0,
            'in_progress': 50,
            'completed': 100,
            'error': 0
        }

        return {
            'progress': progress_map.get(keyword.status, 0),
            'status': keyword.status,
            'results_count': keyword.total_results or 0
        }

    def start_background_updates(self):
        """Start background task for real-time updates"""
        import threading
        import time

        def background_updater():
            while True:
                try:
                    # Send system stats to system monitoring room
                    self.send_system_stats()

                    # Send scraping updates to relevant rooms
                    self.update_scraping_progress()

                    time.sleep(5)  # Update every 5 seconds

                except Exception as e:
                    logger.logger.error(f"Background updater error: {e}")
                    time.sleep(30)  # Wait longer on error

        thread = threading.Thread(target=background_updater, daemon=True)
        thread.start()

    def update_scraping_progress(self):
        """Update scraping progress for all active scraping rooms"""
        for room in list(self.room_subscriptions.keys()):
            if room.startswith('scraping_'):
                keyword_id = room.replace('scraping_', '')
                progress = self.get_scraping_progress(keyword_id)

                self.broadcast_to_room(room, 'scraping_progress', {
                    'keyword_id': keyword_id,
                    'progress': progress,
                    'timestamp': datetime.utcnow().isoformat()
                })


# Global instance
realtime_dashboard = RealTimeDashboard()