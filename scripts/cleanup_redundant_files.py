#!/usr/bin/env python3
"""
Cleanup Redundant Files Script
Identifies and optionally removes redundant/duplicate files
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# Files to remove (confirmed redundant)
FILES_TO_REMOVE = [
    "app_original_backup.py",
    "CLEANUP_REPORT.md",
    "FINAL_SESSION_VERIFICATION_REPORT.md",
    "GITHUB_HISTORY_CLEANUP.md",
    "QUICK_START_CLEANUP.md",
    "MOBILE_RESPONSIVENESS_REPORT.md",
    "UX_ENHANCEMENT_SUMMARY.md",
    "ONBOARDING_LOGIC_IMPLEMENTATION.md",
    "GOOGLE_OAUTH_CONFIG.md",  # Duplicate of docs/GOOGLE_OAUTH_SETUP.md
    "OAUTH_CLIENT_SETUP.md",   # Duplicate/merge candidate
    "frontend/BUG_REPORT.md",
    "frontend/INTEGRATION_TEST.md",  # Merge into TESTING_CHECKLIST
]

# Files to archive (move to archive/ instead of delete)
FILES_TO_ARCHIVE = [
    # Historical reports that might be useful for reference
]

def create_archive_directory():
    """Create archive directory if it doesn't exist"""
    archive_dir = Path("archive")
    archive_dir.mkdir(exist_ok=True)
    return archive_dir

def remove_file(filepath, dry_run=True):
    """Remove a file (or report if dry_run)"""
    path = Path(filepath)
    if not path.exists():
        print(f"⚠️  File not found: {filepath}")
        return False
    
    if dry_run:
        print(f"📋 Would remove: {filepath}")
        return True
    else:
        try:
            path.unlink()
            print(f"✅ Removed: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Error removing {filepath}: {e}")
            return False

def archive_file(filepath, archive_dir, dry_run=True):
    """Archive a file (or report if dry_run)"""
    path = Path(filepath)
    if not path.exists():
        print(f"⚠️  File not found: {filepath}")
        return False
    
    archive_path = archive_dir / path.name
    
    if dry_run:
        print(f"📦 Would archive: {filepath} → archive/{path.name}")
        return True
    else:
        try:
            shutil.move(str(path), str(archive_path))
            print(f"✅ Archived: {filepath} → archive/{path.name}")
            return True
        except Exception as e:
            print(f"❌ Error archiving {filepath}: {e}")
            return False

def main():
    """Main cleanup function"""
    import sys
    
    # Check for --execute flag
    dry_run = "--execute" not in sys.argv
    
    if dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
        print("   Add --execute flag to actually remove files\n")
    else:
        print("⚠️  EXECUTE MODE - Files will be removed!")
        response = input("Continue? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            return
    
    archive_dir = create_archive_directory()
    
    print("\n" + "="*60)
    print("FILE CLEANUP REPORT")
    print("="*60 + "\n")
    
    removed_count = 0
    archived_count = 0
    not_found_count = 0
    
    # Remove redundant files
    print("📋 Removing Redundant Files:")
    print("-" * 60)
    for filepath in FILES_TO_REMOVE:
        if remove_file(filepath, dry_run=dry_run):
            removed_count += 1
        else:
            not_found_count += 1
    
    # Archive files
    print("\n📦 Archiving Files:")
    print("-" * 60)
    for filepath in FILES_TO_ARCHIVE:
        if archive_file(filepath, archive_dir, dry_run=dry_run):
            archived_count += 1
        else:
            not_found_count += 1
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"✅ Files to remove: {removed_count}")
    print(f"📦 Files to archive: {archived_count}")
    print(f"⚠️  Files not found: {not_found_count}")
    
    if dry_run:
        print("\n💡 Run with --execute flag to perform cleanup")
    else:
        print("\n✅ Cleanup completed!")

if __name__ == "__main__":
    main()





