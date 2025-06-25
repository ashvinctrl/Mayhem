import os
import logging
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

db = SQLAlchemy()

class ChaosExperiment(db.Model):
    """Model for storing chaos experiment results with enhanced error handling"""
    __tablename__ = 'chaos_experiments'
    
    id = db.Column(db.Integer, primary_key=True)
    scenario = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    intensity = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='running')
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    result = db.Column(db.Text)
    metrics_before = db.Column(db.Text)  # JSON string
    metrics_after = db.Column(db.Text)   # JSON string
    error_message = db.Column(db.Text)
    user_agent = db.Column(db.String(200))
    client_ip = db.Column(db.String(45))
    
    def to_dict(self):
        """Convert experiment to dictionary with error handling"""
        try:
            return {
                'id': self.id,
                'scenario': self.scenario,
                'duration': self.duration,
                'intensity': self.intensity,
                'status': self.status,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': self.end_time.isoformat() if self.end_time else None,
                'result': self.result,
                'metrics_before': self._safe_json_loads(self.metrics_before),
                'metrics_after': self._safe_json_loads(self.metrics_after),
                'error_message': self.error_message,
                'user_agent': self.user_agent,
                'client_ip': self.client_ip
            }
        except Exception as e:
            logger.error(f"Error converting ChaosExperiment {self.id} to dict: {e}")
            # Return minimal safe dictionary
            return {
                'id': self.id,
                'scenario': self.scenario or 'unknown',
                'status': self.status or 'unknown',
                'error': f'Conversion error: {str(e)}'
            }
    
    def _safe_json_loads(self, json_str):
        """Safely load JSON string with error handling"""
        if not json_str:
            return None
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse JSON data: {e}")
            return {'error': 'Invalid JSON data'}

class SystemMetrics(db.Model):
    """Model for storing system metrics snapshots"""
    __tablename__ = 'system_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    cpu_percent = db.Column(db.Float)
    memory_percent = db.Column(db.Float)
    disk_percent = db.Column(db.Float)
    network_bytes_sent = db.Column(db.BigInteger)
    network_bytes_recv = db.Column(db.BigInteger)
    active_processes = db.Column(db.Integer)
    load_average = db.Column(db.Float)
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'disk_percent': self.disk_percent,
            'network_bytes_sent': self.network_bytes_sent,
            'network_bytes_recv': self.network_bytes_recv,
            'active_processes': self.active_processes,
            'load_average': self.load_average
        }

class AILearning(db.Model):
    """Model for storing AI learning data and patterns"""
    __tablename__ = 'ai_learning'
    
    id = db.Column(db.Integer, primary_key=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('chaos_experiments.id'))
    pattern_type = db.Column(db.String(50))  # 'failure_pattern', 'recovery_pattern', etc.
    pattern_data = db.Column(db.Text)  # JSON string
    confidence_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    experiment = db.relationship('ChaosExperiment', backref='ai_patterns')
    
    def to_dict(self):
        return {
            'id': self.id,
            'experiment_id': self.experiment_id,
            'pattern_type': self.pattern_type,
            'pattern_data': json.loads(self.pattern_data) if self.pattern_data else None,
            'confidence_score': self.confidence_score,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

def init_database(app):
    """Initialize database with Flask app"""
    database_url = os.getenv('DATABASE_URL', 'sqlite:///chaos_platform.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        
        # Create indexes for better performance
        try:
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_chaos_experiments_start_time ON chaos_experiments(start_time)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_chaos_experiments_scenario ON chaos_experiments(scenario)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp)'))
            db.session.commit()
        except Exception as e:
            print(f"Index creation warning: {e}")

def cleanup_old_data(days_to_keep=30):
    """Clean up old data to prevent database bloat"""
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    
    # Clean old experiments
    old_experiments = ChaosExperiment.query.filter(
        ChaosExperiment.start_time < cutoff_date
    ).delete()
    
    # Clean old metrics
    old_metrics = SystemMetrics.query.filter(
        SystemMetrics.timestamp < cutoff_date
    ).delete()
    
    db.session.commit()
    return old_experiments, old_metrics
