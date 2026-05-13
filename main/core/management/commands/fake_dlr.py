"""
Django management command for Fake DLR operations

Usage:
    python manage.py fake_dlr list_connectors
    python manage.py fake_dlr list_routes
    python manage.py fake_dlr create_connector --cid=fake_01 --name="Test Connector"
    python manage.py fake_dlr start_connector --cid=fake_01
    python manage.py fake_dlr stop_connector --cid=fake_01
    python manage.py fake_dlr statistics
    python manage.py fake_dlr init_demo
"""
from django.core.management.base import BaseCommand, CommandError
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


class Command(BaseCommand):
    help = 'Manage Fake DLR connectors and routes'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=[
                'list_connectors',
                'list_routes',
                'create_connector',
                'start_connector',
                'stop_connector',
                'delete_connector',
                'statistics',
                'init_demo',
            ],
            help='Action to perform'
        )
        
        # Connector options
        parser.add_argument('--cid', type=str, help='Connector ID')
        parser.add_argument('--name', type=str, help='Connector name')
        parser.add_argument('--success-rate', type=int, default=100, help='Success rate (0-100)')
        parser.add_argument('--min-delay', type=int, default=0, help='Minimum delay in seconds')
        parser.add_argument('--max-delay', type=int, default=15, help='Maximum delay in seconds')
        parser.add_argument('--instant', action='store_true', help='Instant response')
        
        # RabbitMQ options
        parser.add_argument('--rabbitmq-host', type=str, default='127.0.0.1', help='RabbitMQ host')
        parser.add_argument('--rabbitmq-port', type=int, default=5672, help='RabbitMQ port')
        parser.add_argument('--rabbitmq-user', type=str, default='guest', help='RabbitMQ username')
        parser.add_argument('--rabbitmq-pass', type=str, default='guest', help='RabbitMQ password')

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'list_connectors':
            self.list_connectors()
        elif action == 'list_routes':
            self.list_routes()
        elif action == 'create_connector':
            self.create_connector(options)
        elif action == 'start_connector':
            self.start_connector(options)
        elif action == 'stop_connector':
            self.stop_connector(options)
        elif action == 'delete_connector':
            self.delete_connector(options)
        elif action == 'statistics':
            self.show_statistics()
        elif action == 'init_demo':
            self.init_demo()

    def list_connectors(self):
        """List all Fake DLR connectors"""
        connectors = FakeDLRConnectorModel.objects.all().order_by('cid')
        
        if not connectors:
            self.stdout.write(self.style.WARNING('No Fake DLR connectors found'))
            return
        
        self.stdout.write(self.style.SUCCESS('\nFake DLR Connectors:'))
        self.stdout.write('-' * 100)
        
        header = f"{'CID':<15} {'Name':<25} {'Enabled':<10} {'Success%':<10} {'Delay':<15} {'Messages':<10}"
        self.stdout.write(header)
        self.stdout.write('-' * 100)
        
        for c in connectors:
            delay = 'Instant' if c.instant_response else f"{c.min_delay}-{c.max_delay}s"
            enabled = 'Yes' if c.enabled else 'No'
            row = f"{c.cid:<15} {c.name:<25} {enabled:<10} {c.success_rate:<10} {delay:<15} {c.total_messages:<10}"
            self.stdout.write(row)
        
        self.stdout.write('-' * 100)

    def list_routes(self):
        """List all Fake DLR routes"""
        routes = FakeDLRRouteModel.objects.all().select_related('fake_dlr_connector').order_by('order')
        
        if not routes:
            self.stdout.write(self.style.WARNING('No Fake DLR routes found'))
            return
        
        self.stdout.write(self.style.SUCCESS('\nFake DLR Routes:'))
        self.stdout.write('-' * 120)
        
        header = f"{'Order':<8} {'Name':<25} {'Enabled':<10} {'Fake%':<8} {'Connector':<15} {'Real CID':<15} {'Messages':<10}"
        self.stdout.write(header)
        self.stdout.write('-' * 120)
        
        for r in routes:
            enabled = 'Yes' if r.enabled else 'No'
            row = (f"{r.order:<8} {r.name:<25} {enabled:<10} {r.fake_dlr_percentage:<8} "
                  f"{r.fake_dlr_connector.cid:<15} {r.real_connector_cid:<15} {r.total_messages:<10}")
            self.stdout.write(row)
        
        self.stdout.write('-' * 120)

    def create_connector(self, options):
        """Create a new Fake DLR connector"""
        cid = options.get('cid')
        name = options.get('name')
        
        if not cid or not name:
            raise CommandError('--cid and --name are required')
        
        if FakeDLRConnectorModel.objects.filter(cid=cid).exists():
            raise CommandError(f"Connector '{cid}' already exists")
        
        connector = FakeDLRConnectorModel.objects.create(
            cid=cid,
            name=name,
            success_rate=options['success_rate'],
            min_delay=options['min_delay'],
            max_delay=options['max_delay'],
            instant_response=options['instant'],
            enabled=True,
        )
        
        # Register in runtime
        config = connector.get_config()
        register_fake_dlr_connector(connector.cid, config)
        
        self.stdout.write(self.style.SUCCESS(f"Created Fake DLR connector: {cid}"))

    def start_connector(self, options):
        """Start a Fake DLR connector"""
        cid = options.get('cid')
        
        if not cid:
            raise CommandError('--cid is required')
        
        try:
            connector = FakeDLRConnectorModel.objects.get(cid=cid)
        except FakeDLRConnectorModel.DoesNotExist:
            raise CommandError(f"Connector '{cid}' not found")
        
        # Get or register runtime connector
        runtime_connector = get_fake_dlr_connector(connector.cid)
        if not runtime_connector:
            config = connector.get_config()
            runtime_connector = register_fake_dlr_connector(connector.cid, config)
        
        # Start connector
        rabbitmq_config = {
            'host': options['rabbitmq_host'],
            'port': options['rabbitmq_port'],
            'username': options['rabbitmq_user'],
            'password': options['rabbitmq_pass'],
        }
        
        if runtime_connector.start(rabbitmq_config):
            connector.enabled = True
            connector.save()
            self.stdout.write(self.style.SUCCESS(f"Started connector: {cid}"))
        else:
            raise CommandError(f"Failed to start connector: {cid}")

    def stop_connector(self, options):
        """Stop a Fake DLR connector"""
        cid = options.get('cid')
        
        if not cid:
            raise CommandError('--cid is required')
        
        try:
            connector = FakeDLRConnectorModel.objects.get(cid=cid)
        except FakeDLRConnectorModel.DoesNotExist:
            raise CommandError(f"Connector '{cid}' not found")
        
        # Stop runtime connector
        runtime_connector = get_fake_dlr_connector(connector.cid)
        if runtime_connector:
            runtime_connector.stop()
        
        connector.enabled = False
        connector.save()
        
        self.stdout.write(self.style.SUCCESS(f"Stopped connector: {cid}"))

    def delete_connector(self, options):
        """Delete a Fake DLR connector"""
        cid = options.get('cid')
        
        if not cid:
            raise CommandError('--cid is required')
        
        try:
            connector = FakeDLRConnectorModel.objects.get(cid=cid)
        except FakeDLRConnectorModel.DoesNotExist:
            raise CommandError(f"Connector '{cid}' not found")
        
        # Unregister from runtime
        unregister_fake_dlr_connector(connector.cid)
        
        # Delete from database
        connector.delete()
        
        self.stdout.write(self.style.SUCCESS(f"Deleted connector: {cid}"))

    def show_statistics(self):
        """Show routing statistics"""
        router = get_fake_dlr_router()
        stats = router.get_statistics()
        
        self.stdout.write(self.style.SUCCESS('\n=== Fake DLR Statistics ===\n'))
        
        # Route statistics
        if stats['routes']:
            self.stdout.write(self.style.SUCCESS('Routes:'))
            self.stdout.write('-' * 100)
            header = f"{'Order':<8} {'Name':<25} {'Total':<10} {'Fake':<10} {'Real':<10} {'Actual%':<10}"
            self.stdout.write(header)
            self.stdout.write('-' * 100)
            
            for r in stats['routes']:
                row = (f"{r['order']:<8} {r['name']:<25} {r['total_messages']:<10} "
                      f"{r['fake_dlr_messages']:<10} {r['real_messages']:<10} "
                      f"{r['actual_fake_percentage']:.2f}%")
                self.stdout.write(row)
            
            self.stdout.write('-' * 100)
        
        # Connector statistics
        if stats['connectors']:
            self.stdout.write(self.style.SUCCESS('\nConnectors:'))
            self.stdout.write('-' * 100)
            header = f"{'CID':<15} {'Name':<25} {'Total':<10} {'Delivered':<12} {'Failed':<10} {'Rate%':<10}"
            self.stdout.write(header)
            self.stdout.write('-' * 100)
            
            for c in stats['connectors']:
                row = (f"{c['cid']:<15} {c['name']:<25} {c['total_messages']:<10} "
                      f"{c['delivered_count']:<12} {c['failed_count']:<10} "
                      f"{c['delivery_rate']:.2f}%")
                self.stdout.write(row)
            
            self.stdout.write('-' * 100)

    def init_demo(self):
        """Initialize demo configuration"""
        self.stdout.write(self.style.SUCCESS('Initializing Fake DLR demo configuration...'))
        
        # Create demo connectors
        connectors = [
            {
                'cid': 'fake_demo_high',
                'name': 'Demo High Success',
                'success_rate': 98,
                'min_delay': 3,
                'max_delay': 10,
            },
            {
                'cid': 'fake_demo_medium',
                'name': 'Demo Medium Success',
                'success_rate': 85,
                'min_delay': 5,
                'max_delay': 15,
            },
            {
                'cid': 'fake_demo_instant',
                'name': 'Demo Instant',
                'success_rate': 100,
                'instant_response': True,
            },
        ]
        
        for conn_data in connectors:
            cid = conn_data['cid']
            if not FakeDLRConnectorModel.objects.filter(cid=cid).exists():
                connector = FakeDLRConnectorModel.objects.create(**conn_data, enabled=True)
                register_fake_dlr_connector(connector.cid, connector.get_config())
                self.stdout.write(f"  Created connector: {cid}")
            else:
                self.stdout.write(f"  Connector already exists: {cid}")
        
        self.stdout.write(self.style.SUCCESS('\nDemo configuration initialized!'))
        self.stdout.write('\nNext steps:')
        self.stdout.write('1. Create routes in Django Admin')
        self.stdout.write('2. Configure traffic splitting percentages')
        self.stdout.write('3. Start connectors with: python manage.py fake_dlr start_connector --cid=fake_demo_high')
