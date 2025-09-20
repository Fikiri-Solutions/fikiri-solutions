#!/usr/bin/env python3
"""
Test OpenAI Integration with Sentry Monitoring
Demonstrates how Sentry captures LLM interactions and performance
"""

import sentry_sdk
from openai import OpenAI
import os
import time

# Initialize Sentry with enhanced configuration
sentry_sdk.init(
    dsn="https://05d4170350ee081a3bfee0dda0220df6@o4510053728845824.ingest.us.sentry.io/4510053767249920",
    traces_sample_rate=1.0,
    # Add data like inputs and responses to/from LLMs and tools;
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
)

def test_openai_with_sentry():
    """Test OpenAI API call with Sentry monitoring"""
    
    # Log the start of the operation
    sentry_sdk.logger.info("Starting OpenAI API test")
    
    try:
        # Initialize OpenAI client
        client = OpenAI()
        
        # Start a Sentry transaction to track the API call
        with sentry_sdk.start_transaction(op="openai", name="chat_completion") as transaction:
            # Add context about the API call
            transaction.set_tag("model", "gpt-4o-mini")
            transaction.set_tag("service", "openai")
            
            # Log the request
            sentry_sdk.logger.info("Making OpenAI API request")
            
            # Make the API call
            start_time = time.time()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Tell me a joke"}],
            )
            end_time = time.time()
            
            # Calculate duration
            duration = end_time - start_time
            
            # Add performance data to transaction
            transaction.set_data("duration_ms", duration * 1000)
            transaction.set_data("model", "gpt-4o-mini")
            transaction.set_data("tokens_used", response.usage.total_tokens if response.usage else 0)
            
            # Log the response
            sentry_sdk.logger.info(f"OpenAI API call completed in {duration:.2f}s")
            sentry_sdk.logger.info(f"Response: {response.choices[0].message.content}")
            
            # Print the response
            print(f"OpenAI Response: {response.choices[0].message.content}")
            
            # Log success
            sentry_sdk.logger.info("OpenAI API test completed successfully")
            
            return response.choices[0].message.content
            
    except Exception as e:
        # Log the error
        sentry_sdk.logger.error(f"OpenAI API call failed: {str(e)}")
        
        # Capture the exception in Sentry
        sentry_sdk.capture_exception(e)
        
        # Re-raise the exception
        raise

def test_error_scenario():
    """Test error handling with Sentry"""
    
    try:
        # This will cause an error
        sentry_sdk.logger.info("Testing error scenario")
        
        # Simulate an error
        raise ValueError("This is a test error for Sentry monitoring")
        
    except Exception as e:
        # Log the error
        sentry_sdk.logger.error(f"Error scenario test: {str(e)}")
        
        # Capture the exception
        sentry_sdk.capture_exception(e)
        
        print(f"Error captured: {str(e)}")

if __name__ == "__main__":
    print("🚀 Testing OpenAI Integration with Sentry Monitoring")
    print("=" * 50)
    
    # Test successful API call
    try:
        result = test_openai_with_sentry()
        print(f"✅ Success: {result}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    print("\n" + "=" * 50)
    
    # Test error scenario
    test_error_scenario()
    
    print("\n🎯 Check your Sentry dashboard for:")
    print("- Performance transactions")
    print("- Log messages")
    print("- Error events")
    print("- LLM interaction data")
