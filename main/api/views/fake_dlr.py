"""
REST API Views for Fake DLR Connectors and Routes
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from main.core.models.fake_dlr import FakeDLRConnectorModel, FakeDLRRouteModel
from main.core.fake_dlr import (
    register_fake_dlr_connector,
    get_fake_dlr_connector,
    unregister_fake_dlr_connector,
    list_fake_dlr_connectors,
)
from main.core.fake_dlr_router import get_fake_dlr_router
import logging

logger = logging.getLogger(__name__)


class FakeDLRConnectorViewSet(viewsets.ViewSet):
    """
    ViewSet for managing Fake DLR Connectors
    
    Endpoints:
    - GET /api/fake-dlr-connectors/ - List all connectors
    - GET /api/fake-dlr-connectors/{cid}/ - Get connector details
    - POST /api/fake-dlr-connectors/ - Create new connector
    - PUT /api/fake-dlr-connectors/{cid}/ - Update connector
    - DELETE /api/fake-dlr-connectors/{cid}/ - Delete connector
    - POST /api/fake-dlr-connectors/{cid}/start/ - Start connector
    - POST /api/fake-dlr-connectors/{cid}/stop/ - Stop connector
    - GET /api/fake-dlr-connectors/{cid}/status/ - Get connector status
    """
    
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """List all Fake DLR connectors"""
        try:
            connectors = FakeDLRConnectorModel.objects.all().order_by('cid')
            data = [
                {
                    'cid': c.cid,
                    'name': c.name,
                    'description': c.description,
                    'enabled': c.enabled,
                    'success_rate': c.success_rate,
                    'min_delay': c.min_delay,
                    'max_delay': c.max_delay,
                    'instant_response': c.instant_response,
                    'error_code': c.error_code,
                    'total_messages': c.total_messages,
                    'delivered_count': c.delivered_count,
                    'failed_count': c.failed_count,
                    'delivery_rate': c.delivery_rate,
                    'created': c.created.isoformat() if c.created else None,
                    'modified': c.modified.isoformat() if c.modified else None,
                }
                for c in connectors
            ]
            return Response({'connectors': data})
        except Exception as e:
            logger.error(f"Error listing Fake DLR connectors: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, pk=None):
        """Get details of a specific Fake DLR connector"""
        try:
            connector = get_object_or_404(FakeDLRConnectorModel, cid=pk)
            data = {
                'cid': connector.cid,
                'name': connector.name,
                'description': connector.description,
                'enabled': connector.enabled,
                'success_rate': connector.success_rate,
                'min_delay': connector.min_delay,
                'max_delay': connector.max_delay,
                'instant_response': connector.instant_response,
                'error_code': connector.error_code,
                'total_messages': connector.total_messages,
                'delivered_count': connector.delivered_count,
                'failed_count': connector.failed_count,
                'delivery_rate': connector.delivery_rate,
                'created': connector.created.isoformat() if connector.created else None,
                'modified': connector.modified.isoformat() if connector.modified else None,
            }
            return Response({'connector': data})
        except Exception as e:
            logger.error(f"Error retrieving Fake DLR connector: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def create(self, request):
        """Create a new Fake DLR connector"""
        try:
            data = request.data
            
            # Validate required fields
            if not data.get('cid'):
                return Response(
                    {'error': 'cid is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not data.get('name'):
                return Response(
                    {'error': 'name is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if connector already exists
            if FakeDLRConnectorModel.objects.filter(cid=data['cid']).exists():
                return Response(
                    {'error': f"Connector with cid '{data['cid']}' already exists"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create connector in database
            connector = FakeDLRConnectorModel.objects.create(
                cid=data['cid'],
                name=data['name'],
                description=data.get('description', ''),
                enabled=data.get('enabled', True),
                success_rate=data.get('success_rate', 100),
                min_delay=data.get('min_delay', 0),
                max_delay=data.get('max_delay', 15),
                instant_response=data.get('instant_response', False),
                error_code=data.get('error_code', '000'),
            )
            
            # Register connector in runtime
            config = connector.get_config()
            register_fake_dlr_connector(connector.cid, config)
            
            logger.info(f"Created Fake DLR connector: {connector.cid}")
            
            return Response(
                {
                    'message': 'Connector created successfully',
                    'connector': {
                        'cid': connector.cid,
                        'name': connector.name,
                    }
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Error creating Fake DLR connector: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, pk=None):
        """Update a Fake DLR connector"""
        try:
            connector = get_object_or_404(FakeDLRConnectorModel, cid=pk)
            data = request.data
            
            # Update fields
            if 'name' in data:
                connector.name = data['name']
            if 'description' in data:
                connector.description = data['description']
            if 'enabled' in data:
                connector.enabled = data['enabled']
            if 'success_rate' in data:
                connector.success_rate = data['success_rate']
            if 'min_delay' in data:
                connector.min_delay = data['min_delay']
            if 'max_delay' in data:
                connector.max_delay = data['max_delay']
            if 'instant_response' in data:
                connector.instant_response = data['instant_response']
            if 'error_code' in data:
                connector.error_code = data['error_code']
            
            connector.save()
            
            # Update runtime connector
            runtime_connector = get_fake_dlr_connector(connector.cid)
            if runtime_connector:
                runtime_connector.engine.config = connector.get_config()
            
            logger.info(f"Updated Fake DLR connector: {connector.cid}")
            
            return Response({
                'message': 'Connector updated successfully',
                'connector': {'cid': connector.cid}
            })
        except Exception as e:
            logger.error(f"Error updating Fake DLR connector: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, pk=None):
        """Delete a Fake DLR connector"""
        try:
            connector = get_object_or_404(FakeDLRConnectorModel, cid=pk)
            
            # Unregister from runtime
            unregister_fake_dlr_connector(connector.cid)
            
            # Delete from database
            connector.delete()
            
            logger.info(f"Deleted Fake DLR connector: {pk}")
            
            return Response({
                'message': 'Connector deleted successfully',
                'cid': pk
            })
        except Exception as e:
            logger.error(f"Error deleting Fake DLR connector: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a Fake DLR connector"""
        try:
            connector = get_object_or_404(FakeDLRConnectorModel, cid=pk)
            
            # Get or register runtime connector
            runtime_connector = get_fake_dlr_connector(connector.cid)
            if not runtime_connector:
                config = connector.get_config()
                runtime_connector = register_fake_dlr_connector(connector.cid, config)
            
            # Start connector
            rabbitmq_config = {
                'host': request.data.get('rabbitmq_host', '127.0.0.1'),
                'port': request.data.get('rabbitmq_port', 5672),
                'username': request.data.get('rabbitmq_username', 'guest'),
                'password': request.data.get('rabbitmq_password', 'guest'),
                'vhost': request.data.get('rabbitmq_vhost', '/'),
            }
            
            if runtime_connector.start(rabbitmq_config):
                connector.enabled = True
                connector.save()
                return Response({
                    'message': 'Connector started successfully',
                    'cid': connector.cid
                })
            else:
                return Response(
                    {'error': 'Failed to start connector'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            logger.error(f"Error starting Fake DLR connector: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Stop a Fake DLR connector"""
        try:
            connector = get_object_or_404(FakeDLRConnectorModel, cid=pk)
            
            # Stop runtime connector
            runtime_connector = get_fake_dlr_connector(connector.cid)
            if runtime_connector:
                runtime_connector.stop()
            
            connector.enabled = False
            connector.save()
            
            return Response({
                'message': 'Connector stopped successfully',
                'cid': connector.cid
            })
        except Exception as e:
            logger.error(f"Error stopping Fake DLR connector: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get status of a Fake DLR connector"""
        try:
            connector = get_object_or_404(FakeDLRConnectorModel, cid=pk)
            runtime_connector = get_fake_dlr_connector(connector.cid)
            
            if runtime_connector:
                runtime_status = runtime_connector.get_status()
            else:
                runtime_status = {'status': 'not_registered'}
            
            return Response({
                'cid': connector.cid,
                'database_enabled': connector.enabled,
                'runtime_status': runtime_status,
            })
        except Exception as e:
            logger.error(f"Error getting Fake DLR connector status: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FakeDLRRouteViewSet(viewsets.ViewSet):
    """
    ViewSet for managing Fake DLR Routes
    
    Endpoints:
    - GET /api/fake-dlr-routes/ - List all routes
    - GET /api/fake-dlr-routes/{order}/ - Get route details
    - POST /api/fake-dlr-routes/ - Create new route
    - PUT /api/fake-dlr-routes/{order}/ - Update route
    - DELETE /api/fake-dlr-routes/{order}/ - Delete route
    - GET /api/fake-dlr-routes/statistics/ - Get routing statistics
    """
    
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """List all Fake DLR routes"""
        try:
            routes = FakeDLRRouteModel.objects.all().select_related(
                'fake_dlr_connector'
            ).order_by('order')
            
            data = [
                {
                    'order': r.order,
                    'name': r.name,
                    'enabled': r.enabled,
                    'fake_dlr_percentage': r.fake_dlr_percentage,
                    'fake_dlr_connector': {
                        'cid': r.fake_dlr_connector.cid,
                        'name': r.fake_dlr_connector.name,
                    },
                    'real_connector_cid': r.real_connector_cid,
                    'filter_user_uid': r.filter_user_uid,
                    'filter_source_addr_pattern': r.filter_source_addr_pattern,
                    'filter_destination_addr_pattern': r.filter_destination_addr_pattern,
                    'total_messages': r.total_messages,
                    'fake_dlr_messages': r.fake_dlr_messages,
                    'real_messages': r.real_messages,
                    'actual_fake_percentage': r.actual_fake_percentage,
                }
                for r in routes
            ]
            return Response({'routes': data})
        except Exception as e:
            logger.error(f"Error listing Fake DLR routes: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get routing statistics"""
        try:
            router = get_fake_dlr_router()
            stats = router.get_statistics()
            return Response(stats)
        except Exception as e:
            logger.error(f"Error getting routing statistics: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Wrapper functions for URL routing (matching existing pattern)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def fake_dlr_connector_list(request):
    """List or create Fake DLR connectors"""
    viewset = FakeDLRConnectorViewSet()
    if request.method == 'GET':
        return viewset.list(request)
    else:
        return viewset.create(request)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def fake_dlr_connector_detail(request, cid):
    """Get, update, or delete a Fake DLR connector"""
    viewset = FakeDLRConnectorViewSet()
    if request.method == 'GET':
        return viewset.retrieve(request, pk=cid)
    elif request.method == 'PUT':
        return viewset.update(request, pk=cid)
    else:
        return viewset.destroy(request, pk=cid)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def fake_dlr_connector_start(request, cid):
    """Start a Fake DLR connector"""
    viewset = FakeDLRConnectorViewSet()
    return viewset.start(request, pk=cid)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def fake_dlr_connector_stop(request, cid):
    """Stop a Fake DLR connector"""
    viewset = FakeDLRConnectorViewSet()
    return viewset.stop(request, pk=cid)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fake_dlr_connector_status(request, cid):
    """Get status of a Fake DLR connector"""
    viewset = FakeDLRConnectorViewSet()
    return viewset.status(request, pk=cid)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fake_dlr_route_list(request):
    """List all Fake DLR routes"""
    viewset = FakeDLRRouteViewSet()
    return viewset.list(request)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fake_dlr_route_detail(request, order):
    """Get details of a Fake DLR route"""
    viewset = FakeDLRRouteViewSet()
    return viewset.retrieve(request, pk=order)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fake_dlr_route_statistics(request):
    """Get routing statistics"""
    viewset = FakeDLRRouteViewSet()
    return viewset.statistics(request)
