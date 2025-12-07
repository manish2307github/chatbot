"""
Simple Neo4j Sandbox Connection Test
No complex imports - just the basics
"""

from neo4j import GraphDatabase

# Your sandbox credentials
URI = "bolt://3.83.182.137:7687"
USERNAME = "neo4j"
PASSWORD = "alternation-flaps-trigger"

print("=" * 60)
print("Neo4j Sandbox Connection Test")
print("=" * 60)
print(f"URI: {URI}")
print(f"User: {USERNAME}")
print()

try:
    print("Attempting connection...")
    
    # Create driver with minimal config
    driver = GraphDatabase.driver(
        URI,
        auth=(USERNAME, PASSWORD)
    )
    
    print("✓ Driver created")
    
    # Test the connection
    print("Testing connection...")
    with driver.session() as session:
        result = session.run("RETURN 'Connection successful!' as message")
        record = result.single()
        
        if record:
            print(f"✓ {record['message']}")
        else:
            print("✗ No response from database")
    
    # Test write capability
    print("Testing write capability...")
    with driver.session() as session:
        session.run("""
            CREATE (test:TestNode {
                message: 'Test successful',
                timestamp: datetime()
            })
        """)
        print("✓ Successfully wrote to database")
    
    # Close driver
    driver.close()
    print()
    print("=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    print()
    print("Your Neo4j Sandbox connection is working correctly.")
    print("You can now run the chatbot application.")
    
except Exception as e:
    print()
    print("=" * 60)
    print("✗ CONNECTION FAILED")
    print("=" * 60)
    print(f"Error: {e}")
    print()
    print("Troubleshooting steps:")
    print()
    print("1. Verify your credentials:")
    print(f"   - URI: {URI}")
    print(f"   - User: {USERNAME}")
    print(f"   - Check password is correct (case-sensitive)")
    print()
    print("2. Check if sandbox instance is running:")
    print("   - Visit https://sandbox.neo4j.com/")
    print("   - Ensure your instance is not paused")
    print()
    print("3. Try alternative URI scheme:")
    print("   - Change to: neo4j+ssc://6455f144f7180dbd52fcbb0657fda1d4.neo4jsandbox.com")
    print("   - (ssc = skip certificate verification)")
    print()
    print("4. Check firewall/network:")
    print("   - Ensure you can access neo4jsandbox.com")
    print()
    print("Full error details:")
    print(f"   Type: {type(e).__name__}")
    print(f"   Message: {str(e)}")