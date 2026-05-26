#!/usr/bin/env python
"""
SMPP Connectivity Test Script
Tests all aspects of SMPP functionality after Fake DLR deployment
"""

import sys
import os

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.pro')
import django
django.setup()

from main.core.smpp.smppccm import SMPPCCM
from main.core.smpp.conn import TelnetConnection

def test_telnet_connection():
    """Test basic telnet connection to Jasmin"""
    print("=" * 60)
    print("TEST 1: Telnet Connection to Jasmin")
    print("=" * 60)
    try:
        conn = TelnetConnection()
        print("✅ Successfully connected to Jasmin telnet")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to Jasmin telnet: {e}")
        return False

def test_smpp_connector_list():
    """Test listing SMPP connectors"""
    print("\n" + "=" * 60)
    print("TEST 2: List SMPP Connectors")
    print("=" * 60)
    try:
        smpp = SMPPCCM()
        connectors = smpp.get_connector_list()
        print(f"✅ Successfully retrieved connector list")
        print(f"   Total connectors: {len(connectors)}")
        
        if connectors:
            print("\n   Connector Details:")
            for i, conn in enumerate(connectors, 1):
                print(f"   {i}. {conn}")
        else:
            print("   ⚠️  No connectors configured")
        
        return True
    except Exception as e:
        print(f"❌ Failed to list connectors: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_smpp_connector_details():
    """Test getting specific connector details"""
    print("\n" + "=" * 60)
    print("TEST 3: Get Connector Details")
    print("=" * 60)
    try:
        smpp = SMPPCCM()
        connectors = smpp.get_connector_list()
        
        if not connectors:
            print("⚠️  No connectors to test")
            return True
        
        # Get first connector CID
        cid = connectors[0][0] if isinstance(connectors[0], list) else connectors[0]
        print(f"   Testing connector: {cid}")
        
        details = smpp.get_smppccm(cid)
        print(f"✅ Successfully retrieved connector details")
        print(f"   Details: {details}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to get connector details: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fake_dlr_models():
    """Test Fake DLR models are accessible"""
    print("\n" + "=" * 60)
    print("TEST 4: Fake DLR Models")
    print("=" * 60)
    try:
        from main.core.models import FakeDLRConnectorModel, FakeDLRRouteModel
        
        connector_count = FakeDLRConnectorModel.objects.count()
        route_count = FakeDLRRouteModel.objects.count()
        
        print(f"✅ Fake DLR models are accessible")
        print(f"   Fake DLR Connectors: {connector_count}")
        print(f"   Fake DLR Routes: {route_count}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to access Fake DLR models: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_tables():
    """Test database tables exist"""
    print("\n" + "=" * 60)
    print("TEST 5: Database Tables")
    print("=" * 60)
    try:
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Check SMPP table
            cursor.execute("SELECT COUNT(*) FROM tbl_smppccm")
            smpp_count = cursor.fetchone()[0]
            print(f"✅ tbl_smppccm exists: {smpp_count} records")
            
            # Check Fake DLR tables
            cursor.execute("SELECT COUNT(*) FROM tbl_fake_dlr_connectors")
            fake_conn_count = cursor.fetchone()[0]
            print(f"✅ tbl_fake_dlr_connectors exists: {fake_conn_count} records")
            
            cursor.execute("SELECT COUNT(*) FROM tbl_fake_dlr_routes")
            fake_route_count = cursor.fetchone()[0]
            print(f"✅ tbl_fake_dlr_routes exists: {fake_route_count} records")
        
        return True
    except Exception as e:
        print(f"❌ Database table check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_smpp_port():
    """Test SMPP port is listening"""
    print("\n" + "=" * 60)
    print("TEST 6: SMPP Port Connectivity")
    print("=" * 60)
    try:
        import socket
        
        # Test SMPP port 2775
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('jasmin', 2775))
        sock.close()
        
        if result == 0:
            print("✅ SMPP port 2775 is listening and accepting connections")
            return True
        else:
            print(f"❌ SMPP port 2775 is not accessible (error code: {result})")
            return False
    except Exception as e:
        print(f"❌ Failed to test SMPP port: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("SMPP CONNECTIVITY TEST SUITE")
    print("Testing SMPP functionality after Fake DLR deployment")
    print("=" * 60)
    
    results = []
    
    # Run all tests
    results.append(("Telnet Connection", test_telnet_connection()))
    results.append(("SMPP Connector List", test_smpp_connector_list()))
    results.append(("SMPP Connector Details", test_smpp_connector_details()))
    results.append(("Fake DLR Models", test_fake_dlr_models()))
    results.append(("Database Tables", test_database_tables()))
    results.append(("SMPP Port", test_smpp_port()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! SMPP is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
