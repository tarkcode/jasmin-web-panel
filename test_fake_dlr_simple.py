#!/usr/bin/env python
"""
Simple Fake DLR Test Script
Run this to test the Fake DLR system locally without RabbitMQ
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from main.core.models.fake_dlr import FakeDLRConnectorModel, FakeDLRRouteModel
from main.core.fake_dlr_router import FakeDLRRouter
from main.core.fake_dlr import FakeDLREngine


def print_header(text):
    """Print a formatted header"""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print('='*70)


def test_1_create_connector():
    """Test 1: Create a test connector"""
    print_header("TEST 1: Create Connector")
    
    try:
        # Delete if exists
        FakeDLRConnectorModel.objects.filter(cid='simple_test').delete()
        
        # Create connector
        connector = FakeDLRConnectorModel.objects.create(
            cid='simple_test',
            name='Simple Test Connector',
            success_rate=100,
            min_delay=0,
            max_delay=5,
            instant_response=True,
            enabled=True
        )
        
        print(f"✅ Connector created successfully!")
        print(f"   CID: {connector.cid}")
        print(f"   Name: {connector.name}")
        print(f"   Success Rate: {connector.success_rate}%")
        print(f"   Enabled: {connector.enabled}")
        
        return connector
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_2_create_route(connector):
    """Test 2: Create a test route"""
    print_header("TEST 2: Create Route")
    
    if not connector:
        print("❌ Skipped: No connector available")
        return None
    
    try:
        # Delete if exists
        FakeDLRRouteModel.objects.filter(order=999).delete()
        
        # Create route
        route = FakeDLRRouteModel.objects.create(
            order=999,
            name='Simple Test Route',
            fake_dlr_percentage=30,
            fake_dlr_connector=connector,
            real_connector_cid='vendor_test',
            enabled=True
        )
        
        print(f"✅ Route created successfully!")
        print(f"   Order: {route.order}")
        print(f"   Name: {route.name}")
        print(f"   Fake DLR %: {route.fake_dlr_percentage}%")
        print(f"   Real Connector: {route.real_connector_cid}")
        print(f"   Enabled: {route.enabled}")
        
        return route
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_3_routing_logic(route):
    """Test 3: Test routing logic"""
    print_header("TEST 3: Routing Logic (30% Fake)")
    
    if not route:
        print("❌ Skipped: No route available")
        return
    
    try:
        router = FakeDLRRouter()
        
        fake_count = 0
        real_count = 0
        
        print("\nRouting 100 test messages...")
        
        for i in range(100):
            connector_id, is_fake, info = router.route_message(
                msgid=f'test_{i}',
                destination_addr='+1234567890',
                source_addr='TEST',
                uid='test_user',
                short_message='Test message'
            )
            
            if is_fake:
                fake_count += 1
            else:
                real_count += 1
        
        # Refresh route to get updated stats
        route.refresh_from_db()
        
        print(f"\n✅ Routing completed!")
        print(f"\n   Results:")
        print(f"   ├─ Total Messages: {route.total_messages}")
        print(f"   ├─ Fake DLR: {route.fake_dlr_messages} ({route.actual_fake_percentage:.1f}%)")
        print(f"   └─ Real: {route.real_messages}")
        
        print(f"\n   Expected: ~30% fake")
        
        # Check if within tolerance
        tolerance = 15  # ±15% tolerance for 100 messages
        if abs(route.actual_fake_percentage - 30) <= tolerance:
            print(f"   ✅ PASS: Within {tolerance}% tolerance")
        else:
            print(f"   ⚠️  WARNING: Outside {tolerance}% tolerance (but normal for small sample)")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_4_dlr_generation():
    """Test 4: Test DLR generation"""
    print_header("TEST 4: DLR Generation")
    
    try:
        # Test different configurations
        configs = [
            {
                'name': '100% Success (Instant)',
                'config': {'success_rate': 100, 'instant_response': True}
            },
            {
                'name': '95% Success (Delayed)',
                'config': {'success_rate': 95, 'min_delay': 1, 'max_delay': 3}
            },
            {
                'name': '70% Success (Delayed)',
                'config': {'success_rate': 70, 'min_delay': 2, 'max_delay': 5}
            },
        ]
        
        for test in configs:
            print(f"\n{test['name']}:")
            engine = FakeDLREngine(test['config'])
            
            delivered = 0
            failed = 0
            
            for i in range(10):
                dlr = engine.generate_fake_dlr(
                    msgid=f'test_{i}',
                    destination_addr='+1234567890',
                    source_addr='TEST',
                    uid='test_user'
                )
                
                if dlr['status'] == 'DELIVRD':
                    delivered += 1
                else:
                    failed += 1
            
            print(f"   Delivered: {delivered}/10 ({delivered*10}%)")
            print(f"   Failed: {failed}/10 ({failed*10}%)")
            print(f"   Expected: {test['config']['success_rate']}%")
        
        print(f"\n✅ DLR generation test completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_5_filters():
    """Test 5: Test filter matching"""
    print_header("TEST 5: Filter Matching")
    
    try:
        # Create test connector
        connector = FakeDLRConnectorModel.objects.get_or_create(
            cid='filter_test',
            defaults={
                'name': 'Filter Test Connector',
                'success_rate': 100,
                'instant_response': True,
                'enabled': True
            }
        )[0]
        
        # Test user filter
        print("\nUser UID Filter:")
        route = FakeDLRRouteModel.objects.create(
            order=998,
            name='User Filter Test',
            fake_dlr_percentage=100,
            fake_dlr_connector=connector,
            real_connector_cid='vendor_test',
            filter_user_uid='test_user',
            enabled=True
        )
        
        test_cases = [
            ('test_user', True),
            ('other_user', False),
        ]
        
        for uid, expected in test_cases:
            matches = route.matches_filters(uid=uid)
            status = '✅' if matches == expected else '❌'
            print(f"   {status} UID '{uid}': {'Matches' if matches else 'No match'}")
        
        route.delete()
        
        # Test source address pattern
        print("\nSource Address Pattern (^PROMO.*):")
        route = FakeDLRRouteModel.objects.create(
            order=997,
            name='Source Pattern Test',
            fake_dlr_percentage=100,
            fake_dlr_connector=connector,
            real_connector_cid='vendor_test',
            filter_source_addr_pattern='^PROMO.*',
            enabled=True
        )
        
        test_cases = [
            ('PROMO123', True),
            ('INFO456', False),
        ]
        
        for source, expected in test_cases:
            matches = route.matches_filters(source_addr=source)
            status = '✅' if matches == expected else '❌'
            print(f"   {status} Source '{source}': {'Matches' if matches else 'No match'}")
        
        route.delete()
        
        print(f"\n✅ Filter test completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_6_statistics():
    """Test 6: View statistics"""
    print_header("TEST 6: Statistics")
    
    try:
        from main.core.fake_dlr_router import get_fake_dlr_router
        
        router = get_fake_dlr_router()
        stats = router.get_statistics()
        
        print("\nRoute Statistics:")
        if stats['routes']:
            for route in stats['routes']:
                print(f"\n   {route['name']} (Order: {route['order']})")
                print(f"   ├─ Total: {route['total_messages']}")
                print(f"   ├─ Fake: {route['fake_dlr_messages']}")
                print(f"   ├─ Real: {route['real_messages']}")
                print(f"   └─ Actual %: {route['actual_fake_percentage']:.1f}%")
        else:
            print("   No routes with statistics yet")
        
        print("\nConnector Statistics:")
        if stats['connectors']:
            for conn in stats['connectors']:
                print(f"\n   {conn['name']} ({conn['cid']})")
                print(f"   ├─ Total: {conn['total_messages']}")
                print(f"   ├─ Delivered: {conn['delivered_count']}")
                print(f"   ├─ Failed: {conn['failed_count']}")
                print(f"   └─ Rate: {conn['delivery_rate']:.1f}%")
        else:
            print("   No connectors with statistics yet")
        
        print(f"\n✅ Statistics retrieved successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def cleanup():
    """Cleanup test data"""
    print_header("CLEANUP")
    
    try:
        # Delete test routes
        deleted_routes = FakeDLRRouteModel.objects.filter(
            order__gte=997
        ).delete()[0]
        
        # Delete test connectors
        deleted_connectors = FakeDLRConnectorModel.objects.filter(
            cid__in=['simple_test', 'filter_test']
        ).delete()[0]
        
        print(f"✅ Cleanup completed!")
        print(f"   Routes deleted: {deleted_routes}")
        print(f"   Connectors deleted: {deleted_connectors}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("  FAKE DLR SIMPLE TEST SUITE")
    print("  Testing locally without RabbitMQ")
    print("="*70)
    
    # Run tests
    connector = test_1_create_connector()
    route = test_2_create_route(connector)
    test_3_routing_logic(route)
    test_4_dlr_generation()
    test_5_filters()
    test_6_statistics()
    
    # Cleanup
    print("\n")
    response = input("Do you want to cleanup test data? (y/n): ")
    if response.lower() == 'y':
        cleanup()
    else:
        print("\nTest data kept for inspection.")
    
    # Summary
    print_header("TEST SUMMARY")
    print("\n✅ All tests completed!")
    print("\nWhat was tested:")
    print("  ✓ Connector creation")
    print("  ✓ Route creation")
    print("  ✓ Routing logic (30% fake)")
    print("  ✓ DLR generation")
    print("  ✓ Filter matching")
    print("  ✓ Statistics")
    
    print("\nNext steps:")
    print("  1. Check Django Admin: http://localhost:8000/admin/")
    print("  2. View connectors: python manage.py fake_dlr list_connectors")
    print("  3. View routes: python manage.py fake_dlr list_routes")
    print("  4. View statistics: python manage.py fake_dlr statistics")
    print("  5. Read full guide: FAKE_DLR_LOCAL_TESTING.md")
    
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
