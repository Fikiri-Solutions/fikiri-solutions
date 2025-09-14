#!/usr/bin/env python3
"""
Fikiri Solutions - Google Colab Setup Script
Quick setup script for Google Colab environment.
"""

import subprocess
import sys
from pathlib import Path

def install_dependencies():
    """Install required dependencies."""
    print("📦 Installing dependencies...")
    
    try:
        # Install from requirements.txt
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Dependencies installed successfully!")
            return True
        else:
            print(f"❌ Failed to install dependencies: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def setup_environment():
    """Set up the environment."""
    print("🔧 Setting up environment...")
    
    # Create auth directory if it doesn't exist
    auth_dir = Path("auth")
    auth_dir.mkdir(exist_ok=True)
    print("✅ Auth directory created")
    
    # Create data directory if it doesn't exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    print("✅ Data directory created")
    
    return True

def main():
    """Main setup function."""
    print("🚀 Fikiri Solutions - Google Colab Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("main.py").exists():
        print("❌ main.py not found. Please run this script from the Fikiri directory.")
        return
    
    # Setup environment
    if not setup_environment():
        print("❌ Environment setup failed")
        return
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Dependency installation failed")
        return
    
    print("\n🎉 Setup completed successfully!")
    print("\n📝 Next steps:")
    print("1. Upload your Gmail API credentials to auth/credentials.json")
    print("2. Run: python main.py auth")
    print("3. Test with: python test_colab.py")

if __name__ == "__main__":
    main()
