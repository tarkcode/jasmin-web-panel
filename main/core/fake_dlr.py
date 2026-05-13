"""
Fake DLR (Delivery Report) Engine

This module implements a "Fake DLR" or "Dump Route" system that generates
internal delivery reports without actually sending messages to vendors.

Use Cases:
- Grey routes
- Testing routes
- Promotional/low-quality traffic
- Cost reduction (messages not sent but reported as delivered)

Flow:
1. Messages routed to Fake DLR connector
2. System generates internal DLR (DELIVRD, UNDELIV, etc.)
3. Customer receives delivery status
4. No actual SMS sent to operator/vendor
"""
import logging
import random
import time
import uuid
from datetime import datetime
from typing import Dict, Optional, Tuple
from threading import Thread
import pika

logger = logging.getLogger(__name__)


class FakeDLREngine:
    """
    Fake DLR Engine that generates internal delivery reports
    without sending messages to actual vendors.
    """
    
    # DLR Status options
    STATUS_DELIVRD = "DELIVRD"
    STATUS_UNDELIV = "UNDELIV"
    STATUS_EXPIRED = "EXPIRED"
    STATUS_REJECTD = "REJECTD"
    
    # Default configuration
    DEFAULT_CONFIG = {
        'success_rate': 100,  # Percentage of messages marked as DELIVRD
        'min_delay': 0,       # Minimum delay in seconds before generating DLR
        'max_delay': 15,      # Maximum delay in seconds before generating DLR
        'instant_response': False,  # If True, generate DLR immediately
        'error_code': '000',  # Error code for DELIVRD status
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Fake DLR Engine
        
        Args:
            config: Configuration dictionary with keys:
                - success_rate: Percentage (0-100) of messages marked as DELIVRD
                - min_delay: Minimum delay in seconds
                - max_delay: Maximum delay in seconds
                - instant_response: Boolean for immediate DLR
                - error_code: Error code for delivery reports
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.rabbitmq_connection = None
        self.rabbitmq_channel = None
        logger.info(f"FakeDLREngine initialized with config: {self.config}")
    
    def connect_rabbitmq(self, host='127.0.0.1', port=5672, 
                        username='guest', password='guest', vhost='/'):
        """
        Connect to RabbitMQ for publishing DLR messages
        
        Args:
            host: RabbitMQ host
            port: RabbitMQ port
            username: RabbitMQ username
            password: RabbitMQ password
            vhost: RabbitMQ virtual host
        """
        try:
            credentials = pika.PlainCredentials(username, password)
            parameters = pika.ConnectionParameters(
                host=host,
                port=port,
                virtual_host=vhost,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            self.rabbitmq_connection = pika.BlockingConnection(parameters)
            self.rabbitmq_channel = self.rabbitmq_connection.channel()
            logger.info(f"Connected to RabbitMQ at {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def disconnect_rabbitmq(self):
        """Disconnect from RabbitMQ"""
        try:
            if self.rabbitmq_channel:
                self.rabbitmq_channel.close()
            if self.rabbitmq_connection:
                self.rabbitmq_connection.close()
            logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")
    
    def generate_status(self) -> str:
        """
        Generate a DLR status based on success_rate configuration
        
        Returns:
            Status string (DELIVRD, UNDELIV, etc.)
        """
        success_rate = self.config.get('success_rate', 100)
        rand_val = random.randint(1, 100)
        
        if rand_val <= success_rate:
            return self.STATUS_DELIVRD
        else:
            # Randomly choose from failure statuses
            failure_statuses = [
                self.STATUS_UNDELIV,
                self.STATUS_EXPIRED,
                self.STATUS_REJECTD
            ]
            return random.choice(failure_statuses)
    
    def calculate_delay(self) -> float:
        """
        Calculate delay before generating DLR
        
        Returns:
            Delay in seconds
        """
        if self.config.get('instant_response', False):
            return 0
        
        min_delay = self.config.get('min_delay', 0)
        max_delay = self.config.get('max_delay', 15)
        
        return random.uniform(min_delay, max_delay)
    
    def generate_fake_dlr(self, msgid: str, destination_addr: str, 
                         source_addr: str, uid: str) -> Dict:
        """
        Generate a fake DLR for a message
        
        Args:
            msgid: Message ID
            destination_addr: Destination phone number
            source_addr: Source address/sender ID
            uid: User ID
        
        Returns:
            Dictionary with DLR information
        """
        status = self.generate_status()
        error_code = self.config.get('error_code', '000')
        
        dlr = {
            'msgid': msgid,
            'destination_addr': destination_addr,
            'source_addr': source_addr,
            'uid': uid,
            'status': status,
            'error_code': error_code,
            'timestamp': datetime.utcnow().isoformat(),
            'fake_dlr': True,  # Flag to identify fake DLRs
        }
        
        logger.info(f"Generated Fake DLR: msgid={msgid}, status={status}, "
                   f"dest={destination_addr}, uid={uid}")
        
        return dlr
    
    def publish_dlr_to_rabbitmq(self, dlr: Dict, routing_key: str = 'dlr_thrower.http'):
        """
        Publish DLR to RabbitMQ queue
        
        Args:
            dlr: DLR dictionary
            routing_key: RabbitMQ routing key
        """
        if not self.rabbitmq_channel:
            logger.error("RabbitMQ channel not initialized")
            return False
        
        try:
            # Prepare message properties
            properties = pika.BasicProperties(
                message_id=dlr['msgid'],
                content_type='application/json',
                delivery_mode=2,  # Persistent
                headers={
                    'message_status': dlr['status'],
                    'error_code': dlr['error_code'],
                    'fake_dlr': 'true',
                }
            )
            
            # Publish to exchange
            self.rabbitmq_channel.basic_publish(
                exchange='messaging',
                routing_key=routing_key,
                body=str(dlr).encode('utf-8'),
                properties=properties
            )
            
            logger.info(f"Published Fake DLR to RabbitMQ: msgid={dlr['msgid']}, "
                       f"status={dlr['status']}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish DLR to RabbitMQ: {e}")
            return False
    
    def process_message(self, msgid: str, destination_addr: str, 
                       source_addr: str, uid: str, 
                       async_mode: bool = True) -> Tuple[bool, str]:
        """
        Process a message through Fake DLR system
        
        Args:
            msgid: Message ID
            destination_addr: Destination phone number
            source_addr: Source address/sender ID
            uid: User ID
            async_mode: If True, generate DLR asynchronously with delay
        
        Returns:
            Tuple of (success, message_id)
        """
        logger.info(f"Processing message through Fake DLR: msgid={msgid}, "
                   f"dest={destination_addr}, uid={uid}")
        
        if async_mode:
            # Generate DLR asynchronously with delay
            delay = self.calculate_delay()
            thread = Thread(
                target=self._delayed_dlr_generation,
                args=(msgid, destination_addr, source_addr, uid, delay)
            )
            thread.daemon = True
            thread.start()
        else:
            # Generate DLR immediately
            dlr = self.generate_fake_dlr(msgid, destination_addr, source_addr, uid)
            self.publish_dlr_to_rabbitmq(dlr)
        
        # Return success immediately (message "accepted")
        return True, msgid
    
    def _delayed_dlr_generation(self, msgid: str, destination_addr: str,
                               source_addr: str, uid: str, delay: float):
        """
        Internal method to generate DLR after a delay
        
        Args:
            msgid: Message ID
            destination_addr: Destination phone number
            source_addr: Source address
            uid: User ID
            delay: Delay in seconds
        """
        if delay > 0:
            logger.debug(f"Waiting {delay:.2f}s before generating DLR for msgid={msgid}")
            time.sleep(delay)
        
        dlr = self.generate_fake_dlr(msgid, destination_addr, source_addr, uid)
        self.publish_dlr_to_rabbitmq(dlr)


class FakeDLRConnector:
    """
    Fake DLR Connector that mimics a real SMPP connector
    but generates fake delivery reports instead of sending messages.
    """
    
    def __init__(self, connector_id: str, config: Optional[Dict] = None):
        """
        Initialize Fake DLR Connector
        
        Args:
            connector_id: Unique connector identifier
            config: Configuration for the Fake DLR engine
        """
        self.connector_id = connector_id
        self.engine = FakeDLREngine(config)
        self.status = 'stopped'
        logger.info(f"FakeDLRConnector '{connector_id}' initialized")
    
    def start(self, rabbitmq_config: Optional[Dict] = None):
        """
        Start the Fake DLR connector
        
        Args:
            rabbitmq_config: RabbitMQ connection configuration
        """
        rabbitmq_config = rabbitmq_config or {}
        if self.engine.connect_rabbitmq(**rabbitmq_config):
            self.status = 'started'
            logger.info(f"FakeDLRConnector '{self.connector_id}' started")
            return True
        else:
            self.status = 'error'
            logger.error(f"FakeDLRConnector '{self.connector_id}' failed to start")
            return False
    
    def stop(self):
        """Stop the Fake DLR connector"""
        self.engine.disconnect_rabbitmq()
        self.status = 'stopped'
        logger.info(f"FakeDLRConnector '{self.connector_id}' stopped")
    
    def send_message(self, msgid: str, destination_addr: str,
                    source_addr: str, uid: str, **kwargs) -> Tuple[bool, str]:
        """
        "Send" a message (actually just generate fake DLR)
        
        Args:
            msgid: Message ID
            destination_addr: Destination phone number
            source_addr: Source address
            uid: User ID
            **kwargs: Additional parameters (ignored)
        
        Returns:
            Tuple of (success, message_id)
        """
        if self.status != 'started':
            logger.error(f"FakeDLRConnector '{self.connector_id}' not started")
            return False, ""
        
        return self.engine.process_message(msgid, destination_addr, source_addr, uid)
    
    def get_status(self) -> Dict:
        """
        Get connector status
        
        Returns:
            Dictionary with connector status information
        """
        return {
            'connector_id': self.connector_id,
            'status': self.status,
            'type': 'fake_dlr',
            'config': self.engine.config,
        }


# Global registry of Fake DLR connectors
_fake_dlr_connectors: Dict[str, FakeDLRConnector] = {}


def register_fake_dlr_connector(connector_id: str, config: Optional[Dict] = None) -> FakeDLRConnector:
    """
    Register a new Fake DLR connector
    
    Args:
        connector_id: Unique connector identifier
        config: Configuration dictionary
    
    Returns:
        FakeDLRConnector instance
    """
    if connector_id in _fake_dlr_connectors:
        logger.warning(f"Fake DLR connector '{connector_id}' already registered")
        return _fake_dlr_connectors[connector_id]
    
    connector = FakeDLRConnector(connector_id, config)
    _fake_dlr_connectors[connector_id] = connector
    logger.info(f"Registered Fake DLR connector: {connector_id}")
    return connector


def get_fake_dlr_connector(connector_id: str) -> Optional[FakeDLRConnector]:
    """
    Get a registered Fake DLR connector
    
    Args:
        connector_id: Connector identifier
    
    Returns:
        FakeDLRConnector instance or None
    """
    return _fake_dlr_connectors.get(connector_id)


def unregister_fake_dlr_connector(connector_id: str) -> bool:
    """
    Unregister a Fake DLR connector
    
    Args:
        connector_id: Connector identifier
    
    Returns:
        True if unregistered, False if not found
    """
    if connector_id in _fake_dlr_connectors:
        connector = _fake_dlr_connectors[connector_id]
        connector.stop()
        del _fake_dlr_connectors[connector_id]
        logger.info(f"Unregistered Fake DLR connector: {connector_id}")
        return True
    return False


def list_fake_dlr_connectors() -> Dict[str, Dict]:
    """
    List all registered Fake DLR connectors
    
    Returns:
        Dictionary mapping connector_id to status info
    """
    return {cid: conn.get_status() for cid, conn in _fake_dlr_connectors.items()}
