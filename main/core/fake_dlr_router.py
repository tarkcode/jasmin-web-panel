"""
Fake DLR Router - Traffic splitting and routing logic

This module intercepts outgoing messages and routes them either to:
1. Real SMPP connectors (actual delivery)
2. Fake DLR connectors (simulated delivery)

Based on configured percentage splits and filters.
"""
import logging
import uuid
from typing import Optional, Tuple, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class FakeDLRRouter:
    """
    Router that splits traffic between real connectors and Fake DLR connectors
    """
    
    def __init__(self):
        """Initialize the Fake DLR Router"""
        self.enabled = True
        logger.info("FakeDLRRouter initialized")
    
    def route_message(self, msgid: str, destination_addr: str, source_addr: str,
                     uid: str, short_message: str, **kwargs) -> Tuple[str, bool, Dict]:
        """
        Route a message to either real connector or Fake DLR connector
        
        Args:
            msgid: Message ID
            destination_addr: Destination phone number
            source_addr: Source address/sender ID
            uid: User ID
            short_message: Message content
            **kwargs: Additional message parameters
        
        Returns:
            Tuple of (connector_id, is_fake_dlr, routing_info)
        """
        if not self.enabled:
            return self._route_to_real_connector(msgid, uid)
        
        # Find matching route
        route = self._find_matching_route(uid, source_addr, destination_addr)
        
        if not route:
            # No Fake DLR route found, use real connector
            return self._route_to_real_connector(msgid, uid)
        
        # Decide whether to use Fake DLR based on percentage
        use_fake_dlr = route.should_use_fake_dlr()
        
        if use_fake_dlr:
            # Route to Fake DLR connector
            connector_id = f"fake_dlr_{route.fake_dlr_connector.cid}"
            routing_info = {
                'route_id': route.id,
                'route_name': route.name,
                'fake_dlr_connector': route.fake_dlr_connector.cid,
                'routed_at': datetime.utcnow().isoformat(),
            }
            
            # Update statistics
            route.increment_stats(is_fake_dlr=True)
            
            logger.info(f"Routing message {msgid} to Fake DLR connector: "
                       f"{route.fake_dlr_connector.cid}")
            
            return connector_id, True, routing_info
        else:
            # Route to real connector
            connector_id = route.real_connector_cid
            routing_info = {
                'route_id': route.id,
                'route_name': route.name,
                'real_connector': connector_id,
                'routed_at': datetime.utcnow().isoformat(),
            }
            
            # Update statistics
            route.increment_stats(is_fake_dlr=False)
            
            logger.info(f"Routing message {msgid} to real connector: {connector_id}")
            
            return connector_id, False, routing_info
    
    def _find_matching_route(self, uid: str, source_addr: str, 
                            destination_addr: str):
        """
        Find the first matching Fake DLR route based on filters
        
        Args:
            uid: User ID
            source_addr: Source address
            destination_addr: Destination address
        
        Returns:
            FakeDLRRouteModel instance or None
        """
        try:
            from main.core.models.fake_dlr import FakeDLRRouteModel
            
            # Get all enabled routes ordered by priority
            routes = FakeDLRRouteModel.objects.filter(
                enabled=True,
                fake_dlr_connector__enabled=True
            ).select_related('fake_dlr_connector').order_by('order')
            
            for route in routes:
                if route.matches_filters(uid, source_addr, destination_addr):
                    return route
            
            return None
        except Exception as e:
            logger.error(f"Error finding matching route: {e}")
            return None
    
    def _route_to_real_connector(self, msgid: str, uid: str) -> Tuple[str, bool, Dict]:
        """
        Default routing to real connector (no Fake DLR)
        
        Args:
            msgid: Message ID
            uid: User ID
        
        Returns:
            Tuple of (connector_id, is_fake_dlr, routing_info)
        """
        routing_info = {
            'default_routing': True,
            'routed_at': datetime.utcnow().isoformat(),
        }
        return 'default', False, routing_info
    
    def process_fake_dlr_message(self, msgid: str, destination_addr: str,
                                source_addr: str, uid: str, 
                                connector_id: str) -> Tuple[bool, str]:
        """
        Process a message through Fake DLR connector
        
        Args:
            msgid: Message ID
            destination_addr: Destination phone number
            source_addr: Source address
            uid: User ID
            connector_id: Fake DLR connector ID
        
        Returns:
            Tuple of (success, message_id)
        """
        try:
            from main.core.fake_dlr import get_fake_dlr_connector
            
            # Extract connector CID from connector_id
            cid = connector_id.replace('fake_dlr_', '')
            
            # Get the connector
            connector = get_fake_dlr_connector(cid)
            
            if not connector:
                logger.error(f"Fake DLR connector not found: {cid}")
                return False, ""
            
            # Process message through Fake DLR
            success, returned_msgid = connector.send_message(
                msgid, destination_addr, source_addr, uid
            )
            
            return success, returned_msgid
        except Exception as e:
            logger.error(f"Error processing Fake DLR message: {e}")
            return False, ""
    
    def get_statistics(self) -> Dict:
        """
        Get routing statistics
        
        Returns:
            Dictionary with statistics for all routes
        """
        try:
            from main.core.models.fake_dlr import FakeDLRRouteModel, FakeDLRConnectorModel
            
            routes = FakeDLRRouteModel.objects.filter(enabled=True).select_related(
                'fake_dlr_connector'
            )
            
            connectors = FakeDLRConnectorModel.objects.filter(enabled=True)
            
            stats = {
                'routes': [
                    {
                        'order': r.order,
                        'name': r.name,
                        'total_messages': r.total_messages,
                        'fake_dlr_messages': r.fake_dlr_messages,
                        'real_messages': r.real_messages,
                        'actual_fake_percentage': r.actual_fake_percentage,
                        'configured_percentage': r.fake_dlr_percentage,
                    }
                    for r in routes
                ],
                'connectors': [
                    {
                        'cid': c.cid,
                        'name': c.name,
                        'total_messages': c.total_messages,
                        'delivered_count': c.delivered_count,
                        'failed_count': c.failed_count,
                        'delivery_rate': c.delivery_rate,
                    }
                    for c in connectors
                ],
            }
            
            return stats
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {'routes': [], 'connectors': []}


# Global router instance
_fake_dlr_router = None


def get_fake_dlr_router() -> FakeDLRRouter:
    """
    Get the global Fake DLR router instance
    
    Returns:
        FakeDLRRouter instance
    """
    global _fake_dlr_router
    if _fake_dlr_router is None:
        _fake_dlr_router = FakeDLRRouter()
    return _fake_dlr_router


def enable_fake_dlr_routing():
    """Enable Fake DLR routing"""
    router = get_fake_dlr_router()
    router.enabled = True
    logger.info("Fake DLR routing enabled")


def disable_fake_dlr_routing():
    """Disable Fake DLR routing"""
    router = get_fake_dlr_router()
    router.enabled = False
    logger.info("Fake DLR routing disabled")


def route_message_with_fake_dlr(msgid: str, destination_addr: str, source_addr: str,
                                uid: str, short_message: str, **kwargs) -> Tuple[str, bool, Dict]:
    """
    Convenience function to route a message through Fake DLR router
    
    Args:
        msgid: Message ID
        destination_addr: Destination phone number
        source_addr: Source address
        uid: User ID
        short_message: Message content
        **kwargs: Additional parameters
    
    Returns:
        Tuple of (connector_id, is_fake_dlr, routing_info)
    """
    router = get_fake_dlr_router()
    return router.route_message(msgid, destination_addr, source_addr, uid, 
                               short_message, **kwargs)
