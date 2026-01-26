"""
Test Warning System
Submits various reports to test warning levels
Run: python test_warnings.py
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5000/api/v1"

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def submit_report(node_id, date, fever, cough, gi, description):
    """Submit a report and display results"""
    print(f"📊 {description}")
    print(f"   Symptoms: Fever={fever}, Cough={cough}, GI={gi}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/node/report",
            json={
                "node_id": node_id,
                "token": "test_token",
                "date": date,
                "symptoms": {
                    "fever": fever,
                    "cough": cough,
                    "gi": gi
                }
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data["success"]:
                report_data = data["data"]
                print(f"   ✅ Status: {report_data['validation_status']}")
                print(f"   🔢 Suspicion Score: {report_data['suspicion_score']}")
                print(f"   🚩 Requires Review: {report_data['requires_review']}")
                
                if report_data['warnings']:
                    print(f"   ⚠️  Warnings ({len(report_data['warnings'])}):")
                    for warning in report_data['warnings']:
                        severity_emoji = {
                            'HIGH': '🔴',
                            'MEDIUM': '🟡',
                            'LOW': '🟢'
                        }.get(warning['severity'], '⚪')
                        print(f"      {severity_emoji} [{warning['severity']}] {warning['message']}")
                        if 'suggestion' in warning:
                            print(f"         💡 {warning['suggestion']}")
                else:
                    print("   ✅ No warnings")
            else:
                print(f"   ❌ Failed: {data.get('error', {}).get('message', 'Unknown error')}")
        else:
            print(f"   ❌ HTTP {response.status_code}: {response.text[:100]}")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()


def test_warning_system():
    """Run comprehensive warning tests"""
    
    print_section("🧪 BioHIVE Warning System Test Suite")
    
    today = datetime.now().date().isoformat()
    yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
    week_ago = (datetime.now().date() - timedelta(days=7)).isoformat()
    
    # Test 1: Normal values (no warnings)
    print_section("Test Group 1: Normal Values")
    submit_report("clinic_1", today, 5, 8, 3, "Normal day - should have no warnings")
    
    # Test 2: Slightly elevated (low warnings)
    print_section("Test Group 2: Slightly Elevated (Low Warnings)")
    submit_report("clinic_2", today, 35, 35, 18, "Moderately busy day - should trigger LOW warnings")
    
    # Test 3: High values (medium warnings)
    print_section("Test Group 3: High Values (Medium Warnings)")
    submit_report("clinic_3", today, 60, 65, 35, "Very busy day - should trigger MEDIUM warnings")
    
    # Test 4: Extremely high values (high warnings)
    print_section("Test Group 4: Extremely High Values (High Warnings)")
    submit_report("clinic_4", today, 120, 150, 70, "Outbreak levels - should trigger HIGH warnings")
    
    # Test 5: Spike detection
    print_section("Test Group 5: Spike Detection")
    submit_report("clinic_5", yesterday, 10, 15, 5, "Baseline day")
    submit_report("clinic_5", today, 50, 60, 25, "Sudden spike - should detect spike warnings")
    
    # Test 6: All zeros
    print_section("Test Group 6: All Zeros")
    submit_report("clinic_6", today, 0, 0, 0, "No cases - should warn about zero values")
    
    # Test 7: Old data
    print_section("Test Group 7: Old Data")
    submit_report("clinic_7", week_ago, 10, 12, 5, "Week-old data - should warn about date")
    
    # Test 8: Round numbers
    print_section("Test Group 8: Suspicious Round Numbers")
    submit_report("clinic_8", today, 50, 60, 20, "Round numbers - should flag as suspicious")
    
    # Test 9: Extreme spike
    print_section("Test Group 9: Extreme Spike")
    submit_report("clinic_1", yesterday, 5, 8, 2, "Normal baseline")
    submit_report("clinic_1", today, 100, 150, 40, "10x+ spike - should trigger HIGH spike warnings")
    
    # Summary
    print_section("📋 Test Summary")
    print("All tests completed!")
    print("\n💡 Check results above to verify warning system")
    print("🔍 View flagged reports: GET /api/v1/node/flagged")
    print("📊 View node status: GET /api/v1/node/status")


def check_flagged_reports():
    """Check flagged reports endpoint"""
    print_section("🚩 Checking Flagged Reports")
    
    try:
        response = requests.get(f"{BASE_URL}/node/flagged")
        
        if response.status_code == 200:
            data = response.json()["data"]
            flagged = data["flagged_reports"]
            
            print(f"Found {len(flagged)} flagged report(s)\n")
            
            for i, report in enumerate(flagged, 1):
                print(f"{i}. Node: {report['node_name']} ({report['node_id']})")
                print(f"   Date: {report['date']}")
                print(f"   Symptoms: {report['symptoms']}")
                print(f"   🔢 Suspicion Score: {report['suspicion_score']}")
                print()
        else:
            print(f"❌ Failed to get flagged reports: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("\n" + "🔬" * 35)
    print("Starting Warning System Tests...")
    print("🔬" * 35)
    
    # Run tests
    test_warning_system()
    
    # Check flagged reports
    check_flagged_reports()
    
    print("\n✅ Testing complete!\n")